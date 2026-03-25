from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    def run(self, context: dict) -> dict:
        ...

    def __repr__(self) -> str:
        return f"<Agent: {self.name}>"