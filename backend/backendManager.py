from motor import motor_asyncio
from pymongo import MongoClient
from backend.gridManager import GridManager


class BackOffice:
    def __init__(self, ):
        self.connection = MongoClient("mongodb://127.0.0.1:27017", maxPoolSize=20)
        self.as_connection = motor_asyncio.AsyncIOMotorClient("mongodb://127.0.0.1:27017")
        self.grid_manager = GridManager(self.connection)
