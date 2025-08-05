import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordRequestForm
from app.models.departments_model import Department
from app.db.dbp import get_db  
from app.models.user_model import User, usuario_helper
from app.Schemas.Esquema import UserCreate, UserResponse  
from app.auth.security import hash_password, verify_password, create_access_token
from sqlalchemy import func
from sqlalchemy.orm import selectinload


router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db=Depends(get_db)):

    # Verifica si usuario ya existe
    existing_user = await db["users"].find_one({"username": user.username.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuario ya existe!")

    # Verifica email
    existing_email = await db["users"].find_one({"email": user.email.lower()})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email ya existe!")

    # Verifica extensión telefónica
    existing_phone_ext = await db["users"].find_one({"phone_ext": user.phone_ext})
    if existing_phone_ext:
        raise HTTPException(status_code=400, detail="Extensión ya existe!")


    # Crear usuario
    new_user = {
        "fullname": user.fullname,
        "email": user.email,
        "phone_ext": user.phone_ext,
        "department": user.department,  # ID directo
        "username": user.username,
        "password": hash_password(user.password),
        "status": user.status,
        "role": 0,
        "createdAt": datetime.datetime.utcnow(),
        "updatedAt": datetime.datetime.utcnow(),
    }
    
    await db["users"].insert_one(new_user)

    return UserResponse(
        id=str(new_user["_id"]),  # MongoDB usa _id como identificador
        username=new_user["username"],
        email=new_user["email"],
    )

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    # Primero obtenemos el usuario
    user = await db["users"].find_one({"username": form_data.username})

    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrecto")
    
    if not user["status"]:
        raise HTTPException(status_code=401, detail="Usuario inactivo")

    # Luego, si el usuario tiene department_id, hacemos otra consulta para obtenerlo
    department = None
    if user.get("department"):
        department = await db["departments"].find_one({"_id": ObjectId(user["department"])})

    token = create_access_token(data={"sub": user["username"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "department": {
                "id": str(department["_id"]),
                "name": department["name"],
            } if department else None,
        }
}
