import datetime
from bson import ObjectId
from sqlalchemy import Boolean, String, Table, Column, Integer, ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import relationship
from app.db.base import Base
from pydantic import BaseModel
from typing import Optional, List



async def obtener_departments(db: AsyncIOMotorDatabase) -> List[dict]:
    """
    Obtiene todas los departamentos de la base de datos.
    """
    departments_collection = db["departments"]
    departments_data = await departments_collection.find({}).to_list(None)
    return departments_data


async def obtener_departments_por_id(db: AsyncIOMotorDatabase, category_id: str) -> Optional[dict]:
    """
    Obtiene una categoría por su ID.
    """
    categories_collection = db["categories"]
    try:
        object_id = ObjectId(category_id)
    except Exception:
        return None # ID inválido
    category_data = await categories_collection.find_one({"_id": object_id})
    return category_data

async def crear_departments(db: AsyncIOMotorDatabase, category_data: dict) -> dict:
    """
    Crea una nueva categoría en la base de datos.
    """
    categories_collection = db["categories"]
    category_data["createdAt"] = datetime.utcnow()
    category_data["updatedAt"] = datetime.utcnow()
    result = await categories_collection.insert_one(category_data)
    created_category = await categories_collection.find_one({"_id": result.inserted_id})
    return created_category

async def actualizar_category(db: AsyncIOMotorDatabase, category_id: str, update_data: dict) -> Optional[dict]:
    """
    Actualiza una categoría existente.
    """
    categories_collection = db["categories"]
    try:
        object_id = ObjectId(category_id)
    except Exception:
        return None # ID inválido
    
    update_data["updated_at"] = datetime.utcnow()
    result = await categories_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return None # Categoría no encontrada
    updated_category = await categories_collection.find_one({"_id": object_id})
    return updated_category

async def eliminar_departments(db: AsyncIOMotorDatabase, category_id: str) -> bool:
    """
    Elimina una categoría por su ID.
    """
    categories_collection = db["categories"]
    try:
        object_id = ObjectId(category_id)
    except Exception:
        return False # ID inválido
    result = await categories_collection.delete_one({"_id": object_id})
    return result.deleted_count > 0


# Tabla de relación para supervisión de departamentos
user_supervision_departments = Table(
    "user_supervision_departments",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("department", Integer, ForeignKey("departments.id", ondelete="CASCADE"))
)

# Modelo de SQLAlchemy
class DepartmentModel(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(Boolean, default=True)  # Valor predeterminado

    tickets = relationship("Ticket", back_populates="assigned_department")
    category_departments = relationship("CategoryDepartment", back_populates="department")
    users = relationship("User ", back_populates="department")
    supervised_by = relationship(
        "User ",
        secondary=user_supervision_departments,
        back_populates="supervision_departments"
    )

# Modelo de Pydantic
class Department(BaseModel):
    id: int
    name: str
    status: bool

def departments_helper(department: DepartmentModel) -> dict:
    """Helper function to convert a Department object to a dictionary."""
    return {
        "id": department.id,
        "name": department.name,
        "status": department.status  # Usa el campo real
    }
