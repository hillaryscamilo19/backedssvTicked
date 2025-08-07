import traceback
from typing import List
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from app.auth.dependencies import get_current_user
from app.db.dbp import get_db
from app.models.tickets_model import Ticket, ticket_helper
from app.models.ticket_assigned_user_model import TicketAssignedUser 
from app.models.user_model import User
from app.models.messages_model import Message, messages_helper
from app.Schemas.Ticket import TicketCreate, TicketUpdate
from app.Schemas.Message import MessageCreate
from app.models.attachments_model import Attachment
from fastapi import UploadFile, File
import os

from app.utils.email_utils import send_email

router = APIRouter()

# Generar nombre con base en el nombre original y numeración de 4 dígitos
def generar_nombre_incremental(nombre_base, extension, carpeta="app/uploads"):
    archivos = os.listdir(carpeta)
    numeros = []
    for f in archivos:
        if f.startswith(nombre_base + "_") and f.endswith("." + extension):
            parte = f[len(nombre_base) + 1 : -(len(extension) + 1)]
            if parte.isdigit():
                numeros.append(int(parte))
    siguiente = max(numeros, default=0) + 1
    numero_formateado = f"{siguiente:04d}"
    return f"{nombre_base}_{numero_formateado}.{extension}"

# 1. Obtener todos los tickets
@router.get("/")
async def get_tickets(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    tickets = await db["tickets"].find().to_list(length=None)
    return [ticket_helper(ticket) for ticket in tickets]

# 2. Obtener ticket por ID
@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, db=Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await db["tickets"].find_one({"_id": ObjectId(ticket_id)})
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket_helper(ticket)

# 3. Crear ticket
@router.post("/")
async def create_ticket(
    data: TicketCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data_dict = data.dict()  # Convertir a diccionario
    data_dict["created_user_id"] = str(current_user.id)

    # Manejar campos opcionales
    if data_dict.get("category") == 0:
        data_dict["category"] = None
    if data_dict.get("assigned_department") in (None, 0, ""):
        data_dict["assigned_department"] = None

    # Crear el nuevo ticket en MongoDB
    new_ticket = await db["tickets"].insert_one(data_dict)
    created_ticket = await db["tickets"].find_one({"_id": new_ticket.inserted_id})

    # Obtener usuarios del departamento asignado
    if data_dict.get("assigned_department"):
        dept_users = await db["users"].find({"department_id": ObjectId(data_dict["assigned_department"]), "status": True}).to_list(None)

   # Obtener datos relacionados
    if created_ticket.get("category"):
        category = await db["categories"].find_one({"_id": ObjectId(created_ticket["category"])})
        created_ticket["category"] = {
            "id": str(category["_id"]),
            "name": category["name"] if category else None
        }

    if created_ticket.get("assigned_department"):
        department = await db["departments"].find_one({"_id": ObjectId(created_ticket["assigned_department"])})
        created_ticket["assigned_department"] = {
            "id": str(department["_id"]),
            "name": department["name"] if department else None
        }

    if created_ticket.get("created_user_id"):
        user = await db["users"].find_one({"_id": ObjectId(created_ticket["created_user_id"])})
        created_ticket["created_user"] = {
            "id": str(user["_id"]),
            "fullname": user["fullname"] if user else None,
            "email": user["email"] if user else None,
            "phone_ext": user["phone_ext"] if user else None
        }

    # Enviar correos a los usuarios del departamento
    for user in dept_users:
            send_email(
                to=user["email"],
                subject="Nuevo ticket asignado a tu departamento",
                body=f"Hola {user['fullname']},\n\nSe ha creado un nuevo ticket #{str(new_ticket.inserted_id)} asignado a tu departamento.\n\nPor favor revisa el sistema."
            )

    # Retornar el ticket creado
    return ticket_helper(created_ticket)

# 4. Actualizar ticket estado
@router.put("/{ticket_id}/estado")
async def actualizar_estado_ticket(
    ticket_id: str,
    estado_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        ESTADOS = {
            0: "Cancelado",
            1: "Abierto",
            2: "Proceso",
            3: "Espera",
            4: "Revisión",
            5: "Completado"
        }

        if estado_id not in ESTADOS:
            raise HTTPException(status_code=400, detail="ID de estado inválido")

        ticket = await db["tickets"].find_one({"_id": ObjectId(ticket_id)})
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        if ticket["status"] in {"0", "5"}:
            raise HTTPException(status_code=400, detail="No se puede cambiar el estado de un ticket que ya está cancelado o completado")

        # Validaciones de permisos
        es_creador = current_user.id == ticket["created_user_id"]
        es_asignado = current_user.id in [u["user_id"] for u in ticket["assigned_users"]]

        if estado_id == 0 and not es_creador:
            raise HTTPException(status_code=403, detail="Solo el creador puede cancelar el ticket")

        ticket["status"] = str(estado_id)
        await db["tickets"].update_one({"_id": ObjectId(ticket_id)}, {"$set": {"status": ticket["status"]}})

        return {
            "message": f"Estado actualizado correctamente a código {estado_id}",
            "ticket": ticket_helper(ticket)
        }

    except HTTPException:
        raise  # Deja pasar excepciones HTTP personalizadas

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error interno al actualizar el estado del ticket")

# 7. Asignar usuarios al ticket
@router.post("/{ticket_id}/asignar-usuarios")
async def asignar_usuarios_a_ticket(
    ticket_id: str,
    asignaciones: List[int],
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = await db["tickets"].find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if ticket["status"] in {"0", "5"}:
        raise HTTPException(status_code=400, detail="No se pueden asignar usuarios a un ticket cancelado o completado")

    if ticket["assigned_department"] != current_user.department:
        raise HTTPException(status_code=403, detail="Solo el departamento asignado al ticket puede asignar usuarios")

    usuarios_asignados_actuales = {u["user_id"] for u in ticket["assigned_users"]}

    usuarios_validos = await db["users"].find({
        "id": {"$in": asignaciones},
        "department": current_user.department
    }).to_list(length=None)

    invalidos = set(asignaciones) - {u["id"] for u in usuarios_validos}
    if invalidos:
        raise HTTPException(status_code=400, detail=f"Los siguientes usuarios no pertenecen a tu departamento: {invalidos}")

    nuevos_asignados = 0

    for user_id in usuarios_validos:
        if user_id not in usuarios_asignados_actuales:
            asignado = TicketAssignedUser (ticket_id=ticket_id, user_id=user_id)
            await db["ticket_assigned_users"].insert_one(asignado.dict())
            nuevos_asignados += 1

    if nuevos_asignados == 0:
        raise HTTPException(status_code=400, detail="El usuario ya estaba asignado al ticket")

    return {"message": f"{nuevos_asignados} usuario(s) asignado(s) correctamente"}

# 8. Obtener tickets asignados al usuario actual
@router.get("/asignados-a-mi/")
async def get_tickets_asignados_a_mi(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    tickets = await db["tickets"].find({"assigned_users": str(current_user.id)}).to_list(length=None)
    
    # Formatear la respuesta
    formatted_tickets = []
    for ticket in tickets:
        formatted_ticket = {
            "id": ticket.get("_id"),
            "title": ticket.get("title"),
            "description": ticket.get("description"),
            "category": {
                "id": ticket.get("category", {}).get("_id"),
                "name": ticket.get("category", {}).get("name")
            },
            "assigned_department": {
                "id": ticket.get("assigned_department", {}).get("_id"),
                "name": ticket.get("assigned_department", {}).get("name")
            },
            "created_user": {
                "id": ticket.get("created_user_id"),
                "fullname": ticket.get("created_user_fullname"),
                "email": ticket.get("created_user_email")
            },
            "assigned_users": [
                {
                    "id": user.get("_id"),
                    "fullname": user.get("fullname"),
                    "email": user.get("email")
                } for user in ticket.get("assigned_users", [])
            ],
            "messages": ticket.get("messages", []),
            "status": ticket.get("status"),
            "createdAt": ticket.get("createdAt"),
            "updatedAt": ticket.get("updatedAt")
        }
        formatted_tickets.append(formatted_ticket)

    return formatted_tickets


# 9. Obtener tickets asignados al departamento del usuario
@router.get("/asignados-departamento/")
async def get_tickets_departamento(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    tickets = await db["tickets"].find({"assigned_department": current_user.department}).to_list(length=None)
    return [ticket_helper(t) for t in tickets]

# 10. Obtener tickets creados por el usuario y su departamento
@router.get("/creados/")
async def get_tickets_creados(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    # Obtener todos los tickets creados por usuarios en el mismo departamento
    departamento_tickets = await db["tickets"].find({
        "created_user_id": {"$in": [str(user["_id"]) for user in await db["users"].find({"department": current_user.department}).to_list(length=None)]}
    }).to_list(length=None)

    # Formatear la respuesta
    formatted_tickets = []
    for ticket in departamento_tickets:
        formatted_ticket = {
            "id": ticket.get("_id"),
            "title": ticket.get("title"),
            "description": ticket.get("description"),
            "category": {
                "id": ticket.get("category", {}).get("_id"),
                "name": ticket.get("category", {}).get("name")
            },
            "assigned_department": {
                "id": ticket.get("assigned_department", {}).get("_id"),
                "name": ticket.get("assigned_department", {}).get("name")
            },
            "created_user": {
                "id": ticket.get("created_user_id"),
                "fullname": ticket.get("created_user_fullname"),
                "email": ticket.get("created_user_email")
            },
            "assigned_users": [
                {
                    "id": user.get("_id"),
                    "fullname": user.get("fullname"),
                    "email": user.get("email")
                } for user in ticket.get("assigned_users", [])
            ],
            "messages": ticket.get("messages", []),
            "status": ticket.get("status"),
            "createdAt": ticket.get("createdAt"),
            "updatedAt": ticket.get("updatedAt")
        }
        formatted_tickets.append(formatted_ticket)

    return formatted_tickets



# 11. Agregar mensaje a un ticket
@router.post("/{ticket_id}/mensajes/")
async def crear_mensaje_ticket(
    ticket_id: str,
    data: MessageCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = await db["tickets"].find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if current_user.id != ticket["created_user_id"] and not any(
        assignment["user_id"] == current_user.id for assignment in ticket["assigned_users"]
    ):
        raise HTTPException(status_code=403, detail="No tienes permiso para escribir en este ticket")

    nuevo_mensaje = Message(
        ticket_id=ticket_id,
        created_by_id=current_user.id,
        message=data.message
    )
    await db["messages"].insert_one(nuevo_mensaje.dict())

    return {
        "message": "Mensaje enviado correctamente",
        "mensaje": messages_helper(nuevo_mensaje)
    }

# 12. Ruta para agregar un archivo a un ticket
@router.post("/{ticket_id}/attachments")
async def subir_attachment(
    ticket_id: str,
    request: Request,
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = await db["tickets"].find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    upload_folder = "app/uploads"
    os.makedirs(upload_folder, exist_ok=True)

    nombre_archivo = file.filename.rsplit(".", 1)[0].replace(" ", "_")
    extension = file.filename.rsplit(".", 1)[-1].lower()
    nombre_final = generar_nombre_incremental(nombre_archivo, extension, upload_folder)

    relative_path = f"/uploads/{nombre_final}"
    save_path = os.path.join(upload_folder, nombre_final)

    try:
        content = await file.read()
        with open(save_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    new_attachment = Attachment(
        file_name=nombre_final,
        file_path=relative_path,
        file_extension=extension,
        ticket_id=ticket_id
    )
    await db["attachments"].insert_one(new_attachment.dict())

    base_url = str(request.base_url).rstrip("/")
    file_url = f"{base_url}{relative_path}"

    return JSONResponse(
        status_code=201,
        content={
            "message": "Archivo subido exitosamente",
            "attachment_id": new_attachment.id,
            "file_path": new_attachment.file_path,
            "file_url": file_url
        }
    )

# 13. Obtener todos los tickets creados por usuarios del mismo departamento
@router.get("/todos-creados-por-mi-departamento/")
async def get_all_tickets_by_department_users(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result_users = await db["users"].find({"department": str(current_user.department)}).to_list(length=None)
    user_ids = [str(user["_id"]) for user in result_users]  # Asegúrate de usar el ID correcto

    result_tickets = await db["tickets"].find({"created_user_id": {"$in": user_ids}}).to_list(length=None)
    return [ticket_helper(ticket) for ticket in result_tickets]

 