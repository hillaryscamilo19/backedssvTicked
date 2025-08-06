from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from bson import ObjectId, errors
from datetime import datetime
from bson import ObjectId, errors
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from app.db import db
from bson import ObjectId

def ticket_helper(ticket) -> dict:
    return {
        "id": str(ticket["_id"]),  # Convertir ObjectId a string
        "title": ticket.get("title"),
        "description": ticket.get("description"),
        "category": {
            "id": str(ticket.get("category")) if ticket.get("category") else None,
            "name": None  # Aquí puedes agregar lógica para obtener el nombre de la categoría si es necesario
        },
        "assigned_department": {
            "id": str(ticket.get("assigned_department")) if ticket.get("assigned_department") else None,
            "name": None  # Aquí puedes agregar lógica para obtener el nombre del departamento si es necesario
        },
        "created_user": {
            "id": str(ticket.get("created_user")) if ticket.get("created_user") else None,
            "fullname": None,  # Aquí puedes agregar lógica para obtener el nombre completo del usuario si es necesario
            "email": None,  # Aquí puedes agregar lógica para obtener el email del usuario si es necesario
            "phone_ext": None,  # Aquí puedes agregar lógica para obtener la extensión telefónica del usuario si es necesario
        },
        "status": ticket.get("status"),
        "createdAt": ticket.get("createdAt"),
        "updatedAt": ticket.get("updatedAt"),
        "assigned_users": [
            {
                "id": str(u) if isinstance(u, ObjectId) else u,  # Convertir ObjectId a string
                "fullname": None,  # Aquí puedes agregar lógica para obtener el nombre completo del usuario asignado
                "email": None,  # Aquí puedes agregar lógica para obtener el email del usuario asignado
                "phone_ext": None,  # Aquí puedes agregar lógica para obtener la extensión telefónica del usuario asignado
            } for u in ticket.get("assigned_users", [])
        ],
        "messages": [
            {
                "id": str(m) if isinstance(m, ObjectId) else m,  # Convertir ObjectId a string
                "content": None,  # Aquí puedes agregar lógica para obtener el contenido del mensaje
                "createdAt": None,  # Aquí puedes agregar lógica para obtener la fecha de creación del mensaje
            } for m in ticket.get("messages", [])
        ],
        "attachments": [
            {
                "id": str(a) if isinstance(a, ObjectId) else a,  # Convertir ObjectId a string
                "file_name": None,  # Aquí puedes agregar lógica para obtener el nombre del archivo
                "file_path": None,  # Aquí puedes agregar lógica para obtener la ruta del archivo
                "file_extension": None,  # Aquí puedes agregar lógica para obtener la extensión del archivo
            } for a in ticket.get("attachments", [])
        ],
    }


class Ticket:
       def __init__(self, **kwargs):
           self.id = str(kwargs.get("_id"))  # Convertir ObjectId a string
           self.title = kwargs.get("title")
           self.description = kwargs.get("description")
           self.category = kwargs.get("category")
           self.assigned_department = kwargs.get("assigned_department")
           self.created_user = kwargs.get("created_user")
           self.status = kwargs.get("status")
           self.createdAt = kwargs.get("createdAt")
           self.updated_at = kwargs.get("updatedAt")
           self.assigned_users = kwargs.get("assigned_users", [])
           self.messages = kwargs.get("messages", [])
           self.attachments = kwargs.get("attachments", [])
   
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
