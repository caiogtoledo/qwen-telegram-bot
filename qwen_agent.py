"""
Agente Qwen-Code wrapper.
Invoca o qwen-code via CLI e gerencia a comunicação com o modelo.
"""

import subprocess
import os
import logging
import asyncio
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


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

    async def chat_async(
        self,
        message: str,
        context: Optional[str] = None,
        timeout: int = 45000  # Reduzido para 45s
    ) -> str:
        """
        Versão assíncrona: Envia uma mensagem para o qwen-code e retorna a resposta.

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
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["NODE_NO_WARNINGS"] = "1"

        try:
            logger.info(f"[ASYNC] Iniciando subprocesso para qwen-code, timeout={timeout}ms")
            logger.info(f"[ASYNC] Prompt length: {len(full_prompt)} chars")
            
            # Usa subprocesso assíncrono para não bloquear o event loop
            process = await asyncio.create_subprocess_exec(
                self.qwen_command, "-p", full_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                env=env
            )
            
            logger.info(f"[ASYNC] Processo iniciado com PID={process.pid}")

            # Aguarda com timeout
            start_time = asyncio.get_event_loop().time()
            try:
                logger.info(f"[ASYNC] Aguardando communicate() com timeout={timeout/1000}s")
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout / 1000
                )
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.info(f"[ASYNC] communicate() completou em {elapsed:.2f}s, returncode={process.returncode}")
            except asyncio.TimeoutError:
                logger.error(f"[ASYNC] TIMEOUT após {timeout}ms! Matando processo {process.pid}")
                process.kill()
                await process.wait()
                logger.error(f"qwen-code timed out after {timeout}ms")
                return "[Timeout] qwen-code took too long to respond"

            # Decodifica stdout como resposta
            response = stdout.decode('utf-8', errors='replace').strip() if stdout else ""

            # Log stderr para debugging
            if stderr:
                stderr_text = stderr.decode('utf-8', errors='replace')
                logger.debug(f"qwen stderr: {stderr_text[:500]}")

            # Se não houver stdout, usa stderr como fallback
            if not response and stderr:
                response = f"[Error] {stderr.decode('utf-8', errors='replace').strip()}"

            logger.debug(f"Response length: {len(response)} chars")
            return response if response else "[No response from qwen-code]"

        except FileNotFoundError:
            logger.error(f"Command '{self.qwen_command}' not found")
            return f"[Error] Command '{self.qwen_command}' not found. Make sure qwen-code is installed and in PATH."
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"[Error] {str(e)}"

    async def chat(
        self,
        message: str,
        context: Optional[str] = None,
        timeout: int = 120000
    ) -> str:
        """
        Versão assíncrona: Envia uma mensagem para o qwen-code e retorna a resposta.

        Args:
            message: Mensagem do usuário.
            context: Contexto adicional (histórico, memórias, etc).
            timeout: Timeout em milissegundos para a execução.

        Returns:
            Resposta do qwen-code.
        """
        # Tenta detectar se estamos em um event loop ativo
        try:
            loop = asyncio.get_running_loop()
            # Se temos um loop rodando, usamos executor para não bloquear
            logger.debug("Running in event loop context, using executor")
            return await loop.run_in_executor(
                None, 
                lambda: self._chat_sync(message, context, timeout)
            )
        except RuntimeError:
            # Sem event loop rodando, usa versão síncrona direta
            return self._chat_sync(message, context, timeout)

    def _chat_sync(
        self,
        message: str,
        context: Optional[str] = None,
        timeout: int = 120000
    ) -> str:
        """
        Implementação síncrona interna para chat.
        """
        # Monta o prompt completo
        if context:
            full_prompt = f"{context}\n\n=== MENSAGEM DO USUÁRIO ===\n{message}"
        else:
            full_prompt = message

        # Prepara comando
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["NODE_NO_WARNINGS"] = "1"

        try:
            logger.debug(f"Executing qwen command (sync) with timeout={timeout}ms")
            
            # Executa qwen-code com o prompt
            process = subprocess.Popen(
                [self.qwen_command, "-p", full_prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                env=env,
                encoding="utf-8",
                errors="replace"
            )

            # Aguarda com timeout
            try:
                stdout, stderr = process.communicate(timeout=timeout / 1000)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                logger.error(f"qwen-code timed out after {timeout}ms")
                return "[Timeout] qwen-code took too long to respond"

            # Retorna stdout como resposta
            response = stdout.strip() if stdout else ""

            # Log stderr para debugging
            if stderr:
                logger.debug(f"qwen stderr: {stderr[:500]}")

            # Se não houver stdout, usa stderr como fallback
            if not response and stderr:
                response = f"[Error] {stderr.strip()}"

            logger.debug(f"Response length: {len(response)} chars")
            return response if response else "[No response from qwen-code]"

        except FileNotFoundError:
            logger.error(f"Command '{self.qwen_command}' not found")
            return f"[Error] Command '{self.qwen_command}' not found. Make sure qwen-code is installed and in PATH."
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"[Error] {str(e)}"

    async def chat_with_memory_async(
        self,
        message: str,
        recent_history: list[str],
        relevant_memories: list[tuple[str, float]],
        max_history: int = 10,
        max_memories: int = 5
    ) -> str:
        """
        Versão assíncrona: Envia mensagem com contexto de memória e histórico.

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
        return await self.chat_async(message, context=context)

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
