from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from datetime import datetime

# NO HAY IMPORTACIONES DE SQLAlchemy AQUÍ

async def obtener_attachments(db: AsyncIOMotorDatabase) -> List[dict]:
    """
    Obtiene todos los attachments de la base de datos.
    """
    attachments_collection = db["attachments"]
    attachments_data = await attachments_collection.find({}).to_list(None)
    return attachments_data

async def obtener_attachment_por_id(db: AsyncIOMotorDatabase, attachment_id: str) -> Optional[dict]:
    """
    Obtiene un attachment por su ID.
    """
    attachments_collection = db["attachments"]
    try:
        object_id = ObjectId(attachment_id)
    except Exception:
        return None # ID inválido
    attachment_data = await attachments_collection.find_one({"_id": object_id})
    return attachment_data

async def crear_attachment(db: AsyncIOMotorDatabase, attachment_data: dict) -> dict:
    """
    Crea un nuevo attachment en la base de datos.
    """
    attachments_collection = db["attachments"]
    attachment_data["created_at"] = datetime.utcnow()
    result = await attachments_collection.insert_one(attachment_data)
    created_attachment = await attachments_collection.find_one({"_id": result.inserted_id})
    return created_attachment

async def actualizar_attachment(db: AsyncIOMotorDatabase, attachment_id: str, update_data: dict) -> Optional[dict]:
    """
    Actualiza un attachment existente.
    """
    attachments_collection = db["attachments"]
    try:
        object_id = ObjectId(attachment_id)
    except Exception:
        return None # ID inválido
    
    update_data["updated_at"] = datetime.utcnow()
    result = await attachments_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return None # Attachment no encontrado
    updated_attachment = await attachments_collection.find_one({"_id": object_id})
    return updated_attachment

async def eliminar_attachment(db: AsyncIOMotorDatabase, attachment_id: str) -> bool:
    """
    Elimina un attachment por su ID.
    """
    attachments_collection = db["attachments"]
    try:
        object_id = ObjectId(attachment_id)
    except Exception:
        return False # ID inválido
    result = await attachments_collection.delete_one({"_id": object_id})
    return result.deleted_count > 0
