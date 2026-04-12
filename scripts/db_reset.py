import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("POSTGRES__HOST", "localhost"),
    port=os.getenv("POSTGRES__PORT", 5432),
    dbname=os.getenv("POSTGRES__DB", "kupio"),
    user=os.getenv("POSTGRES__USER"),
    password=os.getenv("POSTGRES__PASSWORD"),
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
conn.close()
print("Schema dropped and recreated.")
