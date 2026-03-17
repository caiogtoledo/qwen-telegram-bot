# Bot Telegram + Qwen-Code

Bot do Telegram integrado com Qwen-Code para conversas com memória persistente.

## 📁 Localização

```
src/infrastructure/telegram/bot.py
```

## Funcionalidades

- 💬 Conversa natural mantendo contexto
- 🧠 Memória de curto e longo prazo
- 📊 Histórico por usuário
- 🔍 Busca semântica de memórias relevantes
- ⚡ Integração com qwen-code CLI

## Instalação

### 1. Instale as dependências

```bash
pip install -r requirements.txt
```

### 2. Obtenha um token do Telegram

1. Abra o Telegram e busque por **@BotFather**
2. Envie `/newbot` e siga as instruções
3. Copie o token gerado

### 3. Configure a variável de ambiente

```bash
export TELEGRAM_BOT_TOKEN='seu-token-aqui'
```

Opcionalmente, configure o comando do qwen-code:

```bash
export QWEN_COMMAND='qwen'  # padrão: "qwen"
```

## Uso

### Executar o bot

```bash
python -m src.infrastructure.telegram.bot
```

Ou com variáveis explícitas:

```bash
TELEGRAM_BOT_TOKEN='seu-token' python -m src.infrastructure.telegram.bot
```

### Comandos disponíveis

| Comando | Descrição |
|---------|-----------|
| `/start` | Inicia/reinicia a conversa |
| `/clear` | Limpa histórico deste chat |
| `/memory` | Mostra estatísticas da memória |
| `/help` | Mostra ajuda |

## Arquitetura

```
Telegram → bot.py → qwen_agent.py → qwen (CLI)
                    ↓
          conversation_manager.py
                    ↓
          memory_manager.py
                    ↓
          (FAISS + Short-term)
```

### Componentes

| Componente | Descrição |
|------------|-----------|
| `src/infrastructure/telegram/bot.py` | Bot principal do Telegram |
| `src/agents/qwen_agent.py` | Wrapper para invocar qwen-code |
| `src/core/conversation/manager.py` | Gerencia contexto por usuário |
| `src/core/memory/manager.py` | Sistema de memória |

## Fluxo de Conversa

1. Usuário envia mensagem no Telegram
2. Bot adiciona ao histórico do usuário
3. Busca memórias relevantes (curto + longo prazo)
4. Monta contexto: [histórico + memórias + mensagem]
5. Invoca `qwen` com contexto completo
6. Envia resposta no Telegram
7. Salva interação na memória

## Configurações

O bot pode ser configurado via parâmetros no código:

```python
from src.infrastructure.telegram.bot import TelegramQwenBot

bot = TelegramQwenBot(
    token="seu-token",
    qwen_command="qwen",        # Comando qwen-code
    memory_path="./memory_storage",
    max_history=20,             # Mensagens no contexto
    max_memories=5              # Memórias relevantes
)
```

## Exemplo de Conversa

```
Usuário: Oi, me chamo João
Bot: Olá João! Como posso ajudar?

[Horas depois...]

Usuário: Qual meu nome?
Bot: Seu nome é João!
```

## Troubleshooting

### "qwen não encontrado"

Certifique-se de que o qwen-code está instalado:

```bash
qwen --help
```

Se não estiver no PATH, configure:

```bash
export QWEN_COMMAND='/caminho/para/qwen'
```

### Bot não responde

Verifique:
1. Token está correto
2. Bot foi adicionado ao chat
3. Logs para erros específicos

## Logs

Os logs são exibidos no console. Para mais detalhes:

```bash
PYTHONPATH=. python -c "import logging; logging.basicConfig(level=logging.DEBUG); from src.infrastructure.telegram.bot import TelegramQwenBot"
```

## Testes

```bash
python -m tests.integration.test_integration
```
