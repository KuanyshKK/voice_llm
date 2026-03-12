# AlmatyEventsAgent

AI-агент для поиска событий в Алматы с использованием LangChain + LangGraph + MCP Playwright.

## Возможности

- Поиск концертов, спектаклей, выставок и других событий
- Парсинг актуальных афиш с нескольких сайтов
- Фильтрация по датам (сегодня, завтра, выходные, конкретная дата)
- Интерактивный режим с rich-форматированием
- Демо-режим для тестирования без API

## Источники данных

- [ticketon.kz/almaty](https://ticketon.kz/almaty) - концерты, театр, детские мероприятия
- [sxodim.com/almaty](https://sxodim.com/almaty) - куда сходить в Алматы
- [afisha.yandex.kz/almaty](https://afisha.yandex.kz/almaty) - Яндекс Афиша

## Установка

```bash
# Клонировать/перейти в директорию проекта
cd AlmatyEventsAgent

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
.\venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Установить браузеры Playwright
playwright install

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env и добавить OPENAI_API_KEY
```

## Настройка MCP Playwright

Для полной работы с браузером необходим MCP сервер Playwright:

```bash
# MCP сервер установится автоматически при первом запуске
# или установите вручную:
npx -y @executeautomation/playwright-mcp-server
```

## Использование

### Интерактивный режим

```bash
python main.py
```

### Демо режим (без API)

```bash
python main.py --demo
```

### Одиночный запрос

```bash
python main.py -q "концерты на выходных"
python main.py --demo -q "спектакли для детей"
```

### Примеры запросов

- "концерты на этой неделе"
- "спектакли на выходных в Алматы"
- "детские мероприятия сегодня"
- "куда сходить 15 марта"
- "рок-концерты в марте"
- "балет в ГАТОБ"

## Архитектура

```
AlmatyEventsAgent/
├── main.py           # Точка входа, CLI
├── agent.py          # LangGraph агент
├── tools.py          # Инструменты (анализ запроса, форматирование)
├── mcp_client.py     # MCP Playwright клиент
├── prompts.py        # Системные промпты
├── config.py         # Конфигурация
├── requirements.txt  # Зависимости
└── .env.example      # Пример конфига
```

### LangGraph Flow

```
START → [Agent] ←→ [Tools] → [Process] → END
              ↓
    Анализ запроса
    Выбор сайтов
    Навигация (MCP)
    Извлечение данных
    Форматирование
```

## Технологии

- **LangChain** - фреймворк для LLM
- **LangGraph** - граф состояний агента
- **MCP Playwright** - браузерная автоматизация
- **OpenAI GPT-4o-mini** - LLM для обработки
- **Rich** - форматирование CLI

## Конфигурация

Настройки в `config.py`:

```python
# LLM
llm_model = "gpt-4o-mini"
llm_temperature = 0.0

# Результаты
max_events_per_site = 10
max_results = 5

# Браузер
playwright_headless = True
playwright_timeout = 30000
```

## Troubleshooting

### Ошибка "OPENAI_API_KEY is required"

Создайте файл `.env` и добавьте ваш ключ:
```
OPENAI_API_KEY=sk-your-key
```

### Playwright не запускается

```bash
playwright install chromium
```

### MCP не подключается

Убедитесь, что MCP сервер доступен:
```bash
npx -y @executeautomation/playwright-mcp-server
```

## Лицензия

MIT
