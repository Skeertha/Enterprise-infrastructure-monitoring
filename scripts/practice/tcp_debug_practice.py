import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from infra_monitor.checks.network import TCPCollector


def main():
    collector = TCPCollector(
        asset_id="DEBUG-NET-01",
        host="127.0.0.1",
        port=1,
        timeout_seconds=2,
    )

    result = collector.collect()

    print("TCP debugging result:")
    print(result)


if __name__ == "__main__":
    main()
