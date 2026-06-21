---
name: Backup & Upgrade Safety System
description: Enterprise backup/restore for safe system upgrades — disk storage, pre-restore snapshots, global backup, integrity validation
---

## Architecture

**Storage path**: `data/backups/*.json.gz` (gzip compressed JSON on disk)
**Schema version constant**: `SCHEMA_VERSION = "2.0.0"` in `backend/routes/backup_routes.py`
**Schema version in DB**: `main_db.system_meta` → `{key: "schema_version", version: "..."}`

## Backup Types (prefixes)
- `BKP-` — regular tenant backup
- `GLB-` — global backup (super_admin, ALL tenant DBs + main_db)
- `PRE-` — pre-restore auto-snapshot (safety net, always created before restore)
- `RST-` — restore log entry (records the fact that a restore was performed)

## Key Endpoints
- `POST /api/backup/create` — tenant backup to disk
- `POST /api/backup/global` — super_admin only, dumps main_db + all `tenant_*` databases
- `GET /api/backup/{id}/download` — serves actual stored file (NOT re-generated)
- `POST /api/backup/{id}/restore` — safe restore: auto-PRE-snapshot → restore → integrity check → rollback on failure
- `POST /api/backup/restore-upload` — disaster recovery: upload .json/.json.gz file
- `GET /api/backup/schema-version` — current vs system version
- `POST /api/backup/schema-version/sync` — mark DB as upgraded (super_admin)
- `GET /api/backup/stats/summary` — includes disk_size_bytes, disk_files_count, schema info

## Envelope Format (on disk)
```json
{
  "schema_version": "2.0.0",
  "backup_number": "BKP-00001",
  "backup_type": "full",
  "entity_type": "tenant",
  "entity_id": "...",
  "created_at": "...",
  "data": { "collection_name": [...docs] }
}
```
Global backup: `databases: { "main": {...}, "tenant_abc": {...} }`

## Safe Upgrade Flow
1. Tenant admin or super_admin creates backup (BKP/GLB)
2. Downloads .json.gz file externally
3. Performs system upgrade
4. If schema changed: super_admin calls POST /backup/schema-version/sync
5. If rollback needed: use restore endpoint — auto PRE- snapshot + integrity validation + rollback on failure

**Why:** Old system re-generated data at download time (race condition bug) and had no disk storage, no integrity checks, no global backup, no schema versioning.

**How to apply:** Whenever touching backup_routes.py — always increment SCHEMA_VERSION when schema changes require migration.
