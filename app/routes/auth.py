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
        # Solo convertir phone_ext a string si es int
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        
        # Convertir department ObjectId a string si es necesario
        if 'department' in user_data and isinstance(user_data['department'], ObjectId):
            user_data['department'] = str(user_data['department'])

        return UserInDB(**user_data)
    return None

async def get_user_by_email(email: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"email": email})
    if user_data:
        # Solo convertir phone_ext a string si es int
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        
        # Convertir department ObjectId a string si es necesario
        if 'department' in user_data and isinstance(user_data['department'], ObjectId):
            user_data['department'] = str(user_data['department'])

        return UserInDB(**user_data)
    return None

async def get_user_by_phone_ext(phone_ext: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"phone_ext": phone_ext})
    if user_data:
        # Crear una copia para evitar modificar el original
        user_data_copy = user_data.copy()
        
        # Convertir phone_ext a string si es int
        if 'phone_ext' in user_data_copy and isinstance(user_data_copy['phone_ext'], int):
            user_data_copy['phone_ext'] = str(user_data_copy['phone_ext'])
        
        # Convertir department ObjectId a string si es necesario
        if 'department' in user_data_copy:
            if isinstance(user_data_copy['department'], ObjectId):
                user_data_copy['department'] = str(user_data_copy['department'])
            elif user_data_copy['department'] is None:
                user_data_copy['department'] = None
        
        # Eliminar campos que no son parte del modelo
        if '__v' in user_data_copy:
            del user_data_copy['__v']

        return UserInDB(**user_data_copy)
    return None

async def get_department_by_id(department_id: str, db: AsyncIOMotorDatabase):
    departments_collection = db["departments"]
    try:
        object_id = ObjectId(department_id)
    except Exception:
        return None # ID inválido
    department_data = await departments_collection.find_one({"_id": object_id})
    if department_data:
        # Crear una copia para evitar modificar el original
        department_data_copy = department_data.copy()
        
        # Eliminar campos que no son parte del modelo
        if '__v' in department_data_copy:
            del department_data_copy['__v']
            
        return DepartmentResponse(**department_data_copy)
    return None


# Función auxiliar para construir la respuesta de usuario con el departamento anidado (CORREGIDA)
async def build_user_response(user_doc: dict, db: AsyncIOMotorDatabase) -> UserResponse:
    # Crear una copia para evitar modificar el original
    user_doc_copy = user_doc.copy()
    
    # Convertir phone_ext a string si es int
    if 'phone_ext' in user_doc_copy and isinstance(user_doc_copy['phone_ext'], int):
        user_doc_copy['phone_ext'] = str(user_doc_copy['phone_ext'])

    # Obtener información del departamento si existe
    department_info = None
    if user_doc_copy.get("department"):
        department_id = str(user_doc_copy["department"]) if isinstance(user_doc_copy["department"], ObjectId) else user_doc_copy["department"]
        department = await get_department_by_id(department_id, db)
        if department:
            department_info = department

    # Convertir department ObjectId a string para la respuesta
    if 'department' in user_doc_copy:
        if isinstance(user_doc_copy['department'], ObjectId):
            user_doc_copy['department'] = str(user_doc_copy['department'])
        elif user_doc_copy['department'] is None:
            user_doc_copy['department'] = None

    # Eliminar campos que no son parte del modelo
    if '__v' in user_doc_copy:
        del user_doc_copy['__v']

    # Construir la respuesta
    user_doc_copy['department_info'] = department_info  # Usar department_info para evitar conflicto
    
    return UserResponse(**user_doc_copy)



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
    # Convertir department string a ObjectId si se proporciona
    if user_dict.get("department"):
        user_dict["department"] = ObjectId(user_dict["department"])

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
    if user.department: # user.department ahora debería ser un string
        department_data = await get_department_by_id(user.department, db)

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
            "createdAt": user.createdAt.isoformat() if user.createdAt else None, # Asegurar isoformat
            "updatedAt": user.updatedAt.isoformat() if user.updatedAt else None, # Asegurar isoformat
            "department": {
                "id": str(department_data.id),
                "name": department_data.name,
                "created_at": department_data.created_at.isoformat() if department_data.created_at else None,
                "updated_at": department_data.updated_at.isoformat() if department_data.updated_at else None,
            } if department_data else None,
        }
    }
