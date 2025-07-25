from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from datetime import datetime

# NO HAY IMPORTACIONES DE SQLAlchemy AQUÍ

async def obtener_mensajes(db: AsyncIOMotorDatabase) -> List[dict]:
    """
    Obtiene todos los mensajes de la base de datos.
    """
    messages_collection = db["messages"]
    # CORRECCIÓN CRÍTICA: Usar find().to_list() de Motor, no db.execute(select(Message))
    messages_data = await messages_collection.find({}).to_list(None)
    return messages_data

async def obtener_mensaje_por_id(db: AsyncIOMotorDatabase, message_id: str) -> Optional[dict]:
    """
    Obtiene un mensaje por su ID.
    """
    messages_collection = db["messages"]
    try:
        object_id = ObjectId(message_id)
    except Exception:
        return None # ID inválido
    message_data = await messages_collection.find_one({"_id": object_id})
    return message_data

async def crear_message(db: AsyncIOMotorDatabase, message_data: dict) -> dict:
    """
    Crea un nuevo mensaje en la base de datos.
    """
    messages_collection = db["messages"]
    message_data["created_at"] = datetime.utcnow()
    result = await messages_collection.insert_one(message_data)
    created_message = await messages_collection.find_one({"_id": result.inserted_id})
    return created_message

async def actualizar_message(db: AsyncIOMotorDatabase, message_id: str, update_data: dict) -> Optional[dict]:
    """
    Actualiza un mensaje existente.
    """
    messages_collection = db["messages"]
    try:
        object_id = ObjectId(message_id)
    except Exception:
        return None # ID inválido
    
    update_data["updated_at"] = datetime.utcnow()
    result = await messages_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return None # Mensaje no encontrado
    updated_message = await messages_collection.find_one({"_id": object_id})
    return updated_message

async def eliminar_message(db: AsyncIOMotorDatabase, message_id: str) -> bool:
    """
    Elimina un mensaje por su ID.
    """
    messages_collection = db["messages"]
    try:
        object_id = ObjectId(message_id)
    except Exception:
        return False # ID inválido
    result = await messages_collection.delete_one({"_id": object_id})
    return result.deleted_count > 0
