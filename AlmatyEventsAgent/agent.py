"""LangGraph Agent for AlmatyEventsAgent with real Playwright integration."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Annotated, Any, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from config import config
from prompts import SYSTEM_PROMPT
from tools import (
    analyze_query,
    format_events_response,
    get_extraction_hints,
    get_site_urls,
    parse_extracted_content,
)

logging.basicConfig(
    level=logging.INFO if config.verbose else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install")


class AgentState(TypedDict):
    """State for the events agent."""
    messages: Annotated[list, add_messages]
    query: str
    query_analysis: dict
    collected_events: list[dict]
    sites_visited: list[str]
    current_site: str
    error_count: int
    final_response: str


class RealPlaywrightBrowser:
    """Real Playwright browser for web scraping."""

    _instance: Optional['RealPlaywrightBrowser'] = None
    _playwright = None
    _browser: Optional[Browser] = None
    _page: Optional[Page] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def start_browser(self) -> str:
        """Start real browser session."""
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: Playwright not installed. Run: pip install playwright && playwright install chromium"

        try:
            if self._browser is None:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=config.playwright_headless
                )
                self._page = await self._browser.new_page()
                self._page.set_default_timeout(config.playwright_timeout)
                logger.info("Browser started successfully")
            return "Browser session started"
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return f"Error starting browser: {e}"

    async def navigate(self, url: str) -> str:
        """Navigate to URL."""
        try:
            if self._page is None:
                await self.start_browser()

            logger.info(f"Navigating to: {url}")
            await self._page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)  # Wait for dynamic content
            title = await self._page.title()
            return f"Navigated to {url}. Page title: {title}"
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return f"Error navigating to {url}: {e}"

    async def get_page_content(self) -> str:
        """Get visible text content from current page."""
        try:
            if self._page is None:
                return "Error: Browser not started"

            # Get text content
            content = await self._page.evaluate("""
                () => {
                    // Get all visible text
                    const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, a, li, div, time, [class*="event"], [class*="card"], [class*="title"], [class*="date"], [class*="price"], [class*="venue"]');
                    const texts = [];
                    elements.forEach(el => {
                        const text = el.innerText?.trim();
                        if (text && text.length > 2 && text.length < 500) {
                            texts.push(text);
                        }
                    });
                    return [...new Set(texts)].join('\\n');
                }
            """)
            logger.info(f"Got page content: {len(content)} chars")
            return content[:15000]  # Limit content size
        except Exception as e:
            logger.error(f"Error getting content: {e}")
            return f"Error getting page content: {e}"

    async def get_events_from_page(self) -> str:
        """Extract events from current page using smart selectors."""
        try:
            if self._page is None:
                return "Error: Browser not started"

            events = await self._page.evaluate("""
                () => {
                    const events = [];

                    // Sxodim.com selectors
                    const sxodimCards = document.querySelectorAll('.impression-card');
                    sxodimCards.forEach(card => {
                        const title = card.querySelector('.impression-card-title')?.innerText?.trim();
                        const info = card.querySelector('.impression-card-info')?.innerText?.trim() || '';
                        const link = card.querySelector('a')?.href;
                        const category = card.getAttribute('data-category') || '';

                        if (title && title.length > 3) {
                            events.push({
                                title: title,
                                info: info,
                                category: category,
                                url: link || '',
                                source: 'sxodim.com'
                            });
                        }
                    });

                    // Generic selectors for other sites
                    if (events.length === 0) {
                        const genericCards = document.querySelectorAll('[class*="event-card"], [class*="event-item"], article[class*="event"]');
                        genericCards.forEach(card => {
                            const title = card.querySelector('h1, h2, h3, h4, [class*="title"]')?.innerText?.trim();
                            const info = card.querySelector('[class*="info"], [class*="date"], [class*="price"]')?.innerText?.trim() || '';
                            const link = card.querySelector('a')?.href;

                            if (title && title.length > 3) {
                                events.push({
                                    title: title.substring(0, 200),
                                    info: info,
                                    url: link || '',
                                    source: window.location.hostname
                                });
                            }
                        });
                    }

                    // Deduplicate by title
                    const seen = new Set();
                    return events.filter(e => {
                        if (seen.has(e.title)) return false;
                        seen.add(e.title);
                        return true;
                    }).slice(0, 10);
                }
            """)
            logger.info(f"Extracted {len(events)} events")
            return json.dumps(events, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error extracting events: {e}")
            return f"Error extracting events: {e}"

    async def scroll_down(self) -> str:
        """Scroll page down."""
        try:
            if self._page is None:
                return "Error: Browser not started"

            await self._page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1)
            logger.info("Scrolled down")
            return "Scrolled down successfully"
        except Exception as e:
            return f"Error scrolling: {e}"

    async def click_element(self, selector: str) -> str:
        """Click element by selector."""
        try:
            if self._page is None:
                return "Error: Browser not started"

            await self._page.click(selector)
            await asyncio.sleep(1)
            logger.info(f"Clicked: {selector}")
            return f"Clicked element: {selector}"
        except Exception as e:
            return f"Error clicking {selector}: {e}"

    async def close_browser(self) -> str:
        """Close browser."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._browser = None
            self._page = None
            self._playwright = None
            logger.info("Browser closed")
            return "Browser closed"
        except Exception as e:
            return f"Error closing browser: {e}"


