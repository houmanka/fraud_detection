import os
from pathlib import Path
from typing import Final, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Config(BaseSettings):
    app_env: str = "dev"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env", env_file_encoding="utf-8"
    )
    database_url: SecretStr

_config: Optional[Config] = None


def get_config() -> Config:
    """Lazily load and return the configuration.
    This is only loaded when needed, avoiding sys.exit during test collection.
    """
    global _config
    if _config is None:
        try:
            # In production, rely on real environment variables (Render, etc.) and do not
            # depend on a local `.env` file being present.
            env = (os.getenv("APP_ENV") or os.getenv("app_env") or "dev").lower()
            env_file = None if env in {"prod", "production"} else Config.model_config.get("env_file")
            _config = Config(_env_file=env_file)
        except Exception as e:
            raise RuntimeError(f"Configuration Error: {e}") from e
    return _config

# For backward compatibility with scripts that expect a global 'config'
try:
    config = get_config()
except RuntimeError:
    # If config fails to load, don't exit immediately - let the code that needs it fail
    # This allows tests to run even if .env is missing
    config = None