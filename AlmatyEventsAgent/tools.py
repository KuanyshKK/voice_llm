"""Tools for AlmatyEventsAgent using MCP Playwright."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from config import config

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """Event model."""
    title: str = Field(description="Название события")
    date: str = Field(description="Дата проведения")
    time: Optional[str] = Field(default=None, description="Время начала")
    venue: Optional[str] = Field(default=None, description="Место проведения")
    price: Optional[str] = Field(default=None, description="Цена")
    description: Optional[str] = Field(default=None, description="Описание")
    url: str = Field(description="Ссылка на событие")
    source: str = Field(description="Источник (сайт)")


class QueryAnalysis(BaseModel):
    """Analyzed user query."""
    event_type: str = Field(description="Тип события: concert/theater/kids/exhibition/sport/other/any")
    date_filter: str = Field(description="Фильтр дат: today/tomorrow/weekend/this_week/specific/any")
    specific_date: Optional[str] = Field(default=None, description="Конкретная дата YYYY-MM-DD")
    keywords: list[str] = Field(default_factory=list, description="Ключевые слова")
    recommended_sites: list[str] = Field(default_factory=list, description="Рекомендуемые сайты")


def get_date_range(date_filter: str, specific_date: Optional[str] = None) -> tuple[datetime, datetime]:
    """Get date range based on filter."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if date_filter == "today":
        return today, today + timedelta(days=1)
    elif date_filter == "tomorrow":
        tomorrow = today + timedelta(days=1)
        return tomorrow, tomorrow + timedelta(days=1)
    elif date_filter == "weekend":
        # Find next Saturday
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0 and today.weekday() == 5:
            saturday = today
        else:
            saturday = today + timedelta(days=days_until_saturday)
        sunday = saturday + timedelta(days=1)
        return saturday, sunday + timedelta(days=1)
    elif date_filter == "this_week":
        # Current week (Monday to Sunday)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday + timedelta(days=1)
    elif date_filter == "specific" and specific_date:
        try:
            date = datetime.strptime(specific_date, "%Y-%m-%d")
            return date, date + timedelta(days=1)
        except ValueError:
            pass

    # Default: next 7 days
    return today, today + timedelta(days=7)


def get_site_url(site: str, event_type: str) -> str:
    """Get appropriate URL for site based on event type."""
    site_config = config.target_sites.get(site, {})

    if event_type == "concert":
        return site_config.get("concerts_url", site_config.get("base_url", ""))
    elif event_type == "theater":
        return site_config.get("theater_url", site_config.get("base_url", ""))
    elif event_type == "kids":
        return site_config.get("kids_url", site_config.get("base_url", ""))
    else:
        return site_config.get("base_url", "")


@tool
def analyze_query(query: str) -> dict:
    """
    Анализирует запрос пользователя о событиях.

    Args:
        query: Запрос пользователя на русском языке

    Returns:
        Структурированная информация о запросе
    """
    query_lower = query.lower()

    # Determine event type
    event_type = "any"
    if any(word in query_lower for word in ["концерт", "музык", "выступлен"]):
        event_type = "concert"
    elif any(word in query_lower for word in ["театр", "спектакл", "пьес"]):
        event_type = "theater"
    elif any(word in query_lower for word in ["дет", "ребен", "детск"]):
        event_type = "kids"
    elif any(word in query_lower for word in ["выставк", "музей", "галере"]):
        event_type = "exhibition"
    elif any(word in query_lower for word in ["спорт", "матч", "футбол", "хоккей"]):
        event_type = "sport"

    # Determine date filter
    date_filter = "any"
    specific_date = None

    if "сегодня" in query_lower:
        date_filter = "today"
    elif "завтра" in query_lower:
        date_filter = "tomorrow"
    elif any(word in query_lower for word in ["выходн", "суббот", "воскресен"]):
        date_filter = "weekend"
    elif any(word in query_lower for word in ["этой недел", "на неделе", "эта недел"]):
        date_filter = "this_week"
    else:
        # Try to find specific date patterns
        import re
        date_patterns = [
            r"(\d{1,2})[\.\-/](\d{1,2})(?:[\.\-/](\d{2,4}))?",  # dd.mm.yyyy
            r"(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
        ]

        months_ru = {
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
            "мая": 5, "июня": 6, "июля": 7, "августа": 8,
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
        }

        for pattern in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        if groups[1] in months_ru:
                            day = int(groups[0])
                            month = months_ru[groups[1]]
                            year = datetime.now().year
                        else:
                            day = int(groups[0])
                            month = int(groups[1])
                            year = int(groups[2]) if len(groups) > 2 and groups[2] else datetime.now().year
                            if year < 100:
                                year += 2000

                        specific_date = f"{year}-{month:02d}-{day:02d}"
                        date_filter = "specific"
                        break
                except (ValueError, IndexError):
                    pass

    # Recommend sites based on event type
    if event_type == "concert":
        recommended_sites = ["ticketon", "yandex_afisha"]
    elif event_type == "theater":
        recommended_sites = ["ticketon", "yandex_afisha"]
    elif event_type == "kids":
        recommended_sites = ["ticketon", "sxodim"]
    elif event_type == "exhibition":
        recommended_sites = ["sxodim", "yandex_afisha"]
    else:
        recommended_sites = ["ticketon", "sxodim"]

    # Extract keywords
    stopwords = {"в", "на", "и", "для", "алматы", "алмате", "событи", "ивент", "мероприяти"}
    keywords = [w for w in query_lower.split() if len(w) > 2 and w not in stopwords]

    return {
        "event_type": event_type,
        "date_filter": date_filter,
        "specific_date": specific_date,
        "keywords": keywords,
        "recommended_sites": recommended_sites,
        "date_range": {
            "start": get_date_range(date_filter, specific_date)[0].isoformat(),
            "end": get_date_range(date_filter, specific_date)[1].isoformat()
        }
    }


