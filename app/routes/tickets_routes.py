from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.Schemas.user import PasswordReset, UserStatusUpdate, UserUpdate
from app.auth.security import hash_password
from app.Schemas.Esquema import UserCreate
from app.db.dbp import get_db  
from app.models.user_model import obtener_usuarios, usuario_helper, User, update_fields
from app.auth.dependencies import get_current_user

router = APIRouter()

# Ruta para obtener el usuario actual
@router.get("/me")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

# Ruta para obtener todos los usuarios
@router.get("/")
async def get_usuarios(db: AsyncSession = Depends(get_db) , current_user: User = Depends(get_current_user)):
    return await obtener_usuarios(db)

# Ruta para obtener un usuario por el id
@router.get("/{user_id}")
async def get_user_by_id( user_id: int,current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .options(selectinload(User.department), selectinload(User.supervision_departments))
        .filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario_helper(user)


# Ruta para crear un usuario
@router.post("/")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db), current_user : User = Depends(get_current_user)):
    # Verificar si el usuario ya existe
    result = await db.execute(select(User).filter(User.email == user.email))
    user_db = result.scalar_one_or_none()
    if user_db:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    # Crear el usuario
    user_db = User(**user.dict())
    db.add(user_db)
    await db.commit()
    await db.refresh(user_db)
    return usuario_helper(user_db)


# Ruta para actualizar un usuario
@router.put("/estado/{user_id}")
async def update_user( user_id: int, updated_data: dict, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role not in (0, 1, 2):
        raise HTTPException(status_code=403, detail="No tienes permisos suficientes")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Actualizar usuario con datos permitidos
    updated_user = await update_fields(user, updated_data, db)

    # Recargar usuario con relaciones para evitar error de lazy load en async
    result = await db.execute(
        select(User)
        .options(selectinload(User.department), selectinload(User.supervision_departments))
        .filter(User.id == updated_user.id)
    )
    user_with_relations = result.scalar_one_or_none()

    return usuario_helper(user_with_relations)

# Ruta para actualizar un usuarios completo 
@router.put("/{user_id}")
async def update_user(
    user_id: int,
    updated_data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in (0, 1, 2):
        raise HTTPException(status_code=403, detail="No tienes permisos suficientes")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    update_dict = updated_data.dict(exclude_unset=True)

    updated_user = await update_fields(user, update_dict, db)

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.department),
            selectinload(User.supervision_departments)
        )
        .filter(User.id == updated_user.id)
    )
    user_with_relations = result.scalar_one_or_none()

    return usuario_helper(user_with_relations)

# NUEVA RUTA: Toggle de estado de usuario (activar/desactivar)
@router.put("/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Verificar permisos (solo administradores)
        if current_user.role not in (0, 1, 2):
            raise HTTPException(
                status_code=403, 
                detail="No tienes permisos para cambiar el estado de usuarios"
            )

        # Buscar el usuario
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # No permitir que un usuario se desactive a sí mismo
        if user.id == current_user.id:
            raise HTTPException(
                status_code=400, 
                detail="No puedes cambiar tu propio estado"
            )

        # Actualizar el estado usando tu función update_fields existente
        update_data = {"status": status_data.status}
        updated_user = await update_fields(user, update_data, db)
        
        status_text = "activado" if updated_user.status else "desactivado"
        
        return {
            "message": f"Usuario {status_text} exitosamente",
            "user_id": updated_user.id,
            "username": updated_user.username,
            "new_status": updated_user.status
        }
        
    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error en toggle_user_status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

# Ruta para restablecer contraseña
@router.put("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_data: PasswordReset,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verificar permisos (solo administradores o el propio usuario)
    if current_user.role not in (0, 1, 2) and current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para restablecer esta contraseña"
        )

    # Buscar el usuario
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Validar la nueva contraseña
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    # Hashear y actualizar la contraseña
    hashed_password = hash_password(password_data.new_password)
    
    # Actualizar solo el campo de contraseña
    user.password = hashed_password
    await db.commit()
    await db.refresh(user)

    return {"message": "Contraseña restablecida exitosamente"}


# Ruta para eliminar un usuario
@router.delete("/{user_id}")
async def delete_user( user_id: int,current_user=Depends(get_current_user),
db: AsyncSession = Depends(get_db),):
    if current_user.role not in (0, 1):
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar usuarios")

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await db.delete(user)
    await db.commit()
    return {"message": "Usuario eliminado exitosamente"}


# Ruta para obtener colaboradores del departamento (solo activos)
@router.get("/departamento/colaboradores")
async def get_colaboradores_del_departamento(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.department_id:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a ningún departamento.")

    result = await db.execute(
        select(User)
        .filter(
            User.department_id == current_user.department_id,
            User.status == True,  # Solo usuarios activos
            User.id != current_user.id  # Excluir al usuario actual
        )
    )
    colaboradores = result.scalars().all()

    return [
        {
            "id": u.id,
            "fullname": u.fullname,
            "email": u.email,
            "phone_ext": u.phone_ext, 
            "status": u.status,
            "department_id": u.department_id,
        }
        for u in colaboradores
    ]
