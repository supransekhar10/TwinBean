from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    firebase_project_id: str | None
    cors_origins: tuple[str, ...]


def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    )
    return Settings(
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID") or None,
        cors_origins=origins,
    )
