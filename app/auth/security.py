from typing import Optional
from passlib.context import CryptContext
from datetime import datetime, timedelta
# --- CORRECCIÓN AQUÍ: Importa jwt de jose ---
from jose import jwt
# --- FIN CORRECCIÓN ---
import os

# Asumiendo que SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES están en config.py
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # La función jwt.encode() se llama igual, pero ahora viene de jose.jwt
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
