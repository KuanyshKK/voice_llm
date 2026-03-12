"""
LangChain Agent with MCP Playwright - TEAMMATE IMPLEMENTATION
Connect to Playwright MCP server, browse event sites, return relevant info.
"""
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are a helpful voice assistant for leisure planning in Almaty, Kazakhstan.

When users ask about events, concerts, movies, shows, or activities:
1. Use the Playwright browser tools to visit relevant sites:
   - https://sxodim.com/almaty (events and shows)
   - https://kino.kz (movies)
   - https://ticketon.kz (tickets and events)
2. Read the page content to find current/upcoming events
3. Summarize the most relevant options for the user

Keep responses concise (2-4 sentences) since they will be spoken aloud.
Always mention specific times, prices, or locations when available.
Respond in the same language the user used (Russian or English)."""


async def run_langchain_agent(user_text: str) -> str:
    server_params = StdioServerParameters(
        command="npx",
        args=["@playwright/mcp@latest", "--headless"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)

            llm = ChatAnthropic(
                model="claude-sonnet-4-6",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])

            agent = create_tool_calling_agent(llm, tools, prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=10,
                handle_parsing_errors=True,
            )

            result = await executor.ainvoke({"input": user_text})
            return result["output"]
