import logging
from datetime import datetime, timezone
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, role: str):
        self.role = role
        self._agents: list[BaseAgent] = []
        logger.info("Pipeline создан для роли: %s", role)

    def add_agent(self, agent: BaseAgent) -> "Pipeline":
        if not isinstance(agent, BaseAgent):
            raise TypeError(f"Ожидался BaseAgent, получен: {type(agent)}")
        self._agents.append(agent)
        logger.debug("Добавлен агент: %s (всего: %d)", agent.name, len(self._agents))
        return self

    def run(self) -> dict:
        if not self._agents:
            raise RuntimeError("Pipeline пуст — добавь хотя бы одного агента.")

        context: dict = {
            "role": self.role,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("=" * 50)
        logger.info("Запуск Pipeline: %s", self.role)
        logger.info("Агентов: %d", len(self._agents))
        logger.info("=" * 50)

        for i, agent in enumerate(self._agents, start=1):
            logger.info("[%d/%d] Запуск: %s", i, len(self._agents), agent.name)
            try:
                result = agent.run(context)
            except Exception as e:
                logger.error("Агент %s упал: %s", agent.name, e)
                raise RuntimeError(f"Агент '{agent.name}' завершился с ошибкой: {e}") from e

            if not isinstance(result, dict):
                raise TypeError(f"Агент '{agent.name}' вернул {type(result)}, ожидался dict.")

            context.update(result)
            logger.info("[%d/%d] Готово: %s", i, len(self._agents), agent.name)

        logger.info("=" * 50)
        logger.info("Pipeline завершён")
        logger.info("=" * 50)
        return context