import json
import logging
import os
import time

from groq import Groq

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 4096
MAX_RETRIES = 3


class LLMClient:
    def __init__(self, log_prompts: bool = False):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY не найден. "
                "Скопируй .env.example в .env и вставь свой ключ."
            )
        self.client = Groq(api_key=api_key)
        self.log_prompts = log_prompts
        logger.info("LLMClient инициализирован, модель: %s", MODEL)

    def ask(self, system_prompt: str, user_prompt: str) -> str:
        if self.log_prompts:
            logger.debug("--- SYSTEM PROMPT ---\n%s", system_prompt)
            logger.debug("--- USER PROMPT ---\n%s", user_prompt)
        start = time.time()

        message = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        elapsed = time.time() - start
        response_text = message.choices[0].message.content
        if self.log_prompts:
            logger.debug("--- RESPONSE (%.2f сек) ---\n%s", elapsed, response_text)
        return response_text

    def ask_json(self, system_prompt: str, user_prompt: str) -> dict:
        for attempt in range(1, MAX_RETRIES + 1):
            response_text = self.ask(system_prompt, user_prompt)

            try:
                cleaned = self._strip_markdown_json(response_text)
                result = json.loads(cleaned)
                if attempt > 1:
                    logger.info("JSON успешно распарсен с попытки %d", attempt)
                return result

            except json.JSONDecodeError as e:
                logger.warning("Попытка %d/%d: невалидный JSON — %s", attempt, MAX_RETRIES, e)
                if attempt == MAX_RETRIES:
                    logger.error("Последний ответ:\n%s", response_text)
                    raise ValueError(f"Невалидный JSON после {MAX_RETRIES} попыток: {e}") from e

                user_prompt = (
                    f"{user_prompt}\n\n"
                    f"ВАЖНО: предыдущий ответ содержал невалидный JSON. "
                    f"Верни ТОЛЬКО чистый JSON без markdown и комментариев."
                )

    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines)
        return text.strip()