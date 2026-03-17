#!/usr/bin/env python3
"""
Servidor MCP para Qwen-CLI com habilidades de memória.
Fornece ferramentas para salvar e recuperar informações da memória.
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.core.memory.manager import MemoryManager

# Inicializa servidor e gerenciador de memória
server = Server("qwen-memory")
memory = MemoryManager(
    short_term_max_size=100,
    short_term_ttl_minutes=None,
    long_term_storage_path="./memory_storage",
    auto_consolidate=True
)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista as ferramentas disponíveis."""
    return [
        Tool(
            name="save_memory",
            description="Save information to memory for later retrieval. Use this to store important facts, context, or user preferences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content/information to save to memory"
                    },
                    "importance": {
                        "type": "number",
                        "description": "Importance level from 0.0 to 1.0 (default: 1.0). Higher values are more likely to be consolidated to long-term memory.",
                        "default": 1.0
                    },
                    "long_term": {
                        "type": "boolean",
                        "description": "Whether to also store in long-term memory (default: true)",
                        "default": True
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="search_memory",
            description="Search for relevant information in memory. Use this to retrieve previously saved context or facts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant memory content"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_recent_memories",
            description="Get the most recent items from short-term memory. Use this to recall recent conversation context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of recent items to retrieve (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_memory_stats",
            description="Get statistics about memory usage including size and utilization.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="clear_memory",
            description="Clear memory. Use with caution as this will delete stored information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "What to clear: 'short' (short-term only), 'long' (long-term only), or 'all' (both)",
                        "enum": ["short", "long", "all"],
                        "default": "all"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executa uma ferramenta."""

    if name == "save_memory":
        content = arguments.get("content")
        importance = arguments.get("importance", 1.0)
        long_term = arguments.get("long_term", True)

        if not content:
            return [TextContent(
                type="text",
                text="Error: 'content' is required"
            )]

        result = memory.add(
            content=content,
            importance=importance,
            store_long_term=long_term
        )

        response = (
            f"✓ Memory saved successfully!\n"
            f"- Short-term: {'Stored' if result['short_term'] else 'Failed'}\n"
            f"- Long-term: {'Stored' if result['long_term'] else 'Not stored'}\n"
            f"- Content: {content[:100]}{'...' if len(content) > 100 else ''}"
        )

        return [TextContent(type="text", text=response)]

    elif name == "search_memory":
        query = arguments.get("query")
        top_k = arguments.get("top_k", 5)

        if not query:
            return [TextContent(
                type="text",
                text="Error: 'query' is required"
            )]

        results = memory.search(query, top_k=top_k)

        response_lines = [f"Search results for: '{query}'\n"]

        # Long-term results
        if results.long_term:
            response_lines.append("📚 Long-term memory:")
            for item, score in results.long_term:
                response_lines.append(f"  • [Score: {score:.2f}] {item.content}")

        # Short-term results
        if results.short_term:
            response_lines.append("\n⏱️ Short-term memory (recent):")
            for item in results.short_term:
                response_lines.append(f"  • {item.content}")

        if not results.long_term and not results.short_term:
            response_lines.append("No relevant memories found.")

        return [TextContent(type="text", text="\n".join(response_lines))]

    elif name == "get_recent_memories":
        n = arguments.get("n", 10)

        items = memory.short_term.get_recent(n)

        if not items:
            return [TextContent(
                type="text",
                text="No recent memories found."
            )]

        response_lines = [f"📋 Recent memories (last {len(items)} items):\n"]
        for i, item in enumerate(items, 1):
            response_lines.append(f"{i}. {item.content}")

        return [TextContent(type="text", text="\n".join(response_lines))]

    elif name == "get_memory_stats":
        stats = memory.stats()

        response = (
            "📊 Memory Statistics\n"
            "══════════════════════\n"
            f"Short-term Memory:\n"
            f"  • Size: {stats['short_term']['size']}/{stats['short_term']['max_size']}\n"
            f"  • Utilization: {stats['short_term']['utilization']}\n\n"
            f"Long-term Memory:\n"
            f"  • Items: {stats['long_term']['size']}\n"
            f"  • Model: {stats['long_term']['model']}"
        )

        return [TextContent(type="text", text=response)]

    elif name == "clear_memory":
        scope = arguments.get("scope", "all")

        if scope == "short":
            memory.clear_short_term()
            message = "Short-term memory cleared."
        elif scope == "long":
            memory.clear_long_term()
            message = "Long-term memory cleared."
        else:
            memory.clear_all()
            message = "All memory cleared."

        return [TextContent(type="text", text=f"✓ {message}")]

    else:
        return [TextContent(
            type="text",
            text=f"Error: Unknown tool '{name}'"
        )]


async def main():
    """Executa o servidor MCP."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
