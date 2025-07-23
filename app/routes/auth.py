# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId # Importa ObjectId

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

# --- Funciones auxiliares ---
async def get_user_by_username(username: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"username": username})
    if user_data:
        # Asegúrate de que phone_ext y department_id sean strings si son ints en la DB
        if 'phone_ext' in user_data and isinstance(user_data['phone_ext'], int):
            user_data['phone_ext'] = str(user_data['phone_ext'])
        if 'department_id' in user_data and isinstance(user_data['department_id'], int):
            user_data['department_id'] = str(user_data['department_id'])
        
        # --- CORRECCIÓN AQUÍ: Añade created_at y updated_at si faltan ---
        if 'created_at' not in user_data:
            user_data['created_at'] = None # O datetime.min si prefieres una fecha por defecto
        if 'updated_at' not in user_data:
            user_data['updated_at'] = None # O datetime.min si prefieres una fecha por defecto
        # --- FIN CORRECCIÓN ---

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
        
        # --- CORRECCIÓN AQUÍ: Añade created_at y updated_at si faltan ---
        if 'created_at' not in user_data:
            user_data['created_at'] = None
        if 'updated_at' not in user_data:
            user_data['updated_at'] = None
        # --- FIN CORRECCIÓN ---

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
        
        # --- CORRECCIÓN AQUÍ: Añade created_at y updated_at si faltan ---
        if 'created_at' not in user_data:
            user_data['created_at'] = None
        if 'updated_at' not in user_data:
            user_data['updated_at'] = None
        # --- FIN CORRECCIÓN ---

        return UserInDB(**user_data)
    return None

async def get_department_by_id(department_id: str, db: AsyncIOMotorDatabase):
    departments_collection = db["departments"]
    try:
        object_id = ObjectId(department_id) # Convierte a ObjectId
    except Exception:
        return None # O levanta HTTPException si prefieres

    department_data = await departments_collection.find_one({"_id": object_id})
    if department_data:
        # Asegúrate de que _id sea un string si es un ObjectId
        if '_id' in department_data and isinstance(department_data['_id'], ObjectId):
            department_data['id'] = str(department_data['_id']) # Mapea _id a id y lo convierte a string
            del department_data['_id'] # Elimina el _id original si no lo necesitas en la respuesta
        return DepartmentResponse(**department_data)
    return None


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
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    user_dict["role"] = user.role

    result = await users_collection.insert_one(user_dict)
    
    created_user_data = await users_collection.find_one({"_id": result.inserted_id})
    if not created_user_data:
        raise HTTPException(status_code=500, detail="Error al crear el usuario en la base de datos.")

    # Asegúrate de que phone_ext y department_id sean strings si son ints en la DB
    if 'phone_ext' in created_user_data and isinstance(created_user_data['phone_ext'], int):
        created_user_data['phone_ext'] = str(created_user_data['phone_ext'])
    if 'department_id' in created_user_data and isinstance(created_user_data['department_id'], int):
        created_user_data['department_id'] = str(created_user_data['department_id'])

    # Formatea el _id a string para la respuesta
    if '_id' in created_user_data and isinstance(created_user_data['_id'], ObjectId):
        created_user_data['id'] = str(created_user_data['_id'])
        del created_user_data['_id']

    return UserResponse(**created_user_data)


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await get_user_by_username(form_data.username, db)

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrecto")

    if not user.status:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    department_data = None
    if user.department_id:
        department_data = await get_department_by_id(user.department_id, db)

    token = create_access_token(data={"sub": user.username})
    
    # Asegúrate de que created_at y updated_at sean isoformat si no son None
    user_created_at_iso = user.created_at.isoformat() if user.created_at else None
    user_updated_at_iso = user.updated_at.isoformat() if user.updated_at else None

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
            "created_at": user_created_at_iso, # Usa la versión formateada
            "updated_at": user_updated_at_iso, # Usa la versión formateada
            "department": {
                "id": str(department_data.id),
                "name": department_data.name,
            } if department_data else None,
        }
    }
