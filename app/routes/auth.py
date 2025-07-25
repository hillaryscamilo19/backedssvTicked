# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId # Importar ObjectId

from app.db.dbp import get_db
from app.Schemas.Esquema import UserCreate, UserResponse, DepartmentResponse, UserInDB
from app.auth.security import hash_password, verify_password, create_access_token
from typing import Optional

# --- Tus modelos Pydantic (asegúrate de que estén en app/Schemas/Esquema.py) ---
from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Tus funciones de seguridad (asegúrate de que estén en app/auth/security.py) ---
# Y tus variables de configuración (asegúrate de que estén en config.py)
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

# --- Funciones auxiliares (CORREGIDAS para mapear nombres de campo de MongoDB) ---
async def get_user_by_username(username: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"username": username})
    if user_data:
        # Mapear campos de MongoDB a nombres de Pydantic
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        
        # Mapear 'department' a 'department_id'
        if 'department' in user_data and isinstance(user_data['department'], ObjectId):
            user_data['department_id'] = str(user_data.pop('department'))
        elif 'department' in user_data and isinstance(user_data['department'], str):
            user_data['department_id'] = user_data.pop('department')
        else:
            user_data['department_id'] = None # Asegurar que sea None si no existe o no es válido

        # Mapear 'createdAt' a 'created_at'
        if 'createdAt' in user_data:
            user_data['created_at'] = user_data.pop('createdAt')
        # Mapear 'updatedAt' a 'updated_at'
        if 'updatedAt' in user_data:
            user_data['updated_at'] = user_data.pop('updatedAt')

        return UserInDB(**user_data)
    return None

async def get_user_by_email(email: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"email": email})
    if user_data:
        # Mapear campos de MongoDB a nombres de Pydantic
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        
        if 'department' in user_data and isinstance(user_data['department'], ObjectId):
            user_data['department_id'] = str(user_data.pop('department'))
        elif 'department' in user_data and isinstance(user_data['department'], str):
            user_data['department_id'] = user_data.pop('department')
        else:
            user_data['department_id'] = None

        if 'createdAt' in user_data:
            user_data['created_at'] = user_data.pop('createdAt')
        if 'updatedAt' in user_data:
            user_data['updated_at'] = user_data.pop('updatedAt')

        return UserInDB(**user_data)
    return None

async def get_user_by_phone_ext(phone_ext: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"phone_ext": phone_ext})
    if user_data:
        # Mapear campos de MongoDB a nombres de Pydantic
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        
        if 'department' in user_data and isinstance(user_data['department'], ObjectId):
            user_data['department_id'] = str(user_data.pop('department'))
        elif 'department' in user_data and isinstance(user_data['department'], str):
            user_data['department_id'] = user_data.pop('department')
        else:
            user_data['department_id'] = None

        if 'createdAt' in user_data:
            user_data['created_at'] = user_data.pop('createdAt')
        if 'updatedAt' in user_data:
            user_data['updated_at'] = user_data.pop('updatedAt')

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
        # Asegurarse de que los campos de fecha también se mapeen si son camelCase en DB
        if 'createdAt' in department_data:
            department_data['created_at'] = department_data.pop('createdAt')
        if 'updatedAt' in department_data:
            department_data['updated_at'] = department_data.pop('updatedAt')
        return DepartmentResponse(**department_data)
    return None

# Función auxiliar para construir la respuesta de usuario con el departamento anidado (CORREGIDA)
async def build_user_response(user_doc: dict, db: AsyncIOMotorDatabase) -> UserResponse:
    # Mapear _id a id
    user_id_str = str(user_doc["_id"]) if "_id" in user_doc else None

    # Mapear phone_ext a string si es int
    phone_ext_str = str(user_doc['phone_ext']) if 'phone_ext' in user_doc and isinstance(user_doc['phone_ext'], int) else user_doc.get('phone_ext')

    # Mapear 'department' (ObjectId) a 'department_id' (string)
    department_id_from_db = user_doc.get("department")
    department_id_str = str(department_id_from_db) if isinstance(department_id_from_db, ObjectId) else department_id_from_db

    department_info = None
    if department_id_str:
        department = await get_department_by_id(department_id_str, db)
        if department:
            department_info = department # Esto ya es una instancia de DepartmentResponse

    # Construye el diccionario para UserResponse explícitamente
    user_response_data = {
        "id": user_id_str,
        "username": user_doc.get("username"),
        "email": user_doc.get("email"),
        "fullname": user_doc.get("fullname"),
        "phone_ext": phone_ext_str,
        "department_id": department_id_str, # Usar el ID de departamento mapeado
        "status": user_doc.get("status"),
        "role": user_doc.get("role"),
        "created_at": user_doc.get("createdAt"), # Usar 'createdAt' de MongoDB
        "updated_at": user_doc.get("updatedAt"), # Usar 'updatedAt' de MongoDB
        "department": department_info,
    }
    
    return UserResponse(**user_response_data)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
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
    # Al crear, usa los nombres de campo que MongoDB almacenará
    user_dict["createdAt"] = datetime.utcnow()
    user_dict["updatedAt"] = datetime.utcnow()
    user_dict["role"] = user.role
    # Mapear department_id de Pydantic a 'department' para MongoDB
    if user_dict.get("department_id"):
        user_dict["department"] = ObjectId(user_dict.pop("department_id"))
    else:
        user_dict.pop("department_id", None) # Eliminar si es None

    result = await users_collection.insert_one(user_dict)
    
    created_user_data = await users_collection.find_one({"_id": result.inserted_id})
    if not created_user_data:
        raise HTTPException(status_code=500, detail="Error al crear el usuario en la base de datos.")

    return await build_user_response(created_user_data, db)


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await get_user_by_username(form_data.username, db)

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrecto")

    if not user.status:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    department_data = None
    if user.department_id: # user.department_id ahora debería ser un string
        department_data = await get_department_by_id(user.department_id, db)

    token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "fullname": user.fullname,
            "phone_ext": user.phone_ext,
            "status": user.status,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None, # Asegurar isoformat
            "updated_at": user.updated_at.isoformat() if user.updated_at else None, # Asegurar isoformat
            "department": {
                "id": str(department_data.id),
                "name": department_data.name,
                "created_at": department_data.created_at.isoformat() if department_data.created_at else None,
                "updated_at": department_data.updated_at.isoformat() if department_data.updated_at else None,
            } if department_data else None,
        }
    }
