from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId # Necesario para manejar ObjectId de MongoDB
from datetime import datetime # Para timestamps

from app.db.dbp import get_db
from app.Schemas.Esquema import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.auth.dependencies import get_current_user # Mantén esta importación si necesitas autenticación

router = APIRouter()

# Ruta para obtener todos los departamentos
@router.get("/", response_model=List[DepartmentResponse])
async def get_departments(
  db: AsyncIOMotorDatabase = Depends(get_db),
  # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
  """
  Obtiene todos los departamentos de la base de datos.
  """
  departments_collection = db["departments"]
  
  departments_data = await departments_collection.find({}).to_list(None)
  
  if not departments_data:
      return []

  return [DepartmentResponse(**d) for d in departments_data]

# Ruta para obtener un departamento por id
@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department_by_id(
  department_id: str, # El ID de MongoDB es un string
  db: AsyncIOMotorDatabase = Depends(get_db),
  # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
  """
  Obtiene un departamento por su ID.
  """
  departments_collection = db["departments"]
  
  try:
      object_id = ObjectId(department_id)
  except Exception:
      raise HTTPException(status_code=400, detail="ID de departamento inválido.")

  department_data = await departments_collection.find_one({"_id": object_id})
  
  if not department_data:
      raise HTTPException(status_code=404, detail="Departamento no encontrado.")

  return DepartmentResponse(**department_data)

# Ruta para crear un nuevo departamento
@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
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
  department_dict["created_at"] = datetime.utcnow()
  department_dict["updated_at"] = datetime.utcnow()

  result = await departments_collection.insert_one(department_dict)
  
  created_department_data = await departments_collection.find_one({"_id": result.inserted_id})
  if not created_department_data:
      raise HTTPException(status_code=500, detail="Error al crear el departamento en la base de datos.")

  return DepartmentResponse(**created_department_data)

# Ruta para actualizar un departamento
@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
  department_id: str,
  data: DepartmentUpdate,
  db: AsyncIOMotorDatabase = Depends(get_db),
  # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
  """
  Actualiza un departamento existente.
  """
  departments_collection = db["departments"]

  try:
      object_id = ObjectId(department_id)
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
@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
  department_id: str,
  db: AsyncIOMotorDatabase = Depends(get_db),
  # current_user: dict = Depends(get_current_user) # Descomenta si necesitas autenticación
):
  """
  Elimina un departamento por su ID.
  """
  departments_collection = db["departments"]

  try:
      object_id = ObjectId(department_id)
  except Exception:
      raise HTTPException(status_code=400, detail="ID de departamento inválido.")

  result = await departments_collection.delete_one({"_id": object_id})

  if result.deleted_count == 0:
      raise HTTPException(status_code=404, detail="Departamento no encontrado.")
  
  return {"message": "Departamento eliminado correctamente"} # FastAPI 0.100+ permite retornar un dict con 204
