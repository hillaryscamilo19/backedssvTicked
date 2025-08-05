from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from datetime import datetime

# No necesitamos un modelo de base de datos aquí, solo funciones para interactuar con la colección

async def obtener_categories(db: AsyncIOMotorDatabase) -> List[dict]:
    """
    Obtiene todas las categorías de la base de datos.
    """
    categories_collection = db["categories"]
    categories_data = await categories_collection.find({}).to_list(None)
    return categories_data

async def obtener_category_por_id(db: AsyncIOMotorDatabase, category_id: str) -> Optional[dict]:
    """
    Obtiene una categoría por su ID.
    """
    categories_collection = db["categories"]
    try:
        object_id = ObjectId(category_id)
    except Exception:
        return None # ID inválido
    category_data = await categories_collection.find_one({"_id": object_id})
    return category_data

async def crear_category(db: AsyncIOMotorDatabase, category_data: dict) -> dict:
    """
    Crea una nueva categoría en la base de datos.
    """
    categories_collection = db["categories"]
    category_data["createdAt"] = datetime.utcnow()
    category_data["updatedAt"] = datetime.utcnow()
    result = await categories_collection.insert_one(category_data)
    created_category = await categories_collection.find_one({"_id": result.inserted_id})
    return created_category

async def actualizar_category(db: AsyncIOMotorDatabase, category_id: str, update_data: dict) -> Optional[dict]:
    """
    Actualiza una categoría existente.
    """
    categories_collection = db["categories"]
    try:
        object_id = ObjectId(category_id)
    except Exception:
        return None # ID inválido
    
    update_data["updated_at"] = datetime.utcnow()
    result = await categories_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return None # Categoría no encontrada
    updated_category = await categories_collection.find_one({"_id": object_id})
    return updated_category

async def eliminar_category(db: AsyncIOMotorDatabase, category_id: str) -> bool:
    """
    Elimina una categoría por su ID.
    """
    categories_collection = db["categories"]
    try:
        object_id = ObjectId(category_id)
    except Exception:
        return False # ID inválido
    result = await categories_collection.delete_one({"_id": object_id})
    return result.deleted_count > 0
