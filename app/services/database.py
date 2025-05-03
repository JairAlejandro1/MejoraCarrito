from pymongo import MongoClient
from config.config import Config

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(Config.MONGO_URI)
        return _client.tienda_online
    return _client.tienda_online