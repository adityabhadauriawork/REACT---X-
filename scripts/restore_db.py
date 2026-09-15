#!/usr/bin/env python3
"""
REACT-X Automated Database Restore Utility
==========================================
Restores a REACT-X database snapshot from a backup file with checksum verification.

Usage:
    python scripts/restore_db.py --file <backup_file> [--target <target_db_url_or_path>]

Features:
- Validates SHA-256 checksum before attempting restoration
- Decompresses gzip streams safely
- Supports restoring to alternate target DB paths for verification
"""

import os
import sys
import gzip
import shutil
import hashlib
import sqlite3
import argparse
import subprocess
import json
from pathlib import Path

def calculate_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def restore_sqlite(backup_file: Path, target_path: Path) -> dict:
    """Restores SQLite database from a .db.gz archive."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_path.with_suffix(".restoring")
    
    with gzip.open(backup_file, "rb") as f_in:
        with open(temp_target, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
            
    # Verify sqlite integrity
    con = sqlite3.connect(str(temp_target))
    cursor = con.cursor()
    cursor.execute("PRAGMA integrity_check;")
    integrity_result = cursor.fetchone()[0]
    con.close()
    
    if integrity_result != "ok":
        temp_target.unlink(missing_ok=True)
        raise RuntimeError(f"Database integrity check failed: {integrity_result}")
        
    if target_path.exists():
        target_path.unlink()
    temp_target.rename(target_path)
    
    return {
        "status": "success",
        "engine": "sqlite",
        "target": str(target_path),
        "integrity_check": integrity_result
    }

def restore_postgres(backup_file: Path, db_url: str) -> dict:
    """Restores PostgreSQL database using pg_restore."""
    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        f"--dbname={db_url}",
        str(backup_file)
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("pg_restore executable not found in PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pg_restore failed: {e.stderr}")
        
    return {
        "status": "success",
        "engine": "postgresql",
        "target": db_url.split("@")[-1] if "@" in db_url else db_url
    }

def restore_database(backup_file: Path, target: str = None) -> dict:
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
    # Check for manifest file to verify checksum
    manifest_file = backup_file.with_suffix(".json")
    if not manifest_file.exists() and backup_file.name.endswith(".db.gz"):
        manifest_file = backup_file.parent / (backup_file.name[:-6] + ".json")
        
    if manifest_file.exists():
        with open(manifest_file, "r") as f:
            manifest = json.load(f)
            expected_sha = manifest.get("details", {}).get("sha256")
            if expected_sha:
                actual_sha = calculate_sha256(backup_file)
                if actual_sha != expected_sha:
                    raise ValueError(f"Checksum mismatch! Expected {expected_sha}, got {actual_sha}. Aborting restore.")

    if backup_file.name.endswith((".db.gz", ".sqlite.gz", ".db")):
        target_path = Path(target) if target else backup_file.parent / "restored_database.db"
        return restore_sqlite(backup_file, target_path)
    else:
        if not target:
            raise ValueError("Target PostgreSQL database URL must be provided via --target for pg_restore.")
        return restore_postgres(backup_file, target)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="REACT-X Automated Restore Utility")
    parser.add_argument("--file", type=Path, required=True, help="Backup file to restore")
    parser.add_argument("--target", type=str, default=None, help="Target database path or connection URL")
    args = parser.parse_args()

    try:
        res = restore_database(args.file, args.target)
        print(f"[SUCCESS] REACT-X Database Restored Successfully:")
        print(json.dumps(res, indent=2))
    except Exception as ex:
        print(f"[ERROR] Database restore failed: {ex}", file=sys.stderr)
        sys.exit(1)
