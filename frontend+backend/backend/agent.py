import os
from openai import AsyncOpenAI


async def run_agent(user_text: str) -> str:
    # Try LangChain+MCP agent first (teammate's implementation)
    try:
        from langchain_agent import run_langchain_agent
        return await run_langchain_agent(user_text)
    except Exception as e:
        print(f"[Agent] LangChain agent failed ({e}), using fallback")

    # Fallback: basic OpenAI response
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful voice assistant for leisure planning in Almaty, Kazakhstan. "
                    "Help users find events, concerts, movies, shows. "
                    "Keep answers concise (2-3 sentences max) since they will be spoken aloud. "
                    "Note: Web browsing not available in fallback mode."
                ),
            },
            {"role": "user", "content": user_text},
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content
