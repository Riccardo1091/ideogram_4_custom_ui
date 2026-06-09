"""
Abstract base class representing the runtime layer interface.
"""

from abc import ABC, abstractmethod
from backend.schemas import GenerationRequest, GenerationResult

class BaseRuntime(ABC):
    @abstractmethod
    def health(self) -> dict:
        """Returns diagnostic health information for the runtime."""
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Loads and warms up the model components to ready state."""
        pass

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Executes inference and returns the GenerationResult."""
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the name of the runtime engine."""
        pass

    def get_progress(self) -> dict:
        """Returns the current progress telemetry."""
        return {
            "active": False,
            "current_step": 0,
            "total_steps": 0,
            "percentage": 0.0,
            "elapsed_time": 0.0,
            "estimated_time_remaining": 0.0
        }
