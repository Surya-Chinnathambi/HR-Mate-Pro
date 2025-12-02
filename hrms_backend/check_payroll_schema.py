import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='hrms_db',
    user='postgres',
    password='Admin@123'
)
cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'payrolls' 
    ORDER BY ordinal_position
""")
columns = cur.fetchall()
print("Payrolls table columns:")
for col in columns:
    print(f"  {col[0]}: {col[1]}")
cur.close()
conn.close()
