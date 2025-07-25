from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId # Necesario para manejar ObjectId de MongoDB

from app.db.dbp import get_db
from app.Schemas.Esquema import AttachmentCreate, AttachmentUpdate, AttachmentResponse
from app.auth.dependencies import get_current_user # Mantén esta importación si necesitas autenticación
from app.models import attachments_model # Importa las funciones de tu nuevo modelo

router = APIRouter()

# Función auxiliar para formatear un documento de attachment de MongoDB a AttachmentResponse
def format_attachment_document(doc: dict) -> AttachmentResponse:
    # CORRECCIÓN: Asegurarse de que ticket_id y uploaded_by sean strings
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['id'] = str(doc['_id'])
    if 'ticket_id' in doc and isinstance(doc['ticket_id'], ObjectId):
        doc['ticket_id'] = str(doc['ticket_id'])
    if 'uploaded_by' in doc and isinstance(doc['uploaded_by'], ObjectId):
        doc['uploaded_by'] = str(doc['uploaded_by'])
    
    return AttachmentResponse(**doc)

# Ruta para obtener todos los attachments
@router.get("/", response_model=List[AttachmentResponse])
async def read_attachments(
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Obtiene todos los attachments de la base de datos.
    """
    attachments_data = await attachments_model.obtener_attachments(db)
    
    if not attachments_data:
        return []

    return [format_attachment_document(a) for a in attachments_data]

# Ruta para obtener un attachment por ID
@router.get("/{attachment_id}", response_model=AttachmentResponse)
async def get_attachment_by_id(
    attachment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Obtiene un attachment por su ID.
    """
    attachment_data = await attachments_model.obtener_attachment_por_id(db, attachment_id)
    
    if not attachment_data:
        raise HTTPException(status_code=404, detail="Attachment no encontrado.")

    return format_attachment_document(attachment_data)

# Ruta para crear un nuevo attachment (aunque la subida se maneja en tickets_routes)
@router.post("/", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def create_attachment(
    attachment_data: AttachmentCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Crea un nuevo attachment.
    """
    created_attachment = await attachments_model.crear_attachment(db, attachment_data.dict())
    if not created_attachment:
        raise HTTPException(status_code=500, detail="Error al crear el attachment en la base de datos.")

    return format_attachment_document(created_attachment)

# Ruta para actualizar un attachment
@router.put("/{attachment_id}", response_model=AttachmentResponse)
async def update_attachment(
    attachment_id: str,
    data: AttachmentUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Actualiza un attachment existente.
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar.")
    
    updated_attachment = await attachments_model.actualizar_attachment(db, attachment_id, update_data)
    if not updated_attachment:
        raise HTTPException(status_code=404, detail="Attachment no encontrado o error al actualizar.")

    return format_attachment_document(updated_attachment)

# Ruta para eliminar un attachment
@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Elimina un attachment por su ID.
    """
    deleted = await attachments_model.eliminar_attachment(db, attachment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Attachment no encontrado.")
    
    return {"message": "Attachment eliminado correctamente"}
