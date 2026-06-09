"""
Handles mapping parameters (steps, mu, std) to the scheduler setup for Ideogram 4.
"""

from typing import Dict, Any

class IdeogramScheduler:
    @staticmethod
    def get_schedule(steps: int, mu: float, std: float) -> Dict[str, Any]:
        """
        Builds the scheduler parameters for the sampling loop.
        These are typically used for Flow Matching / Rectified Flow schedules.
        """
        # Under normal conditions, steps dictate the discretization of [0, 1] interval.
        # mu and std control the shift of time-steps toward paths where models perform better.
        return {
            "steps": steps,
            "mu": mu,
            "std": std,
            "timesteps": [i / steps for i in range(steps + 1)] # Basic linear steps representation
        }
