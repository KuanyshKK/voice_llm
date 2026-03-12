"""Configuration for AlmatyEventsAgent."""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # LLM Settings
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    llm_temperature: float = 0.0

    # MCP Playwright Settings
    playwright_headless: bool = field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    )
    playwright_timeout: int = 30000  # 30 seconds

    # Target websites for Almaty events
    target_sites: dict = field(default_factory=lambda: {
        "ticketon": {
            "base_url": "https://ticketon.kz/almaty",
            "concerts_url": "https://ticketon.kz/almaty/category/koncerty",
            "theater_url": "https://ticketon.kz/almaty/category/teatr",
            "kids_url": "https://ticketon.kz/almaty/category/detskie-meropriyatiya",
            "description": "Основная афиша Казахстана - концерты, театр, детские мероприятия"
        },
        "sxodim": {
            "base_url": "https://sxodim.com/almaty",
            "search_url": "https://sxodim.com/almaty/search",
            "description": "Куда сходить в Алматы - события, выставки, развлечения"
        },
        "yandex_afisha": {
            "base_url": "https://afisha.yandex.kz/almaty",
            "concerts_url": "https://afisha.yandex.kz/almaty/concert",
            "theater_url": "https://afisha.yandex.kz/almaty/theatre",
            "kids_url": "https://afisha.yandex.kz/almaty/kids",
            "description": "Яндекс Афиша - концерты, театр, детские мероприятия"
        }
    })

    # Agent settings
    max_events_per_site: int = 10
    max_results: int = 5
    verbose: bool = True

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 2.0


config = Config()
