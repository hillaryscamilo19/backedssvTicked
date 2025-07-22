from dotenv import load_dotenv
import os




# Opcional: Si usas autenticación, descomenta y configura estas variables en .env
# MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")
# MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")

# Validación básica para asegurar que las variables se cargaron

load_dotenv()  # Lee las variables desde el archivo .env

DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_NAME = os.getenv("DATABASE_NAME")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", 27017))
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "tzy")
if not MONGODB_HOST or not MONGODB_PORT or not MONGODB_DATABASE:
    raise ValueError("Las variables de entorno de MongoDB (MONGODB_HOST, MONGODB_PORT, MONGODB_DATABASE) no se cargaron correctamente.")
# config.py
# Asegúrate de tener estas variables en tu archivo .env
# Por ejemplo:
# MONGODB_HOST=localhost
# MONGODB_PORT=27017
# MONGODB_DATABASE=your_database_name


