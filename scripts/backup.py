"""Consistent local SQLite backup, including committed WAL content."""
from datetime import datetime, timezone
from contextlib import closing
import sqlite3
from goalsift.paths import resolve_under_root
from goalsift.config import load_env

def main():
    load_env()
    source = resolve_under_root('goalsift.sqlite')
    if not source.exists():
        raise SystemExit('No application database exists yet.')
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = resolve_under_root(f'backups/goalsift-{name}.sqlite')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
    print(destination)

if __name__ == '__main__':
    main()
