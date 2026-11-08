from app.database import get_connection


def find_tenant_by_key_hash(key_hash):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT id, name
            FROM tenants
            WHERE api_key_hash = ?
            """,
            (key_hash,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()