from dataclasses import dataclass
from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest
from google.genai import errors as genai_errors

from app.core.config import Settings
from app.llm.context_builder import ConversationContext, SYSTEM_INSTRUCTION
from app.llm.gemini_service import (
    GeminiRequest,
    GeminiService,
    GeminiServiceError,
    build_gemini_contents,
    build_gemini_system_instruction,
    map_exception_to_service_error,
)


@dataclass
class FakeChunk:
    text: str | None


def make_context(*, history: str = "") -> ConversationContext:
    return ConversationContext(
        system_instruction=SYSTEM_INSTRUCTION,
        conversation_history=history,
    )


def make_request(**overrides) -> GeminiRequest:
    defaults = {
        "organization_id": "acme",
        "room_id": "engineering",
        "room_name": "Engineering",
        "conversation_context": make_context(
            history="[2026-02-08 14:30] Sarah: We need a caching strategy."
        ),
        "triggering_message": "@Gemini what do you recommend?",
    }
    defaults.update(overrides)
    return GeminiRequest(**defaults)


def make_mock_client(stream_impl) -> MagicMock:
    client = MagicMock()
    client.aio.models.generate_content_stream = stream_impl
    return client


async def successful_stream(*args, **kwargs) -> AsyncIterator[FakeChunk]:
    yield FakeChunk(text="Hello")
    yield FakeChunk(text="")
    yield FakeChunk(text=" world")


@pytest.mark.asyncio
async def test_stream_response_yields_text_chunks() -> None:
    service = GeminiService(
        settings=Settings(
            firebase_project_id="test-project",
            gemini_model="gemini-2.0-flash",
        ),
        client=make_mock_client(successful_stream),
    )

    chunks = [chunk async for chunk in service.stream_response(make_request())]

    assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
async def test_stream_response_passes_model_contents_and_config() -> None:
    captured: dict[str, object] = {}

    async def tracking_stream(*, model, contents, config) -> AsyncIterator[FakeChunk]:
        captured["model"] = model
        captured["contents"] = contents
        captured["config"] = config
        async for chunk in successful_stream():
            yield chunk

    service = GeminiService(
        settings=Settings(
            firebase_project_id="test-project",
            gemini_model="gemini-2.0-flash",
            vertex_ai_location="us-central1",
        ),
        client=make_mock_client(tracking_stream),
    )
    request = make_request()

    async for _ in service.stream_response(request):
        pass

    assert captured["model"] == "gemini-2.0-flash"
    assert "Sarah: We need a caching strategy." in captured["contents"]
    assert "@Gemini what do you recommend?" in captured["contents"]
    assert str(captured["config"].system_instruction).startswith(SYSTEM_INSTRUCTION)
    assert "Organization ID: acme" in captured["config"].system_instruction
    assert "Room name: Engineering" in captured["config"].system_instruction


def test_build_gemini_contents_includes_history_and_trigger() -> None:
    contents = build_gemini_contents(make_request())

    assert "Sarah: We need a caching strategy." in contents
    assert "Latest user message:" in contents
    assert "@Gemini what do you recommend?" in contents


def test_build_gemini_contents_fallback_when_empty() -> None:
    contents = build_gemini_contents(
        make_request(
            conversation_context=make_context(history=""),
            triggering_message=None,
        )
    )

    assert contents == "Please assist the team based on the conversation context."


def test_build_gemini_system_instruction_includes_room_context() -> None:
    instruction = build_gemini_system_instruction(make_request())

    assert instruction.startswith(SYSTEM_INSTRUCTION)
    assert "Organization ID: acme" in instruction
    assert "Room ID: engineering" in instruction
    assert "Room name: Engineering" in instruction


def test_map_exception_to_service_error_for_authentication() -> None:
    error = map_exception_to_service_error(genai_errors.ClientError(401, {}, None))

    assert error == GeminiServiceError(
        code="authentication",
        message="Gemini authentication failed",
        retryable=False,
    )


def test_map_exception_to_service_error_for_invalid_request() -> None:
    error = map_exception_to_service_error(genai_errors.ClientError(400, {}, None))

    assert error.code == "invalid_request"
    assert error.retryable is False


