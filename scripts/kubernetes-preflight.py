#!/usr/bin/env python3
"""Read-only local-cluster memory gate; never starts or stops any service."""
import json
from pathlib import Path
import shutil


def inspect() -> dict:
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:', 'MemAvailable:'))}
    required = 6 * 1024**3  # ~4 GiB workload limits during ingestion + control plane/headroom
    return {'total_bytes': memory['MemTotal'], 'available_bytes': memory['MemAvailable'],
            'required_available_bytes': required, 'cluster_attempt_allowed': memory['MemAvailable'] >= required,
            'kubectl': bool(shutil.which('kubectl')), 'kind': bool(shutil.which('kind')), 'k3d': bool(shutil.which('k3d'))}


if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2))
