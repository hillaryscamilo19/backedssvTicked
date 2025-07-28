# schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserUpdate(BaseModel):
    fullname: Optional[str]
    email: Optional[EmailStr]
    phone_ext: Optional[int]
    department: Optional[int]
    role: Optional[int]
    username: Optional[str]
    status: Optional[bool]

    class Config:
        extra = "forbid"  # impide recibir campos como "additionalProp1"

class UserStatusUpdate(BaseModel):
    status: Optional[bool]

class PasswordReset(BaseModel):
    new_password: str