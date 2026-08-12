"""
Test setup: proje kökünü sys.path'e ekler (pipeline/app importları için),
cwd'den bağımsız çalışsın diye.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
