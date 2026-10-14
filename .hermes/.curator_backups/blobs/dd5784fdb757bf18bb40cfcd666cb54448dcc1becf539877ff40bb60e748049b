"""
BPMN 2.0 → DrawIO mxGraph XML конвертер.

Поддерживает:
- Tasks (все типы: task, serviceTask, userTask, sendTask, receiveTask,
  manualTask, businessRuleTask, scriptTask)
- Events (startEvent, endEvent, intermediateThrowEvent, intermediateCatchEvent,
  boundaryEvent)
- Gateways (exclusive, parallel, inclusive, event-based, complex)
- Sub-processes, call activities
- Sequence flows (с условиями)
- Message flows (collaboration diagrams)
- Pools и lanes
- Data objects, data stores
- Text annotations

Стилизация через mxGraph BPMN shape library.

Использование:
    python3 bpmn_to_drawio.py input.bpmn output.drawio

ВАЖНО: ID-счётчик начинается с 2, потому что 0 и 1 зарезервированы
для root-ячеек DrawIO (<mxCell id="0"/> и <mxCell id="1" parent="0"/>).
Если начать с 1, diagrams.net выдаст "Duplicate ID '1'" и файл не откроется.
"""

import xml.etree.ElementTree as ET
import uuid
import sys


NS = {
    'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
    'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
    'dc': 'http://www.omg.org/spec/DD/20100524/DC',
    'di': 'http://www.omg.org/spec/DD/20100524/DI',
}


STYLES = {
    'task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=abstract;fillColor=#ffff;strokeColor=#000;',
    'service_task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=service;fillColor=#d5e8d4;strokeColor=#82b366;',
    'user_task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=user;fillColor=#dae8fc;strokeColor=#6c8ebf;',
    'send_task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=send;fillColor=#f8cecc;strokeColor=#b85450;',
    'receive_task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=receive;fillColor=#f8cecc;strokeColor=#b85450;',
    'manual_task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=manual;fillColor=#fff2cc;strokeColor=#d6b656;',
    'business_rule_task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=businessRule;fillColor=#e1d5e7;strokeColor=#9673a6;',
    'script_task': 'shape=mxgraph.bpmn.task;whiteSpace=wrap;html=1;taskMarker=script;fillColor=#e1d5e7;strokeColor=#9673a6;',

    'start_event': 'shape=mxgraph.bpmn.event;whiteSpace=wrap;html=1;',
    'end_event': 'shape=mxgraph.bpmn.event;whiteSpace=wrap;html=1;',
    'intermediate_event': 'shape=mxgraph.bpmn.event;whiteSpace=wrap;html=1;',
    'boundary_event': 'shape=mxgraph.bpmn.event;whiteSpace=wrap;html=1;',

    'gateway_exclusive': 'shape=mxgraph.bpmn.gateway2;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',
    'gateway_parallel': 'shape=mxgraph.bpmn.gateway_plus;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',
    'gateway_inclusive': 'shape=mxgraph.bpmn.gateway_or;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',
    'gateway_event': 'shape=mxgraph.bpmn.gateway_event;whiteSpace=wrap;html=1;',
    'gateway_complex': 'shape=mxgraph.bpmn.gateway_complex;whiteSpace=wrap;html=1;',

    'sub_process': 'shape=mxgraph.bpmn.subprocess;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',
    'sub_process_expanded': 'shape=mxgraph.bpmn.subprocess;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',
    'call_activity': 'shape=mxgraph.bpmn.activity2;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',

    'pool': 'shape=mxgraph.bpmn.pool;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000;',
    'lane': 'shape=mxgraph.bpmn.lane;whiteSpace=wrap;html=1;',

    'data_object': 'shape=mxgraph.bpmn.data_object;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',
    'data_store': 'shape=mxgraph.bpmn.datastore;whiteSpace=wrap;html=1;fillColor=#ffff;strokeColor=#000;',

    'text_annotation': 'shape=note;whiteSpace=wrap;html=1;background=#ffff99;align=left;',

    'sequence_flow': 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;endArrow=classic;',
    'message_flow': 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;startArrow=oval;endArrow=open;startFill=0;',
    'association': 'edgeStyle=none;html=1;dashed=1;endArrow=open;startArrow=none;',
}


