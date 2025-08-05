
import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.models import departments_model
from app.models.user_model import User
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.Schemas.Departamento import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.db.dbp import get_db
from app.models.departments_model import DepartmentModel, departments_helper
from app.models.departments_model import Department
from sqlalchemy.future import select

router = APIRouter()

class DepartmentResponse(BaseModel):
    id: str  # Cambiado a str para aceptar ObjectId
    name: str
    status: bool

def format_category_document(doc: dict) -> DepartmentResponse:
    # Asegúrate de que todos los campos requeridos estén presentes
    return DepartmentResponse(
        id=str(doc["_id"]),  # Convierte ObjectId a str
        name=doc["name"],
        status=doc.get("status", True)  # Proporciona un valor predeterminado si no está presente
    )

# Ruta para obtener todos los departamentos
@router.get("/", response_model=List[DepartmentResponse])  # Usa el modelo de Pydantic aquí
async def get_departments(
    db: AsyncSession = Depends(get_db)    
):
    """
    Obtiene todas los departamentos de la base de datos.
    """
    departments_data = await departments_model.obtener_departments(db)
    if not departments_data:
        return []
    return [format_category_document(c) for c in departments_data]

# Ruta para obtener un departamento por id
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department_by_id(department: str, token: str = Depends(oauth2_scheme), db: AsyncIOMotorDatabase = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Obtén el departamento desde la base de datos
    department_data = await db.your_database.your_collection.find_one({"_id": ObjectId(department)})
    
    if not department_data:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    
    # Asegúrate de que todos los campos requeridos estén presentes
    return DepartmentResponse(
        id=str(department_data["_id"]),  # Convierte ObjectId a str
        name=department_data["name"],
        status=department_data.get("status", True)  # Proporciona un valor predeterminado si no está presente
    )


# Ruta para crear un nuevo departamento
@router.post("/", response_model=DepartmentResponse)
async def create_department(
  department_data: DepartmentCreate,
  db: AsyncIOMotorDatabase = Depends(get_db),
  # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
  """
  Crea un nuevo departamento.
  """
  departments_collection = db["departments"]

  # Verifica si ya existe un departamento con el mismo nombre (insensible a mayúsculas/minúsculas)
  existing_department = await departments_collection.find_one({"name": {"$regex": department_data.name, "$options": "i"}})
  if existing_department:
      raise HTTPException(status_code=400, detail="El departamento ya existe.")

  department_dict = department_data.dict()
  department_dict["createdAt"] = datetime.utcnow()
  department_dict["updated_at"] = datetime.utcnow()

  result = await departments_collection.insert_one(department_dict)
  
  created_department_data = await departments_collection.find_one({"_id": result.inserted_id})
  if not created_department_data:
      raise HTTPException(status_code=500, detail="Error al crear el departamento en la base de datos.")

  return DepartmentResponse(**created_department_data)

# Ruta para actualizar un departamento
@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
  department: str,
  data: DepartmentUpdate,
  db: AsyncIOMotorDatabase = Depends(get_db),
  # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
  """
  Actualiza un departamento existente.
  """
  departments_collection = db["departments"]

  try:
      object_id = ObjectId(department)
  except Exception:
      raise HTTPException(status_code=400, detail="ID de departamento inválido.")

  # Prepara los datos para la actualización, excluyendo campos no establecidos
  update_data = data.dict(exclude_unset=True)
  if not update_data:
      raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar.")
  
  update_data["updated_at"] = datetime.utcnow() # Actualiza el timestamp de modificación

  result = await departments_collection.update_one(
      {"_id": object_id},
      {"$set": update_data}
  )

  if result.matched_count == 0:
      raise HTTPException(status_code=404, detail="Departamento no encontrado.")
  
  # Recupera el documento actualizado para la respuesta
  updated_department_data = await departments_collection.find_one({"_id": object_id})
  if not updated_department_data:
      raise HTTPException(status_code=500, detail="Error al recuperar el departamento actualizado.")

  return DepartmentResponse(**updated_department_data)

# Ruta para eliminar un departamento
@router.delete("/{department_id}")
async def delete_department(
  department: str,
  db: AsyncIOMotorDatabase = Depends(get_db),
  # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
  """
  Elimina un departamento por su ID.
  """
  departments_collection = db["departments"]

  try:
      object_id = ObjectId(department)
  except Exception:
      raise HTTPException(status_code=400, detail="ID de departamento inválido.")

  result = await departments_collection.delete_one({"_id": object_id})

  if result.deleted_count == 0:
      raise HTTPException(status_code=404, detail="Departamento no encontrado.")
  
  return {"message": "Departamento eliminado correctamente"} # FastAPI 0.100+ permite retornar un dict con 204

