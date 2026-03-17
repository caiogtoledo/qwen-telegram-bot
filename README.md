# Qwen Space - QwenCode conectado no Bot do Telegram

Sistema de memória para aplicações de IA com suporte a:
- **Memória de Curto Prazo (STM)**: Baseada em deque com capacidade limitada e TTL
- **Memória de Longo Prazo (LTM)**: Usando FAISS para busca vetorial com embeddings locais
- **MCP Server**: Integração com Qwen-CLI via Model Context Protocol
- **Telegram Bot**: Interface de conversa via Telegram

## 📁 Estrutura do Projeto

```
qwen-space/
├── src/
│   ├── core/                    # Núcleo do sistema
│   │   ├── memory/              # Sistema de memória
│   │   │   ├── short_term.py
│   │   │   ├── long_term.py
│   │   │   └── manager.py
│   │   └── conversation/        # Gerenciamento de conversas
│   │       └── manager.py
│   │
│   ├── agents/                  # Agentes de IA
│   │   └── qwen_agent.py
│   │
│   └── infrastructure/          # Integrações externas
│       ├── telegram/
│       │   └── bot.py
│       └── mcp/
│           └── server.py
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── scripts/
│   └── setup_env.sh
│
├── config/
│   └── mcp_server_config.json
│
├── .env.example
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## 🚀 Instalação

### 1. Usar o script de setup (recomendado)

```bash
./scripts/setup_env.sh
```

### 2. Instalação manual

Criar ambiente virtual:

```bash
python3 -m venv venv
```

Ativar o ambiente virtual:

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

Instalar dependências:

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` e adicione seu token do Telegram:

```
TELEGRAM_BOT_TOKEN=seu-token-aqui
```

## 📖 Uso Básico

```python
from src.core.memory import MemoryManager

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

## 🤖 Telegram Bot

Executar o bot:

```bash
python -m src.infrastructure.telegram.bot
```

### Comandos do Bot

| Comando | Descrição |
|---------|-----------|
| `/start` | Inicia/reinicia a conversa |
| `/clear` | Limpa histórico do chat |
| `/memory` | Mostra estatísticas da memória |
| `/help` | Mostra ajuda |

## 🔧 MCP Server (Qwen-CLI)

O servidor MCP permite que o Qwen-CLI acesse a memória através de ferramentas.

### Configuração

Adicione ao arquivo de configuração do Qwen-CLI (`~/.qwen/config.json`):

```json
{
  "mcpServers": {
    "qwen-memory": {
      "command": "python",
      "args": ["-m", "src.infrastructure.mcp.server"],
      "cwd": "/path/to/qwen-space"
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

## 🧪 Testes

Executar testes de integração:

```bash
python -m tests.integration.test_integration
```

## 📊 API

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

## 🛠️ Desenvolvimento

Instalar dependências de desenvolvimento:

```bash
pip install -r requirements-dev.txt
```

### Rodar testes com pytest

```bash
pytest tests/
```

### Formatação de código

```bash
black src/ tests/
isort src/ tests/
```

### Linting

```bash
flake8 src/ tests/
```

## 📝 Modelos de Embedding Disponíveis

- `all-MiniLM-L6-v2` (rápido, 384 dimensões)
- `all-mpnet-base-v2` (melhor qualidade, 768 dimensões)
- `paraphrase-multilingual-MiniLM-L12-v2` (multilíngue)

Veja mais em: https://www.sbert.net/docs/pretrained_models.html

## 📚 Documentação Adicional

- [MCP Server](MCP_README.md)
- [Telegram Bot](TELEGRAM_README.md)
