from pydantic import BaseModel

class Department(BaseModel):
    id: int
    name: str
    status: bool


class DepartmentUpdate(BaseModel):
    name: str 
    status: bool


class DepartmentResponse(BaseModel):
    id: int
    name: str
    status: bool

class DepartmentCreate(BaseModel):
    name: str
    status: bool 
