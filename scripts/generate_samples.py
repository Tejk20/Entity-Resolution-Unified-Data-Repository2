import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.services.seed import generate_samples

if __name__ == "__main__":
    paths = generate_samples()
    for key, path in paths.items():
        print(f"{key}: {path}")
