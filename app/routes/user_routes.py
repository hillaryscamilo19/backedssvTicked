from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId # Necesario para manejar ObjectId de MongoDB
from datetime import datetime

from app.db.dbp import get_db
from app.Schemas.Esquema import UserCreate, UserUpdate, UserResponse, UserInDB, DepartmentResponse
from app.auth.dependencies import get_current_user # Mantén esta importación si necesitas autenticación
from app.auth.security import hash_password # Para el registro o actualización de contraseña

router = APIRouter()

# --- Funciones auxiliares (copiadas de auth.py para evitar dependencias circulares si es necesario) ---
async def get_user_by_username(username: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"username": username})
    if user_data:
        # Asegúrate de que phone_ext y department_id sean strings si son ints en la DB
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        if 'department_id' in user_data and isinstance(user_data['department_id'], int):
            user_data['department_id'] = str(user_data['department_id'])
        return UserInDB(**user_data)
    return None

async def get_user_by_email(email: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"email": email})
    if user_data:
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        if 'department_id' in user_data and isinstance(user_data['department_id'], int):
            user_data['department_id'] = str(user_data['department_id'])
        return UserInDB(**user_data)
    return None

async def get_user_by_phone_ext(phone_ext: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"phone_ext": phone_ext})
    if user_data:
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        if 'department_id' in user_data and isinstance(user_data['department_id'], int):
            user_data['department_id'] = str(user_data['department_id'])
        return UserInDB(**user_data)
    return None

async def get_department_by_id(department_id: str, db: AsyncIOMotorDatabase):
    departments_collection = db["departments"]
    try:
        object_id = ObjectId(department_id)
    except Exception:
        return None # ID inválido
    department_data = await departments_collection.find_one({"_id": object_id})
    if department_data:
        # Pydantic se encargará de _id a id en DepartmentResponse
        return DepartmentResponse(**department_data)
    return None

# Función auxiliar para construir la respuesta de usuario con el departamento anidado
async def build_user_response(user_doc: dict, db: AsyncIOMotorDatabase) -> UserResponse:
    # Asegúrate de que phone_ext y department_id sean strings si son ints en la DB
    # Esto es una conversión de tipo si la DB los guarda como int, para que Pydantic los acepte como str
    if 'phone_ext' in user_doc and isinstance(user_doc['phone_ext'], int):
        user_doc['phone_ext'] = str(user_doc['phone_ext'])
    if 'department_id' in user_doc and isinstance(user_doc['department_id'], int):
        user_doc['department_id'] = str(user_doc['department_id'])

    department_info = None
    if user_doc.get("department_id"):
        department = await get_department_by_id(user_doc["department_id"], db)
        if department:
            department_info = department # Esto ya es una instancia de DepartmentResponse

    # Construye el diccionario para UserResponse explícitamente
    # Asegúrate de que todos los campos requeridos por UserResponse estén presentes
    user_response_data = {
        "id": str(user_doc["_id"]) if "_id" in user_doc else None, # Mapea _id a id
        "username": user_doc.get("username"),
        "email": user_doc.get("email"),
        "fullname": user_doc.get("fullname"),
        "phone_ext": user_doc.get("phone_ext"),
        "department_id": user_doc.get("department_id"),
        "status": user_doc.get("status"),
        "role": user_doc.get("role"),
        "created_at": user_doc.get("created_at"),
        "updated_at": user_doc.get("updated_at"),
        "department": department_info,
    }
    
    # Filtra None para campos opcionales si es necesario, aunque Pydantic los maneja bien
    # user_response_data = {k: v for k, v in user_response_data.items() if v is not None}

    return UserResponse(**user_response_data)


# Ruta para obtener todos los usuarios
@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación
):
    """
    Obtiene todos los usuarios de la base de datos.
    """
    users_collection = db["users"]
    users_data = await users_collection.find({}).to_list(None)
    
    if not users_data:
        return []

    response_users = []
    for user_doc in users_data:
        response_users.append(await build_user_response(user_doc, db))
    
    return response_users

# Ruta para obtener un usuario por ID
@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación
):
    """
    Obtiene un usuario por su ID.
    """
    users_collection = db["users"]
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido.")

    user_data = await users_collection.find_one({"_id": object_id})
    
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    return await build_user_response(user_data, db)

# Ruta para crear un nuevo usuario (si no se usa /register)
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación
):
    """
    Crea un nuevo usuario.
    """
    users_collection = db["users"]

    existing_user_by_username = await get_user_by_username(user.username.lower(), db)
    if existing_user_by_username:
        raise HTTPException(status_code=400, detail="Usuario Ya Existe !")

    existing_user_by_email = await get_user_by_email(user.email.lower(), db)
    if existing_user_by_email:
        raise HTTPException(status_code=400, detail="Email Ya Existe !")

    existing_user_by_phone_ext = await get_user_by_phone_ext(user.phone_ext, db)
    if existing_user_by_phone_ext:
        raise HTTPException(status_code=400, detail="Extension Ya Existe !")

    hashed_password = hash_password(user.password)
    
    user_dict = user.dict(exclude_unset=True)
    user_dict["password"] = hashed_password
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    user_dict["role"] = user.role

    result = await users_collection.insert_one(user_dict)
    
    created_user_data = await users_collection.find_one({"_id": result.inserted_id})
    if not created_user_data:
        raise HTTPException(status_code=500, detail="Error al crear el usuario en la base de datos.")

    return await build_user_response(created_user_data, db)

# Ruta para actualizar un usuario
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación
):
    """
    Actualiza un usuario existente.
    """
    users_collection = db["users"]

    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido.")

    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar.")

    # Si se intenta actualizar la contraseña, hashearla
    if "password" in update_data:
        update_data["password"] = hash_password(update_data["password"])
    
    update_data["updated_at"] = datetime.utcnow()

    result = await users_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    updated_user_data = await users_collection.find_one({"_id": object_id})
    if not updated_user_data:
        raise HTTPException(status_code=500, detail="Error al recuperar el usuario actualizado.")

    return await build_user_response(updated_user_data, db)

# Ruta para eliminar un usuario
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación
):
    """
    Elimina un usuario por su ID.
    """
    users_collection = db["users"]

    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido.")

    result = await users_collection.delete_one({"_id": object_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    return {"message": "Usuario eliminado correctamente"}

# Ruta para obtener colaboradores de un departamento específico
@router.get("/departamento/{department_id}/colaboradores", response_model=List[UserResponse])
async def get_colaboradores_del_departamento(
    department_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user) # Requiere autenticación
):
    """
    Obtiene todos los colaboradores de un departamento específico.
    """
    users_collection = db["users"]
    
    colaboradores_data = await users_collection.find({"department_id": department_id}).to_list(None)

    if not colaboradores_data:
        return []

    response_colaboradores = []
    for user_doc in colaboradores_data:
        response_colaboradores.append(await build_user_response(user_doc, db))
    
    return response_colaboradores
