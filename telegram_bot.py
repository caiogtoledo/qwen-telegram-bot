#!/usr/bin/env python3
"""
Bot do Telegram integrado com Qwen-Code.
Permite conversar com o agente de IA através do Telegram,
mantendo histórico e usando o sistema de memória.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from memory_manager import MemoryManager
from conversation_manager import ConversationManager
from qwen_agent import QwenAgent

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


class TelegramQwenBot:
    """
    Bot do Telegram que integra com Qwen-Code.
    
    Permite conversar com o agente de IA através do Telegram,
    mantendo contexto e usando memória de longo/curto prazo.
    """

    # IDs de usuários autorizados
    AUTHORIZED_USERS = [5827420769]  # Adicione mais IDs se necessário

    def __init__(
        self,
        token: str,
        qwen_command: str = "qwen",
        memory_path: str = "./memory_storage",
        max_history: int = 20,
        max_memories: int = 5
    ):
        """
        Inicializa o bot.

        Args:
            token: Token do bot do Telegram.
            qwen_command: Comando para invocar qwen-code.
            memory_path: Caminho para armazenamento da memória.
            max_history: Máximo de mensagens de histórico para contexto.
            max_memories: Máximo de memórias relevantes para contexto.
        """
        self.token = token
        self.max_history = max_history
        self.max_memories = max_memories

        # Inicializa sistema de memória
        self.memory = MemoryManager(
            short_term_max_size=100,
            long_term_storage_path=memory_path,
            auto_consolidate=True
        )

        # Gerenciador de conversas
        self.conv_manager = ConversationManager(
            memory=self.memory,
            max_history_per_user=50
        )

        # Agente Qwen
        self.qwen_agent = QwenAgent(qwen_command=qwen_command)

        # Aplicação do Telegram
        self.application: Optional[Application] = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para o comando /start."""
        user = update.effective_user
        chat_id = update.effective_chat.id

        # Cria/obtém conversa
        self.conv_manager.get_or_create(chat_id, user.username if user else None)

        welcome_msg = (
            f"Olá {user.first_name if user else 'Usuário'}! 👋\n\n"
            "Sou um bot integrado com Qwen-Code. Posso:\n"
            "• Conversar naturalmente mantendo contexto\n"
            "• Lembrar de informações importantes\n"
            "• Buscar conhecimento relevante\n\n"
            "Comandos disponíveis:\n"
            "/start - Reinicia a conversa\n"
            "/clear - Limpa histórico do chat\n"
            "/memory - Mostra estatísticas da memória\n"
            "/help - Ajuda\n\n"
            "Pode começar a conversar!"
        )

        await update.message.reply_text(welcome_msg)
        logger.info(f"Usuário {user.first_name} iniciou o bot")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para o comando /help."""
        help_text = (
            "🤖 **Bot Telegram + Qwen-Code**\n\n"
            "Este bot permite conversar com o agente de IA Qwen-Code,\n"
            "mantendo histórico e usando memória inteligente.\n\n"
            "**Comandos:**\n"
            "/start - Inicia/reinicia conversa\n"
            "/clear - Limpa histórico deste chat\n"
            "/memory - Estatísticas da memória\n"
            "/help - Mostra esta ajuda\n\n"
            "**Dicas:**\n"
            "• O bot lembra do contexto da conversa\n"
            "• Informações importantes são salvas automaticamente\n"
            "• Quanto mais você conversa, mais o bot te conhece!"
        )

        await update.message.reply_text(help_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para o comando /clear."""
        chat_id = update.effective_chat.id

        self.conv_manager.clear_conversation(chat_id)

        await update.message.reply_text(
            "🗑️ Histórico deste chat foi limpo!\n"
            "A memória de longo prazo permanece intacta."
        )
        logger.info(f"Chat {chat_id} limpou histórico")

    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para o comando /memory."""
        stats = self.memory.stats()
        conv_stats = self.conv_manager.stats()

        memory_info = (
            "📊 **Estatísticas da Memória**\n\n"
            f"**Curto Prazo:**\n"
            f"  • Itens: {stats['short_term']['size']}/{stats['short_term']['max_size']}\n"
            f"  • Uso: {stats['short_term']['utilization']}\n\n"
            f"**Longo Prazo:**\n"
            f"  • Itens: {stats['long_term']['size']}\n"
            f"  • Modelo: {stats['long_term']['model']}\n\n"
            f"**Conversas:**\n"
            f"  • Chats ativos: {conv_stats['active_chats']}\n"
            f"  • Total mensagens: {conv_stats['total_messages']:.0f}"
        )

        await update.message.reply_text(memory_info)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para mensagens de texto."""
        logger.debug(f"Update recebido: {update}")
        
        if not update.message or not update.message.text:
            logger.warning("Mensagem vazia ou inválida")
            return

        user = update.effective_user
        chat_id = update.effective_chat.id
        
        logger.info(f"Usuário ID: {user.id}, Nome: {user.first_name}")
        logger.info(f"AUTHORIZED_USERS: {self.AUTHORIZED_USERS}")

        # Verifica se o usuário está autorizado
        if user.id not in self.AUTHORIZED_USERS:
            logger.warning(f"Usuário não autorizado tentou acesso: {user.first_name} (ID: {user.id})")
            await update.message.reply_text(
                "⛔ Acesso negado. Este bot é privado."
            )
            return

        message_text = update.message.text.strip()
        logger.info(f"Mensagem recebida de {user.first_name}: {message_text[:50]}...")

        # Ignora mensagens vazias
        if not message_text:
            return

        # Adiciona mensagem do usuário ao histórico
        self.conv_manager.add_message(
            chat_id=chat_id,
            role="user",
            content=message_text,
            username=user.username if user else None
        )

        # Envia "digitando..." para feedback
        await update.message.chat_action(action="typing")

        # Obtém contexto (histórico + memórias relevantes)
        history, memories = self.conv_manager.get_context(
            chat_id=chat_id,
            query=message_text,
            max_history=self.max_history,
            max_memories=self.max_memories
        )

        # Chama Qwen-Code
        response = self.qwen_agent.chat_with_memory(
            message=message_text,
            recent_history=history,
            relevant_memories=memories,
            max_history=10,
            max_memories=5
        )

        logger.info(f"Resposta Qwen: {response[:100]}...")

        # Adiciona resposta ao histórico
        self.conv_manager.add_message(
            chat_id=chat_id,
            role="assistant",
            content=response
        )

        # Salva interação na memória (importância média)
        # Salva tanto a pergunta quanto a resposta
        self.conv_manager.save_to_memory(
            chat_id=chat_id,
            content=f"Pergunta: {message_text}",
            importance=0.6,
            store_long_term=True
        )
        self.conv_manager.save_to_memory(
            chat_id=chat_id,
            content=f"Resposta: {response[:500]}",  # Limita tamanho
            importance=0.5,
            store_long_term=True
        )

        # Envia resposta (pode ser longa, então divide se necessário)
        await self._send_long_message(update.message, response)

    async def _send_long_message(self, message, text: str, max_length: int = 4096):
        """
        Envia mensagem longa, dividindo se necessário.

        O Telegram tem limite de 4096 caracteres por mensagem.
        """
        if len(text) <= max_length:
            await message.reply_text(text)
            return

        # Divide em múltiplas mensagens
        parts = []
        while len(text) > max_length:
            # Encontra último espaço antes do limite
            split_at = text.rfind(" ", 0, max_length)
            if split_at == -1:
                split_at = max_length

            parts.append(text[:split_at])
            text = text[split_at:].strip()

        if text:
            parts.append(text)

        # Envia cada parte
        for i, part in enumerate(parts):
            if i > 0:
                await asyncio.sleep(0.5)  # Pequeno delay entre mensagens
            await message.reply_text(part)

    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para erros."""
        logger.error(f"Erro em update {update}: {context.error}")

        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Ocorreu um erro ao processar sua mensagem.\n"
                "Tente novamente ou use /help para mais informações."
            )

    def run(self) -> None:
        """
        Inicia o bot.
        
        Este método é bloqueante e roda até o bot ser parado.
        """
        # Verifica se qwen-code está disponível
        if not self.qwen_agent.is_available():
            logger.warning(
                "⚠️  qwen-code não encontrado no PATH. "
                "Certifique-se de que está instalado e acessível."
            )

        logger.info("Iniciando bot do Telegram...")
        logger.info(f"Memória: {self.memory.stats()}")

        # Cria aplicação
        self.application = (
            Application.builder()
            .token(self.token)
            .build()
        )

        # Adiciona handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("memory", self.memory_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Adiciona handler de erros
        self.application.add_error_handler(self.handle_error)

        # Inicia polling
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Ponto de entrada principal."""
    # Pega token do ambiente ou variável
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ Erro: TELEGRAM_BOT_TOKEN não definido!")
        print("\nPara obter um token:")
        print("1. Abra o Telegram e busque por @BotFather")
        print("2. Envie /newbot e siga as instruções")
        print("3. Copie o token e defina a variável de ambiente:")
        print("   export TELEGRAM_BOT_TOKEN='seu-token-aqui'")
        return 1

    # Cria e executa bot
    bot = TelegramQwenBot(
        token=token,
        qwen_command=os.getenv("QWEN_COMMAND", "qwen"),
        memory_path=os.getenv("MEMORY_PATH", "./memory_storage")
    )

    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nBot parado pelo usuário.")
    except Exception as e:
        logger.error(f"Erro ao executar bot: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
