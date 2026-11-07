"""Exact sample statistics, using linear interpolation (not histogram estimates)."""
import math
from statistics import mean


def percentile(values: list[float], percentile_value: float) -> float:
    if not values or not 0 <= percentile_value <= 100:
        raise ValueError('Nonempty samples and percentile between 0 and 100 required')
    if not all(math.isfinite(value) and value >= 0 for value in values):
        raise ValueError('Samples must be finite and nonnegative')
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value / 100
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def summarize(values: list[float]) -> dict[str, float]:
    return {'avg_ms': mean(values), 'p95_ms': percentile(values, 95),
            'p99_ms': percentile(values, 99), 'min_ms': min(values), 'max_ms': max(values)}
