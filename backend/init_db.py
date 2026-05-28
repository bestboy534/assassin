from app.config import get_settings
from app.database import init_db

settings = get_settings()
init_db(settings.sqlite_path)
print(f"SQLite database initialized at {settings.sqlite_path}")
