import pytest

from app.llm.mention_detector import AiMention, contains_ai_mention, detect_ai_mention


@pytest.mark.parametrize(
    "content",
    [
        "@Gemini can you help?",
        "Hey @AI, thoughts?",
        "Please review this @gemini",
        "Ask @GEMINI for a summary",
        "Loop in @ai on this",
        "Check with @Ai before we ship",
        "(@Gemini)",
        "Thanks @Gemini.",
        "Good point @AI!",
        "What about @Gemini?",
    ],
)
def test_detect_ai_mention_matches_valid_mentions(content: str) -> None:
    assert detect_ai_mention(content) is not None
    assert contains_ai_mention(content)


@pytest.mark.parametrize(
    ("content", "expected_trigger"),
    [
        ("@Gemini help", "Gemini"),
        ("@gemini help", "Gemini"),
        ("@AI help", "AI"),
        ("@ai help", "AI"),
    ],
)
def test_detect_ai_mention_normalizes_trigger(content: str, expected_trigger: str) -> None:
    mention = detect_ai_mention(content)

    assert mention == AiMention(trigger=expected_trigger)


def test_detect_ai_mention_returns_first_match_when_both_present() -> None:
    mention = detect_ai_mention("@Gemini please also ask @AI")

    assert mention == AiMention(trigger="Gemini")


@pytest.mark.parametrize(
    "content",
    [
        "We need to decide on a caching strategy.",
        "Gemini can you help?",
        "Ask the AI team for feedback",
        "@GeminiBot please help",
        "@GeminiHelper",
        "user@Gemini.com",
        "email@ai.com",
        "@AI-powered tooling",
        "",
        "   ",
    ],
)
def test_detect_ai_mention_rejects_false_positives(content: str) -> None:
    assert detect_ai_mention(content) is None
    assert not contains_ai_mention(content)


def test_detect_ai_mention_at_start_middle_and_end() -> None:
    assert detect_ai_mention("@Gemini start here") == AiMention(trigger="Gemini")
    assert detect_ai_mention("Please ask @AI in the middle") == AiMention(trigger="AI")
    assert detect_ai_mention("End with @Gemini") == AiMention(trigger="Gemini")
