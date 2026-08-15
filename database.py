from functools import lru_cache
from pymongo import MongoClient
from config import settings

@lru_cache(maxsize=1)
def get_client():
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI is not set")
    return MongoClient(settings.mongodb_uri, appname="durable-trial-match")

def get_db():
    return get_client()[settings.mongodb_db]
