from retail_os.core.database import SessionLocal
from sqlalchemy import text

session = SessionLocal()
try:
    session.execute(text("ALTER TABLE system_commands ADD COLUMN error_code TEXT"))
    session.execute(text("ALTER TABLE system_commands ADD COLUMN error_message TEXT"))
    session.commit()
    print("SUCCESS: Columns added to system_commands table")
except Exception as e:
    print(f"ERROR: {e}")
    session.rollback()
finally:
    session.close()
