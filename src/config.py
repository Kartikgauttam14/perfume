"""Central configuration and SSOT constants for Mansam AI Concierge."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application runtime settings and official brand constants."""

    APP_NAME: str = "Mansam Luxury Fragrance AI Concierge"
    APP_VERSION: str = "1.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

    # Data & Vector DB paths
    CHUNKS_PATH: Path = BASE_DIR / "mansam_chunks.jsonl"
    SUMMARY_PATH: Path = BASE_DIR / "mansam_chunks_summary.json"
    CHROMA_PERSIST_DIRECTORY: Path = BASE_DIR / "chroma_db"
    CHROMA_COLLECTION_NAME: str = "mansam_knowledge"
    CHROMA_DISTANCE_METRIC: str = "cosine"

    # LLM API — OpenRouter (OpenAI-compatible)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # SSOT brand guidelines
    BRAND_AR: str = "منسم"
    BRAND_EN: str = "Mansam"
    DIALECT: str = "Khaleeji-Saudi"
    PRICE_OUD_SAR: float = 1150.0
    PRICE_STANDARD_SAR: float = 850.0
    OFFER_TEXT: str = "Complimentary 12ml with any 100ml EDP purchase"
    STORE_HOURS: str = "10:00 AM — 11:00 PM daily"
    WEBSITE_URL: str = "https://mansamworld.com"
    KSA_WHATSAPP: str = "+966 53 982 2844"
    UAE_WHATSAPP: str = "+971 54 485 4544"
    SUPPORT_EMAIL: str = "customercare@mansamworld.com"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
