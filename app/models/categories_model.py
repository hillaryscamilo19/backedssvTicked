from sqlalchemy import String, Column, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload
from app.models.category_department_model import CategoryDepartment  # Usa el import correcto relativo a tu proyecto
from app.db.base import Base

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    tickets = relationship("Ticket", back_populates="category")
    category_departments = relationship("CategoryDepartment", back_populates="category")

def category_helper(category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "departments": [
            {
                "id": cd.department.id,
                "name": cd.department.name
            }
            for cd in category.category_departments if cd.department
        ]
    }


async def obtener_categories(db: AsyncSession):
    result = await db.execute(
        select(Category)
        .options(
            selectinload(Category.category_departments)
            .selectinload(CategoryDepartment.department)  # <-- ✅ Importante: usa la clase, no el string
        )
    )
    categorias = result.scalars().all()
    return [category_helper(c) for c in categorias]
