import shutil
from datetime import datetime

from sqlalchemy import inspect

from database.database import engine
from config import DATABASE_PATH


# --------------------------------------------------
# BACKUP DATABASE
# --------------------------------------------------

database_path = DATABASE_PATH

if database_path.exists():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = database_path.with_name(
        f"{database_path.stem}_backup_{timestamp}{database_path.suffix}"
    )

    shutil.copy2(database_path, backup_path)
    print(f"Database backup created: {backup_path}")
else:
    print("Database file not found at configured path.")
    print(f"Configured path: {database_path}")


# --------------------------------------------------
# NEW LEAD COLUMNS
# --------------------------------------------------

new_columns = {
    "product_category": "VARCHAR",
    "product_variant": "VARCHAR",
    "product_specification": "TEXT",
    "application": "TEXT",
    "unit": "VARCHAR",
    "required_length": "VARCHAR",
    "required_height": "VARCHAR",
    "required_thickness": "VARCHAR",
    "budget": "VARCHAR",
    "installation_required": "BOOLEAN",
}


# --------------------------------------------------
# CHECK AND ADD MISSING COLUMNS
# --------------------------------------------------

inspector = inspect(engine)

existing_columns = {
    column["name"]
    for column in inspector.get_columns("leads")
}

with engine.begin() as connection:
    for column_name, column_type in new_columns.items():

        if column_name not in existing_columns:
            sql = (
                f"ALTER TABLE leads "
                f"ADD COLUMN {column_name} {column_type}"
            )

            connection.exec_driver_sql(sql)

            print(f"Added column: {column_name}")

        else:
            print(f"Already exists: {column_name}")


print("Lead table migration completed.")
