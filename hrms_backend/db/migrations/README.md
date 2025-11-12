This folder contains raw SQL migration scripts created by the assistant.

0001_create_notifications_schema.sql - Core schema for notifications, RBAC, inbox, tasks, leave, audit logs,
and websocket connections. Includes PL/pgSQL trigger functions that emit PostgreSQL NOTIFY events.

How to apply (development):
1. Set your DATABASE_URL environment variable:
   - Windows (PowerShell): $env:DATABASE_URL = "postgresql://user:pass@localhost:5432/dbname"
2. Run the helper script (requires python and asyncpg installed):
   - cd hrms_backend
   - python -m pip install asyncpg
   - python scripts\apply_migrations.py

WARNING: Prefer using Alembic for production migrations. Treat these SQL files as a starting point.
