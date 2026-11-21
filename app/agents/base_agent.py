
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):

    @abstractmethod
    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        pass