@tool
def get_site_urls(event_type: str, sites: list[str]) -> dict:
    """
    Получает URLs для сайтов на основе типа события.

    Args:
        event_type: Тип события (concert/theater/kids/exhibition/any)
        sites: Список сайтов (ticketon/sxodim/yandex_afisha)

    Returns:
        Словарь с URLs для каждого сайта
    """
    urls = {}
    for site in sites:
        url = get_site_url(site, event_type)
        if url:
            urls[site] = url
    return urls


@tool
def format_events_response(events: list[dict], query: str) -> str:
    """
    Форматирует список событий в текст для голосового ответа (TTS).

    Args:
        events: Список событий в формате JSON
        query: Исходный запрос пользователя

    Returns:
        Текстовый ответ для озвучивания
    """
    if not events:
        return "К сожалению, по твоему запросу ничего не нашлось. Попробуй изменить дату или тип события."

    # Берем только первые 5 событий для краткости
    top_events = events[:min(5, config.max_results)]

    response = f"Вот что я нашёл по запросу {query}. "

    for i, event in enumerate(top_events, 1):
        title = event.get("title", "")
        info = event.get("info", "")

        # Если нет info, собираем из других полей
        if not info:
            date = event.get("date", "")
            venue = event.get("venue", "")
            price = event.get("price", "")
            info = f"{date}, {venue}, {price}".strip(", ")

        if title:
            response += f"{i}. {title}"
            if info:
                response += f", {info}"
            response += ". "

    response += "Хочешь узнать подробнее о каком-то событии?"

    return response


# Extraction patterns for different sites
SITE_EXTRACTION_HINTS = {
    "ticketon": {
        "event_selector": ".event-card, .event-item, [class*='event']",
        "title_selector": ".event-title, h3, h4",
        "date_selector": ".event-date, .date",
        "price_selector": ".event-price, .price",
        "venue_selector": ".event-venue, .venue, .location"
    },
    "sxodim": {
        "event_selector": ".event-card, .card, [class*='event']",
        "title_selector": ".title, h3, h4",
        "date_selector": ".date, time",
        "price_selector": ".price",
        "venue_selector": ".place, .venue"
    },
    "yandex_afisha": {
        "event_selector": "[class*='event'], [class*='Event']",
        "title_selector": "[class*='title'], [class*='Title']",
        "date_selector": "[class*='date'], [class*='Date']",
        "price_selector": "[class*='price'], [class*='Price']",
        "venue_selector": "[class*='place'], [class*='Place']"
    }
}


@tool
def get_extraction_hints(site: str) -> dict:
    """
    Получает подсказки для извлечения данных с сайта.

    Args:
        site: Название сайта (ticketon/sxodim/yandex_afisha)

    Returns:
        CSS селекторы для извлечения данных
    """
    return SITE_EXTRACTION_HINTS.get(site, SITE_EXTRACTION_HINTS["ticketon"])


@tool
def parse_extracted_content(content: str, source: str) -> list[dict]:
    """
    Парсит извлеченный контент и возвращает структурированные события.

    Args:
        content: Текстовый контент страницы или JSON
        source: Источник данных (название сайта)

    Returns:
        Список событий в структурированном формате
    """
    events = []

    # Try to parse as JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    events.append({
                        "title": item.get("title", item.get("name", "")),
                        "date": item.get("date", ""),
                        "time": item.get("time", ""),
                        "venue": item.get("venue", item.get("place", "")),
                        "price": item.get("price", ""),
                        "description": item.get("description", ""),
                        "url": item.get("url", item.get("link", "")),
                        "source": source
                    })
        return events
    except json.JSONDecodeError:
        pass

    # If not JSON, try to parse as text
    # Split by common separators
    lines = content.split("\n")
    current_event = {}

    for line in lines:
        line = line.strip()
        if not line:
            if current_event.get("title"):
                current_event["source"] = source
                events.append(current_event)
                current_event = {}
            continue

        # Try to identify field types
        line_lower = line.lower()
        if any(x in line_lower for x in ["дата:", "date:"]):
            current_event["date"] = line.split(":", 1)[-1].strip()
        elif any(x in line_lower for x in ["время:", "time:"]):
            current_event["time"] = line.split(":", 1)[-1].strip()
        elif any(x in line_lower for x in ["место:", "venue:", "площадка:"]):
            current_event["venue"] = line.split(":", 1)[-1].strip()
        elif any(x in line_lower for x in ["цена:", "price:", "от "]):
            current_event["price"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif any(x in line_lower for x in ["http://", "https://"]):
            current_event["url"] = line
        elif not current_event.get("title") and len(line) > 3:
            current_event["title"] = line

    # Don't forget last event
    if current_event.get("title"):
        current_event["source"] = source
        events.append(current_event)

    return events


def get_all_tools() -> list:
    """Return all available tools."""
    return [
        analyze_query,
        get_site_urls,
        format_events_response,
        get_extraction_hints,
        parse_extracted_content,
    ]
