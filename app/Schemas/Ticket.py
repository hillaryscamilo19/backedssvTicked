from pydantic import BaseModel
from typing import Optional

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
