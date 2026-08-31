import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Literal

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.core.config import Settings, settings as default_settings
from app.llm.context_builder import ConversationContext

GeminiErrorCode = Literal[
    "authentication",
    "invalid_request",
    "rate_limited",
    "unavailable",
    "internal",
]

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class GeminiRequest:
    organization_id: str
    room_id: str
    room_name: str | None
    conversation_context: ConversationContext
    triggering_message: str | None = None


@dataclass
class GeminiServiceError(Exception):
    code: GeminiErrorCode
    message: str
    retryable: bool

    def __str__(self) -> str:
        return self.message


class GeminiService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self._settings = settings or default_settings
        self._client = client
        self._client_instance: Any | None = None

    async def stream_response(self, request: GeminiRequest) -> AsyncIterator[str]:
        async for chunk in self._stream_with_retry(request):
            yield chunk

    async def _stream_with_retry(self, request: GeminiRequest) -> AsyncIterator[str]:
        max_retries = max(self._settings.gemini_max_retries, 1)
        base_delay = self._settings.gemini_retry_base_delay_seconds
        last_error: GeminiServiceError | None = None

        for attempt in range(max_retries):
            yielded = False
            try:
                async for chunk in self._generate_stream(request):
                    yielded = True
                    yield chunk
                return
            except GeminiServiceError as exc:
                if yielded or not exc.retryable:
                    raise
                last_error = exc
            except Exception as exc:
                service_error = map_exception_to_service_error(exc)
                if yielded or not service_error.retryable:
                    raise service_error from exc
                last_error = service_error

            if attempt < max_retries - 1:
                await asyncio.sleep(base_delay * (2**attempt))

        if last_error is not None:
            raise last_error
        raise GeminiServiceError(
            code="unavailable",
            message="Gemini request failed after retries",
            retryable=True,
        )

    async def _generate_stream(self, request: GeminiRequest) -> AsyncIterator[str]:
        client = self._get_client()
        stream_result = client.aio.models.generate_content_stream(
            model=self._settings.gemini_model,
            contents=build_gemini_contents(request),
            config=genai_types.GenerateContentConfig(
                system_instruction=build_gemini_system_instruction(request),
            ),
        )
        stream = await stream_result if isawaitable(stream_result) else stream_result
        async for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        if self._client_instance is None:
            project_id = self._settings.effective_vertex_ai_project_id
            if not project_id:
                raise GeminiServiceError(
                    code="invalid_request",
                    message="Vertex AI project ID is not configured",
                    retryable=False,
                )
            self._client_instance = genai.Client(
                vertexai=True,
                project=project_id,
                location=self._settings.vertex_ai_location,
            )
        return self._client_instance


def build_gemini_system_instruction(request: GeminiRequest) -> str:
    metadata_lines = [
        f"Organization ID: {request.organization_id}",
        f"Room ID: {request.room_id}",
    ]
    if request.room_name:
        metadata_lines.append(f"Room name: {request.room_name}")

    return (
        f"{request.conversation_context.system_instruction}\n\n"
        f"Context:\n" + "\n".join(metadata_lines)
    )


def build_gemini_contents(request: GeminiRequest) -> str:
    parts: list[str] = []
    if request.conversation_context.conversation_history:
        parts.append(request.conversation_context.conversation_history)
    if request.triggering_message and request.triggering_message.strip():
        parts.append(f"Latest user message:\n{request.triggering_message.strip()}")
    if not parts:
        return "Please assist the team based on the conversation context."
    return "\n\n".join(parts)


def map_exception_to_service_error(exc: Exception) -> GeminiServiceError:
    if isinstance(exc, genai_errors.ClientError):
        status_code = exc.code
        if status_code in {401, 403}:
            return GeminiServiceError(
                code="authentication",
                message=_extract_error_message(exc, "Gemini authentication failed"),
                retryable=False,
            )
        if status_code == 429:
            return GeminiServiceError(
                code="rate_limited",
                message=_extract_error_message(exc, "Gemini rate limit exceeded"),
                retryable=True,
            )
        return GeminiServiceError(
            code="invalid_request",
            message=_extract_error_message(exc, "Invalid Gemini request"),
            retryable=False,
        )

    if isinstance(exc, genai_errors.ServerError):
        return GeminiServiceError(
            code="unavailable",
            message=_extract_error_message(exc, "Gemini service unavailable"),
            retryable=exc.code in RETRYABLE_STATUS_CODES,
        )

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError, OSError)):
        return GeminiServiceError(
            code="unavailable",
            message="Gemini request timed out or failed to connect",
            retryable=True,
        )

    return GeminiServiceError(
        code="internal",
        message=str(exc) or "Unexpected Gemini service error",
        retryable=False,
    )


def is_retryable_exception(exc: Exception) -> bool:
    return map_exception_to_service_error(exc).retryable


def _extract_error_message(exc: Exception, fallback: str) -> str:
    response_json = getattr(exc, "response_json", None)
    if isinstance(response_json, dict):
        error = response_json.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message
        message = response_json.get("message")
        if isinstance(message, str) and message.strip():
            return message
    return fallback
