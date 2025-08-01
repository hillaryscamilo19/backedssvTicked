from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.models.user_model import User
from app.Schemas.Departamento import DepartmentCreate, DepartmentUpdate
from app.db.dbp import get_db
from app.models.departments_model import departments_helper, obtener_departments
from app.models.departments_model import Department
from sqlalchemy.future import select

router = APIRouter()

# Ruta para obtener todos los departamentos
@router.get("/")
async def get_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department))
    departments = result.scalars().all()
    return [{"id": d.id, "name": d.name} for d in departments]

# Ruta para obtener un departamento por id
@router.get("/{department_id}")
async def get_department_by_id(department_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Department).filter(Department.id == department_id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return departments_helper(department)

# Ruta para crear un nuevo departamento
@router.post("/")
async def create_department(department_data: DepartmentCreate, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    new_department = Department(**department_data.dict())
    db.add(new_department)
    await db.commit()
    await db.refresh(new_department)
    return departments_helper(new_department)

 # Ruta para actualizar un departamento
@router.put("/{department_id}")
async def update_department(department_id: int, data: DepartmentUpdate, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Department).filter(Department.id == department_id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(department, key, value)

    await db.commit()
    await db.refresh(department)
    return departments_helper(department)

# Ruta para eliminar un departamento
@router.delete("/{department_id}")
async def delete_department(department_id: int, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Department).filter(Department.id == department_id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    await db.delete(department)
    await db.commit()
    return {"message": "Departamento eliminado correctamente"}
