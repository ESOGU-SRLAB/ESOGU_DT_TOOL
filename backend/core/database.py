"""
database.py
-----------
MongoDB bağlantısını ve temel veritabanı işlemlerini yönetir.
Örneğin, koleksiyonlara erişim, CRUD işlemleri gibi fonksiyonları burada tanımlayabilirsiniz.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from core.settings import get_settings

# Logger settings
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_db():
    """
    Returns a synchronous MongoDB database connection
    """
    try:
        logger.info("Connecting to MongoDB (sync)")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

        # Test the connection
        client.server_info()
        db = client[DATABASE_NAME]
        logger.info("MongoDB sync connection successful")
        return db
    except Exception as e:
        logger.error(f"MongoDB sync connection failed: {str(e)}")
        raise

_settings = get_settings()
MONGO_URI = _settings.mongo_uri
DATABASE_NAME = _settings.database_name

async def get_database():
    try:
        logger.info("Connecting to MongoDB (async)")
        client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000
        )
        await client.list_database_names()
        db = client[DATABASE_NAME]
        logger.info("MongoDB async connection successful")
        return db
    except Exception as e:
        logger.error(f"MongoDB async connection failed: {str(e)}")
        raise
