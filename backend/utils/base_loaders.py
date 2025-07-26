from abc import ABC, abstractmethod

class BaseLoader(ABC):
    @abstractmethod
    async def load(self) -> str:
        pass
