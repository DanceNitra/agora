"""
CSDMonitor — Continuous Statistical Drift detection and metric tracking.

Part of the Observability (O) layer in the Agora 5-layer architecture.
Collects agent metrics, detects anomalous drift (CSD alerts), and
provides a centralised check_all() health summary.
"""

from __future__ import annotations

import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class AlertSeverity(str, Enum):
    """Severity levels for CSD alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """A single data point for a metric at a timestamp."""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class CSDAlert:
    """A drift alert produced by the monitor."""
    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    deviation_z: float
    severity: AlertSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CSDMonitor
# ---------------------------------------------------------------------------

class CSDMonitor:
    """Collects metrics and detects anomalous statistical drift.

    Maintains a sliding window of metric data points. On each
    :meth:`check_all` call, it computes z-scores against a baseline
    and raises alerts for values exceeding configurable thresholds.

    Typical usage::

        monitor = CSDMonitor(window_size=100, z_threshold=3.0)

        # Record metrics as agents act
        monitor.push_metric("response_time", 0.32, labels={"agent": "alpha"})
        monitor.push_metric("tool_call_count", 7)

        # Check for drift — returns list of alerts
        alerts = monitor.check_all()
        for alert in alerts:
            print(f"[{alert.severity}] {alert.message}")
    """

    def __init__(
        self,
        window_size: int = 100,
        z_threshold_warning: float = 2.0,
        z_threshold_critical: float = 3.5,
        baseline_percentile: float = 0.10,
    ) -> None:
        """
        Args:
            window_size: Maximum number of recent data points retained per metric.
            z_threshold_warning: Z-score above which a WARNING alert fires.
            z_threshold_critical: Z-score above which a CRITICAL alert fires.
            baseline_percentile: Fraction of data points used to compute baseline
                (e.g. 0.10 = first 10% of window).
        """
        self._window_size = window_size
        self._z_warn = z_threshold_warning
        self._z_crit = z_threshold_critical
        self._baseline_pct = baseline_percentile

        # metric_name -> list of MetricPoint
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        # Registered health-check callbacks (called by check_all)
        self._checks: List[Callable[[], Optional[List[CSDAlert]]]] = []

    # ------------------------------------------------------------------
    # Metric recording
    # ------------------------------------------------------------------

    def push_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric data point.

        Args:
            name:   Metric identifier (e.g. ``"response_time"``).
            value:  Numeric value to record.
            labels: Optional key-value labels for filtering / grouping.
        """
        point = MetricPoint(value=value, labels=labels or {})
        bucket = self._metrics[name]
        bucket.append(point)

        # Trim to window size
        if len(bucket) > self._window_size:
            bucket[: len(bucket) - self._window_size] = []

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------

    def check_all(self) -> List[CSDAlert]:
        """Run all drift checks and registered callbacks.

        1. Statistical drift detection for every tracked metric.
        2. Each registered health-check callback.

        Returns:
            Combined list of :class:`CSDAlert` instances, sorted by
            severity (CRITICAL first).
        """
        alerts: List[CSDAlert] = []

        # 1. Per-metric drift checks
        for metric_name, points in self._metrics.items():
            if len(points) < 5:
                continue  # not enough data for meaningful drift detection

            baseline_count = max(2, int(len(points) * self._baseline_pct))
            baseline_values = [p.value for p in points[:baseline_count]]
            recent_points = points[baseline_count:]

            if not recent_points:
                continue

            baseline_mean = statistics.mean(baseline_values)
            baseline_std = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0.0

            if baseline_std == 0.0:
                continue  # no variance to compare against

            for point in recent_points:
                z_score = (point.value - baseline_mean) / baseline_std
                if abs(z_score) >= self._z_crit:
                    severity = AlertSeverity.CRITICAL
                elif abs(z_score) >= self._z_warn:
                    severity = AlertSeverity.WARNING
                else:
                    continue

                direction = "high" if point.value > baseline_mean else "low"
                alerts.append(CSDAlert(
                    metric_name=metric_name,
                    current_value=point.value,
                    baseline_mean=baseline_mean,
                    baseline_std=baseline_std,
                    deviation_z=round(z_score, 2),
                    severity=severity,
                    message=(
                        f"Metric '{metric_name}' is abnormally {direction}: "
                        f"{point.value:.4f} vs baseline {baseline_mean:.4f}±{baseline_std:.4f} "
                        f"(z={z_score:.2f})"
                    ),
                    labels=point.labels,
                ))

        # 2. Registered callbacks
        for check_fn in self._checks:
            try:
                result = check_fn()
                if result:
                    alerts.extend(result)
            except Exception as exc:
                alerts.append(CSDAlert(
                    metric_name="__check_callback__",
                    current_value=0.0,
                    baseline_mean=0.0,
                    baseline_std=0.0,
                    deviation_z=0.0,
                    severity=AlertSeverity.WARNING,
                    message=f"Health-check callback {check_fn.__name__!r} raised: {exc}",
                ))

        # Sort: CRITICAL first, then WARNING, then INFO
        severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 99))
        return alerts

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def register_check(self, fn: Callable[[], Optional[List[CSDAlert]]]) -> None:
        """Register an external health-check function.

        The function should return ``None`` or a list of :class:`CSDAlert`.
        """
        self._checks.append(fn)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_metric(self, name: str) -> List[MetricPoint]:
        """Return all data points for a given metric."""
        return list(self._metrics.get(name, []))

    def get_metric_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Return summary statistics for a metric, or ``None`` if empty."""
        points = self._metrics.get(name)
        if not points:
            return None
        values = [p.value for p in points]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        }

    def clear_metric(self, name: str) -> None:
        """Remove all data for a specific metric."""
        self._metrics.pop(name, None)

    def clear_all(self) -> None:
        """Reset all tracked metrics and alerts."""
        self._metrics.clear()
        self._checks.clear()

    @property
    def metric_names(self) -> List[str]:
        """List of metric names currently tracked."""
        return list(self._metrics.keys())

    @property
    def total_points(self) -> int:
        """Total number of data points across all metrics."""
        return sum(len(p) for p in self._metrics.values())

    # ------------------------------------------------------------------
    # Built-in CSD alert detection helpers
    # ------------------------------------------------------------------

    def detect_metric_anomaly(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[CSDAlert]:
        """Convenience: push a metric point and immediately check for drift.

        Equivalent to calling ``push_metric`` followed by a targeted
        drift check for that single metric.

        Returns:
            A :class:`CSDAlert` if the value is anomalous, else ``None``.
        """
        self.push_metric(metric_name, value, labels=labels)
        alerts = self.check_all()
        for alert in alerts:
            if alert.metric_name == metric_name:
                return alert
        return None
