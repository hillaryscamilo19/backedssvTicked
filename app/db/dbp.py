from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT, DATABASE_NAME

# Validación para asegurar que se cargó correctamente
if not DATABASE_PASSWORD:
    raise ValueError("DATABASE_PASSWORD no se cargó correctamente desde el .env")

password_encoded = quote_plus(DATABASE_PASSWORD)

DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{password_encoded}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
