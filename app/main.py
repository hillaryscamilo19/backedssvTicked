from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# Importamos routers de las diferentes rutas de la aplicación
from app.routes.user_routes import router as user_router
from app.routes.tickets_routes import router as tickets_router
from app.routes.categories_routes import router as categories_router
from app.routes.attachments_routes import router as attachments_router
from app.routes.departments_routes import router as departments_router
from app.routes.messages_routes import router as message_router
from app.routes.auth import router as auth_router
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

# Configuramos la plantilla de Jinja2 para servir HTML desde la carpeta 'templates'
templates = Jinja2Templates(directory="templates")

# Creamos la instancia principal de la aplicación FastAPI
app = FastAPI ()

# Incluimos los routers para cada módulo, asignándoles un prefijo y tags para documentación
app.include_router(auth_router, prefix="", tags=["Login"])
app.include_router(user_router, prefix="/usuarios", tags=["Usuario"])
app.include_router(tickets_router, prefix="/tickets", tags=["Tickets"])
app.include_router(categories_router, prefix="/categories", tags=["Categories"])
app.include_router(attachments_router, prefix="/attachments", tags=["Attachments"])
app.include_router(departments_router, prefix="/departments", tags=["Departments"])
app.include_router(message_router, prefix="/messages", tags=["messages"])
# app.include_router(message_router, prefix="/messages", tags=["messages"]) # Esta línea está duplicada, la dejo comentada

# Asegúrate de que la carpeta existe
os.makedirs("uploads", exist_ok=True)
# Montamos una ruta estática para servir archivos estáticos desde la carpeta 'app/uploads'
os.makedirs("app/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

# Configuración CORS para permitir peticiones desde los orígenes listados
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://10.0.0.15:5173",

]

# Añadimos middleware de CORS para gestionar acceso desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials=True,
    allow_methods=["*"], # Permitir todos los métodos HTTP (GET, POST, etc.)
    allow_headers=["*"], # Permitir todos los headers
)

@app.get("/")
def read_root():
    return {"mensaje": "Servidor funcionando correctamente"}
