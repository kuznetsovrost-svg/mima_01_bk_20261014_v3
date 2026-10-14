#!/usr/bin/env python3
"""End-to-end test for JEV (TypeSafe System One model).

Tests all 3 primitives (Choice, Score, Noul) plus:
- Structured state (JSON)
- Multiple questions in parallel
- Confidence handling
- Cache layer

Run: python3 tests/test_e2e.py
"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from jev_client import jev_decide, jev_choice, jev_score, jev_noul


def test_noul():
    """Test single Noul question."""
    print("\n=== Test 1: jev_noul ===")
    prob = jev_noul("Привет, как дела?", "Это приветствие?")
    assert 0.7 < prob < 1.0, f"Expected high prob, got {prob}"
    print(f"  ✓ is_greeting = {prob}")
    return True


def test_choice():
    """Test single Choice question."""
    print("\n=== Test 2: jev_choice ===")
    chosen, prob = jev_choice(
        state="Найди мне информацию про BPMN",
        options={
            "code": "кодинг, скрипты, отладка",
            "research": "research, поиск информации",
            "chat": "болтовня, приветствие",
            "command": "прямая команда системе",
        }
    )
    assert prob > 0.5, f"Expected high confidence, got {prob}"
    print(f"  ✓ type = {chosen} (prob={prob:.2f})")
    assert chosen == "research", f"Expected 'research', got {chosen}"
    return True


def test_score():
    """Test single Score question."""
    print("\n=== Test 3: jev_score ===")
    text = "BPMN (Business Process Model and Notation) — это графическая нотация для моделирования бизнес-процессов. Стандарт OMG. Поддерживает шлюзы, события, задачи."
    score, conf = jev_score(
        state=text,
        scale=[
            "0: мусор",
            "1: плохо",
            "2: средне",
            "3: хорошо",
            "4: отлично",
        ]
    )
    print(f"  ✓ quality = {score} (confidence={conf:.2f})")
    assert score >= 2, f"Expected decent quality, got {score}"
    return True


def test_structured_state():
    """Test structured (JSON) state."""
    print("\n=== Test 4: Structured state ===")
    result = jev_decide(
        state={
            "file": {"name": "lecture_2026_10.mp3", "size_kb": 5400},
            "audio": {"duration_sec": 1800, "bitrate_bps": 128000},
            "metadata": {"title": "BPMN шлюзы", "speaker": "Иванов"},
        },
        questions={
            "language": {
                "type": "choice",
                "criteria": {"ru": "Russian", "en": "English"}
            },
            "needs_transcription": {
                "type": "noul",
                "instructions": "Should this be transcribed?"
            }
        }
    )
    lang = result["answers"]["language"]["choice"]
    transcribe = result["answers"]["needs_transcription"]["noul"]
    print(f"  ✓ language = {lang}")
    print(f"  ✓ needs_transcription = {transcribe:.2f}")
    assert lang == "ru"
    return True


def test_multiple_questions():
    """Test multiple questions in parallel (single JEV call)."""
    print("\n=== Test 5: Multiple questions in parallel ===")
    state = {
        "ticket": {
            "subject": "Не могу войти в систему",
            "priority": "high",
        },
        "customer": {"tier": "premium", "tenure_months": 24}
    }
    result = jev_decide(
        state=state,
        questions={
            "category": {
                "type": "choice",
                "criteria": {
                    "auth": "проблема с входом/авторизацией",
                    "billing": "вопрос по оплате",
                    "feature": "запрос на функциональность",
                    "bug": "баг в системе",
                }
            },
            "urgency": {
                "type": "score",
                "criteria": [
                    "0: routine",
                    "1: today",
                    "2: urgent",
                    "3: critical",
                ]
            },
            "needs_human": {
                "type": "noul",
                "instructions": "Требует ли вмешательства человека?"
            }
        }
    )
    print(f"  ✓ category = {result['answers']['category']['choice']}")
    print(f"  ✓ urgency = {result['answers']['urgency']['score']}")
    print(f"  ✓ needs_human = {result['answers']['needs_human']['noul']:.2f}")
    return True


def test_cache():
    """Test that caching works."""
    print("\n=== Test 6: Caching ===")
    import time

    state = {"test": "cache_test_unique_value_xyz123"}
    questions = {
        "test": {
            "type": "noul",
            "instructions": "Is this a test?"
        }
    }

    t0 = time.time()
    r1 = jev_decide(state, questions, use_cache=True)
    elapsed1 = time.time() - t0

    t0 = time.time()
    r2 = jev_decide(state, questions, use_cache=True)
    elapsed2 = time.time() - t0

    print(f"  ✓ First call: {elapsed1*1000:.0f}ms (real API)")
    print(f"  ✓ Second call: {elapsed2*1000:.0f}ms (cached)")
    assert r1 == r2, "Cached result should match"
    assert elapsed2 < elapsed1, "Cached should be faster"
    return True


def test_router():
    """Test 3-layer router."""
    print("\n=== Test 7: 3-layer router ===")
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from router import route, should_use_jev, should_use_llm_only

    test_tasks = [
        ({"type": "quality_gate", "description": "Check output"}, "jev"),
        ({"type": "playbook_generation", "description": "Create playbook"}, "llm"),
        ({"type": "classification", "description": "Classify this"}, "jev"),
        ({"type": "research", "description": "Find papers"}, "llm"),
        ({"type": "unknown", "description": "Это спам?"}, "jev"),  # keyword match
        ({"type": "unknown", "description": "Find recent papers"}, "llm"),
    ]

    for task, expected in test_tasks:
        result = route(task)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {task['type']:25s} | {task['description']:30s} → {result} (expected {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("JEV End-to-End Test Suite")
    print("=" * 60)

    tests = [
        test_noul,
        test_choice,
        test_score,
        test_structured_state,
        test_multiple_questions,
        test_cache,
        test_router,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
