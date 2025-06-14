import datetime
from typing import Optional
from pydantic import BaseModel, Field 

class UserCreate(BaseModel):
    """User creation model."""
    fullname: str
    email: str
    phone_ext: int
    department_id: int
    role: int = Field(default=1)       
    username: str
    password: str
    status: Optional[bool] = False   
  

    class Config:
        arbitrary_types_allowed = True 
        orm_mode = True

class UserLogin(BaseModel):
    """User login model."""
    username: str = Field(..., title="Username")
    password: str = Field(..., title="Password")

class UserResponse(BaseModel):
    """User response model."""
    username: str = Field(..., title="Username")
    class Config:
        orm_mode = True

class DepartmentOut(BaseModel):
    id: str
    name: str
    status: bool
