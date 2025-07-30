import psycopg2
import json

# Update these with your Cloud SQL/Postgres credentials
conn = psycopg2.connect(
    host="127.0.0.1",
    dbname="bravo_vectors",
    user="bravo_user",
    password="Il2hBVadl@post!",
    port=5432
)



tables = [
    "user_vectors",
]

for table in tables:
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {table};")
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        with open(f"{table}.json", "w") as f:
            json.dump(data, f, indent=2)

conn.close()
print("Export complete.")