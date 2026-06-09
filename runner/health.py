import hashlib
import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKUP_DIR = ROOT / "backups"
HEALTH_FILE = ROOT / "health.json"
MAX_BACKUPS = 20

STATE_FILES = [
    "memory.md", "lessons.md", "heart.md", "intuition.md",
    "summary.md", "mood.json", "config.json", "session_buffer.json",
    "learnings.md",
]

BACKUP_INTERVAL = 300


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ""


def _read_health() -> dict:
    try:
        return json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"checksums": {}, "backups": [], "last_checkup": "", "mode": "normal"}


def _write_health(data: dict):
    HEALTH_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def verify_state() -> list[str]:
    health = _read_health()
    corrupted = []
    for sf in STATE_FILES:
        p = ROOT / sf
        if not p.exists():
            continue
        current = _sha256(p)
        expected = health.get("checksums", {}).get(sf)
        if expected and current != expected:
            corrupted.append(sf)
    return corrupted


def repair_state() -> list[str]:
    repaired = []
    health = _read_health()
    backups = health.get("backups", [])
    if not backups:
        return repaired
    latest = ROOT / "backups" / backups[-1]
    for sf in STATE_FILES:
        p = ROOT / sf
        backup_file = latest / sf
        if not p.exists() and backup_file.exists():
            shutil.copy2(backup_file, p)
            repaired.append(sf)
            logging.warning(f"Restored missing: {sf}")
        elif p.exists():
            current = _sha256(p)
            expected = health.get("checksums", {}).get(sf)
            if expected and current != expected and backup_file.exists():
                backup_sha = _sha256(backup_file)
                if backup_sha == expected:
                    shutil.copy2(backup_file, p)
                    repaired.append(sf)
                    logging.warning(f"Repaired corrupted: {sf}")
    if repaired:
        update_checksums()
    return repaired


def update_checksums():
    health = _read_health()
    checksums = {}
    for sf in STATE_FILES:
        p = ROOT / sf
        if p.exists():
            checksums[sf] = _sha256(p)
    health["checksums"] = checksums
    _write_health(health)


def backup_state() -> str | None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / ts
    backup_path.mkdir(parents=True, exist_ok=True)
    count = 0
    for sf in STATE_FILES:
        src = ROOT / sf
        if src.exists():
            shutil.copy2(src, backup_path / sf)
            count += 1
    health = _read_health()
    backups = health.get("backups", [])
    backups.append(ts)
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        old_path = BACKUP_DIR / old
        if old_path.exists():
            shutil.rmtree(old_path)
    health["backups"] = backups
    _write_health(health)
    update_checksums()
    logging.info(f"Backup {ts}: {count} files")
    return ts


def checkup() -> dict:
    corrupted = verify_state()
    result = {
        "ok": len(corrupted) == 0,
        "corrupted": corrupted,
        "mode": "normal",
    }
    if corrupted:
        repaired = repair_state()
        if repaired:
            result["repaired"] = repaired
        else:
            result["mode"] = "readonly"
            result["ok"] = False
    health = _read_health()
    health["last_checkup"] = datetime.now().isoformat()
    _write_health(health)
    return result


def disk_ok(min_free_mb: int = 200) -> bool:
    try:
        stat = shutil.disk_usage(ROOT)
        free_mb = stat.free // (1024 * 1024)
        if free_mb < min_free_mb:
            logging.warning(f"Low disk space: {free_mb} MB free (min {min_free_mb} MB)")
            return False
        return True
    except Exception as e:
        logging.warning(f"Could not check disk space: {e}")
        return True


def change_mode(mode: str):
    health = _read_health()
    health["mode"] = mode
    _write_health(health)


def current_mode() -> str:
    return _read_health().get("mode", "normal")
