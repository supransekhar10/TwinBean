from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    firebase_project_id: str | None
    cors_origins: tuple[str, ...]
    cors_origin_regex: str | None
    aki_model_artifact_dir: Path
    aki_inference_concurrency: int
    groq_api_key: str | None
    groq_model: str


def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    )
    release_name = os.getenv("AKI_MODEL_RELEASE", "aki-24h-2026.10.08b")
    if Path(release_name).name != release_name or release_name in {"", ".", ".."}:
        raise ValueError("AKI_MODEL_RELEASE must name one controlled artifact release")
    try:
        inference_concurrency = int(os.getenv("AKI_INFERENCE_CONCURRENCY", "2"))
    except ValueError as error:
        raise ValueError("AKI_INFERENCE_CONCURRENCY must be a positive integer") from error
    if inference_concurrency < 1:
        raise ValueError("AKI_INFERENCE_CONCURRENCY must be a positive integer")
    artifact_root = Path(__file__).resolve().parents[1] / "model_artifacts"
    return Settings(
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID") or None,
        cors_origins=origins,
        cors_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
        aki_model_artifact_dir=artifact_root / release_name,
        aki_inference_concurrency=inference_concurrency,
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    )
