from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Annotated, List
from datetime import datetime
from bson import ObjectId # Necesitas instalar 'bson' si no lo tienes: pip install pymongo

# Custom type for ObjectId to handle conversion
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserCreate(BaseModel):
    fullname: str
    email: str # Sigue siendo requerido para la creación de nuevos usuarios
    phone_ext: str
    department_id: Optional[str] = None
    username: str
    password: str
    status: bool = True
    role: int = 0

class UserUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[str] = None # Puede ser opcional para actualizaciones
    phone_ext: Optional[str] = None
    department_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None # Permite actualizar la contraseña
    status: Optional[bool] = None
    role: Optional[int] = None

    class Config:
        extra = "forbid" # Opcional: prohíbe campos adicionales no definidos

class UserInDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str
    email: str # Mantenemos requerido para UserInDB, asumiendo que una vez en DB, el email existe
    fullname: str
    phone_ext: str
    department_id: Optional[str] = None
    password: str
    status: bool
    role: int
    created_at: Optional[datetime] = None # Hacemos opcional para compatibilidad con datos existentes
    updated_at: Optional[datetime] = None # Hacemos opcional para compatibilidad con datos existentes

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

class UserResponse(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str
    email: Optional[str] = None # <--- CAMBIADO A OPCIONAL AQUÍ
    fullname: str
    phone_ext: str
    department_id: Optional[str] = None
    status: bool
    role: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    department: Optional["DepartmentResponse"] = None # Añadido para incluir el departamento anidado

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(DepartmentBase):
    name: Optional[str] = None

class DepartmentResponse(DepartmentBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# --- Modelos para Categorías ---
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    name: Optional[str] = None
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# Actualización para UserResponse para permitir la referencia circular
UserResponse.model_rebuild()
