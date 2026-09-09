"""
CLI management tool for Nyaya Mitra backup, restore, and test-restore verification.

Usage:
  python scripts/backup_restore.py backup [--dir BACKUP_DIR] [--with-docs]
  python scripts/backup_restore.py restore <backup_file>
  python scripts/backup_restore.py test-restore <backup_file>
"""

from __future__ import annotations
import sys
import argparse
import json
from pathlib import Path

# Ensure backend root is on sys.path
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.operations.backup_restore import (
    create_backup,
    restore_backup,
    test_restore_verification,
)


def main():
    parser = argparse.ArgumentParser(description="Nyaya Mitra Backup & Disaster Recovery CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Backup command
    backup_p = subparsers.add_parser("backup", help="Create an online snapshot backup")
    backup_p.add_argument("--dir", dest="target_dir", default=None, help="Directory to save the backup")
    backup_p.add_argument("--with-docs", dest="with_docs", action="store_true", help="Include documents in archive")

    # Restore command
    restore_p = subparsers.add_parser("restore", help="Restore database from snapshot")
    restore_p.add_argument("backup_file", help="Path to .db backup file")

    # Test Restore command
    test_p = subparsers.add_parser("test-restore", help="Run automated sandbox restore verification")
    test_p.add_argument("backup_file", help="Path to .db backup file")

    args = parser.parse_args()

    if args.command == "backup":
        manifest = create_backup(target_dir=args.target_dir, include_documents=args.with_docs)
        print(f"Backup created successfully:")
        print(json.dumps(manifest.model_dump(), indent=2))

    elif args.command == "restore":
        res = restore_backup(args.backup_file)
        print(f"Restore completed:")
        print(json.dumps(res, indent=2))

    elif args.command == "test-restore":
        report = test_restore_verification(args.backup_file)
        print(f"Test Restore Report [{report.status}]:")
        print(json.dumps(report.model_dump(), indent=2))
        if report.status != "PASSED":
            sys.exit(1)


if __name__ == "__main__":
    main()
