"""
Gerenciador de conversas.
Mantém o histórico e contexto por usuário, integrando com o sistema de memória.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import threading

from memory_manager import MemoryManager


@dataclass
class Message:
    """Mensagem individual em uma conversa."""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

    def format(self) -> str:
        """Formata a mensagem para exibição."""
        prefix = "Usuário" if self.role == "user" else "Assistente"
        return f"{prefix}: {self.content}"


@dataclass
class Conversation:
    """Conversa de um único usuário."""
    chat_id: int
    username: Optional[str]
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str) -> Message:
        """Adiciona uma mensagem à conversa."""
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self.last_activity = datetime.now()
        return msg

    def get_recent_messages(self, n: int = 10) -> list[str]:
        """Retorna as n mensagens mais recentes formatadas."""
        recent = self.messages[-n:] if len(self.messages) > n else self.messages
        return [msg.format() for msg in recent]

    def get_history_for_context(self, max_messages: int = 20) -> list[str]:
        """Retorna histórico formatado para contexto do agente."""
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [msg.content for msg in recent]

    def clear(self) -> None:
        """Limpa o histórico de mensagens."""
        self.messages.clear()


class ConversationManager:
    """
    Gerencia conversas de múltiplos usuários.
    
    Mantém o estado de cada conversa e integra com o sistema
    de memória para fornecer contexto ao agente de IA.
    """

    def __init__(
        self,
        memory: MemoryManager,
        max_history_per_user: int = 50,
        inactive_timeout_minutes: Optional[int] = None
    ):
        """
        Inicializa o gerenciador de conversas.

        Args:
            memory: Instância do MemoryManager para integração.
            max_history_per_user: Máximo de mensagens por usuário.
            inactive_timeout_minutes: Timeout para conversas inativas (None = sem timeout).
        """
        self._conversations: dict[int, Conversation] = {}
        self._lock = threading.Lock()
        self._memory = memory
        self._max_history = max_history_per_user
        self._inactive_timeout = inactive_timeout_minutes

    def get_or_create(
        self,
        chat_id: int,
        username: Optional[str] = None
    ) -> Conversation:
        """
        Obtém ou cria uma conversa para um usuário.

        Args:
            chat_id: ID único do chat no Telegram.
            username: Username do usuário (opcional).

        Returns:
            Conversa do usuário.
        """
        with self._lock:
            if chat_id not in self._conversations:
                self._conversations[chat_id] = Conversation(
                    chat_id=chat_id,
                    username=username
                )
            elif username and not self._conversations[chat_id].username:
                self._conversations[chat_id].username = username

            return self._conversations[chat_id]

    def add_message(
        self,
        chat_id: int,
        role: str,
        content: str,
        username: Optional[str] = None
    ) -> Message:
        """
        Adiciona uma mensagem à conversa de um usuário.

        Args:
            chat_id: ID do chat.
            role: "user" ou "assistant".
            content: Conteúdo da mensagem.
            username: Username do usuário.

        Returns:
            Mensagem adicionada.
        """
        with self._lock:
            conv = self.get_or_create(chat_id, username)

            # Limita histórico
            if len(conv.messages) >= self._max_history:
                # Remove mensagens antigas (mantém as mais recentes)
                conv.messages = conv.messages[-(self._max_history // 2):]

            return conv.add_message(role, content)

    def get_context(
        self,
        chat_id: int,
        query: str,
        max_history: int = 10,
        max_memories: int = 5
    ) -> tuple[list[str], list[tuple[str, float]]]:
        """
        Obtém contexto para uma query de um usuário específico.

        Args:
            chat_id: ID do chat.
            query: Texto da query para busca de memórias.
            max_history: Máximo de itens do histórico.
            max_memories: Máximo de memórias relevantes.

        Returns:
            Tupla (histórico_recente, memórias_relevantes).
        """
        with self._lock:
            conv = self._conversations.get(chat_id)

            # Histórico recente
            history = conv.get_history_for_context(max_history) if conv else []

            # Busca memórias relevantes
            results = self._memory.search(query, top_k=max_memories)

            # Combina resultados de longo prazo
            memories = [
                (item.content, score)
                for item, score in results.long_term
            ]

            return history, memories

    def save_to_memory(
        self,
        chat_id: int,
        content: str,
        importance: float = 0.5,
        store_long_term: bool = True
    ) -> dict:
        """
        Salva conteúdo na memória para um usuário.

        Args:
            chat_id: ID do chat.
            content: Conteúdo para salvar.
            importance: Nível de importância (0.0-1.0).
            store_long_term: Se True, salva também em longo prazo.

        Returns:
            Resultado da operação.
        """
        # Adiciona contexto do usuário
        conv = self._conversations.get(chat_id)
        username = conv.username if conv else f"User-{chat_id}"

        tagged_content = f"[{username}]: {content}"
        return self._memory.add(
            content=tagged_content,
            importance=importance,
            store_long_term=store_long_term
        )

    def get_conversation(self, chat_id: int) -> Optional[Conversation]:
        """
        Obtém uma conversa específica.

        Args:
            chat_id: ID do chat.

        Returns:
            Conversa ou None se não existir.
        """
        return self._conversations.get(chat_id)

    def list_active_chats(self) -> list[Conversation]:
        """
        Lista todas as conversas ativas.

        Returns:
            Lista de conversas.
        """
        with self._lock:
            return list(self._conversations.values())

    def cleanup_inactive(self) -> int:
        """
        Remove conversas inativas (se timeout estiver configurado).

        Returns:
            Número de conversas removidas.
        """
        if self._inactive_timeout is None:
            return 0

        with self._lock:
            now = datetime.now()
            to_remove = []

            for chat_id, conv in self._conversations.items():
                elapsed = (now - conv.last_activity).total_seconds() / 60
                if elapsed > self._inactive_timeout:
                    to_remove.append(chat_id)

            for chat_id in to_remove:
                del self._conversations[chat_id]

            return len(to_remove)

    def clear_conversation(self, chat_id: int) -> bool:
        """
        Limpa o histórico de uma conversa específica.

        Args:
            chat_id: ID do chat.

        Returns:
            True se a conversa existia, False caso contrário.
        """
        with self._lock:
            if chat_id in self._conversations:
                self._conversations[chat_id].clear()
                return True
            return False

    def stats(self) -> dict:
        """
        Retorna estatísticas das conversas.

        Returns:
            Dicionário com estatísticas.
        """
        with self._lock:
            total_messages = sum(
                len(conv.messages) for conv in self._conversations.values()
            )

            return {
                "active_chats": len(self._conversations),
                "total_messages": total_messages,
                "avg_messages_per_chat": (
                    total_messages / len(self._conversations)
                    if self._conversations else 0
                )
            }
