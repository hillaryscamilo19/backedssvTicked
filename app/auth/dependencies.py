from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from bson import ObjectId # Importar ObjectId

from app.db.dbp import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase # Importa el tipo correcto para la DB
from app.Schemas.Esquema import UserInDB # Asegúrate de que UserInDB esté definido en Esquema.py
from config import SECRET_KEY, ALGORITHM # Importa tus variables de configuración

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Función auxiliar para obtener el usuario por username (CORREGIDA para convertir ObjectId)
async def get_user_by_username(username: str, db: AsyncIOMotorDatabase):
    users_collection = db["users"]
    user_data = await users_collection.find_one({"username": username})
    if user_data:
        # Crear una copia para evitar modificar el original
        user_data_copy = user_data.copy()
        
        # Convertir phone_ext a string si es int
        if 'phone_ext' in user_data_copy and isinstance(user_data_copy['phone_ext'], int):
            user_data_copy['phone_ext'] = str(user_data_copy['phone_ext'])
        
        # CORRECCIÓN CRÍTICA: Convertir department ObjectId a string si es necesario
        if 'department' in user_data_copy:
            if isinstance(user_data_copy['department'], ObjectId):
                user_data_copy['department'] = str(user_data_copy['department'])
            elif user_data_copy['department'] is None:
                user_data_copy['department'] = None
            # Si ya es string, lo dejamos como está
        
        # Eliminar campos que no son parte del modelo UserInDB
        if '__v' in user_data_copy:
            del user_data_copy['__v']

        # DEBUG: Imprimir para verificar la conversión
        print(f"DEBUG - user_data_copy antes de UserInDB: {user_data_copy}")
        print(f"DEBUG - department type: {type(user_data_copy.get('department'))}")
        print(f"DEBUG - department value: {user_data_copy.get('department')}")

        return UserInDB(**user_data_copy)
    return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncIOMotorDatabase = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(username, db)

    if user is None:
        raise credentials_exception
    return user

# Puedes añadir una función para obtener el usuario activo si la necesitas
async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if not current_user.status: # Asumiendo que 'status' es un booleano en UserInDB
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user
