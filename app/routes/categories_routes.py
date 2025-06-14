from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.models.user_model import User
from app.Schemas.Category import CategoryCreate, CategoryUpdate
from app.models.category_department_model import CategoryDepartment
from app.models.categories_model import Category, category_helper, obtener_categories
from app.db.dbp import get_db
from sqlalchemy.orm import selectinload


router = APIRouter()

# Ruta para obtener todas las categorias
@router.get("/")
async def get_categories(db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    categories = await obtener_categories(db)
    return categories

# Ruta para obtener una categoria por id
@router.get("/{category_id}")
async def get_category_by_id(category_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Category)
        .options(
            selectinload(Category.category_departments)
            .selectinload(CategoryDepartment.department)
        )
        .filter(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category_helper(category)


# Ruta para crear una categoria
@router.post("/")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_category = Category(name=data.name)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    # Recargar la categoría con las relaciones
    result = await db.execute(
        select(Category)
        .options(
            selectinload(Category.category_departments)
            .selectinload(CategoryDepartment.department)
        )
        .filter(Category.id == new_category.id)
    )
    category_with_relations = result.scalar_one()
    return category_helper(category_with_relations)




@router.put("/{category_id}")
async def update_category(category_id: int, data: CategoryUpdate, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Category).filter(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    category.name = data.name
    await db.commit()
    await db.refresh(category)
    return category_helper(category)



# Ruta para eliminar un id
@router.delete("/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Category).filter(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    await db.delete(category)
    await db.commit()
    return {"message": "Categoría eliminada correctamente"}
