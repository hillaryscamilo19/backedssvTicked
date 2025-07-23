from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.db.dbp import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase # Importa el tipo correcto para la DB
from app.Schemas.Esquema import UserInDB # Asegúrate de que UserInDB esté definido en Esquema.py
from config import SECRET_KEY, ALGORITHM # Importa tus variables de configuración

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Función auxiliar para obtener el usuario por username (copiada de auth.py)
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
    
    # --- CORRECCIÓN AQUÍ: Usar la función get_user_by_username para MongoDB ---
    user = await get_user_by_username(username, db)
    # --- FIN CORRECCIÓN ---

    if user is None:
        raise credentials_exception
    return user

# Puedes añadir una función para obtener el usuario activo si la necesitas
async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if not current_user.status: # Asumiendo que 'status' es un booleano en UserInDB
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user
