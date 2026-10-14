"""
skill_matcher.py — Сопоставление сущностей таблицы с описаниями.

ПРАВИЛО СОПОСТАВЛЕНИЯ (двойная проверка):
1. ##NNN в описании должен совпадать с ##NNN в таблице (обязательно)
2. #Имя в описании должно совпадать с именем в таблице (обязательно)

Если одно из условий не выполнено — это РАСХОЖДЕНИЕ (mismatch).
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class MatchStatus(Enum):
    """Статус сопоставления сущности с описанием."""
    MATCHED = 'matched'             # NNN + имя совпали
    NNN_MISMATCH = 'nnn_mismatch'   # NNN не совпал (хотя имя совпало)
    NAME_MISMATCH = 'name_mismatch' # Имя не совпало (хотя NNN совпал)
    BOTH_MISMATCH = 'both_mismatch' # И NNN, и имя разные
    ORPHAN_DESCRIPTION = 'orphan'   # Описание без сущности в таблице
    MISSING_DESCRIPTION = 'missing' # Сущность без описания


@dataclass
class SkillRecord:
    """Запись о сущности в таблице."""
    nnn: str
    name: str
    col: int
    row: int
    group_id: str
    extra: Dict = field(default_factory=dict)


@dataclass
class DescriptionRecord:
    """Запись об описании сущности."""
    nnn: str
    name: str
    text: str
    group_id: str
    extra: Dict = field(default_factory=dict)


@dataclass
class MatchResult:
    """Результат сопоставления."""
    nnn: str
    status: MatchStatus
    skill: Optional[SkillRecord] = None
    description: Optional[DescriptionRecord] = None
    issues: List[str] = field(default_factory=list)

    def is_ok(self) -> bool:
        return self.status == MatchStatus.MATCHED


@dataclass
class MatchReport:
    """Отчёт о сопоставлении."""
    matched: List[MatchResult] = field(default_factory=list)
    nnn_mismatches: List[MatchResult] = field(default_factory=list)
    name_mismatches: List[MatchResult] = field(default_factory=list)
    both_mismatches: List[MatchResult] = field(default_factory=list)
    orphan_descriptions: List[DescriptionRecord] = field(default_factory=list)
    missing_descriptions: List[SkillRecord] = field(default_factory=list)

    @property
    def total_skills(self) -> int:
        return (len(self.matched) + len(self.nnn_mismatches) +
                len(self.name_mismatches) + len(self.both_mismatches) +
                len(self.missing_descriptions))

    @property
    def total_descriptions(self) -> int:
        return (len(self.matched) + len(self.nnn_mismatches) +
                len(self.name_mismatches) + len(self.both_mismatches) +
                len(self.orphan_descriptions))

    @property
    def coverage_pct(self) -> float:
        if self.total_skills == 0:
            return 0.0
        return 100.0 * len(self.matched) / self.total_skills

    def to_dict(self) -> Dict[str, Any]:
        return {
            'matched_count': len(self.matched),
            'nnn_mismatch_count': len(self.nnn_mismatches),
            'name_mismatch_count': len(self.name_mismatches),
            'both_mismatch_count': len(self.both_mismatches),
            'orphan_descriptions_count': len(self.orphan_descriptions),
            'missing_descriptions_count': len(self.missing_descriptions),
            'total_skills': self.total_skills,
            'total_descriptions': self.total_descriptions,
            'coverage_pct': round(self.coverage_pct, 1),
            'mismatches': [
                {
                    'nnn': m.nnn,
                    'status': m.status.value,
                    'skill_name': m.skill.name if m.skill else None,
                    'desc_name': m.description.name if m.description else None,
                    'desc_nnn': m.description.nnn if m.description else None,
                    'issues': m.issues,
                }
                for m in (self.nnn_mismatches + self.name_mismatches + self.both_mismatches)
            ],
            'orphan_descriptions': [
                {'nnn': d.nnn, 'name': d.name, 'group_id': d.group_id}
                for d in self.orphan_descriptions
            ],
            'missing_descriptions': [
                {'nnn': s.nnn, 'name': s.name, 'col': s.col, 'row': s.row}
                for s in self.missing_descriptions
            ],
        }


def normalize_name(name: str) -> str:
    """
    Нормализует имя для сравнения.
    Снимает ведущий # (есть в описании, нет в таблице).
    trim + lower + схлопывание пробелов.
    """
    if not name:
        return ''
    name = name.strip()
    # Снимаем ведущий # (в описании имя начинается с #)
    while name.startswith('#'):
        name = name[1:].lstrip()
    return ' '.join(name.lower().split())


def normalize_nnn(nnn: str) -> str:
    """Нормализует номер: strip ведущих нулей."""
    if not nnn:
        return ''
    return str(int(nnn))


def build_skill_index(skills: List[SkillRecord]) -> Dict[str, SkillRecord]:
    """Индекс сущностей по NNN."""
    idx = {}
    for s in skills:
        idx[normalize_nnn(s.nnn)] = s
    return idx


def build_desc_index(descriptions: List[DescriptionRecord]) -> Dict[str, DescriptionRecord]:
    """Индекс описаний по NNN."""
    idx = {}
    for d in descriptions:
        idx[normalize_nnn(d.nnn)] = d
    return idx


def match(skills: List[SkillRecord],
          descriptions: List[DescriptionRecord]) -> MatchReport:
    """
    Сопоставляет сущности и описания по двойной проверке:
    NNN совпадает И имя совпадает.
    """
    report = MatchReport()
    skill_idx = build_skill_index(skills)
    desc_idx = build_desc_index(descriptions)

    matched_nnns = set()

    # 1. Идём по сущностям таблицы — ищем для каждой описание
    for skill in skills:
        nnn = normalize_nnn(skill.nnn)
        desc = desc_idx.get(nnn)

        if desc is None:
            # Нет описания с таким NNN
            report.missing_descriptions.append(skill)
            continue

        nnn_ok = normalize_nnn(desc.nnn) == nnn
        name_ok = normalize_name(desc.name) == normalize_name(skill.name)

        if nnn_ok and name_ok:
            # Полное совпадение
            report.matched.append(MatchResult(
                nnn=nnn,
                status=MatchStatus.MATCHED,
                skill=skill,
                description=desc,
            ))
            matched_nnns.add(nnn)
        elif nnn_ok and not name_ok:
            # NNN совпал, имя нет
            report.name_mismatches.append(MatchResult(
                nnn=nnn,
                status=MatchStatus.NAME_MISMATCH,
                skill=skill,
                description=desc,
                issues=[f"name mismatch: table='{skill.name}' desc='{desc.name}'"],
            ))
            matched_nnns.add(nnn)
        elif not nnn_ok and name_ok:
            # NNN не совпал, имя совпало (странная ситуация)
            report.nnn_mismatches.append(MatchResult(
                nnn=nnn,
                status=MatchStatus.NNN_MISMATCH,
                skill=skill,
                description=desc,
                issues=[f"nnn mismatch: table={nnn} desc={desc.nnn}"],
            ))
            matched_nnns.add(normalize_nnn(desc.nnn))
        else:
            # Оба не совпали
            report.both_mismatches.append(MatchResult(
                nnn=nnn,
                status=MatchStatus.BOTH_MISMATCH,
                skill=skill,
                description=desc,
                issues=[
                    f"nnn mismatch: table={nnn} desc={desc.nnn}",
                    f"name mismatch: table='{skill.name}' desc='{desc.name}'",
                ],
            ))
            matched_nnns.add(normalize_nnn(desc.nnn))

    # 2. Описания без сущности в таблице
    for desc in descriptions:
        nnn = normalize_nnn(desc.nnn)
        if nnn not in matched_nnns and nnn not in skill_idx:
            report.orphan_descriptions.append(desc)

    return report


def find_orphan_descriptions(skills: List[SkillRecord],
                             descriptions: List[DescriptionRecord]) -> List[DescriptionRecord]:
    """Описания, для которых нет сущности в таблице."""
    skill_nnns = {normalize_nnn(s.nnn) for s in skills}
    return [d for d in descriptions if normalize_nnn(d.nnn) not in skill_nnns]


def find_missing_descriptions(skills: List[SkillRecord],
                              descriptions: List[DescriptionRecord]) -> List[SkillRecord]:
    """Сущности без описания."""
    desc_nnns = {normalize_nnn(d.nnn) for d in descriptions}
    return [s for s in skills if normalize_nnn(s.nnn) not in desc_nnns]


def find_name_mismatches(skills: List[SkillRecord],
                         descriptions: List[DescriptionRecord]) -> List[Tuple[SkillRecord, DescriptionRecord]]:
    """Сущности с одинаковым NNN, но разными именами."""
    skill_idx = build_skill_index(skills)
    mismatches = []
    for d in descriptions:
        nnn = normalize_nnn(d.nnn)
        if nnn in skill_idx:
            s = skill_idx[nnn]
            if normalize_name(s.name) != normalize_name(d.name):
                mismatches.append((s, d))
    return mismatches