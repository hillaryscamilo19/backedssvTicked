from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
import app.models


class CategoryDepartment(Base):
    __tablename__ = "category_departments"
    id = Column(Integer, primary_key=True)
    category = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    department = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)

    category = relationship("Category", back_populates="category_departments")
    department = relationship("Department", back_populates="category_departments")
