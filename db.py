import os
import logging
from sqlalchemy import create_engine, MetaData
from databases import Database
from dotenv import load_dotenv

# ✅ Load Environment Variables
load_dotenv()

# ✅ Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Database Credentials from .env
DB_USER = "admin"
DB_PASSWORD = "scalabledatabase1"
DB_HOST = "database-1.cedp9b7wrci2.us-east-1.rds.amazonaws.com"
DB_NAME = "database-1"
DB_PORT = "3306"

# ✅ Connection URL for SQLAlchemy
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Database URL: {DATABASE_URL}")

# ✅ Async Database Connection
database = Database(DATABASE_URL)

# ✅ SQLAlchemy Metadata
metadata = MetaData()

# ✅ SQLAlchemy Engine
engine = create_engine(DATABASE_URL, echo=True)

# ✅ Ensure Tables Are Created
def create_tables():
    metadata.create_all(engine)
    print("✅ Tables created successfully.")

# ✅ Run Table Creation
if __name__ == "__main__":
    create_tables()
