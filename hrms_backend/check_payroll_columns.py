from app.database import get_session
from sqlalchemy import text

session = next(get_session())
result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='payrolls' ORDER BY ordinal_position"))
print("Existing columns in payrolls table:")
for row in result:
    print(f"  - {row[0]}")
