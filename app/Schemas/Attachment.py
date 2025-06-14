from pydantic import BaseModel

class AttachmentCreate(BaseModel):
    file_name: str
    file_path: str
    file_extension: str
    ticket_id: int

    
class AttachmentUpdate(BaseModel):
    file_name: str
    file_path: str
    file_extension: str