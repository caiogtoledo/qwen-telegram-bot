# MCP Server para Qwen-CLI

Servidor MCP (Model Context Protocol) que fornece habilidades de memória para o Qwen-CLI.

## 📁 Localização

```
src/infrastructure/mcp/server.py
```

## Ferramentas Disponíveis

### 1. `save_memory`
Salva informações na memória.

**Parâmetros:**
- `content` (obrigatório): Conteúdo a ser salvo
- `importance` (opcional): Nível de importância (0.0-1.0), padrão: 1.0
- `long_term` (opcional): Salvar na memória de longo prazo, padrão: true

**Exemplo:**
```json
{
  "name": "save_memory",
  "arguments": {
    "content": "O usuário prefere código em Python",
    "importance": 0.9
  }
}
```

### 2. `search_memory`
Busca informações relevantes na memória.

**Parâmetros:**
- `query` (obrigatório): Texto de busca
- `top_k` (opcional): Número máximo de resultados, padrão: 5

**Exemplo:**
```json
{
  "name": "search_memory",
  "arguments": {
    "query": "preferências do usuário",
    "top_k": 3
  }
}
```

### 3. `get_recent_memories`
Recupera as memórias recentes de curto prazo.

**Parâmetros:**
- `n` (opcional): Número de itens, padrão: 10

### 4. `get_memory_stats`
Obtém estatísticas de uso da memória.

### 5. `clear_memory`
Limpa a memória.

**Parâmetros:**
- `scope` (opcional): "short", "long", ou "all"

## Configuração

Adicione ao arquivo de configuração do Qwen-CLI (geralmente `~/.qwen/config.json`):

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

## Uso

### Iniciando o Servidor

```bash
cd /path/to/qwen-space
source venv/bin/activate  # Se estiver usando venv
python -m src.infrastructure.mcp.server
```

### Exemplo de Uso no Qwen-CLI

Depois de configurado, você pode usar no Qwen-CLI:

```
User: Save that my favorite programming language is Python
Assistant: [uses save_memory tool]
✓ Memory saved successfully!

User: What do you know about my preferences?
Assistant: [uses search_memory tool]
Search results for: 'preferences'
📚 Long-term memory:
  • [Score: 0.85] O usuário prefere código em Python
```

## Dependências

```bash
pip install mcp faiss-cpu sentence-transformers numpy
```

Ou:

```bash
pip install -r requirements.txt
```

## Estrutura de Armazenamento

- **Memória de Curto Prazo**: Mantém os últimos 100 itens em memória
- **Memória de Longo Prazo**: Persistida em `./memory_storage/` com FAISS

## Arquitetura

```
┌─────────────┐
│  Qwen-CLI   │
└──────┬──────┘
       │ MCP Protocol
       ▼
┌─────────────────────┐
│   MCP Server        │
│  (server.py)        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  MemoryManager      │
│  ├─ ShortTermMemory │
│  └─ LongTermMemory  │
└─────────────────────┘
```

## Testes

```bash
python -m tests.integration.test_mcp
```