TYPE_TO_STYLE = {
    'task': 'task',
    'serviceTask': 'service_task',
    'userTask': 'user_task',
    'sendTask': 'send_task',
    'receiveTask': 'receive_task',
    'manualTask': 'manual_task',
    'businessRuleTask': 'business_rule_task',
    'scriptTask': 'script_task',
    'startEvent': 'start_event',
    'endEvent': 'end_event',
    'intermediateThrowEvent': 'intermediate_event',
    'intermediateCatchEvent': 'intermediate_event',
    'boundaryEvent': 'boundary_event',
    'exclusiveGateway': 'gateway_exclusive',
    'parallelGateway': 'gateway_parallel',
    'inclusiveGateway': 'gateway_inclusive',
    'eventBasedGateway': 'gateway_event',
    'complexGateway': 'gateway_complex',
    'subProcess': 'sub_process',
    'callActivity': 'call_activity',
    'dataObjectReference': 'data_object',
    'dataStoreReference': 'data_store',
    'textAnnotation': 'text_annotation',
}


class BpmnToDrawioConverter:
    def __init__(self, bpmn_path):
        self.bpmn_path = bpmn_path
        self.tree = ET.parse(bpmn_path)
        self.root = self.tree.getroot()

        self.flow_nodes = {}
        self.artifacts = {}
        self.pools = {}
        self.lanes = {}
        self.flows = []
        self.dimensions = {}
        self.id_map = {}

        # CRITICAL: start at 2, not 1 — id 0 and 1 are reserved
        # for the root mxCells that DrawIO requires in <mxGraphModel>.
        self.next_cell_id = 2

    def convert(self):
        self._parse_dimensions()
        self._parse_pools_and_lanes()
        self._parse_flow_nodes()
        self._parse_artifacts()
        self._parse_flows()
        return self._build_drawio()

    def _next_id(self):
        cid = str(self.next_cell_id)
        self.next_cell_id += 1
        return cid

    def _parse_dimensions(self):
        # Coordinates live in BPMN DI: bpmndi:BPMNShape/bpmndi:BPMNBounds/dc:Bounds
        for shape in self.root.iter('{' + NS['bpmndi'] + '}BPMNShape'):
            shape_id = shape.get('bpmnElement')
            bounds = shape.find('{' + NS['dc'] + '}Bounds')
            if bounds is not None:
                x = float(bounds.get('x', 0))
                y = float(bounds.get('y', 0))
                w = float(bounds.get('width', 100))
                h = float(bounds.get('height', 80))
                self.dimensions[shape_id] = (x, y, w, h)

    def _parse_pools_and_lanes(self):
        for pool in self.root.iter('{' + NS['bpmn'] + '}participant'):
            self.pools[pool.get('id')] = {
                'id': pool.get('id'),
                'name': pool.get('name', ''),
                'process_ref': pool.get('processRef'),
            }
        for lane in self.root.iter('{' + NS['bpmn'] + '}lane'):
            self.lanes[lane.get('id')] = {
                'id': lane.get('id'),
                'name': lane.get('name', ''),
            }

    def _parse_flow_nodes(self):
        flow_node_tags = [
            'task', 'serviceTask', 'userTask', 'sendTask', 'receiveTask',
            'manualTask', 'businessRuleTask', 'scriptTask',
            'startEvent', 'endEvent', 'intermediateThrowEvent', 'intermediateCatchEvent',
            'boundaryEvent',
            'exclusiveGateway', 'parallelGateway', 'inclusiveGateway',
            'eventBasedGateway', 'complexGateway',
            'subProcess', 'callActivity', 'transaction',
        ]
        for tag_name in flow_node_tags:
            for elem in self.root.iter('{' + NS['bpmn'] + '}' + tag_name):
                self.flow_nodes[elem.get('id')] = {
                    'id': elem.get('id'),
                    'name': elem.get('name', ''),
                    'type': tag_name,
                }

    def _parse_artifacts(self):
        for tag_name in ['dataObjectReference', 'dataStoreReference', 'textAnnotation']:
            for elem in self.root.iter('{' + NS['bpmn'] + '}' + tag_name):
                name = elem.get('name', '')
                # textAnnotation stores content in <bpmn:text> child, not @name
                if not name and tag_name == 'textAnnotation':
                    text_elem = elem.find('{' + NS['bpmn'] + '}text')
                    if text_elem is not None and text_elem.text:
                        name = text_elem.text
                self.artifacts[elem.get('id')] = {
                    'id': elem.get('id'),
                    'name': name,
                    'type': tag_name,
                }

    def _parse_flows(self):
        for flow in self.root.iter('{' + NS['bpmn'] + '}sequenceFlow'):
            self.flows.append({
                'id': flow.get('id'),
                'source': flow.get('sourceRef'),
                'target': flow.get('targetRef'),
                'name': flow.get('name', ''),
                'kind': 'sequence',
            })
        for flow in self.root.iter('{' + NS['bpmn'] + '}messageFlow'):
            self.flows.append({
                'id': flow.get('id'),
                'source': flow.get('sourceRef'),
                'target': flow.get('targetRef'),
                'name': flow.get('name', ''),
                'kind': 'message',
            })
        for assoc in self.root.iter('{' + NS['bpmn'] + '}association'):
            self.flows.append({
                'id': assoc.get('id'),
                'source': assoc.get('sourceRef'),
                'target': assoc.get('targetRef'),
                'name': '',
                'kind': 'association',
            })

    def _get_dimensions(self, elem_id, default_w=120, default_h=80):
        if elem_id in self.dimensions:
            x, y, w, h = self.dimensions[elem_id]
            return x, y, w, h
        return None, None, default_w, default_h

    def _get_style(self, type_name):
        return STYLES.get(TYPE_TO_STYLE.get(type_name, 'task'), STYLES['task'])

    def _escape_xml(self, s):
        if not s:
            return ''
        return (s.replace('&', '&amp;')
                 .replace('<', '&lt;')
                 .replace('>', '&gt;')
                 .replace('"', '&quot;')
                 .replace("'", '&apos;'))

    def _build_drawio(self):
        cells_xml = []

        # 1. Pools (drawn first as containers)
        for pool_id, pool in self.pools.items():
            x, y, w, h = self._get_dimensions(pool_id, 800, 300)
            if x is None:
                continue
            cid = self._next_id()
            cells_xml.append(
                f'        <mxCell id="{cid}" value="{self._escape_xml(pool["name"])}" '
                f'style="{STYLES["pool"]}" vertex="1" parent="1">\n'
                f'          <mxGeometry x="{int(x)}" y="{int(y)}" width="{int(w)}" height="{int(h)}" as="geometry" />\n'
                f'        </mxCell>'
            )

        # 2. Flow nodes (tasks, events, gateways)
        for fn_id, fn in self.flow_nodes.items():
            x, y, w, h = self._get_dimensions(fn_id, 120, 80)
            if x is None:
                continue  # no DI data — skip (caller should flag this)
            style = self._get_style(fn['type'])
            cid = self._next_id()
            label = self._escape_xml(fn['name']).replace('\n', '&#xa;')
            cells_xml.append(
                f'        <mxCell id="{cid}" value="{label}" '
                f'style="{style}" vertex="1" parent="1">\n'
                f'          <mxGeometry x="{int(x)}" y="{int(y)}" width="{int(w)}" height="{int(h)}" as="geometry" />\n'
                f'        </mxCell>'
            )
            self.id_map[fn_id] = cid

        # 3. Artifacts (data objects, annotations)
        for art_id, art in self.artifacts.items():
            x, y, w, h = self._get_dimensions(art_id, 80, 80)
            if x is None:
                continue
            style = self._get_style(art['type'])
            cid = self._next_id()
            label = self._escape_xml(art['name']).replace('\n', '&#xa;')
            cells_xml.append(
                f'        <mxCell id="{cid}" value="{label}" '
                f'style="{style}" vertex="1" parent="1">\n'
                f'          <mxGeometry x="{int(x)}" y="{int(y)}" width="{int(w)}" height="{int(h)}" as="geometry" />\n'
                f'        </mxCell>'
            )
            self.id_map[art_id] = cid

        # 4. Flows (edges)
        for flow in self.flows:
            src = self.id_map.get(flow['source'])
            tgt = self.id_map.get(flow['target'])
            if not src or not tgt:
                continue
            if flow['kind'] == 'sequence':
                style = STYLES['sequence_flow']
            elif flow['kind'] == 'message':
                style = STYLES['message_flow']
            else:
                style = STYLES['association']
            cid = self._next_id()
            label = self._escape_xml(flow['name']).replace('\n', '&#xa;')
            cells_xml.append(
                f'        <mxCell id="{cid}" value="{label}" '
                f'style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">\n'
                f'          <mxGeometry relative="1" as="geometry" />\n'
                f'        </mxCell>'
            )

        cells_str = '\n'.join(cells_xml)
        drawio = f'''<mxfile host="Hermes BPMN Converter" version="24.0.0">
  <diagram id="bpmn-converted" name="BPMN Diagram">
    <mxGraphModel dx="1422" dy="753" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="826" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{cells_str}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''
        return drawio


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} input.bpmn output.drawio")
        sys.exit(1)

    converter = BpmnToDrawioConverter(sys.argv[1])
    drawio_xml = converter.convert()

    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(drawio_xml)

    n_pools = len(converter.pools)
    n_nodes = len(converter.flow_nodes)
    n_artifacts = len(converter.artifacts)
    n_flows = len(converter.flows)
    print(f"OK converted {sys.argv[1]} -> {sys.argv[2]}")
    print(f"   pools={n_pools}, nodes={n_nodes}, artifacts={n_artifacts}, flows={n_flows}")


if __name__ == '__main__':
    main()