# database.py
from motor.motor_asyncio import AsyncIOMotorClient

from config import MONGODB_DATABASE, MONGODB_HOST, MONGODB_PORT





# Configuración de la URL de conexión de MongoDB
# Dado que la URL proporcionada no tiene usuario/contraseña, simplificamos la URI
MONGO_URI = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}/{MONGODB_DATABASE}"

# Crea una instancia del cliente de MongoDB
client = AsyncIOMotorClient(MONGO_URI)

# Accede a la base de datos específica
database = client[MONGODB_DATABASE]

async def get_db():
    """
    Dependencia para obtener la instancia de la base de datos de MongoDB.
    """
    try:
        yield database
    finally:
        pass

async def get_collection(collection_name: str):
    """
    Dependencia para obtener una colección específica de la base de datos.
    """
    return database[collection_name]