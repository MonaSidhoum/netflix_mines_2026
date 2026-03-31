import sqlite3
from pathlib import Path

DB_PATH = "cinema.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)

def main() -> None:
    with get_connection() as conn:
        init_db(conn)
        conn.commit()
    print(f"Base de données prête : {DB_PATH}")


if __name__ == "__main__":
    main()
