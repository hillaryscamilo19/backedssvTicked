from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Annotated, List
from datetime import datetime
from bson import ObjectId

# Custom type for ObjectId to handle conversion
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserCreate(BaseModel):
    fullname: str
    email: str
    phone_ext: str
    department_id: Optional[str] = None
    username: str
    password: str
    status: bool = True
    role: int = 0

class UserUpdate(BaseModel):
    fullname: Optional[str] = None
    email: Optional[str] = None
    phone_ext: Optional[str] = None
    department_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    status: Optional[bool] = None
    role: Optional[int] = None

    class Config:
        extra = "forbid"

class UserInDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str
    email: str
    fullname: str
    phone_ext: str
    department_id: Optional[str] = None
    password: str
    status: bool
    role: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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
    email: Optional[str] = None
    fullname: str
    phone_ext: str
    department_id: Optional[str] = None
    status: bool
    role: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    department: Optional["DepartmentResponse"] = None

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

# --- Modelos para Mensajes ---
class MessageBase(BaseModel):
    message: str

class MessageCreate(MessageBase):
    pass

class MessageUpdate(MessageBase):
    message: Optional[str] = None

class MessageResponse(MessageBase):
    id: PyObjectId = Field(alias="_id")
    ticket_id: str
    created_by_id: str
    created_at: Optional[datetime] = None # CAMBIO AQUÍ: HECHO OPCIONAL

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# --- Modelos para Attachments ---
class AttachmentBase(BaseModel):
    file_name: str
    file_path: str
    file_extension: str

class AttachmentCreate(AttachmentBase):
    pass

class AttachmentUpdate(AttachmentBase):
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_extension: Optional[str] = None

class AttachmentResponse(AttachmentBase):
    id: PyObjectId = Field(alias="_id")
    ticket_id: str
    uploaded_by: Optional[str] = None
    created_at: Optional[datetime] = None # CAMBIO AQUÍ: HECHO OPCIONAL

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# --- Modelos para Tickets ---
class TicketBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "0"
    priority: str = "0"
    category_id: Optional[str] = None
    assigned_to: Optional[List[str]] = Field(default_factory=list)
    assigned_department_id: Optional[str] = None

class TicketCreate(TicketBase):
    pass

class TicketUpdate(TicketBase):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category_id: Optional[str] = None
    assigned_to: Optional[List[str]] = None
    assigned_department_id: Optional[str] = None

class TicketResponse(TicketBase):
    id: PyObjectId = Field(alias="_id")
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    category: Optional[CategoryResponse] = None
    assigned_department: Optional["DepartmentResponse"] = None
    created_user: Optional["UserResponse"] = None
    assigned_users: Optional[List["UserResponse"]] = Field(default_factory=list)
    messages: Optional[List["MessageResponse"]] = Field(default_factory=list)
    attachments: Optional[List["AttachmentResponse"]] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# Rebuild models if there are circular references
UserResponse.model_rebuild()
TicketResponse.model_rebuild()
