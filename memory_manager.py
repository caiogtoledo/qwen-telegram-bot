"""
Gerenciador principal de memória.
Integra memória de curto e longo prazo em uma interface unificada.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import logging

from short_term_memory import ShortTermMemory, MemoryItem
from long_term_memory import LongTermMemory, LongTermMemoryItem

logger = logging.getLogger(__name__)


@dataclass
class MemoryResult:
    """Resultado de uma operação de memória."""
    short_term: list[MemoryItem]
    long_term: list[tuple[LongTermMemoryItem, float]]
    query: str


class MemoryManager:
    """
    Gerenciador unificado de memória de curto e longo prazo.
    
    Fornece uma interface simples para armazenar e recuperar
    informações usando ambos os tipos de memória de forma integrada.
    """
    
    def __init__(
        self,
        short_term_max_size: int = 100,
        short_term_ttl_minutes: Optional[int] = None,
        long_term_storage_path: Optional[str] = None,
        long_term_model: str = "all-MiniLM-L6-v2",
        long_term_index_type: str = "flat",
        similarity_threshold: float = 0.3,
        auto_consolidate: bool = True,
        consolidation_threshold: int = 80
    ):
        """
        Inicializa o gerenciador de memória.
        
        Args:
            short_term_max_size: Capacidade máxima da memória de curto prazo.
            short_term_ttl_minutes: TTL dos itens de curto prazo (None = sem expiração).
            long_term_storage_path: Diretório para persistência da memória de longo prazo.
            long_term_model: Modelo para embeddings locais.
            long_term_index_type: Tipo de índice FAISS ("flat", "ivf", "hnsw").
            similarity_threshold: Limiar de similaridade para buscas.
            auto_consolidate: Se deve consolidar automaticamente quando STM estiver cheia.
            consolidation_threshold: Porcentagem da capacidade para trigger de consolidação.
        """
        self._short_term = ShortTermMemory(
            max_size=short_term_max_size,
            ttl_minutes=short_term_ttl_minutes
        )
        
        self._long_term = LongTermMemory(
            storage_path=long_term_storage_path,
            model_name=long_term_model,
            index_type=long_term_index_type,
            similarity_threshold=similarity_threshold
        )
        
        self._auto_consolidate = auto_consolidate
        self._consolidation_threshold = consolidation_threshold
    
    def add(
        self, 
        content: str, 
        importance: float = 1.0,
        store_long_term: bool = True
    ) -> dict:
        """
        Adiciona informação à memória.
        
        Args:
            content: Conteúdo a ser armazenado.
            importance: Nível de importância (0.0-1.0) para memória de curto prazo.
            store_long_term: Se True, também armazena na memória de longo prazo.
            
        Returns:
            Dicionário com informações sobre o armazenamento.
        """
        result = {"short_term": True, "long_term": None}
        
        # Sempre adiciona à memória de curto prazo
        self._short_term.add(content, importance=importance)
        
        # Adiciona à memória de longo prazo se configurado
        if store_long_term:
            result["long_term"] = self._long_term.add(content)
        
        # Verifica necessidade de consolidação automática
        if self._auto_consolidate:
            self._check_consolidation()
        
        return result
    
    def add_batch(
        self,
        contents: list[str],
        importance: float = 1.0,
        store_long_term: bool = True
    ) -> dict:
        """
        Adiciona múltiplos itens à memória.
        
        Args:
            contents: Lista de conteúdos para adicionar.
            importance: Nível de importância para memória de curto prazo.
            store_long_term: Se True, também armazena na memória de longo prazo.
            
        Returns:
            Dicionário com informações sobre o armazenamento.
        """
        result = {"short_term": len(contents), "long_term": None}
        
        # Adiciona à memória de curto prazo
        for content in contents:
            self._short_term.add(content, importance=importance)
        
        # Adiciona à memória de longo prazo em lote
        if store_long_term:
            result["long_term"] = self._long_term.add_batch(contents)
        
        # Verifica necessidade de consolidação automática
        if self._auto_consolidate:
            self._check_consolidation()
        
        return result
    
    def search(self, query: str, top_k: int = 5) -> MemoryResult:
        """
        Busca informações relevantes na memória.

        Args:
            query: Texto de busca.
            top_k: Número máximo de resultados de cada memória.

        Returns:
            MemoryResult com resultados de ambas as memórias.
        """
        logger.info(f"[MEM] search() iniciado: query={query[:50]}..., top_k={top_k}")
        
        logger.info(f"[MEM] Buscando na short_term...")
        short_results = self._short_term.get_recent(top_k)
        logger.info(f"[MEM] Short_term: {len(short_results)} resultados")
        
        logger.info(f"[MEM] Buscando na long_term...")
        long_results = self._long_term.search(query, top_k=top_k)
        logger.info(f"[MEM] Long_term: {len(long_results)} resultados")

        return MemoryResult(
            short_term=short_results,
            long_term=long_results,
            query=query
        )
    
    def get_context(self, query: str, max_items: int = 10) -> list[str]:
        """
        Obtém contexto relevante para uma query.
        
        Útil para fornecer contexto a modelos de linguagem.
        
        Args:
            query: Texto de busca.
            max_items: Número máximo de itens de contexto.
            
        Returns:
            Lista de conteúdos relevantes.
        """
        result = self.search(query, top_k=max_items // 2)
        
        # Combina resultados priorizando os mais relevantes
        contents = []
        
        # Adiciona resultados de longo prazo (busca semântica)
        for item, score in result.long_term:
            contents.append(f"[Relevância: {score:.2f}] {item.content}")
        
        # Adiciona resultados recentes de curto prazo
        for item in result.short_term:
            contents.append(f"[Recente] {item.content}")
        
        return contents[:max_items]
    
    def consolidate(self) -> int:
        """
        Consolida manualmente a memória de curto para longo prazo.
        
        Transferencia itens importantes da memória de curto prazo
        para a memória de longo prazo.
        
        Returns:
            Número de itens consolidados.
        """
        important_items = self._short_term.consolidate()
        
        if important_items:
            contents = [item.content for item in important_items]
            self._long_term.add_batch(contents)
        
        return len(important_items)
    
    def _check_consolidation(self) -> None:
        """Verifica e executa consolidação automática se necessário."""
        capacity_ratio = len(self._short_term) / self._short_term._max_size
        
        if capacity_ratio >= (self._consolidation_threshold / 100):
            consolidated = self.consolidate()
            if consolidated > 0:
                print(f"[Memória] {consolidated} itens consolidados para longo prazo")
    
    def clear_short_term(self) -> None:
        """Limpa a memória de curto prazo."""
        self._short_term.clear()
    
    def clear_long_term(self) -> None:
        """Limpa a memória de longo prazo."""
        self._long_term.clear()
    
    def clear_all(self) -> None:
        """Limpa todas as memórias."""
        self.clear_short_term()
        self.clear_long_term()
    
    @property
    def short_term(self) -> ShortTermMemory:
        """Acesso direto à memória de curto prazo."""
        return self._short_term
    
    @property
    def long_term(self) -> LongTermMemory:
        """Acesso direto à memória de longo prazo."""
        return self._long_term
    
    def stats(self) -> dict:
        """
        Retorna estatísticas das memórias.
        
        Returns:
            Dicionário com estatísticas.
        """
        return {
            "short_term": {
                "size": len(self._short_term),
                "max_size": self._short_term._max_size,
                "utilization": f"{len(self._short_term) / self._short_term._max_size * 100:.1f}%"
            },
            "long_term": {
                "size": len(self._long_term),
                "model": self._long_term._model_name
            }
        }
    
    def __repr__(self) -> str:
        return (
            f"MemoryManager(\n"
            f"  short_term={self._short_term},\n"
            f"  long_term={self._long_term}\n"
            f")"
        )