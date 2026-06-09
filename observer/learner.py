"""Self learner — reads activity context and runs web search for interesting topics.
Results are saved to learnings.md.

Privacy: DuckDuckGo only, no accounts, no tracking.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from runner.tools.registry import get as _get_tool
from runner import memory_manager as mm

logger = logging.getLogger(__name__)

LEARNINGS_PATH = "learnings.md"
SEARCH_COOLDOWN = 3600
MAX_THEMES_PER_CYCLE = 3

# Window titles → search topic mapping
TOPIC_MAP = [
    (r"youtube", "YouTube trends 2026"),
    (r"github|git", "software development 2026"),
    (r"opencode", "opencode AI tool latest"),
    (r"telegram|whatsapp|discord", "messaging apps updates 2026"),
    (r"vs code|code|vscode|studio", "programming news 2026"),
    (r"python", "Python 2026 new features"),
    (r"chrome|firefox|browser", "technology news 2026"),
    (r"game|play|steam", "gaming news 2026"),
    (r"terminal|cmd|powershell|bash", "command line tools 2026"),
]

SEEN_TOPICS_PATH = "._seen_topics.json"


def _load_seen(root: Path) -> set:
    path = root / SEEN_TOPICS_PATH
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _save_seen(root: Path, seen: set):
    path = root / SEEN_TOPICS_PATH
    path.write_text(json.dumps(list(seen), ensure_ascii=False), encoding="utf-8")


def _make_readable_slug(title: str) -> str:
    """Clean a window title into a search-friendly topic."""
    title = title.strip()

    for pattern, topic in TOPIC_MAP:
        if re.search(pattern, title, re.IGNORECASE):
            return topic

    parts = re.split(r"[–—\-|:\[\]()]+", title)
    meaningful = [p.strip() for p in parts if len(p.strip()) > 4 and not p.strip().isdigit()]
    if meaningful:
        return meaningful[0]

    short = title[:60].strip()
    return short if len(short) > 4 else ""


def _is_system_tool(title: str) -> bool:
    low = title.lower()
    system = ["desktop", "program manager", "settings", "control panel", "task manager",
              "file explorer", "calculator", "calendar", "clock", "notification"]
    return any(s in low for s in system)


def _learnings_path(root: Path) -> Path:
    return root / LEARNINGS_PATH


def _save_learning(root: Path, topic: str, summary: str, url: str = ""):
    content = ""
    path = _learnings_path(root)
    if path.exists():
        content = path.read_text(encoding="utf-8")

    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    link = f" [{url}]({url})" if url else ""
    entry = f"\n## {date} — {topic}\n- {summary}{link}\n"

    if content:
        content += entry
    else:
        content = f"# Результаты самообучения\n{entry}"

    path.write_text(content, encoding="utf-8")
    logger.info(f"Learned: {topic}")


def learn(root: Optional[Path] = None) -> list[str]:
    """One learning cycle: check recent activity, search, save."""
    if root is None:
        root = Path(__file__).parent.parent
    seen = _load_seen(root)

    from observer.watcher import get_recent_themes
    themes = get_recent_themes(root, window=30)

    results = []
    searched = 0
    for title in themes:
        if _is_system_tool(title):
            continue
        topic = _make_readable_slug(title)
        if not topic or topic.lower() in seen:
            continue

        if searched >= MAX_THEMES_PER_CYCLE:
            break

        logger.info(f"Searching: {topic}")
        try:
            time.sleep(1)
            search_fn = _get_tool("web_search")
            if not search_fn:
                logger.warning("web_search tool not registered")
                continue
            search_result = search_fn({"query": topic, "max_results": 3})
            if isinstance(search_result, dict) and "error" not in search_result:
                summary = ""
                url = ""
                items = search_result.get("results", [])
                if items:
                    summary = items[0].get("snippet", items[0].get("title", ""))[:200]
                    url = items[0].get("link", "")
                if not summary:
                    summary = f"Изучила тему: {topic}"
                _save_learning(root, topic, summary, url)
                results.append(topic)
            else:
                logger.warning(f"Search failed for: {topic}")
        except Exception as e:
            logger.warning(f"Search error for {topic}: {e}")

        seen.add(topic.lower())
        searched += 1

    if results:
        _save_seen(root, seen)
        logger.info(f"Learned {len(results)} new topics: {', '.join(results)}")

    return results


def get_learnings(root: Optional[Path] = None, limit: int = 20) -> str:
    """Return recent learnings as text."""
    if root is None:
        root = Path(__file__).parent.parent
    path = _learnings_path(root)
    if not path.exists():
        return "Я ещё ничего не узнала нового."
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    return "\n".join(lines[-limit:]) if len(lines) > limit else content


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    learned = learn()
    if learned:
        print(f"✅ Learned: {', '.join(learned)}")
    else:
        print("⏭️  Nothing new to learn")
