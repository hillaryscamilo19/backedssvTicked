from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import SECRET_KEY, ALGORITHM
from app.models.user_model import User
from app.db.dbp import get_db  # Asegúrate de que existe esta función

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        print("Token payload:", payload)
        if username is None:
            print("El campo 'sub' no está presente.")
            raise credentials_exception
    except JWTError as e:
        print("Error al decodificar JWT:", str(e))
        raise credentials_exception

    print(f"Buscando usuario con username = {username}")

    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalar_one_or_none()
    print("Resultado de la base de datos:", user)

    if user is None:
        raise credentials_exception

    print("Usuario encontrado:", user)
    return user
