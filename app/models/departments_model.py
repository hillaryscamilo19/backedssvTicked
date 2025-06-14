from sqlalchemy import Boolean, String, Table, Column, Integer, ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from app.db.base import Base
import app.models


user_supervision_departments = Table(
    "user_supervision_departments",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("department_id", Integer, ForeignKey("departments.id", ondelete="CASCADE"))
)

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(Boolean)

    tickets = relationship("Ticket", back_populates="assigned_department")
    category_departments = relationship("CategoryDepartment", back_populates="department")
    users = relationship("User", back_populates="department")
    supervised_by = relationship(
        "User",
        secondary=user_supervision_departments,
        back_populates="supervision_departments"
    )

def departments_helper(department) -> dict:
    return {
        "id": department.id,
        "name": department.name,
        "status": True  # si tienes un campo real usa ese
    }


# Obtener todos los departamentos
async def obtener_departments(db: AsyncSession):
    try:
        result = await db.execute(select(Department))
        departamentos = result.scalars().all()
        return [departments_helper(dep) for dep in departamentos]
    except Exception as e:
        raise e
    
