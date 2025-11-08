"""
Retry strategy and backoff mechanisms for error handling.

REQ: REQ-A-ErrorHandling

Provides:
- Exponential backoff calculation
- Custom backoff strategies
- Retry configuration
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExponentialBackoff:
    """Exponential backoff strategy."""

    initial_delay: float = 0.01  # 10ms
    multiplier: float = 2.0
    max_delay: float = 10.0

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        AC7: Exponential backoff (100ms, 200ms, 400ms).

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds

        """
        delay = self.initial_delay * (self.multiplier**attempt)
        return min(delay, self.max_delay)


class RetryStrategy:
    """Retry strategy with configurable backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        backoff_strategy: ExponentialBackoff | None = None,
    ) -> None:
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retries
            backoff_strategy: Backoff strategy (default: ExponentialBackoff)

        """
        self.max_retries = max_retries
        self.backoff_strategy = backoff_strategy or ExponentialBackoff()

    def get_retry_delays(self, num_retries: int) -> list[float]:
        """
        Get list of delays for retry attempts.

        AC7: Retry with exponential backoff (100ms, 200ms, 400ms).

        Args:
            num_retries: Number of retries

        Returns:
            List of delays in seconds

        """
        delays = []
        for attempt in range(num_retries):
            delay = self.backoff_strategy.get_delay(attempt)
            delays.append(delay)
            logger.debug(f"Retry attempt {attempt + 1}: delay {delay:.3f}s")

        return delays

    def should_retry(self, attempt: int) -> bool:
        """
        Check if should retry based on attempt number.

        Args:
            attempt: Current attempt number

        Returns:
            True if should retry

        """
        return attempt < self.max_retries
