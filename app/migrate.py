from app.database import PROJECT_ROOT, get_connection


MIGRATIONS_PATH = PROJECT_ROOT / "migrations"


def apply_migration(connection, name, sql):
    existing = connection.execute(
        "SELECT 1 FROM schema_migrations WHERE name = ?",
        (name,),
    ).fetchone()

    if existing:
        return "skipped"

    try:
        connection.executescript("BEGIN IMMEDIATE;\n" + sql)

        connection.execute(
            "INSERT INTO schema_migrations (name) VALUES (?)",
            (name,),
        )

        connection.execute("COMMIT")

    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise

    return "applied"


def migrate():
    migration_files = sorted(MIGRATIONS_PATH.glob("*.sql"))

    if not migration_files:
        raise RuntimeError("No migration files found.")

    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            )
            """
        )

        for migration_file in migration_files:
            sql = migration_file.read_text(encoding="utf-8-sig")

            result = apply_migration(
                connection,
                migration_file.name,
                sql,
            )

            print(f"{result}: {migration_file.name}")

    finally:
        connection.close()

    print("Migrations complete.")


if __name__ == "__main__":
    migrate()