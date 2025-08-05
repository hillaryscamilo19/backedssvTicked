# Modelos Pydantic
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class EmailRequest(BaseModel):
    from_email: EmailStr = "soportetecnico@ssv.com.do"
    to: List[EmailStr]
    subject: str
    html: str
    text: str

class TicketNotification(BaseModel):
    title: str
    description: str
    category_id: Optional[int]
    assigned_department: Optional[int]
    created_user_id: Optional[int]
    status: Optional[str] = "1"

class User(BaseModel):
    id: str
    email: EmailStr
    fullname: Optional[str] = None
    department: Optional[str] = None
    status: bool = True

class EmailResponse(BaseModel):
    success: bool
    message: str
    emails_sent: int
    failed_emails: List[str] = []