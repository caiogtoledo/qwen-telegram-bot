"""
Infraestrutura - integrações externas (Telegram, MCP, etc).
"""

from .telegram import TelegramQwenBot
from .mcp import server

__all__ = ["TelegramQwenBot", "server"]
