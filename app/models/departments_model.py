from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from datetime import datetime

# NO HAY IMPORTACIONES DE SQLAlchemy AQUÍ

async def obtener_departments(db: AsyncIOMotorDatabase) -> List[dict]:
    """
    Obtiene todos los departamentos de la base de datos.
    """
    departments_collection = db["departments"]
    departments_data = await departments_collection.find({}).to_list(None)
    return departments_data

async def obtener_department_por_id(db: AsyncIOMotorDatabase, department_id: str) -> Optional[dict]:
    """
    Obtiene un departamento por su ID.
    """
    departments_collection = db["departments"]
    try:
        object_id = ObjectId(department_id)
    except Exception:
        return None # ID inválido
    department_data = await departments_collection.find_one({"_id": object_id})
    return department_data

async def crear_department(db: AsyncIOMotorDatabase, department_data: dict) -> dict:
    """
    Crea un nuevo departamento en la base de datos.
    """
    departments_collection = db["departments"]
    department_data["created_at"] = datetime.utcnow()
    department_data["updated_at"] = datetime.utcnow()
    result = await departments_collection.insert_one(department_data)
    created_department = await departments_collection.find_one({"_id": result.inserted_id})
    return created_department

async def actualizar_department(db: AsyncIOMotorDatabase, department_id: str, update_data: dict) -> Optional[dict]:
    """
    Actualiza un departamento existente.
    """
    departments_collection = db["departments"]
    try:
        object_id = ObjectId(department_id)
    except Exception:
        return None # ID inválido
    
    update_data["updated_at"] = datetime.utcnow()
    result = await departments_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return None # Departamento no encontrado
    updated_department = await departments_collection.find_one({"_id": object_id})
    return updated_department

async def eliminar_department(db: AsyncIOMotorDatabase, department_id: str) -> bool:
    """
    Elimina un departamento por su ID.
    """
    departments_collection = db["departments"]
    try:
        object_id = ObjectId(department_id)
    except Exception:
        return False # ID inválido
    result = await departments_collection.delete_one({"_id": object_id})
    return result.deleted_count > 0
