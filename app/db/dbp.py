from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_HOST, MONGODB_PORT, MONGODB_DATABASE

   # Crear la conexión a MongoDB
client = AsyncIOMotorClient(f'mongodb://{MONGODB_HOST}:{MONGODB_PORT}')
db = client[MONGODB_DATABASE]

async def get_db():
       return db
   