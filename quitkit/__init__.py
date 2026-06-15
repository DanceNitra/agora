"""quitkit — when to quit a depleting effort, with a measured drawdown-exit threshold (theta~0.6,
an interior optimum). Zero-dependency core."""
from .quitkit import should_quit, Tracker, optimal_theta, compare

__all__ = ["should_quit", "Tracker", "optimal_theta", "compare"]
