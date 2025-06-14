import datetime
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
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):

    # Verifica si usuario ya existe
    result = await db.execute(select(User).filter(func.lower(User.username) == user.username.lower()))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail=" Usuarios Ya Existe !")

    # Verifica email
    result = await db.execute(select(User).filter( func.lower(User.email) == user.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email Ya Existe !")

    # Verifica extensión telefónica
    result = await db.execute(select(User).filter(User.phone_ext == user.phone_ext))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Extension Ya Existe !")

    # Crear usuario
    new_user = User(
        fullname=user.fullname,
        email=user.email,
        phone_ext=user.phone_ext,
        department_id=user.department_id,  # ID directo
        username=user.username,
        password=hash_password(user.password),
        status=user.status,
        role=0,
        created_at= datetime.datetime.utcnow(),
        updated_at= datetime.datetime.utcnow(),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
    )

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Primero obtenemos el usuario
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrecto")
    
    if not user.status:
        raise HTTPException(status_code=401, detail="Usuario inactivo")

    # Luego, si el usuario tiene department_id, hacemos otra consulta para obtenerlo
    department = None
    if user.department_id:
        result = await db.execute(select(Department).filter(Department.id == user.department_id))
        department = result.scalar_one_or_none()

    token = create_access_token(data={"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "department": {
                "id": department.id,
                "name": department.name,
            } if department else None,
        }
    }
