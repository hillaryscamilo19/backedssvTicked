from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from bson import ObjectId, errors
from datetime import datetime
from bson import ObjectId, errors
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from app.db import db
# Ya no necesitamos la clase Ticket de SQLAlchemy aquí.
# Solo funciones para interactuar con la colección de MongoDB.


async def obtener_tickets(db: AsyncIOMotorDatabase) -> List[dict]:
    """
    Obtiene todos los tickets de la base de datos.
    """
    tickets_collection = db["tickets"]
    tickets_data = await tickets_collection.find({}).to_list(None)
    return tickets_data


async def obtener_tickets_asignados_a_usuario(db: AsyncIOMotorDatabase, user_id: str) -> List[dict]:
    """
    Obtiene todos los tickets asignados a un usuario específico.
    """
    print("Tipo de db:", type(db))
    try:
        user_object_id = ObjectId(user_id)
    except errors.InvalidId:
        # Si el ID no es válido, devuelve lista vacía
        return []

    tickets_collection = db["tickets"]
    tickets = await tickets_collection.find({"assigned_users": user_object_id}).to_list(None)
    return tickets


async def obtener_ticket_por_id(db: AsyncIOMotorDatabase, ticket_id: str) -> Optional[dict]:
    """
    Obtiene un ticket por su ID.
    """
    tickets_collection = db["tickets"]
    try:
        object_id = ObjectId(ticket_id)
    except Exception:
        return None # ID inválido
    ticket_data = await tickets_collection.find_one({"_id": object_id})
    return ticket_data

async def crear_ticket(db: AsyncIOMotorDatabase, ticket_data: dict) -> dict:
    """
    Crea un nuevo ticket en la base de datos.
    """
    tickets_collection = db["tickets"]
    ticket_data["created_at"] = datetime.utcnow()
    ticket_data["updated_at"] = datetime.utcnow()
    result = await tickets_collection.insert_one(ticket_data)
    created_ticket = await tickets_collection.find_one({"_id": result.inserted_id})
    return created_ticket

async def actualizar_ticket(db: AsyncIOMotorDatabase, ticket_id: str, update_data: dict) -> Optional[dict]:
    """
    Actualiza un ticket existente.
    """
    tickets_collection = db["tickets"]
    try:
        object_id = ObjectId(ticket_id)
    except Exception:
        return None # ID inválido
    
    update_data["updated_at"] = datetime.utcnow()
    result = await tickets_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return None # Ticket no encontrado
    updated_ticket = await tickets_collection.find_one({"_id": object_id})
    return updated_ticket

async def eliminar_ticket(db: AsyncIOMotorDatabase, ticket_id: str) -> bool:
    """
    Elimina un ticket por su ID.
    """
    tickets_collection = db["tickets"]
    try:
        object_id = ObjectId(ticket_id)
    except Exception:
        return False # ID inválido
    result = await tickets_collection.delete_one({"_id": object_id})
    return result.deleted_count > 0

# La función ticket_helper ya no es necesaria aquí, su lógica se moverá a build_ticket_response en las rutas.