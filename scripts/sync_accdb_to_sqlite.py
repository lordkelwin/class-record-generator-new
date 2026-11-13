#!/usr/bin/env python3
"""
CLI Utility: Sync Microsoft Access (PGO-PI-IGA.accdb) to SQLite (academic_catalog.db).

Run this utility on Windows whenever faculty updates the Access prospectus file.
It synchronizes all BSEE courses, prerequisites, co-requisites, descriptions,
and PGO-PI alignment mappings into the unified SQLite database.
"""
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import accdb_curriculum


def main():
    print("=" * 70)
    print("  USeP OBE: PGO-PI-IGA.accdb -> SQLite Unified Catalog Sync")
    print("=" * 70)

    try:
        count = accdb_curriculum.sync_accdb_to_catalog_and_db()
        print(f"\n[SUCCESS] Successfully synced {count} BSEE courses into academic_catalog.db.")
        print("[INFO] Unified catalog is updated and ready for cloud deployment.")
    except Exception as e:
        print(f"\n[ERROR] Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