def test_map_exception_to_service_error_for_rate_limit_is_retryable() -> None:
    error = map_exception_to_service_error(genai_errors.ClientError(429, {}, None))

    assert error.code == "rate_limited"
    assert error.retryable is True


def test_map_exception_to_service_error_for_server_error_is_retryable() -> None:
    error = map_exception_to_service_error(genai_errors.ServerError(503, {}, None))

    assert error.code == "unavailable"
    assert error.retryable is True


@pytest.mark.asyncio
async def test_stream_response_retries_transient_failures() -> None:
    attempts = 0

    async def flaky_stream(*args, **kwargs) -> AsyncIterator[FakeChunk]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise genai_errors.ServerError(503, {}, None)
        yield FakeChunk(text="Recovered")

    service = GeminiService(
        settings=Settings(
            firebase_project_id="test-project",
            gemini_max_retries=3,
            gemini_retry_base_delay_seconds=0,
        ),
        client=make_mock_client(flaky_stream),
    )

    chunks = [chunk async for chunk in service.stream_response(make_request())]

    assert chunks == ["Recovered"]
    assert attempts == 3


@pytest.mark.asyncio
async def test_stream_response_does_not_retry_authentication_errors() -> None:
    attempts = 0

    async def auth_failure_stream(*args, **kwargs) -> AsyncIterator[FakeChunk]:
        nonlocal attempts
        attempts += 1
        raise genai_errors.ClientError(401, {}, None)
        yield FakeChunk(text="unused")

    service = GeminiService(
        settings=Settings(
            firebase_project_id="test-project",
            gemini_max_retries=3,
            gemini_retry_base_delay_seconds=0,
        ),
        client=make_mock_client(auth_failure_stream),
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        async for _ in service.stream_response(make_request()):
            pass

    assert exc_info.value.code == "authentication"
    assert attempts == 1


@pytest.mark.asyncio
async def test_stream_response_does_not_retry_invalid_request_errors() -> None:
    attempts = 0

    async def invalid_stream(*args, **kwargs) -> AsyncIterator[FakeChunk]:
        nonlocal attempts
        attempts += 1
        raise genai_errors.ClientError(400, {}, None)
        yield FakeChunk(text="unused")

    service = GeminiService(
        settings=Settings(
            firebase_project_id="test-project",
            gemini_max_retries=3,
            gemini_retry_base_delay_seconds=0,
        ),
        client=make_mock_client(invalid_stream),
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        async for _ in service.stream_response(make_request()):
            pass

    assert exc_info.value.code == "invalid_request"
    assert attempts == 1


@pytest.mark.asyncio
async def test_stream_response_raises_after_exhausted_retries() -> None:
    async def always_fail(*args, **kwargs) -> AsyncIterator[FakeChunk]:
        raise genai_errors.ServerError(503, {}, None)
        yield FakeChunk(text="unused")

    service = GeminiService(
        settings=Settings(
            firebase_project_id="test-project",
            gemini_max_retries=2,
            gemini_retry_base_delay_seconds=0,
        ),
        client=make_mock_client(always_fail),
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        async for _ in service.stream_response(make_request()):
            pass

    assert exc_info.value.code == "unavailable"
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_stream_response_does_not_retry_after_partial_output() -> None:
    attempts = 0

    async def fail_mid_stream(*args, **kwargs) -> AsyncIterator[FakeChunk]:
        nonlocal attempts
        attempts += 1
        yield FakeChunk(text="partial")
        raise genai_errors.ServerError(503, {}, None)

    service = GeminiService(
        settings=Settings(
            firebase_project_id="test-project",
            gemini_max_retries=3,
            gemini_retry_base_delay_seconds=0,
        ),
        client=make_mock_client(fail_mid_stream),
    )

    chunks: list[str] = []
    with pytest.raises(GeminiServiceError) as exc_info:
        async for chunk in service.stream_response(make_request()):
            chunks.append(chunk)

    assert chunks == ["partial"]
    assert exc_info.value.code == "unavailable"
    assert attempts == 1


def test_service_requires_configured_project_when_client_not_injected() -> None:
    service = GeminiService(
        settings=Settings(firebase_project_id="", vertex_ai_project_id=""),
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        service._get_client()

    assert exc_info.value.code == "invalid_request"
