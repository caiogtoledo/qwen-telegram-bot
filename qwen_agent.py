"""
Agente Qwen-Code wrapper.
Invoca o qwen-code via CLI e gerencia a comunicação com o modelo.
"""

import subprocess
import os
from typing import Optional
from pathlib import Path


class QwenAgent:
    """
    Wrapper para invocar o qwen-code via linha de comando.
    
    Permite executar o qwen-code passando prompts customizados
    e capturando as respostas do modelo.
    """

    def __init__(self, qwen_command: str = "qwen"):
        """
        Inicializa o agente Qwen.

        Args:
            qwen_command: Comando para invocar o qwen-code (padrão: "qwen").
        """
        self.qwen_command = qwen_command

    def chat(
        self,
        message: str,
        context: Optional[str] = None,
        timeout: int = 120000
    ) -> str:
        """
        Envia uma mensagem para o qwen-code e retorna a resposta.

        Args:
            message: Mensagem do usuário.
            context: Contexto adicional (histórico, memórias, etc).
            timeout: Timeout em milissegundos para a execução.

        Returns:
            Resposta do qwen-code.
        """
        # Monta o prompt completo
        if context:
            full_prompt = f"{context}\n\n=== MENSAGEM DO USUÁRIO ===\n{message}"
        else:
            full_prompt = message

        # Prepara comando
        # O qwen-code aceita input via stdin ou argumento
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            # Executa qwen-code com o prompt
            result = subprocess.run(
                [self.qwen_command, "-p", full_prompt],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=timeout / 1000,
                env=env,
                encoding="utf-8",
                errors="replace"
            )

            # Retorna stdout como resposta
            response = result.stdout.strip()

            # Se não houver stdout, usa stderr como fallback
            if not response and result.stderr:
                response = f"[Error] {result.stderr.strip()}"

            return response if response else "[No response from qwen-code]"

        except subprocess.TimeoutExpired:
            return "[Timeout] qwen-code took too long to respond"
        except FileNotFoundError:
            return f"[Error] Command '{self.qwen_command}' not found. Make sure qwen-code is installed and in PATH."
        except Exception as e:
            return f"[Error] {str(e)}"

    def chat_with_memory(
        self,
        message: str,
        recent_history: list[str],
        relevant_memories: list[tuple[str, float]],
        max_history: int = 10,
        max_memories: int = 5
    ) -> str:
        """
        Envia mensagem com contexto de memória e histórico.

        Args:
            message: Mensagem do usuário.
            recent_history: Histórico recente de mensagens.
            relevant_memories: Memórias relevantes (conteúdo, score).
            max_history: Máximo de itens do histórico para incluir.
            max_memories: Máximo de memórias para incluir.

        Returns:
            Resposta do qwen-code.
        """
        # Constrói contexto estruturado
        context_parts = []

        # System prompt
        context_parts.append(
            "Você é um assistente de IA prestativo e inteligente. "
            "Abaixo estão informações contextuais que podem ajudar na resposta."
        )

        # Memórias relevantes
        if relevant_memories:
            context_parts.append("\n=== MEMÓRIAS RELEVANTES ===")
            for content, score in relevant_memories[:max_memories]:
                context_parts.append(f"[Relevância: {score:.2f}] {content}")

        # Histórico recente
        if recent_history:
            context_parts.append("\n=== HISTÓRICO RECENTE ===")
            for item in recent_history[-max_history:]:
                context_parts.append(f"• {item}")

        context = "\n".join(context_parts)

        # Chama qwen-code com contexto completo
        return self.chat(message, context=context)

    def is_available(self) -> bool:
        """
        Verifica se o qwen-code está disponível no PATH.

        Returns:
            True se disponível, False caso contrário.
        """
        try:
            result = subprocess.run(
                [self.qwen_command, "--help"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
