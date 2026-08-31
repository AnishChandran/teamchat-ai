import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "teamchat-ai"
    debug: bool = False
    firebase_project_id: str = ""
    vertex_ai_project_id: str = ""
    vertex_ai_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_retries: int = 3
    gemini_retry_base_delay_seconds: float = 0.5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def effective_vertex_ai_project_id(self) -> str:
        return self.vertex_ai_project_id or self.firebase_project_id


settings = Settings()


def get_firebase_project_id() -> str:
    """Resolve Firebase/GCP project ID from settings or runtime environment."""
    configured = settings.firebase_project_id.strip()
    if configured:
        return configured

    for key in ("FIREBASE_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "GCP_PROJECT"):
        value = os.environ.get(key, "").strip()
        if value:
            return value

    return ""
