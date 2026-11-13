from sqlalchemy import text

from database.database import engine


def add_call_number_column():
    with engine.connect() as connection:
        try:
            connection.execute(
                text("""
                    ALTER TABLE call_records
                    ADD COLUMN call_number INTEGER
                """)
            )

            connection.commit()

            print("SUCCESS: call_number column added.")

        except Exception as e:
            print("Migration result:", e)


if __name__ == "__main__":
    add_call_number_column()