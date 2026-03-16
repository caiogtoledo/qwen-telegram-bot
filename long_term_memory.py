"""
Módulo de memória de longo prazo usando FAISS e embeddings locais.
Implementa armazenamento vetorial persistente com busca semântica.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading
import pickle
import logging
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except (ImportError, OSError):
    FAISS_AVAILABLE = False
    faiss = None

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class LongTermMemoryItem:
    """Item de memória de longo prazo."""
    id: int
    content: str
    embedding: np.ndarray
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class LongTermMemory:
    """
    Memória de longo prazo usando FAISS para busca vetorial eficiente.
    
    Utiliza embeddings locais gerados por modelos Sentence Transformers
    para permitir busca semântica sobre o conteúdo armazenado.
    """
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        model_name: str = DEFAULT_MODEL,
        index_type: str = "flat",
        similarity_threshold: float = 0.3
    ):
        """
        Inicializa a memória de longo prazo.

        Args:
            storage_path: Diretório para persistência dos dados.
            model_name: Nome do modelo Sentence Transformer para embeddings.
            index_type: Tipo de índice FAISS ("flat", "ivf", "hnsw").
            similarity_threshold: Limiar mínimo de similaridade para buscas.
        """
        logger.info(f"[LTM] LongTermMemory iniciando: model={model_name}, path={storage_path}")
        
        self._storage_path = Path(storage_path) if storage_path else None
        self._model_name = model_name
        self._similarity_threshold = similarity_threshold
        self._lock = threading.Lock()

        # Carregamento lazy do modelo (feito na primeira busca/add)
        self._model = None
        self._embedding_dim = None

        # Inicializa índice FAISS ou usa fallback - também lazy
        self._index = None
        self._index_type = index_type
        self._use_faiss = FAISS_AVAILABLE
        
        if self._use_faiss:
            logger.info("[LTM] FAISS disponível, índice será criado lazy")
        else:
            # Fallback: usa busca por similaridade com numpy
            self._embeddings_list = []
            logger.info("[LTM] FAISS não disponível, usando fallback numpy")

        # Armazena metadados dos itens
        self._items: dict[int, LongTermMemoryItem] = {}
        self._next_id = 0
        
        logger.info(f"[LTM] LongTermMemory inicializado (modelo e índice lazy)")
        
        # Carrega dados persistidos se existirem
        self._load()

        # Carrega o modelo eagerly na inicialização para evitar latência na primeira requisição
        self._ensure_model_loaded()

    def _ensure_model_loaded(self):
        """Carrega o modelo de embeddings e cria o índice sob demanda (lazy loading)."""
        if self._model is None:
            logger.info(f"[LTM] Carregando modelo {self._model_name}...")
            import time
            start = time.time()
            self._model = SentenceTransformer(self._model_name)
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
            elapsed = time.time() - start
            logger.info(f"[LTM] Modelo carregado em {elapsed:.2f}s, dim={self._embedding_dim}")
            
            # Cria o índice FAISS agora que temos a dimensão
            if self._use_faiss and self._index is None:
                logger.info(f"[LTM] Criando índice FAISS tipo={self._index_type}")
                self._index = self._create_index(self._index_type)
    
    def _create_index(self, index_type: str) -> faiss.Index:
        """
        Cria índice FAISS baseado no tipo especificado.
        
        Args:
            index_type: Tipo de índice ("flat", "ivf", "hnsw").
            
        Returns:
            Índice FAISS inicializado.
        """
        if index_type == "flat":
            return faiss.IndexFlatIP(self._embedding_dim)
        elif index_type == "ivf":
            # IVF para datasets maiores (>1000 itens)
            quantizer = faiss.IndexFlatIP(self._embedding_dim)
            return faiss.IndexIVFFlat(quantizer, self._embedding_dim, 100)
        elif index_type == "hnsw":
            # HNSW para busca rápida aproximada
            return faiss.IndexHNSWFlat(self._embedding_dim, 32)
        else:
            raise ValueError(f"Tipo de índice desconhecido: {index_type}")
    
    def add(self, content: str, metadata: Optional[dict] = None) -> int:
        """
        Adiciona um item à memória de longo prazo.
        
        Args:
            content: Conteúdo textual a ser armazenado.
            metadata: Metadados opcionais associados ao item.
            
        Returns:
            ID do item adicionado.
        """
        with self._lock:
            # Garante que o modelo está carregado
            self._ensure_model_loaded()
            
            # Gera embedding
            embedding = self._model.encode(
                [content],
                normalize_embeddings=True,
                convert_to_numpy=True
            )[0]
            
            # Adiciona ao índice FAISS
            self._index.add(embedding.reshape(1, -1))
            
            # Cria e armazena item
            item = LongTermMemoryItem(
                id=self._next_id,
                content=content,
                embedding=embedding,
                metadata=metadata or {}
            )
            self._items[self._next_id] = item
            item_id = self._next_id
            self._next_id += 1
            
            # Persiste se houver caminho configurado
            if self._storage_path:
                self._save()
            
            return item_id
    
    def add_batch(self, contents: list[str]) -> list[int]:
        """
        Adiciona múltiplos itens em lote.
        
        Args:
            contents: Lista de conteúdos para adicionar.
            
        Returns:
            Lista de IDs dos itens adicionados.
        """
        with self._lock:
            # Garante que o modelo está carregado
            self._ensure_model_loaded()
            
            # Gera embeddings em lote
            embeddings = self._model.encode(
                contents,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            
            # Adiciona ao índice
            self._index.add(embeddings)
            
            # Cria itens
            ids = []
            for i, content in enumerate(contents):
                item = LongTermMemoryItem(
                    id=self._next_id,
                    content=content,
                    embedding=embeddings[i],
                    metadata={}
                )
                self._items[self._next_id] = item
                ids.append(self._next_id)
                self._next_id += 1
            
            if self._storage_path:
                self._save()
            
            return ids
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> list[tuple[LongTermMemoryItem, float]]:
        """
        Busca itens similares na memória.
        
        Args:
            query: Texto de busca.
            top_k: Número máximo de resultados.
            threshold: Limiar de similaridade (sobrescreve o padrão).
            
        Returns:
            Lista de tuplas (item, score_de_similaridade).
        """
        with self._lock:
            threshold = threshold if threshold is not None else self._similarity_threshold

            # Garante que o modelo está carregado
            self._ensure_model_loaded()

            # Gera embedding da query
            query_embedding = self._model.encode(
                [query],
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            
            # Busca no índice
            actual_k = min(top_k, len(self._items))
            if actual_k == 0:
                return []
            
            scores, indices = self._index.search(query_embedding, actual_k)
            
            # Filtra por threshold e monta resultados
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self._items) and score >= threshold:
                    item = self._items[int(idx)]
                    results.append((item, float(score)))
            
            return results
    
    def search_by_id(self, item_id: int) -> Optional[LongTermMemoryItem]:
        """
        Busca um item específico pelo ID.
        
        Args:
            item_id: ID do item.
            
        Returns:
            Item encontrado ou None.
        """
        return self._items.get(item_id)
    
    def remove(self, item_id: int) -> bool:
        """
        Remove um item da memória.
        
        Nota: FAISS não suporta remoção direta. O item é removido
        dos metadados mas permanece no índice (baixo impacto).
        
        Args:
            item_id: ID do item a remover.
            
        Returns:
            True se removido, False se não encontrado.
        """
        with self._lock:
            if item_id in self._items:
                del self._items[item_id]
                if self._storage_path:
                    self._save()
                return True
            return False
    
    def clear(self) -> None:
        """Limpa toda a memória."""
        with self._lock:
            self._index = self._create_index("flat")
            self._items.clear()
            self._next_id = 0
            if self._storage_path:
                self._save()
    
    def size(self) -> int:
        """
        Retorna o número de itens armazenados.
        
        Returns:
            Número de itens na memória.
        """
        return len(self._items)
    
    def get_all(self) -> list[LongTermMemoryItem]:
        """
        Retorna todos os itens armazenados.
        
        Returns:
            Lista de todos os itens.
        """
        return list(self._items.values())
    
    def _save(self) -> None:
        """Persiste os dados em disco."""
        if not self._storage_path:
            return
            
        if self._index is None:
            logger.warning("[LTM] Tentativa de salvar sem índice carregado")
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Salva índice FAISS
        faiss.write_index(
            self._index,
            str(self._storage_path / "index.faiss")
        )

        # Salva metadados
        metadata = {
            "items": {
                k: {
                    "id": v.id,
                    "content": v.content,
                    "timestamp": v.timestamp.isoformat(),
                    "metadata": v.metadata
                }
                for k, v in self._items.items()
            },
            "next_id": self._next_id
        }
        with open(self._storage_path / "metadata.pkl", "wb") as f:
            pickle.dump(metadata, f)
    
    def _load(self) -> None:
        """Carrega dados persistidos."""
        if not self._storage_path:
            return
            
        index_path = self._storage_path / "index.faiss"
        metadata_path = self._storage_path / "metadata.pkl"

        if not (index_path.exists() and metadata_path.exists()):
            logger.info(f"[LTM] Nenhum dado persistido encontrado em {self._storage_path}")
            return

        try:
            logger.info(f"[LTM] Carregando dados persistidos...")
            
            # Carrega índice
            self._index = faiss.read_index(str(index_path))
            logger.info(f"[LTM] Índice FAISS carregado: {self._index.ntotal} vetores")

            # Carrega metadados
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)

            self._next_id = metadata.get("next_id", 0)
            
            # Tenta obter dimensão do índice
            if self._index.ntotal > 0:
                self._embedding_dim = self._index.d
                logger.info(f"[LTM] Dimensão do índice: {self._embedding_dim}")

            # Reconstrói embeddings para os itens
            if self._index.ntotal > 0:
                all_embeddings = self._index.reconstruct_n(0, self._index.ntotal)

                for key, item_data in metadata.get("items", {}).items():
                    item = LongTermMemoryItem(
                        id=item_data["id"],
                        content=item_data["content"],
                        embedding=all_embeddings[item_data["id"]],
                        timestamp=datetime.fromisoformat(item_data["timestamp"]),
                        metadata=item_data.get("metadata", {})
                    )
                    self._items[int(key)] = item
                    
            logger.info(f"[LTM] Carregados {len(self._items)} itens")

        except Exception as e:
            logger.error(f"[LTM] Erro ao carregar memória: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Reinicia com estado limpo em caso de erro
            if self._use_faiss and self._index is None:
                self._index = self._create_index("flat")
            self._items.clear()
            self._next_id = 0
    
    def __len__(self) -> int:
        return self.size()
    
    def __repr__(self) -> str:
        return f"LongTermMemory(items={len(self)}, model={self._model_name})"