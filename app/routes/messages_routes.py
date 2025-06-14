from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.models.user_model import User
from app.Schemas.Message import MessageCreate, MessageUpdate
from app.db.dbp import get_db
from app.models.messages_model import Message, messages_helper, obtener_mensajes

router = APIRouter()

@router.get("/")
async def get_messages(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await obtener_mensajes(db)

@router.get("/{message_id}")
async def get_message_by_id(message_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Message).filter(Message.id == message_id))
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return messages_helper(message)

@router.post("/")
async def create_message(message_data: MessageCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Asignamos created_by_id con el usuario actual
    new_message = Message(
        message=message_data.message,
        ticket_id=message_data.ticket_id,
        created_by_id=current_user.id
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    return messages_helper(new_message)

@router.put("/{message_id}")
async def update_message(message_id: int, update_data: MessageUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Message).filter(Message.id == message_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    # Solo el creador del mensaje puede actualizarlo
    if message.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para actualizar este mensaje")

    message.message = update_data.message
    await db.commit()
    await db.refresh(message)
    return messages_helper(message)

@router.delete("/{message_id}")
async def delete_message(message_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Message).filter(Message.id == message_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    # Solo el creador del mensaje puede eliminarlo
    if message.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este mensaje")

    await db.delete(message)
    await db.commit()
    return {"message": "Mensaje eliminado correctamente"}
