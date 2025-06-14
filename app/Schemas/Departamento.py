from pydantic import BaseModel

class DepartmentCreate(BaseModel):
    name: str
    status: bool = True

class DepartmentUpdate(BaseModel):
    name: str | None = None
    status: bool | None = None
