# Sistema de Memória - Curto e Longo Prazo

Sistema de memória para aplicações de IA com suporte a:
- **Memória de Curto Prazo (STM)**: Baseada em deque com capacidade limitada e TTL
- **Memória de Longo Prazo (LTM)**: Usando FAISS para busca vetorial com embeddings locais
- **MCP Server**: Integração com Qwen-CLI via Model Context Protocol

## Instalação

### 1. Criar ambiente virtual (recomendado)

```bash
python3 -m venv venv
```

Ative o ambiente virtual:

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Instalar MCP (opcional, para Qwen-CLI)

```bash
pip install mcp
```

## Estrutura

```
├── short_term_memory.py   # Memória de curto prazo
├── long_term_memory.py    # Memória de longo prazo com FAISS
├── memory_manager.py      # Gerenciador unificado
├── mcp_server.py          # Servidor MCP para Qwen-CLI
├── example.py             # Exemplo de uso
└── requirements.txt       # Dependências
```

## Uso Básico

```python
from memory_manager import MemoryManager

# Inicializa
memory = MemoryManager(
    short_term_max_size=100,
    long_term_storage_path="./memory_storage",
    auto_consolidate=True
)

# Adiciona informações
memory.add("Python é uma linguagem de programação", importance=0.8)

# Busca semântica
result = memory.search("linguagem Python", top_k=5)

# Obtém contexto para LLMs
context = memory.get_context("como usar Python", max_items=10)
```

## MCP Server (Qwen-CLI)

O servidor MCP permite que o Qwen-CLI acesse a memória através de ferramentas.

### Configuração

Adicione ao arquivo de configuração do Qwen-CLI (`~/.qwen/config.json`):

```json
{
  "mcpServers": {
    "qwen-memory": {
      "command": "python",
      "args": ["/home/lechamps/qwen-space/mcp_server.py"],
      "cwd": "/home/lechamps/qwen-space"
    }
  }
}
```

### Ferramentas Disponíveis

| Ferramenta | Descrição |
|------------|-----------|
| `save_memory` | Salva informações na memória |
| `search_memory` | Busca informações relevantes |
| `get_recent_memories` | Recupera memórias recentes |
| `get_memory_stats` | Estatísticas de uso |
| `clear_memory` | Limpa a memória |

### Exemplo de Uso

No Qwen-CLI, após configurar:

```
User: Remember that I prefer Python
Assistant: [uses save_memory] ✓ Memory saved!

User: What do you know about my preferences?
Assistant: [uses search_memory] 
Search results for: 'preferences'
• [Score: 0.85] I prefer Python
```

Veja mais em: [MCP_README.md](MCP_README.md)

## API

### MemoryManager

| Método | Descrição |
|--------|-----------|
| `add(content, importance, store_long_term)` | Adiciona à memória |
| `add_batch(contents, importance, store_long_term)` | Adiciona em lote |
| `search(query, top_k)` | Busca nas duas memórias |
| `get_context(query, max_items)` | Obtém contexto relevante |
| `consolidate()` | Consolida STM → LTM |
| `clear_all()` | Limpa todas as memórias |
| `stats()` | Retorna estatísticas |

### Configurações

**Memória de Curto Prazo:**
- `short_term_max_size`: Capacidade máxima (padrão: 100)
- `short_term_ttl_minutes`: TTL em minutos (padrão: None)

**Memória de Longo Prazo:**
- `long_term_storage_path`: Diretório de persistência
- `long_term_model`: Modelo Sentence Transformer (padrão: `all-MiniLM-L6-v2`)
- `long_term_index_type`: Tipo de índice FAISS (`flat`, `ivf`, `hnsw`)
- `similarity_threshold`: Limiar de similaridade (padrão: 0.3)

## Executar Exemplo

```bash
python example.py
```

## Modelos de Embedding Disponíveis

- `all-MiniLM-L6-v2` (rápido, 384 dimensões)
- `all-mpnet-base-v2` (melhor qualidade, 768 dimensões)
- `paraphrase-multilingual-MiniLM-L12-v2` (multilíngue)

Veja mais em: https://www.sbert.net/docs/pretrained_models.html
