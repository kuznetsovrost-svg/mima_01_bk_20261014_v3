"""Тесты skill_matcher.py — двойная проверка NNN + имя."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from skill_matcher import (
    SkillRecord, DescriptionRecord, match, MatchStatus,
    normalize_name, normalize_nnn,
    find_orphan_descriptions, find_missing_descriptions, find_name_mismatches
)


def make_skill(nnn, name, row=0, col=0):
    return SkillRecord(nnn=nnn, name=name, col=col, row=row, group_id=f"s-{nnn}")


def make_desc(nnn, name, text="описание"):
    return DescriptionRecord(nnn=nnn, name=name, text=text, group_id=f"d-{nnn}")


class TestNormalize:
    def test_name_strips_hash(self):
        assert normalize_name("#Git") == "git"
        assert normalize_name("Git") == "git"
        assert normalize_name("#Git") == normalize_name("Git")

    def test_name_handles_multiple_hashes(self):
        assert normalize_name("##Name") == "name"

    def test_name_lowercases(self):
        assert normalize_name("GitHub") == normalize_name("github")

    def test_name_collapses_spaces(self):
        assert normalize_name("  Git   Sync  ") == "git sync"

    def test_nnn_strips_leading_zeros(self):
        assert normalize_nnn("001") == "1"
        assert normalize_nnn("1") == "1"
        assert normalize_nnn("001") == normalize_nnn("1")


class TestMatch:
    def test_full_match(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("001", "#Git")]
        report = match(skills, descs)
        assert len(report.matched) == 1
        assert len(report.missing_descriptions) == 0
        assert len(report.orphan_descriptions) == 0

    def test_missing_description(self):
        skills = [make_skill("001", "Git")]
        descs = []
        report = match(skills, descs)
        assert len(report.matched) == 0
        assert len(report.missing_descriptions) == 1
        assert report.missing_descriptions[0].nnn == "001"

    def test_orphan_description(self):
        skills = []
        descs = [make_desc("001", "#Git")]
        report = match(skills, descs)
        assert len(report.matched) == 0
        assert len(report.orphan_descriptions) == 1
        assert report.orphan_descriptions[0].nnn == "001"

    def test_name_mismatch(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("001", "#Wrong")]
        report = match(skills, descs)
        assert len(report.matched) == 0
        assert len(report.name_mismatches) == 1
        assert report.name_mismatches[0].status == MatchStatus.NAME_MISMATCH

    def test_nnn_mismatch_with_same_name(self):
        # NNN разный, имя совпало — это orphan_description, не nnn_mismatch.
        # (Логика: skill_index ищет по NNN, не находит —> missing или orphan.)
        skills = [make_skill("001", "Git")]
        descs = [make_desc("002", "#Git")]  # NNN разный
        report = match(skills, descs)
        # skill #001 — нет описания (missing)
        assert len(report.missing_descriptions) == 1
        # desc #002 — нет сущности (orphan)
        assert len(report.orphan_descriptions) == 1

    def test_both_mismatch(self):
        # Если NNN не совпал — это уже orphan/missing, не both_mismatch.
        # both_mismatch возможен только если skill_index нашёл по NNN
        # но имя разное (то же что NAME_MISMATCH).
        skills = [make_skill("001", "Git")]
        descs = [make_desc("002", "#Wrong")]
        report = match(skills, descs)
        assert len(report.matched) == 0
        assert len(report.both_mismatches) == 0  # NNN разный → orphan + missing

    def test_multiple_skills_mixed(self):
        skills = [
            make_skill("001", "Git"),
            make_skill("002", "Parser"),
            make_skill("003", "Render"),  # нет описания
        ]
        descs = [
            make_desc("001", "#Git"),     # match
            make_desc("002", "#Wrong"),   # name mismatch
        ]
        report = match(skills, descs)
        assert len(report.matched) == 1
        assert len(report.name_mismatches) == 1
        assert len(report.missing_descriptions) == 1

    def test_leading_zeros_in_nnn(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("1", "#Git")]
        report = match(skills, descs)
        assert len(report.matched) == 1


class TestCoverage:
    def test_full_coverage(self):
        skills = [make_skill("001", "Git"), make_skill("002", "Parser")]
        descs = [make_desc("001", "#Git"), make_desc("002", "#Parser")]
        report = match(skills, descs)
        assert report.coverage_pct == 100.0

    def test_partial_coverage(self):
        skills = [make_skill("001", "Git"), make_skill("002", "Parser")]
        descs = [make_desc("001", "#Git")]
        report = match(skills, descs)
        assert report.coverage_pct == 50.0


class TestFindOrphan:
    def test_no_orphans(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("001", "#Git")]
        orphans = find_orphan_descriptions(skills, descs)
        assert orphans == []

    def test_with_orphans(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("001", "#Git"), make_desc("002", "#Parser")]
        orphans = find_orphan_descriptions(skills, descs)
        assert len(orphans) == 1
        assert orphans[0].nnn == "002"


class TestFindMissing:
    def test_no_missing(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("001", "#Git")]
        missing = find_missing_descriptions(skills, descs)
        assert missing == []

    def test_with_missing(self):
        skills = [make_skill("001", "Git"), make_skill("002", "Parser")]
        descs = [make_desc("001", "#Git")]
        missing = find_missing_descriptions(skills, descs)
        assert len(missing) == 1
        assert missing[0].nnn == "002"


class TestFindNameMismatches:
    def test_no_mismatches(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("001", "#Git")]
        mismatches = find_name_mismatches(skills, descs)
        assert mismatches == []

    def test_with_mismatch(self):
        skills = [make_skill("001", "Git")]
        descs = [make_desc("001", "#Wrong")]
        mismatches = find_name_mismatches(skills, descs)
        assert len(mismatches) == 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])