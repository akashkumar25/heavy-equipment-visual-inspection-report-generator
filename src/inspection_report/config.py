"""Runtime settings, read from environment variables or a .env file.

The default backend is a small vision-language model that runs locally on CPU.
A hosted model can be used instead through any OpenAI-compatible endpoint.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INSPECTION_", env_file=".env", extra="ignore")

    backend: Literal["local", "api"] = "local"
    local_model: str = "HuggingFaceTB/SmolVLM-256M-Instruct"
    api_base_url: str = "http://localhost:11434/v1"
    api_model: str = "qwen2.5vl:3b"
    api_key: str = "ollama"
    images_dir: Path = Path("data/images")
    reports_dir: Path = Path("data/reports")
