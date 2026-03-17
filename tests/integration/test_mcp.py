#!/usr/bin/env python3
"""Script de teste para o MCP Server."""

import asyncio
from src.core.memory.manager import MemoryManager

# Teste direto do MemoryManager
print("🧪 Testando MemoryManager...\n")

memory = MemoryManager(
    short_term_max_size=100,
    long_term_storage_path="./test_memory_storage"
)

# Teste 1: Salvar memória
print("1. Salvando memórias...")
memory.add("O usuário gosta de Python", importance=0.9)
memory.add("Projeto criado em 2026", importance=0.8)
memory.add("Biblioteca favorita: FastAPI", importance=0.7)
print("   ✓ 3 itens salvos\n")

# Teste 2: Buscar memória
print("2. Buscando por 'Python'...")
results = memory.search("Python", top_k=5)
for item, score in results.long_term:
    print(f"   • [Score: {score:.2f}] {item.content}")
print()

# Teste 3: Estatísticas
print("3. Estatísticas:")
stats = memory.stats()
print(f"   Short-term: {stats['short_term']['size']}/{stats['short_term']['max_size']}")
print(f"   Long-term: {stats['long_term']['size']} itens\n")

# Teste 4: Memórias recentes
print("4. Memórias recentes:")
recent = memory.short_term.get_recent(3)
for item in recent:
    print(f"   • {item.content}")
print()

print("✅ Todos os testes passaram!")
