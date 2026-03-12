"""
AlmatyEventsAgent - AI агент для поиска событий в Алматы.

Использует LangChain + LangGraph + MCP Playwright.
"""

from agent import AlmatyEventsAgent, DemoEventsAgent, get_agent

__version__ = "1.0.0"
__all__ = ["AlmatyEventsAgent", "DemoEventsAgent", "get_agent"]
