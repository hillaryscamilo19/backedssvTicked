from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase # <--- Añadir esta importación
from bson import ObjectId # Necesario para manejar ObjectId de MongoDB

from app.db.dbp import get_db
from app.Schemas.Esquema import MessageCreate, MessageUpdate, MessageResponse, UserInDB
from app.auth.dependencies import get_current_user # Mantén esta importación si necesitas autenticación
from app.models import messages_model # Importa las funciones de tu nuevo modelo
from app.models.user_model import obtener_user_por_id # Para anidar información del usuario

router = APIRouter()

# Función auxiliar para formatear un documento de mensaje de MongoDB a MessageResponse
async def format_message_document(doc: dict, db: AsyncIOMotorDatabase) -> MessageResponse:
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['id'] = str(doc['_id'])
        # No eliminar _id si Pydantic lo necesita para el alias

    # Cargar información del usuario que creó el mensaje
    user_info = None
    if doc.get("created_by_id"):
        user_data = await obtener_user_por_id(db, doc["created_by_id"])
        if user_data:
            # Solo necesitamos id y fullname para el mensaje
            user_info = {"id": str(user_data["_id"]), "fullname": user_data.get("fullname")}
    
    # Construir el diccionario para MessageResponse
    message_response_data = {
        "id": str(doc["_id"]),
        "message": doc.get("message"),
        "ticket_id": doc.get("ticket_id"),
        "created_by_id": doc.get("created_by_id"),
        "created_at": doc.get("created_at"),
        "user": user_info # Anida la información del usuario
    }
    return MessageResponse(**message_response_data)

# Ruta para obtener todos los mensajes
@router.get("/", response_model=List[MessageResponse])
async def get_messages(
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Obtiene todos los mensajes de la base de datos.
    """
    messages_data = await messages_model.obtener_mensajes(db)
    
    if not messages_data:
        return []

    response_messages = []
    for msg_doc in messages_data:
        response_messages.append(await format_message_document(msg_doc, db))
    
    return response_messages

# Ruta para obtener un mensaje por ID
@router.get("/{message_id}", response_model=MessageResponse)
async def get_message_by_id(
    message_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Obtiene un mensaje por su ID.
    """
    message_data = await messages_model.obtener_mensaje_por_id(db, message_id)
    
    if not message_data:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")

    return await format_message_document(message_data, db)

# Ruta para crear un nuevo mensaje (aunque la creación de mensajes de ticket se maneja en tickets_routes)
@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: MessageCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Asumiendo que el creador es el usuario actual
):
    """
    Crea un nuevo mensaje.
    """
    message_dict = message_data.dict()
    message_dict["created_by_id"] = str(current_user.id) # Asigna el ID del usuario actual
    
    created_message = await messages_model.crear_message(db, message_dict)
    if not created_message:
        raise HTTPException(status_code=500, detail="Error al crear el mensaje en la base de datos.")

    return await format_message_document(created_message, db)

# Ruta para actualizar un mensaje
@router.put("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: str,
    data: MessageUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación para actualizar
):
    """
    Actualiza un mensaje existente.
    """
    message_data = await messages_model.obtener_mensaje_por_id(db, message_id)
    if not message_data:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
    
    # Solo el creador del mensaje puede actualizarlo
    if str(message_data.get("created_by_id")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="No tienes permiso para actualizar este mensaje.")

    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar.")
    
    updated_message = await messages_model.actualizar_message(db, message_id, update_data)
    if not updated_message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado o error al actualizar.")

    return await format_message_document(updated_message, db)

# Ruta para eliminar un mensaje
@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación para eliminar
):
    """
    Elimina un mensaje por su ID.
    """
    message_data = await messages_model.obtener_mensaje_por_id(db, message_id)
    if not message_data:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
    
    # Solo el creador del mensaje puede eliminarlo
    if str(message_data.get("created_by_id")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este mensaje.")

    deleted = await messages_model.eliminar_message(db, message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
    
    return {"message": "Mensaje eliminado correctamente"}