# Create browser instance
browser = RealPlaywrightBrowser()


@tool
async def browser_navigate(url: str) -> str:
    """
    Открывает URL в реальном браузере через Playwright.

    Args:
        url: URL для открытия (например https://ticketon.kz/almaty)

    Returns:
        Результат навигации с заголовком страницы
    """
    return await browser.navigate(url)


@tool
async def browser_get_content() -> str:
    """
    Получает текстовый контент текущей страницы.

    Returns:
        Текстовый контент страницы
    """
    return await browser.get_page_content()


@tool
async def browser_get_events() -> str:
    """
    Извлекает события с текущей страницы в структурированном формате JSON.
    Автоматически находит карточки событий и извлекает название, дату, цену, место.

    Returns:
        JSON массив с событиями
    """
    return await browser.get_events_from_page()


@tool
async def browser_scroll() -> str:
    """
    Прокручивает страницу вниз для загрузки дополнительного контента.

    Returns:
        Результат прокрутки
    """
    return await browser.scroll_down()


@tool
async def browser_click(selector: str) -> str:
    """
    Кликает по элементу на странице.

    Args:
        selector: CSS селектор элемента

    Returns:
        Результат клика
    """
    return await browser.click_element(selector)


@tool
async def browser_close() -> str:
    """
    Закрывает браузер и освобождает ресурсы.
    Вызывай после завершения сбора данных.

    Returns:
        Результат закрытия
    """
    return await browser.close_browser()


def create_events_agent():
    """Create the LangGraph events agent."""

    # Initialize LLM
    if config.openai_api_key:
        llm = ChatOpenAI(
            model=config.llm_model,
            temperature=config.llm_temperature,
            api_key=config.openai_api_key,
        )
    else:
        raise ValueError("OPENAI_API_KEY is required. Set it in .env file.")

    # Combine all tools
    all_tools = [
        analyze_query,
        get_site_urls,
        format_events_response,
        get_extraction_hints,
        parse_extracted_content,
        browser_navigate,
        browser_get_content,
        browser_get_events,
        browser_scroll,
        browser_click,
        browser_close,
    ]

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(all_tools)

    # Create tool node
    tool_node = ToolNode(all_tools)

    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Determine if we should continue with tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return "end"

    def call_agent(state: AgentState) -> dict:
        """Call the agent with current state."""
        messages = state["messages"]

        # Add system message if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            system_msg = SystemMessage(content=SYSTEM_PROMPT)
            messages = [system_msg] + messages

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def process_results(state: AgentState) -> dict:
        """Process tool results and update state."""
        messages = state["messages"]
        collected_events = state.get("collected_events", [])

        # Look for parsed events in recent tool messages
        for msg in reversed(messages[-5:]):
            if isinstance(msg, ToolMessage):
                try:
                    content = msg.content
                    if isinstance(content, str):
                        # Try to parse as JSON
                        try:
                            data = json.loads(content)
                            if isinstance(data, list) and all(isinstance(e, dict) for e in data):
                                collected_events.extend(data)
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    logger.warning(f"Error processing tool result: {e}")

        return {"collected_events": collected_events}

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", tool_node)
    workflow.add_node("process", process_results)

    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    workflow.add_edge("tools", "process")
    workflow.add_edge("process", "agent")

    # Compile
    app = workflow.compile()

    return app


class AlmatyEventsAgent:
    """Main agent class for querying Almaty events."""

    def __init__(self):
        self.agent = create_events_agent()
        logger.info("AlmatyEventsAgent initialized")

    async def query(self, user_query: str) -> str:
        """
        Process user query about events in Almaty.

        Args:
            user_query: User's question about events

        Returns:
            Formatted response with events
        """
        logger.info(f"Processing query: {user_query}")

        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "query": user_query,
            "query_analysis": {},
            "collected_events": [],
            "sites_visited": [],
            "current_site": "",
            "error_count": 0,
            "final_response": ""
        }

        try:
            # Use ainvoke for async execution
            result = await self.agent.ainvoke(
                initial_state,
                {"recursion_limit": 25}
            )

            # Get final AI message
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    return msg.content

            return "Не удалось получить результат. Пожалуйста, попробуйте еще раз."

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"Произошла ошибка при обработке запроса: {str(e)}"

    def query_sync(self, user_query: str) -> str:
        """Synchronous version of query."""
        return asyncio.run(self.query(user_query))


