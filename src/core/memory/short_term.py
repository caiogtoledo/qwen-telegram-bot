"""
Módulo de memória de curto prazo.
Implementa uma memória baseada em deque com capacidade limitada e TTL opcional.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
import threading


@dataclass
class MemoryItem:
    """Item de memória com timestamp e conteúdo."""
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 1.0


class ShortTermMemory:
    """
    Memória de curto prazo com capacidade limitada e suporte a TTL.

    A memória de curto prazo armazena informações recentes que são
    rapidamente acessíveis mas podem ser esquecidas com o tempo.
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_minutes: Optional[int] = None
    ):
        """
        Inicializa a memória de curto prazo.

        Args:
            max_size: Número máximo de itens na memória.
            ttl_minutes: Tempo de vida dos itens em minutos (None = sem expiração).
        """
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._ttl = timedelta(minutes=ttl_minutes) if ttl_minutes else None
        self._max_size = max_size

    def add(self, content: Any, importance: float = 1.0) -> None:
        """
        Adiciona um item à memória.

        Args:
            content: Conteúdo a ser armazenado.
            importance: Nível de importância (0.0 a 1.0).
        """
        with self._lock:
            item = MemoryItem(content=content, importance=importance)
            self._buffer.append(item)

    def get_all(self) -> list[MemoryItem]:
        """
        Retorna todos os itens válidos (não expirados).

        Returns:
            Lista de itens de memória.
        """
        with self._lock:
            self._cleanup()
            return list(self._buffer)

    def get_recent(self, n: int = 10) -> list[MemoryItem]:
        """
        Retorna os n itens mais recentes.

        Args:
            n: Número de itens para retornar.

        Returns:
            Lista dos n itens mais recentes.
        """
        with self._lock:
            self._cleanup()
            return list(self._buffer)[-n:]

    def get_contents(self) -> list[Any]:
        """
        Retorna apenas os conteúdos dos itens válidos.

        Returns:
            Lista de conteúdos.
        """
        return [item.content for item in self.get_all()]

    def clear(self) -> None:
        """Limpa toda a memória."""
        with self._lock:
            self._buffer.clear()

    def size(self) -> int:
        """
        Retorna o número atual de itens.

        Returns:
            Número de itens na memória.
        """
        with self._lock:
            self._cleanup()
            return len(self._buffer)

    def _cleanup(self) -> None:
        """Remove itens expirados."""
        if self._ttl is None:
            return

        now = datetime.now()
        while self._buffer and (now - self._buffer[0].timestamp) > self._ttl:
            self._buffer.popleft()

    def consolidate(self) -> list[MemoryItem]:
        """
        Consolida a memória, retornando e removendo itens importantes.

        Este método é usado para transferir informações importantes
        da memória de curto prazo para a de longo prazo.

        Returns:
            Lista de itens importantes para consolidação.
        """
        with self._lock:
            self._cleanup()
            important_items = [
                item for item in self._buffer
                if item.importance > 0.7
            ]

            # Remove itens consolidados da memória de curto prazo
            self._buffer = deque(
                [item for item in self._buffer if item.importance <= 0.7],
                maxlen=self._max_size
            )

            return important_items

    def __len__(self) -> int:
        return self.size()

    def __repr__(self) -> str:
        return f"ShortTermMemory(size={len(self)}, max={self._max_size})"
