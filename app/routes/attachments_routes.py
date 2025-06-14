from fastapi import APIRouter, Depends, File, HTTPException, UploadFile,Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.models.user_model import User
from app.Schemas.Attachment import AttachmentCreate, AttachmentUpdate
from app.models.attachments_model import Attachment, attachments_to_dict, obtener_attachments
from app.db.dbp import get_db
import os
import shutil
from uuid import uuid4

router = APIRouter()

# Ruta para obtener los attachments
@router.get("/")
async def read_attachments(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachments = await obtener_attachments(db)
    return attachments

# Ruta para obtener un attachment
@router.get("/{attachment_id}")
async def get_attachment_by_id(attachment_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Attachment).filter(Attachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return attachments_to_dict(attachment)


#Ruta para crear un attachment
@router.post("/", summary="Subir archivo adjunto para un ticket")
async def create_attachment(
    file: UploadFile = File(...),
    ticket_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    unique_filename = f"{uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_extension = os.path.splitext(file.filename)[1]

    new_attachment = Attachment(
        file_name=file.filename,
        file_path=f"/uploads/{unique_filename}",
        file_extension=file_extension,
        ticket_id=ticket_id
    )

    db.add(new_attachment)
    await db.commit()
    await db.refresh(new_attachment)

    return attachments_to_dict(new_attachment)


# Ruta para actualizar un attachment
@router.put("/{attachment_id}")
async def update_attachment(attachment_id: int, data: AttachmentUpdate, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Attachment).filter(Attachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    for key, value in data.dict().items():
        setattr(attachment, key, value)

    await db.commit()
    await db.refresh(attachment)
    return attachments_to_dict(attachment)


# Ruta para eliminar un attachment 
@router.delete("/{attachment_id}")
async def delete_attachment(attachment_id: int, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Attachment).filter(Attachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    await db.delete(attachment)
    await db.commit()
    return {"message": "Archivo eliminado correctamente"}