# Demo mode agent that doesn't require actual MCP connection
class DemoEventsAgent:
    """Demo agent with simulated data for testing without MCP."""

    DEMO_EVENTS = [
        {
            "title": "Dimash Qudaibergen - Концерт",
            "date": "15.03.2026",
            "time": "19:00",
            "venue": "Almaty Arena",
            "price": "от 15 000 тг",
            "description": "Грандиозное шоу казахстанской звезды мирового уровня",
            "url": "https://ticketon.kz/almaty/dimash-concert",
            "source": "ticketon.kz"
        },
        {
            "title": "Симфонический оркестр - Классика под звездами",
            "date": "14.03.2026",
            "time": "18:30",
            "venue": "Казахская государственная филармония",
            "price": "от 5 000 тг",
            "description": "Произведения Моцарта, Бетховена и Чайковского",
            "url": "https://ticketon.kz/almaty/symphony-stars",
            "source": "ticketon.kz"
        },
        {
            "title": "Stand-Up вечер: Лучшие комики Казахстана",
            "date": "13.03.2026",
            "time": "20:00",
            "venue": "The Ritz-Carlton, Almaty",
            "price": "от 8 000 тг",
            "description": "Вечер юмора с топовыми стендаперами",
            "url": "https://sxodim.com/almaty/standup-evening",
            "source": "sxodim.com"
        },
        {
            "title": "Балет 'Лебединое озеро'",
            "date": "16.03.2026",
            "time": "17:00",
            "venue": "ГАТОБ им. Абая",
            "price": "от 3 000 тг",
            "description": "Классический балет П.И. Чайковского",
            "url": "https://afisha.yandex.kz/almaty/ballet-swan-lake",
            "source": "afisha.yandex.kz"
        },
        {
            "title": "Детский спектакль 'Алладин'",
            "date": "15.03.2026",
            "time": "12:00",
            "venue": "ТЮЗ им. Г. Мусрепова",
            "price": "от 2 000 тг",
            "description": "Музыкальная сказка для всей семьи",
            "url": "https://ticketon.kz/almaty/aladdin-kids",
            "source": "ticketon.kz"
        },
        {
            "title": "Рок-фестиваль 'Almaty Rock Night'",
            "date": "14.03.2026",
            "time": "18:00",
            "venue": "Дворец Республики",
            "price": "от 10 000 тг",
            "description": "Лучшие рок-группы Казахстана и СНГ",
            "url": "https://ticketon.kz/almaty/rock-night",
            "source": "ticketon.kz"
        },
        {
            "title": "Выставка современного искусства",
            "date": "13.03.2026 - 30.03.2026",
            "time": "10:00 - 19:00",
            "venue": "Музей искусств им. Кастеева",
            "price": "от 1 500 тг",
            "description": "Работы современных казахстанских художников",
            "url": "https://sxodim.com/almaty/modern-art-expo",
            "source": "sxodim.com"
        },
    ]

    def __init__(self):
        logger.info("DemoEventsAgent initialized (demo mode)")

    def _filter_events(self, query: str) -> list[dict]:
        """Filter demo events based on query."""
        query_lower = query.lower()
        filtered = []

        for event in self.DEMO_EVENTS:
            # Check for event type matches
            if "концерт" in query_lower or "музык" in query_lower:
                if "концерт" in event["title"].lower() or "рок" in event["title"].lower() or "симфонич" in event["title"].lower():
                    filtered.append(event)
            elif "театр" in query_lower or "спектакл" in query_lower or "балет" in query_lower:
                if any(x in event["title"].lower() for x in ["спектакл", "балет", "пьес"]):
                    filtered.append(event)
            elif "дет" in query_lower:
                if "детск" in event["title"].lower() or "детск" in event.get("description", "").lower():
                    filtered.append(event)
            elif "выставк" in query_lower:
                if "выставк" in event["title"].lower():
                    filtered.append(event)
            else:
                # General query - return all
                filtered.append(event)

        return filtered if filtered else self.DEMO_EVENTS[:5]

    async def query(self, user_query: str) -> str:
        """Process query with demo data."""
        logger.info(f"[DEMO] Processing query: {user_query}")

        # Simulate some processing time
        await asyncio.sleep(0.5)

        # Filter events
        events = self._filter_events(user_query)

        # Format response
        return format_events_response.invoke({
            "events": events,
            "query": user_query
        })

    def query_sync(self, user_query: str) -> str:
        """Synchronous version."""
        return asyncio.run(self.query(user_query))


def get_agent(demo_mode: bool = False):
    """Get appropriate agent based on mode."""
    if demo_mode:
        return DemoEventsAgent()
    return AlmatyEventsAgent()
