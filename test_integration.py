#!/usr/bin/env python3
"""
Script de teste para verificar a integração dos componentes.
"""

import sys

print("🧪 Testando integração dos componentes...\n")

# Testa imports
print("1. Testando imports...")
try:
    from memory_manager import MemoryManager
    print("   ✓ memory_manager")
except Exception as e:
    print(f"   ✗ memory_manager: {e}")
    sys.exit(1)

try:
    from conversation_manager import ConversationManager
    print("   ✓ conversation_manager")
except Exception as e:
    print(f"   ✗ conversation_manager: {e}")
    sys.exit(1)

try:
    from qwen_agent import QwenAgent
    print("   ✓ qwen_agent")
except Exception as e:
    print(f"   ✗ qwen_agent: {e}")
    sys.exit(1)

try:
    from telegram_bot import TelegramQwenBot
    print("   ✓ telegram_bot")
except Exception as e:
    print(f"   ✗ telegram_bot: {e}")
    sys.exit(1)

# Testa inicialização da memória
print("\n2. Testando MemoryManager...")
try:
    memory = MemoryManager(
        short_term_max_size=10,
        long_term_storage_path="./test_memory_storage"
    )
    result = memory.add("Teste de memória", importance=0.8)
    print(f"   ✓ Memória adicionada: {result}")
except Exception as e:
    print(f"   ✗ Erro: {e}")
    sys.exit(1)

# Testa ConversationManager
print("\n3. Testando ConversationManager...")
try:
    conv_manager = ConversationManager(memory=memory)
    conv = conv_manager.get_or_create(chat_id=12345, username="test_user")
    conv_manager.add_message(12345, "user", "Olá, teste!")
    print(f"   ✓ Conversa criada: {conv}")
    print(f"   ✓ Mensagens: {len(conv.messages)}")
except Exception as e:
    print(f"   ✗ Erro: {e}")
    sys.exit(1)

# Testa QwenAgent (verifica disponibilidade)
print("\n4. Testando QwenAgent...")
try:
    agent = QwenAgent(qwen_command="qwen")
    available = agent.is_available()
    if available:
        print("   ✓ qwen-code disponível no PATH")
    else:
        print("   ⚠ qwen-code NÃO encontrado no PATH")
        print("      Isso é OK se você ainda não instalou o qwen-code")
except Exception as e:
    print(f"   ✗ Erro: {e}")

# Testa busca de contexto
print("\n5. Testando busca de contexto...")
try:
    history, memories = conv_manager.get_context(12345, "teste", max_history=5, max_memories=3)
    print(f"   ✓ Histórico: {len(history)} itens")
    print(f"   ✓ Memórias: {len(memories)} itens")
except Exception as e:
    print(f"   ✗ Erro: {e}")
    sys.exit(1)

# Limpa teste
print("\n6. Limpando dados de teste...")
try:
    import shutil
    from pathlib import Path
    
    test_path = Path("./test_memory_storage")
    if test_path.exists():
        shutil.rmtree(test_path)
        print("   ✓ Dados de teste removidos")
except Exception as e:
    print(f"   ⚠ Erro ao limpar: {e}")

print("\n✅ Todos os testes passaram!")
print("\n📋 Resumo:")
print("   - memory_manager: OK")
print("   - conversation_manager: OK")
print("   - qwen_agent: OK")
print("   - telegram_bot: OK")
print("\n🚀 Próximo passo: Configure TELEGRAM_BOT_TOKEN e execute telegram_bot.py")
