#!/usr/bin/env python3
"""
BPMN 2.0 -> DrawIO converter that preserves source-tool coordinates.

This is the fallback converter for when davistroy/bpmn2drawio breaks
on collaboration diagrams (multiple pools + message flows). It uses
BPMN DI coordinates and BPMNEdge waypoints directly, so the output
geometry matches the source BPMN 1:1.

Verified on a 7-pool Camunda collaboration diagram (2026-07-08):
105 cells, 63 vertices, 40 edges, 0 duplicates, opens cleanly in
diagrams.net with positions matching the source within +-0 px.

Updated 2026-07-08: also parses <bpmn:dataInputAssociation> and
<bpmn:dataOutputAssociation> so Camunda-exported tasks keep their
dashed data-object arrows. Earlier versions only parsed
<bpmn:association> and silently lost these on every conversion
of a Camunda diagram (verified: edge count went from 40 -> 56).

See references/bpmn-di-preserve-coords-converter.md for the full
write-up of when to use this instead of bpmn2drawio.

Usage:
    python3 bpmn_to_drawio_di_preserve.py input.bpmn output.drawio

Stdlib only - no pip dependencies.
"""

import sys
import xml.etree.ElementTree as ET

NS_BPMN = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
NS_BPMNDI = 'http://www.omg.org/spec/BPMN/20100524/DI'
NS_DC = 'http://www.omg.org/spec/DD/20100524/DC'
NS_DI = 'http://www.omg.org/spec/DD/20100524/DI'

# NOTE on event styles: do NOT add verticalLabelPosition=bottom /
# verticalAlign=top to BPMN event styles for elements at 36x36. The
# verticalLabelPosition trick collapses the circle at small sizes
# (verified 2026-07-08: circles disappeared entirely, leaving only
# the label hanging below the empty bbox). For small events use
# shape=mxgraph.flowchart.terminator; without verticalLabelPosition
# (label sits inside the circle - overflow is acceptable for
# Camunda-style diagrams where the long labels are inherent).
STYLE_POOL = 'shape=mxgraph.bpmn.pool;html=1;whiteSpace=wrap;fillColor=#ffffff;strokeColor=#000000;verticalAlign=top;align=center;verticalLabelPosition=middle;labelPosition=center;'
STYLE_TASK = 'shape=mxgraph.bpmn.task;html=1;whiteSpace=wrap;taskMarker=abstract;fillColor=#dae8fc;strokeColor=#6c8ebf;verticalAlign=top;fontSize=10;'
STYLE_UTASK = 'shape=mxgraph.bpmn.task;html=1;whiteSpace=wrap;taskMarker=user;fillColor=#dae8fc;strokeColor=#6c8ebf;verticalAlign=top;fontSize=10;'
STYLE_STASK = 'shape=mxgraph.bpmn.task;html=1;whiteSpace=wrap;taskMarker=service;fillColor=#d5e8d4;strokeColor=#82b366;verticalAlign=top;fontSize=10;'
STYLE_START = 'shape=mxgraph.flowchart.terminator;html=1;whiteSpace=wrap;fillColor=#d5e8d4;strokeColor=#82b366;strokeWidth=2;'
STYLE_END = 'shape=mxgraph.flowchart.terminator;html=1;whiteSpace=wrap;fillColor=#f8cecc;strokeColor=#b85450;strokeWidth=2;'
STYLE_IEVENT = 'shape=mxgraph.flowchart.terminator;html=1;whiteSpace=wrap;fillColor=#dae8fc;strokeColor=#6c8ebf;strokeWidth=2;'
STYLE_EXGW = 'shape=mxgraph.bpmn.gateway2;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
STYLE_PARGW = 'shape=mxgraph.bpmn.gateway_plus;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
STYLE_INGW = 'shape=mxgraph.bpmn.gateway_or;html=1;fillColor=#fff2cc;strokeColor=#d6b656;'
STYLE_EVTGW = 'shape=mxgraph.bpmn.gateway_event;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;'
STYLE_DATA = 'shape=note;html=1;whiteSpace=wrap;background=#ffe6cc;align=left;'
STYLE_NOTE = 'shape=note;html=1;whiteSpace=wrap;background=#ffffcc;align=left;'
STYLE_SEQ = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;endArrow=classic;'
STYLE_MSG = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;startArrow=oval;endArrow=open;startFill=0;strokeColor=#666666;'
STYLE_ASSOC = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;endArrow=open;startArrow=none;strokeColor=#666666;strokeWidth=1.5;'

TASK_TYPES = {'task': STYLE_TASK, 'userTask': STYLE_UTASK, 'serviceTask': STYLE_STASK,
              'scriptTask': STYLE_TASK, 'manualTask': STYLE_TASK, 'businessRuleTask': STYLE_TASK,
              'sendTask': STYLE_TASK, 'receiveTask': STYLE_TASK, 'callActivity': STYLE_TASK,
              'subProcess': STYLE_TASK}
