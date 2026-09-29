from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "data" / "monitoring.db",
    ROOT / "data" / "lab_application.db",
]

for target in TARGETS:
    if target.is_file():
        target.unlink()
        print(f"Removed {target.relative_to(ROOT)}")
