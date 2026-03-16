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

        # Envia "digitando..." e "hmm..." IMEDIATAMENTE para feedback
        thinking_message = None
        try:
            await update.effective_message.chat_action(action="typing")
            logger.info(f"[BOT] Enviando mensagem 'hmm...' para chat {chat_id}")
            thinking_message = await update.effective_message.reply_text("🤔 hmm...")
            logger.info(f"[BOT] Mensagem 'hmm...' enviada com message_id={thinking_message.message_id}")
        except Exception as e:
            logger.warning(f"[BOT] Erro ao enviar status inicial: {e}")

        # Obtém contexto (histórico + memórias relevantes)

        logger.info(f"[BOT] Obtendo contexto com get_context()...")
        try:
            # Timeout de 10 segundos para obter contexto
            history, memories = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.conv_manager.get_context(
                        chat_id=chat_id,
                        query=message_text,
                        max_history=self.max_history,
                        max_memories=self.max_memories
                    )
                ),
                timeout=10
            )
            logger.info(f"[BOT] Contexto obtido: {len(history)} history, {len(memories)} memories")
        except asyncio.TimeoutError:
            logger.error(f"[BOT] TIMEOUT de 10s ao obter contexto")
            history, memories = [], []
            logger.info(f"[BOT] Usando fallback sem memória")
        except Exception as e:
            logger.error(f"[BOT] ERRO ao obter contexto: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback: usa apenas histórico vazio
            history, memories = [], []
            logger.info(f"[BOT] Usando fallback sem memória")

        # Chama Qwen-Code em uma thread separada para não bloquear o event loop
        logger.info(f"[BOT] INICIANDO chamada qwen_agent em thread separada")
        logger.info(f"[BOT] Mensagem: {message_text[:50]}...")
        
        async def call_qwen():
            return await self.qwen_agent.chat_with_memory_async(
                message=message_text,
                recent_history=history,
                relevant_memories=memories,
                max_history=10,
                max_memories=5
            )
        
        try:
            # Usa asyncio.wait_for com timeout absoluto
            response = await asyncio.wait_for(call_qwen(), timeout=60)
            logger.info(f"[BOT] qwen_agent COMPLETOU em menos de 60s")
        except asyncio.TimeoutError:
            logger.error(f"[BOT] TIMEOUT de 60s atingido!")
            response = "⚠️ Desculpe, a resposta está demorando mais que o esperado. Tente novamente."
        except Exception as e:
            logger.error(f"[BOT] ERRO em chat_with_memory_async: {e}")
            import traceback
            logger.error(traceback.format_exc())
            response = f"[Erro ao processar] {str(e)}"

        logger.info(f"[BOT] Resposta Qwen ({len(response)} chars): {response[:100]}...")

        # Adiciona resposta ao histórico ANTES de enviar para garantir que está salvo
        self.conv_manager.add_message(
            chat_id=chat_id,
            role="assistant",
            content=response
        )

        # Envia resposta (pode ser longa, então divide se necessário)
        # Se for curta, tenta editar a mensagem "hmm..."
        if len(response) <= 4096:
            if thinking_message:
                try:
                    await thinking_message.edit_text(response)
                    logger.debug("Mensagem 'hmm...' editada com a resposta.")
                except Exception as e:
                    logger.warning(f"Falha ao editar mensagem: {e}. Enviando nova mensagem.")
                    await self._send_long_message(update.effective_message, response)
                    try:
                        await thinking_message.delete()
                    except:
                        pass
            else:
                # Se não temos thinking_message, enviamos normalmente
                await self._send_long_message(update.effective_message, response)
        else:
            # Se for longa, deleta o "hmm..." e envia em partes
            if thinking_message:
                try:
                    await thinking_message.delete()
                except:
                    pass
            await self._send_long_message(update.effective_message, response)

        # Salva interação na memória (importância média)
        try:
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
        except Exception as e:
            logger.error(f"[BOT] Erro ao salvar na memória: {e}")

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

    async def on_startup(self, application):
        """Executado quando o bot inicia."""
        logger.info("Bot iniciado! Aguardando mensagens em tempo real...")
        # Remove webhook para garantir que polling funcione
        await application.bot.delete_webhook()
        logger.info("Webhook removido, polling ativo")

    async def on_shutdown(self, application):
        """Executado quando o bot está parando."""
        logger.info("Bot está parando... limpando recursos...")


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

    # Cria bot
    bot = TelegramQwenBot(
        token=token,
        qwen_command=os.getenv("QWEN_COMMAND", "qwen"),
        memory_path=os.getenv("MEMORY_PATH", "./memory_storage")
    )

    async def run_async():
        """Executa o bot assincronamente."""
        logger.info("Iniciando bot do Telegram...")
        logger.info(f"Memória: {bot.memory.stats()}")

        # Cria aplicação
        app = (
            Application.builder()
            .token(bot.token)
            .post_init(bot.on_startup)
            .post_shutdown(bot.on_shutdown)
            .build()
        )

        # Adiciona handlers
        app.add_handler(CommandHandler("start", bot.start_command))
        app.add_handler(CommandHandler("help", bot.help_command))
        app.add_handler(CommandHandler("clear", bot.clear_command))
        app.add_handler(CommandHandler("memory", bot.memory_command))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message)
        )
        app.add_error_handler(bot.handle_error)

        # Inicia polling
        await app.initialize()
        await app.start()
        await app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            timeout=30,
            drop_pending_updates=True
        )

        # Mantém rodando até ser interrompido
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Parando updater...")
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    try:
        asyncio.run(run_async())
    except KeyboardInterrupt:
        logger.info("Bot parado pelo usuário (KeyboardInterrupt).")
    except Exception as e:
        logger.error(f"Erro ao executar bot: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
