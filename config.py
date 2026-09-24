"""
Configuration module for Mansam Luxury Fragrance AI Concierge.
Loads environment variables and sets system defaults based on SSOT.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Mansam Luxury Fragrance AI Concierge"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Data Files
    CHUNKS_PATH: Path = BASE_DIR / "mansam_chunks.jsonl"
    SUMMARY_PATH: Path = BASE_DIR / "mansam_chunks_summary.json"

    # LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Brand Constants (SSOT 10_Settings)
    BRAND_NAME_AR: str = "منسم"
    BRAND_NAME_EN: str = "Mansam"
    DIALECT: str = "Khaleeji-Saudi"
    PRICE_OUD_SAR: float = 1150.0
    PRICE_STANDARD_SAR: float = 850.0
    PRICE_OUD_AED: float = 1150.0
    PRICE_STANDARD_AED: float = 850.0
    PRICE_OUD_USD: float = 310.50
    PRICE_STANDARD_USD: float = 229.50
    DEFAULT_SIZE: str = "100 ml"
    OFFER_DESCRIPTION: str = "complimentary 12ml of any of the 20 fragrances with any 100ml purchase"
    STORE_HOURS: str = "10am — 11pm daily"
    WEBSITE_URL: str = "https://mansamworld.com"
    KSA_SUPPORT_PHONE: str = "+966 53 982 2844"
    UAE_SUPPORT_PHONE: str = "+971 54 485 4544"
    SUPPORT_EMAIL: str = "customercare@mansamworld.com"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
