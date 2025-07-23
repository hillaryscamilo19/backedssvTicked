from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId # Necesario para manejar ObjectId de MongoDB

from app.db.dbp import get_db
from app.Schemas.Esquema import CategoryCreate, CategoryUpdate, CategoryResponse
from app.auth.dependencies import get_current_user # Mantén esta importación si necesitas autenticación
from app.models import categories_model # Importa las funciones de tu nuevo modelo

router = APIRouter()

# Función auxiliar para formatear un documento de categoría de MongoDB a CategoryResponse
def format_category_document(doc: dict) -> CategoryResponse:
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['id'] = str(doc['_id'])
        del doc['_id']
    return CategoryResponse(**doc)

# Ruta para obtener todas las categorías
@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Obtiene todas las categorías de la base de datos.
    """
    categories_data = await categories_model.obtener_categories(db)
    
    if not categories_data:
        return []

    return [format_category_document(c) for c in categories_data]

# Ruta para obtener una categoría por ID
@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category_by_id(
    category_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Obtiene una categoría por su ID.
    """
    category_data = await categories_model.obtener_category_por_id(db, category_id)
    
    if not category_data:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")

    return format_category_document(category_data)

# Ruta para crear una nueva categoría
@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Crea una nueva categoría.
    """
    # Verifica si ya existe una categoría con el mismo nombre (insensible a mayúsculas/minúsculas)
    existing_category = await db["categories"].find_one({"name": {"$regex": category_data.name, "$options": "i"}})
    if existing_category:
        raise HTTPException(status_code=400, detail="La categoría ya existe.")

    created_category = await categories_model.crear_category(db, category_data.dict())
    if not created_category:
        raise HTTPException(status_code=500, detail="Error al crear la categoría en la base de datos.")

    return format_category_document(created_category)

# Ruta para actualizar una categoría
@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Actualiza una categoría existente.
    """
    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar.")
    
    updated_category = await categories_model.actualizar_category(db, category_id, update_data)
    if not updated_category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada o error al actualizar.")

    return format_category_document(updated_category)

# Ruta para eliminar una categoría
@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
    """
    Elimina una categoría por su ID.
    """
    deleted = await categories_model.eliminar_category(db, category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")
    
    return {"message": "Categoría eliminada correctamente"}
0