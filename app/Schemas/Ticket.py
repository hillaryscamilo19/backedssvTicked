import datetime
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional

from app.Schemas import Category
from app.Schemas.Esquema import PyObjectId
from app.models.departments_model import Department
from app.models.user_model import User

class TicketCreate(BaseModel):
    title: str
    description: str
    category_id: Optional[int]
    assigned_department_id: Optional[int]
    created_user_id: Optional[int]
    status: Optional[str] = "1"

class TicketUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    category_id: Optional[int]
    assigned_department_id: Optional[int]
    status: Optional[str]
class TicketBase(BaseModel):
    title: str
    description: str
    status: Optional[str] = "1"
class TicketCreate(BaseModel):
    title: str
    description: str
    category_id: Optional[int]
    assigned_department: Optional[int]
    created_user_id: Optional[int]
    status: Optional[str] = "1"

class TicketUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    category_id: Optional[int]
    assigned_department: Optional[int]
    status: Optional[str]

class TicketInDB(TicketBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: Optional[str]
    category: Optional[Category] = None
    assigned_department: Optional[Department] = None
    created_user: Optional[User] = None
    assigned_users: Optional[list[User]] = []
    messages: Optional[list] = []
    attachments: Optional[list] = []
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


