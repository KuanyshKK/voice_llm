#!/usr/bin/env python3
"""
AlmatyEventsAgent - AI агент для поиска событий в Алматы.

Использует LangChain + LangGraph + MCP Playwright для парсинга
афиш и ответов на запросы пользователей.

Примеры запросов:
- "концерты на выходных в Алматы"
- "спектакли для детей"
- "ивенты 20 марта"

Запуск:
    python main.py                    # Интерактивный режим
    python main.py --demo             # Демо режим (без MCP)
    python main.py --query "концерты" # Одиночный запрос
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from agent import AlmatyEventsAgent, DemoEventsAgent, get_agent
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO if config.verbose else logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()


def print_banner():
    """Print welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🎭 AlmatyEventsAgent 🎭                   ║
║                                                              ║
║       AI-помощник для поиска событий в Алматы               ║
║   Концерты • Спектакли • Выставки • Детские мероприятия     ║
║                                                              ║
║   Powered by: LangChain + LangGraph + MCP Playwright        ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_help():
    """Print help message."""
    help_text = """
### 📖 Как пользоваться

Просто введите ваш запрос на русском языке. Примеры:

- **Концерты**: "концерты на этой неделе", "рок-концерты в Алматы"
- **Театр**: "спектакли на выходных", "балет в марте"
- **Детские**: "детские мероприятия сегодня", "куда сходить с детьми"
- **По дате**: "события 15 марта", "что будет в субботу"
- **Общие**: "куда сходить на выходных", "интересные события"

### ⌨️ Команды

- `help` - показать эту справку
- `exit` или `quit` - выход
- `clear` - очистить экран

### 🌐 Источники данных

- ticketon.kz/almaty
- sxodim.com/almaty
- afisha.yandex.kz/almaty
    """
    console.print(Markdown(help_text))


async def process_query(agent, query: str) -> str:
    """Process a single query."""
    with console.status("[bold green]Ищу события...", spinner="dots"):
        try:
            result = await agent.query(query)
            return result
        except Exception as e:
            logger.error(f"Error: {e}")
            return f"❌ Ошибка при обработке запроса: {str(e)}"


async def interactive_mode(demo: bool = False):
    """Run agent in interactive mode."""
    print_banner()

    mode_text = "ДЕМО" if demo else "ПОЛНЫЙ"
    console.print(f"\n[dim]Режим: {mode_text}[/dim]")
    console.print("[dim]Введите 'help' для справки, 'exit' для выхода[/dim]\n")

    agent = get_agent(demo_mode=demo)

    while True:
        try:
            query = Prompt.ask("\n[bold cyan]🔍 Ваш запрос[/bold cyan]")

            if not query.strip():
                continue

            query_lower = query.lower().strip()

            if query_lower in ("exit", "quit", "выход", "q"):
                console.print("\n[yellow]До свидания! 👋[/yellow]\n")
                break

            if query_lower == "help":
                print_help()
                continue

            if query_lower == "clear":
                console.clear()
                print_banner()
                continue

            # Process query
            result = await process_query(agent, query)

            # Display result
            console.print()
            console.print(Panel(
                Markdown(result),
                title="[bold green]📋 Результаты[/bold green]",
                border_style="green"
            ))

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Прервано пользователем[/yellow]")
            break
        except EOFError:
            break


async def single_query_mode(query: str, demo: bool = False):
    """Process a single query and exit."""
    agent = get_agent(demo_mode=demo)

    console.print(f"\n[bold]Запрос:[/bold] {query}\n")

    result = await process_query(agent, query)

    console.print(Markdown(result))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AlmatyEventsAgent - AI для поиска событий в Алматы",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python main.py                           # Интерактивный режим
  python main.py --demo                    # Демо режим (без API)
  python main.py -q "концерты в Алматы"    # Одиночный запрос
  python main.py --demo -q "спектакли"     # Демо + одиночный запрос
        """
    )

    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Одиночный запрос (без интерактивного режима)"
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Запуск в демо режиме (без реального MCP/API)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробный вывод логов"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.query:
            asyncio.run(single_query_mode(args.query, demo=args.demo))
        else:
            asyncio.run(interactive_mode(demo=args.demo))
    except KeyboardInterrupt:
        console.print("\n[yellow]Прервано[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
