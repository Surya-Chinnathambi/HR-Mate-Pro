"""
Simple helper to apply SQL migration files directly to the database.
Use with caution - intended for local development/testing. In production, use Alembic.

Requires: DATABASE_URL env var (postgresql://user:pass@host:port/dbname)
"""
import os
import sys
import asyncpg

MIGRATION_FILE = os.path.join(os.path.dirname(__file__), '..', 'db', 'migrations', '0001_create_notifications_schema.sql')

async def apply():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print('DATABASE_URL not set')
        sys.exit(1)

    sql = open(MIGRATION_FILE, 'r', encoding='utf-8').read()
    conn = await asyncpg.connect(database_url)
    try:
        print('Applying migration...')
        await conn.execute(sql)
        print('Migration applied successfully')
    except Exception as e:
        print('Migration failed:', e)
    finally:
        await conn.close()

if __name__ == '__main__':
    import asyncio
    asyncio.run(apply())
