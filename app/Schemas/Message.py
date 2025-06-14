from pydantic import BaseModel

class MessageCreate(BaseModel):
    message: str
    ticket_id: int  

class MessageUpdate(BaseModel):
    message: str

