import datetime
from fastapi import HTTPException
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload 
from app.db.base import Base
from app.models.departments_model import user_supervision_departments  

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String)
    email = Column(String, unique=True, index=True)
    phone_ext = Column(Integer)  
    department = Column(Integer, ForeignKey("departments.id"))
    role = Column(Integer)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    status = Column(Boolean)
    createdAt = Column("createdat", DateTime(timezone=True), server_default=func.now(), nullable=True)
    updatedAt = Column("updatedat", DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    created_tickets = relationship("Ticket", back_populates="created_user")
    assigned_tickets = relationship("TicketAssignedUser", back_populates="user")
    department = relationship("Department", back_populates="users")
    messages = relationship("Message", back_populates="user")
    supervision_departments = relationship(
        "Department",
        secondary=user_supervision_departments,
        back_populates="supervised_by"
    )
    
def usuario_helper(usuario) -> dict:
    return {
        "id": usuario.id,
        "fullname": usuario.fullname,
        "email": usuario.email,
        "phone_ext": usuario.phone_ext,
        "department": {
            "id": usuario.department.id,
            "name": usuario.department.name,
        } if usuario.department else None,
        "role": usuario.role,
        "username": usuario.username,
        "supervision_departments": [
            {"id": d.id, "name": d.name} for d in usuario.supervision_departments or []
        ],
        "status": usuario.status,
        "createdAt": usuario.createdAt,
        "updatedAt": usuario.updatedAt
    }

async def obtener_usuarios(db: AsyncSession):
    result = await db.execute(
        select(User)
        .options(selectinload(User.department), selectinload(User.supervision_departments))
    )
    usuarios = result.scalars().all()
    return [usuario_helper(u) for u in usuarios]

async def update_fields(user: User, updated_data: dict, db: AsyncSession):
    allowed_fields = {
        "status", "fullname", "email", "phone_ext", "department", "role", "username","password"
    }

    disallowed_fields = {"updatedAt", "createdat", "createdAt", "id"}  # Puedes agregar más si es necesario

    # Validar que no se esté intentando modificar campos no permitidos
    for key in updated_data:
        if key in disallowed_fields:
            raise HTTPException(status_code=400, detail=f"No puedes modificar el campo '{key}'")

    # Aplicar los cambios permitidos
    for key, value in updated_data.items():
        if key in allowed_fields:
            setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user
