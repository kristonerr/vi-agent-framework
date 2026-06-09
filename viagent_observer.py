"""vi-agent observer daemon.

Watches active window titles (safe, no content), learns from web search.

Usage:
    python viagent_observer.py                   # single check + learn
    python viagent_observer.py --watch            # start watcher in background (Windows: start /B)
    python viagent_observer.py --learn            # one learning cycle
    python viagent_observer.py --learn --daemon   # learn every hour
"""

import argparse
import logging
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from observer.watcher import watch as _watch
from observer.learner import learn as _learn

DEFAULT_WATCH_INTERVAL = 10
DEFAULT_LEARN_INTERVAL = 3600


def main():
    parser = argparse.ArgumentParser(description="vi-agent observer: watch + learn")
    parser.add_argument("--watch", action="store_true", help="Start window watcher")
    parser.add_argument("--learn", action="store_true", help="Run one learning cycle")
    parser.add_argument("--daemon", action="store_true", help="Run in loop (with --learn)")
    parser.add_argument("--interval", type=int, default=DEFAULT_WATCH_INTERVAL,
                        help="Watcher poll interval in seconds")
    parser.add_argument("--learn-interval", type=int, default=DEFAULT_LEARN_INTERVAL,
                        help="Learning cycle interval in seconds (with --daemon)")
    args = parser.parse_args()

    if args.watch and args.learn:
        from threading import Thread

        def learn_loop():
            while True:
                _learn()
                time.sleep(args.learn_interval)

        t = Thread(target=learn_loop, daemon=True)
        t.start()
        _watch(interval=args.interval)
    elif args.watch:
        _watch(interval=args.interval)
    elif args.learn:
        if args.daemon:
            while True:
                result = _learn()
                if result:
                    logging.info(f"Learned: {', '.join(result)}")
                time.sleep(args.learn_interval)
        else:
            result = _learn()
            if result:
                print(f"✅ Learned: {', '.join(result)}")
            else:
                print("⏭️  Nothing new to learn")
    else:
        result = _learn()
        if result:
            print(f"✅ Learned: {', '.join(result)}")
        else:
            print("⏭️  Nothing new to learn")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
