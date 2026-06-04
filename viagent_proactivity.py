"""vi-agent proactivity daemon.
Checks every hour and writes to queue.json when agent wants to reach out first.

Usage:
    python viagent_proactivity.py           # single check
    python viagent_proactivity.py --daemon  # run forever, check every hour
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))
from runner.proactivity import ProactivityEngine


def main():
    parser = argparse.ArgumentParser(description="vi-agent proactivity daemon")
    parser.add_argument("--daemon", action="store_true", help="Run in background, check every hour")
    parser.add_argument("--interval", type=int, default=3600, help="Check interval in seconds (default: 3600)")
    args = parser.parse_args()

    engine = ProactivityEngine()

    if args.daemon:
        print(f"vi-agent proactivity daemon started. Checking every {args.interval}s.")
        while True:
            engine.tick()
            time.sleep(args.interval)
    else:
        result = engine.tick()
        if result:
            print(f"✅ Message sent: {result}")
        else:
            print("⏭️  No message needed")


if __name__ == "__main__":
    main()
