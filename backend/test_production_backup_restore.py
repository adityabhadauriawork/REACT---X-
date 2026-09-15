import os
import sys
import tempfile
import sqlite3
import pytest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.backup_db import backup_sqlite, calculate_sha256
from scripts.restore_db import restore_sqlite

def test_sqlite_backup_and_restore_cycle():
    """Validates complete database backup creation, compression, SHA-256 verification, and restore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        source_db = tmp_path / "source_test.db"
        backup_file = tmp_path / "backup_test.db.gz"
        restored_db = tmp_path / "restored_test.db"

        # 1. Create source test DB with realistic thermal and facility records
        conn = sqlite3.connect(str(source_db))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE facilities (id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL);")
        cursor.execute("CREATE TABLE thermal_detections (id TEXT PRIMARY KEY, facility_id TEXT, brightness_kelvin REAL, frp_mw REAL);")
        
        cursor.execute("INSERT INTO facilities VALUES ('FAC-001', 'Hazira Plant Alpha', 21.1685, 72.6958);")
        cursor.execute("INSERT INTO facilities VALUES ('FAC-002', 'Jamnagar Refinery', 22.4707, 70.0577);")
        
        for i in range(50):
            cursor.execute(
                f"INSERT INTO thermal_detections VALUES ('DET-{i:03d}', 'FAC-001', {350.0 + i}, {12.5 + i});"
            )
        conn.commit()
        conn.close()

        # 2. Perform backup
        backup_result = backup_sqlite(source_db, backup_file)
        assert backup_file.exists()
        assert backup_result["size_bytes"] > 0
        assert len(backup_result["sha256"]) == 64

        # Verify sha256
        computed_sha = calculate_sha256(backup_file)
        assert computed_sha == backup_result["sha256"]

        # 3. Restore to new location
        restore_result = restore_sqlite(backup_file, restored_db)
        assert restore_result["status"] == "success"
        assert restore_result["integrity_check"] == "ok"
        assert restored_db.exists()

        # 4. Verify all records match exactly
        restored_conn = sqlite3.connect(str(restored_db))
        r_cursor = restored_conn.cursor()
        
        r_cursor.execute("SELECT COUNT(*) FROM facilities;")
        assert r_cursor.fetchone()[0] == 2

        r_cursor.execute("SELECT COUNT(*) FROM thermal_detections;")
        assert r_cursor.fetchone()[0] == 50

        r_cursor.execute("SELECT name, lat, lon FROM facilities WHERE id='FAC-001';")
        assert r_cursor.fetchone() == ('Hazira Plant Alpha', 21.1685, 72.6958)

        restored_conn.close()
