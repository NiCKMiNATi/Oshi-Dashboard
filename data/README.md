# Local data

The backend creates `oshi.db` here on first startup or seed. SQLite files and journal files are ignored by Git.

Seed explicitly with `./scripts/seed.sh`. The seed is repeatable, adds only missing demo rows, and preserves user edits. It does not run automatically on API startup.

Discovery metadata is separate: startup inserts missing entries into `catalog_entities` and `entity_aliases` without modifying personal Oshi, keywords, or updates. `catalog_tracking` links catalog identities only when tracking is requested. Removing a followed Oshi leaves its catalog entry available for re-add. No existing table is altered by this additive schema change.

Stop the backend before making a filesystem backup of the database. Keep backups outside the repository. Never delete a personal database just to apply a schema change; v0.1 creates missing tables but does not migrate existing tables.