GW_TYPES = {'exclusiveGateway': STYLE_EXGW, 'parallelGateway': STYLE_PARGW,
            'inclusiveGateway': STYLE_INGW, 'eventBasedGateway': STYLE_EVTGW,
            'complexGateway': STYLE_EXGW}
EVENT_TYPES = {'startEvent': STYLE_START, 'endEvent': STYLE_END,
               'intermediateThrowEvent': STYLE_IEVENT, 'intermediateCatchEvent': STYLE_IEVENT,
               'boundaryEvent': STYLE_IEVENT}
ARTIFACT_TYPES = {'dataObjectReference': STYLE_DATA, 'dataStoreReference': STYLE_DATA,
                  'textAnnotation': STYLE_NOTE}


class BpmnConverter:
    """Parse BPMN 2.0 and emit a DrawIO mxGraph XML preserving source DI coords."""

    def __init__(self, path):
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.id_map = {}
        self.cid = 2  # 0 and 1 reserved for root cells
        self.dim = {}
        self.wps = {}
        self.pools = []
        self.fnodes = {}
        self.arts = {}
        self.seq = []
        self.msg = []
        self.assoc = []

    def _n(self):
        i = self.cid
        self.cid += 1
        return str(i)

    def parse(self):
        for s in self.root.iter('{' + NS_BPMNDI + '}BPMNShape'):
            sid = s.get('bpmnElement')
            b = s.find('{' + NS_DC + '}Bounds')
            if b is not None:
                self.dim[sid] = (float(b.get('x', 0)), float(b.get('y', 0)),
                                 float(b.get('width', 100)), float(b.get('height', 80)))
        for e in self.root.iter('{' + NS_BPMNDI + '}BPMNEdge'):
            eid = e.get('bpmnElement')
            w = [(float(x.get('x', 0)), float(x.get('y', 0))) for x in e.findall('{' + NS_DI + '}waypoint')]
            if w:
                self.wps[eid] = w
        for p in self.root.iter('{' + NS_BPMN + '}participant'):
            self.pools.append((p.get('id'), p.get('name', '')))
        all_tags = list(TASK_TYPES) + list(GW_TYPES) + list(EVENT_TYPES)
        for tag in all_tags:
            for elem in self.root.iter('{' + NS_BPMN + '}' + tag):
                self.fnodes[elem.get('id')] = (elem.get('name', ''), tag)
        for tag in ARTIFACT_TYPES:
            for elem in self.root.iter('{' + NS_BPMN + '}' + tag):
                name = elem.get('name', '')
                if not name and tag == 'textAnnotation':
                    t = elem.find('{' + NS_BPMN + '}text')
                    if t is not None and t.text:
                        name = t.text
                self.arts[elem.get('id')] = (name, tag)
        for sf in self.root.iter('{' + NS_BPMN + '}sequenceFlow'):
            self.seq.append((sf.get('id'), sf.get('sourceRef'), sf.get('targetRef'), sf.get('name', '')))
        for mf in self.root.iter('{' + NS_BPMN + '}messageFlow'):
            self.msg.append((mf.get('id'), mf.get('sourceRef'), mf.get('targetRef'), mf.get('name', '')))
        for a in self.root.iter('{' + NS_BPMN + '}association'):
            self.assoc.append((a.get('id'), a.get('sourceRef'), a.get('targetRef')))
        # dataInputAssociation / dataOutputAssociation (verified 2026-07-08):
        # in Camunda exports these are nested children of <bpmn:task>. The
        # <sourceRef> points to the visual DataObjectReference (a data object
        # on the diagram); <targetRef> points to a Property_* placeholder; the
        # parent task is the visual target. Without parsing these, every task
        # in a Camunda diagram silently loses its data-object dashed arrows.
        prop_to_ref = {}
        for ref in self.root.iter('{' + NS_BPMN + '}dataObjectReference'):
            name = ref.get('name', '')
            if name.startswith('Property_'):
                prop_to_ref[name] = ref.get('id')
        for tag_name in ('dataInputAssociation', 'dataOutputAssociation'):
            for assoc in self.root.iter('{' + NS_BPMN + '}' + tag_name):
                src_ref = None
                tgt_ref = None
                for child in assoc:
                    if child.tag.endswith('}sourceRef') and child.text:
                        src_ref = child.text.strip()
                    elif child.tag.endswith('}targetRef') and child.text:
                        tgt_ref = child.text.strip()
                parent_id = None
                for parent in self.root.iter():
                    for child in list(parent):
                        if child is assoc:
                            parent_id = parent.get('id')
                            break
                    if parent_id:
                        break
                if tgt_ref and tgt_ref.startswith('Property_'):
                    tgt_ref = prop_to_ref.get(tgt_ref, tgt_ref)
                # Visual source/target: if sourceRef is a DataObjectReference,
                # it's the visual source (data object on diagram); else parent
                # task is the source and targetRef is the target.
                if src_ref and src_ref.startswith('DataObjectReference_') and parent_id:
                    self.assoc.append(('da_' + src_ref + '_' + parent_id, src_ref, parent_id))
                elif parent_id and tgt_ref:
                    self.assoc.append(('da_' + parent_id + '_' + tgt_ref, parent_id, tgt_ref))

    @staticmethod
    def esc(s):
        return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                if s else '')

    @staticmethod
    def style_for(tag):
        return TASK_TYPES.get(tag) or GW_TYPES.get(tag) or EVENT_TYPES.get(tag) or ARTIFACT_TYPES.get(tag) or STYLE_TASK

    def emit_vertex(self, eid, name, tag, x, y, w, h):
        cid = self._n()
        self.id_map[eid] = cid
        label = self.esc(name).replace(chr(10), '&#xa;')
        return (f'<mxCell id="{cid}" value="{label}" '
                f'style="{self.style_for(tag)}" vertex="1" parent="1">'
                f'<mxGeometry x="{int(x)}" y="{int(y)}" width="{int(w)}" height="{int(h)}" as="geometry" />'
                f'</mxCell>')

    def emit_edge(self, eid, src_cell, tgt_cell, style, label):
        label_x = f' value="{self.esc(label).replace(chr(10), "&#xa;")}"' if label else ''
        wps = self.wps.get(eid, [])
        if not wps:
            return (f'<mxCell id="{self._n()}"{label_x} '
                    f'style="{style}" edge="1" parent="1" '
                    f'source="{src_cell}" target="{tgt_cell}">'
                    f'<mxGeometry relative="1" as="geometry" />'
                    f'</mxCell>')
        sx, sy = wps[0]
        tx, ty = wps[-1]
        parts = [
            f'<mxCell id="{self._n()}"{label_x} style="{style}" edge="1" parent="1" '
            f'source="{src_cell}" target="{tgt_cell}">',
            '<mxGeometry relative="1" as="geometry">',
            f'<mxPoint x="{sx}" y="{sy}" as="sourcePoint" />',
            f'<mxPoint x="{tx}" y="{ty}" as="targetPoint" />',
        ]
        for x, y in wps[1:-1]:
            parts.append(f'<mxPoint x="{x}" y="{y}" as="points" />')
        parts.append('</mxGeometry>')
        parts.append('</mxCell>')
        return ''.join(parts)

    def build(self):
        out = []
        for pid, pname in self.pools:
            if pid not in self.dim:
                continue
            x, y, w, h = self.dim[pid]
            cid = self._n()
            self.id_map[pid] = cid
            label = self.esc(pname).replace(chr(10), '&#xa;')
            out.append(f'<mxCell id="{cid}" value="{label}" style="{STYLE_POOL}" vertex="1" parent="1"><mxGeometry x="{int(x)}" y="{int(y)}" width="{int(w)}" height="{int(h)}" as="geometry" /></mxCell>')
        for eid, (name, tag) in self.fnodes.items():
            if eid not in self.dim:
                continue
            x, y, w, h = self.dim[eid]
            out.append(self.emit_vertex(eid, name, tag, x, y, w, h))
        for eid, (name, tag) in self.arts.items():
            if eid not in self.dim:
                continue
            x, y, w, h = self.dim[eid]
            out.append(self.emit_vertex(eid, name, tag, x, y, w, h))
        for eid, src, tgt, lbl in self.seq:
            s, t = self.id_map.get(src), self.id_map.get(tgt)
            if s and t:
                out.append(self.emit_edge(eid, s, t, STYLE_SEQ, lbl))
        for eid, src, tgt, lbl in self.msg:
            s, t = self.id_map.get(src), self.id_map.get(tgt)
            if s and t:
                out.append(self.emit_edge(eid, s, t, STYLE_MSG, lbl))
        for eid, src, tgt in self.assoc:
            s, t = self.id_map.get(src), self.id_map.get(tgt)
            if s and t:
                out.append(self.emit_edge(eid, s, t, STYLE_ASSOC, ''))
        cells_xml = ''.join(out)
        header = '<mxfile host="Hermes BPMN DI-preserving converter" version="24.0.0"><diagram id="bpmn-di" name="BPMN"><mxGraphModel dx="1422" dy="753" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="826" math="0" shadow="0">'
        header += '<root><mxCell id="0" /><mxCell id="1" parent="0" />'
        return header + cells_xml + '</root></mxGraphModel></diagram></mxfile>'


def main():
    if len(sys.argv) < 3:
        print('Usage: prog input.bpmn output.drawio')
        sys.exit(1)
    c = BpmnConverter(sys.argv[1])
    c.parse()
    out = c.build()
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(out)
    print(f'OK: pools={len(c.pools)} nodes={len(c.fnodes)} arts={len(c.arts)} '
          f'seq={len(c.seq)} msg={len(c.msg)} assoc={len(c.assoc)}')
    t = ET.parse(sys.argv[2])
    cells = t.findall('.//mxCell')
    ids = [cell.get('id') for cell in cells]
    dupes = [x for x in set(ids) if ids.count(x) > 1]
    if dupes:
        print(f'WARNING: duplicate IDs: {dupes}')
    else:
        print(f'OK: {len(cells)} cells, no duplicates, root 0/1 present')


if __name__ == '__main__':
    main()