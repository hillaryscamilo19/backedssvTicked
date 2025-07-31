from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, select
from app.db.base import Base

# NO HAY IMPORTACIONES DE SQLAlchemy AQUÍ




class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    message = Column(String)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"))
    createdat = Column(DateTime(timezone=True), server_default=func.now())
    updatedat = Column(DateTime(timezone=True), onupdate=func.now())

    ticket = relationship("Ticket", back_populates="messages")
    user = relationship("User", back_populates="messages", foreign_keys=[created_by_id])


def messages_helper(message: Message):
    return {
        "id": message.id,
        "message": message.message,
        "created_by_id": message.created_by_id,
        "ticket_id": message.ticket_id,
        "created_at": message.createdat,
        "updated_at": message.updatedat,
    }

async def obtener_mensajes(db: AsyncSession):
    result = await db.execute(select(Message))
    mensajes = result.scalars().all()
    return [messages_helper(m) for m in mensajes]
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
