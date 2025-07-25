from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import os
import traceback

from app.db.dbp import get_db
from app.Schemas.Esquema import TicketCreate, TicketUpdate, TicketResponse, UserInDB, CategoryResponse, DepartmentResponse, MessageCreate, AttachmentCreate, AttachmentResponse, MessageResponse
from app.auth.dependencies import get_current_user
from app.models import tickets_model, categories_model
from app.models.user_model import obtener_user_por_id, obtener_users_by_department_id
from app.models.attachments_model import crear_attachment # Asegúrate de que esta función exista y sea correcta
from app.models.messages_model import crear_message, obtener_mensaje_por_id # Importa obtener_mensaje_por_id

from fastapi import BackgroundTasks
from fastapi import UploadFile, File

router = APIRouter()

# --- Funciones auxiliares para construir respuestas anidadas ---
async def build_ticket_response(ticket_doc: dict, db: AsyncIOMotorDatabase) -> TicketResponse:
    # Asegúrate de que _id se mapee a id para el top-level TicketResponse
    ticket_id_str = str(ticket_doc["_id"]) if "_id" in ticket_doc else None
    if not ticket_id_str:
        raise ValueError("Ticket document is missing _id")

    # Mapeo y conversión de IDs de MongoDB a strings para los campos directos del esquema
    # Los campos 'category', 'assigned_department', 'created_user' en MongoDB son ObjectIds
    category_id_val = ticket_doc.get("category")
    category_id_str = str(category_id_val) if isinstance(category_id_val, ObjectId) else None

    assigned_department_id_val = ticket_doc.get("assigned_department")
    assigned_department_id_str = str(assigned_department_id_val) if isinstance(assigned_department_id_val, ObjectId) else None

    created_by_val = ticket_doc.get("created_user")
    created_by_str = str(created_by_val) if isinstance(created_by_val, ObjectId) else None
    
    # Manejar assigned_users: lista de ObjectIds en MongoDB a lista de strings en Pydantic
    assigned_to_list_str = []
    if "assigned_users" in ticket_doc and isinstance(ticket_doc["assigned_users"], list):
        for user_oid in ticket_doc["assigned_users"]:
            if isinstance(user_oid, ObjectId):
                assigned_to_list_str.append(str(user_oid))
            elif isinstance(user_oid, str): # Si ya es un string, lo mantenemos
                assigned_to_list_str.append(user_oid)

    # Manejar status y priority (asegurar que sean strings)
    final_status = str(ticket_doc.get("status", "0"))
    final_priority = str(ticket_doc.get("priority", "0"))

    # --- Población de objetos anidados ---
    category_info = None
    if category_id_str:
        category = await categories_model.obtener_category_por_id(db, category_id_str)
        if category:
            category_info = CategoryResponse(**category)

    assigned_department_info = None
    if assigned_department_id_str:
        from app.models.departments_model import obtener_department_por_id
        department = await obtener_department_por_id(db, assigned_department_id_str)
        if department:
            assigned_department_info = DepartmentResponse(**department)

    created_user_info = None
    if created_by_str:
        created_user = await obtener_user_por_id(db, created_by_str)
        if created_user:
            from app.routes.user_routes import build_user_response as build_user_response_helper
            created_user_info = await build_user_response_helper(created_user, db)

    assigned_users_info = []
    for user_id in assigned_to_list_str:
        assigned_user = await obtener_user_por_id(db, user_id)
        if assigned_user:
            from app.routes.user_routes import build_user_response as build_user_response_helper
            assigned_users_info.append(await build_user_response_helper(assigned_user, db))
    
    messages_info = []
    # NUEVA LÓGICA PARA MENSAJES: Iterar sobre los ObjectIds incrustados en el documento del ticket
    if "messages" in ticket_doc and isinstance(ticket_doc["messages"], list):
        for msg_oid in ticket_doc["messages"]:
            if isinstance(msg_oid, ObjectId):
                msg_data = await obtener_mensaje_por_id(db, str(msg_oid))
                if msg_data:
                    # Asegurar que los IDs sean strings para el esquema MessageResponse
                    messages_info.append(MessageResponse(
                        id=str(msg_data["_id"]),
                        message=msg_data.get("message"),
                        ticket_id=str(msg_data.get("ticket_id")),
                        created_by_id=str(msg_data.get("created_by_id")),
                        created_at=msg_data.get("created_at")
                    ))

    attachments_info = []
    # Lógica actual para attachments (consultando por ticket_id en la colección de attachments)
    # Esto es correcto si los attachments no están incrustados como OIDs en el documento del ticket.
    attachments_collection = db["attachments"]
    ticket_attachments = await attachments_collection.find({"ticket_id": ticket_id_str}).to_list(None)
    for att_doc in ticket_attachments:
        att_doc_id = str(att_doc["_id"]) if "_id" in att_doc else None
        att_ticket_id = str(att_doc["ticket_id"]) if "ticket_id" in att_doc else None
        # Asegúrate de que uploaded_by sea un string si es un ObjectId
        att_uploaded_by = str(att_doc["uploaded_by"]) if "uploaded_by" in att_doc and isinstance(att_doc["uploaded_by"], ObjectId) else None
        
        if att_doc_id and att_ticket_id:
            attachments_info.append(AttachmentResponse(
                id=att_doc_id,
                file_name=att_doc.get("file_name"),
                file_path=att_doc.get("file_path"),
                file_extension=att_doc.get("file_extension"),
                ticket_id=att_ticket_id,
                uploaded_by=att_uploaded_by,
                created_at=att_doc.get("created_at")
            ))

    ticket_response_data = {
        "id": ticket_id_str,
        "title": ticket_doc.get("title"),
        "description": ticket_doc.get("description"),
        "status": final_status,
        "priority": final_priority,
        "category_id": category_id_str, # Mapeado desde 'category' de MongoDB
        "assigned_to": assigned_to_list_str, # Mapeado desde 'assigned_users' de MongoDB
        "assigned_department_id": assigned_department_id_str, # Mapeado desde 'assigned_department' de MongoDB
        "created_by": created_by_str, # Mapeado desde 'created_user' de MongoDB
        "created_at": ticket_doc.get("createdAt"), # Usar el nombre de campo de MongoDB
        "updated_at": ticket_doc.get("updatedAt"), # Usar el nombre de campo de MongoDB
        "category": category_info,
        "assigned_department": assigned_department_info,
        "created_user": created_user_info,
        "assigned_users": assigned_users_info,
        "messages": messages_info,
        "attachments": attachments_info,
    }
    
    return TicketResponse(**ticket_response_data)

# Generar nombre con base en el nombre original y numeración de 4 dígitos
def generar_nombre_incremental(nombre_base, extension, carpeta="app/uploads"):
    archivos = os.listdir(carpeta)
    # Filtrar los archivos que empiezan con el nombre_base
    numeros = []
    for f in archivos:
        if f.startswith(nombre_base + "_") and f.endswith("." + extension):
            parte = f[len(nombre_base) + 1 : -(len(extension) + 1)] # Extrae el número
            if parte.isdigit():
                numeros.append(int(parte))
    siguiente = max(numeros, default=0) + 1
    numero_formateado = f"{siguiente:04d}"
    return f"{nombre_base}_{numero_formateado}.{extension}"

# 1. Obtener todos los tickets
@router.get("/", response_model=List[TicketResponse])
async def get_tickets(db: AsyncIOMotorDatabase = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    tickets_data = await tickets_model.obtener_tickets(db)
    if not tickets_data:
        return []
    response_tickets = []
    for ticket_doc in tickets_data:
        response_tickets.append(await build_ticket_response(ticket_doc, db))
    return response_tickets

# 2. Obtener ticket por ID
@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: AsyncIOMotorDatabase = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return await build_ticket_response(ticket_data, db)

# 3. Crear ticket
@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    ticket_dict = data.dict()
    ticket_dict["created_by"] = str(current_user.id) # Usar el ID de MongoDB del usuario
    ticket_dict["status"] = str(ticket_dict.get("status", 0)) # Asegurar que el estado sea string
    ticket_dict["priority"] = str(ticket_dict.get("priority", 0)) # Asegurar que la prioridad sea string

    if ticket_dict.get("category_id") == "0" or not ticket_dict.get("category_id"): # Ajustar a string "0"
        ticket_dict["category_id"] = None
    if ticket_dict.get("assigned_department_id") == "0" or not ticket_dict.get("assigned_department_id"): # Ajustar a string "0"
        ticket_dict["assigned_department_id"] = None
    
    # Si assigned_to es una lista de IDs de usuario, asegúrate de que sean strings
    if "assigned_to" in ticket_dict and ticket_dict["assigned_to"] is not None:
        ticket_dict["assigned_to"] = [str(uid) for uid in ticket_dict["assigned_to"]]
    else:
        ticket_dict["assigned_to"] = [] # Asegurar que sea una lista vacía si no se asigna

    created_ticket_data = await tickets_model.crear_ticket(db, ticket_dict)
    if not created_ticket_data:
        raise HTTPException(status_code=500, detail="Error al crear el ticket en la base de datos.")

    # ✅ Obtener usuarios del departamento y sus correos para notificación
    # Asegúrate de que obtener_users_by_department_id devuelva una lista de diccionarios de usuario
    recipient_emails = []
    if created_ticket_data.get("assigned_department_id"):
        dept_users_data = await obtener_users_by_department_id(db, created_ticket_data["assigned_department_id"])
        recipient_emails = [user["email"] for user in dept_users_data if user.get("email") and user.get("status") == True]
        
        # ✅ Enviar notificación en segundo plano (descomenta si tienes la implementación)
        # notification_data = TicketNotification(
        #     ticket_id=str(created_ticket_data["_id"]),
        #     title=created_ticket_data["title"],
        #     description=created_ticket_data["description"],
        #     category_id=created_ticket_data.get("category_id"),
        #     assigned_department_id=created_ticket_data.get("assigned_department_id"),
        #     created_user_id=created_ticket_data["created_by"],
        #     recipient_emails=recipient_emails
        # )
        # background_tasks.add_task(notify_ticket_created, notification_data)
    
    return await build_ticket_response(created_ticket_data, db)

# 4. Actualizar ticket estado
@router.put("/{ticket_id}/estado")
async def actualizar_estado_ticket(
    ticket_id: str, # ID de MongoDB es string
    estado_id: int,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
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
        
        estado_str = str(estado_id)
        estado_nombre = ESTADOS[estado_id]

        ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
        if not ticket_data:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
        # Convertir el estado del ticket a int para comparación si es necesario
        current_ticket_status_int = int(ticket_data.get("status", 0))

        if current_ticket_status_int in {0, 5}: # 0: Cancelado, 5: Completado
            raise HTTPException(status_code=400, detail="No se puede cambiar el estado de un ticket que ya está cancelado o completado")
        
        es_creador = str(current_user.id) == str(ticket_data.get("created_by"))
        
        # Para assigned_users, necesitamos obtener los IDs de los usuarios asignados
        assigned_users_ids = [str(uid) for uid in ticket_data.get("assigned_to", [])]
        es_asignado = str(current_user.id) in assigned_users_ids

        if estado_id == 0 and not es_creador:
            raise HTTPException(status_code=403, detail="Solo el creador puede cancelar el ticket")
        if estado_id == 1 and not es_creador:
            raise HTTPException(status_code=403, detail="Solo el creador puede marcarlo como abierto")
        if estado_id == 2 and not es_asignado:
            raise HTTPException(status_code=403, detail="Solo usuarios asignados pueden marcarlo como en proceso")
        if estado_id == 3 and not (es_creador or es_asignado):
            raise HTTPException(status_code=403, detail="Solo el creador o asignados pueden marcarlo en espera")
        if estado_id == 4 and not es_asignado:
            raise HTTPException(status_code=403, detail="Solo usuarios asignados pueden marcarlo en revisión")
        if estado_id == 5 and not (es_creador or str(current_user.department_id) == str(ticket_data.get("assigned_department_id"))):
            raise HTTPException(status_code=403, detail="Solo el creador o miembros del departamento asignado pueden marcarlo como completado")
        
        updated_ticket_data = await tickets_model.actualizar_ticket(db, ticket_id, {"status": estado_str})
        if not updated_ticket_data:
            raise HTTPException(status_code=500, detail="Error al actualizar el estado del ticket en la base de datos.")

        return {
            "message": f"Estado actualizado correctamente a código {estado_str} ({estado_nombre})",
            "ticket": await build_ticket_response(updated_ticket_data, db)
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error interno al actualizar el estado del ticket")

# 7. Asignar usuarios al ticket
@router.post("/{ticket_id}/asignar-usuarios")
async def asignar_usuarios_a_ticket(
    ticket_id: str, # ID de MongoDB es string
    asignaciones: List[str], # Lista de IDs de usuario (strings)
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    current_ticket_status_int = int(ticket_data.get("status", 0))
    if current_ticket_status_int in {0, 5}: # 0: Cancelado, 5: Completado
        raise HTTPException(status_code=400, detail="No se pueden asignar usuarios a un ticket cancelado o completado")
    
    if str(ticket_data.get("assigned_department_id")) != str(current_user.department_id):
        raise HTTPException(status_code=403, detail="Solo el departamento asignado al ticket puede asignar usuarios")
    
    usuarios_asignados_actuales = set(ticket_data.get("assigned_to", []))
    
    # Validar que los usuarios a asignar existen y pertenecen al departamento del usuario actual
    valid_users_in_department = await obtener_users_by_department_id(db, str(current_user.department_id))
    valid_user_ids_in_department = {str(u["_id"]) for u in valid_users_in_department}

    usuarios_a_asignar_validos = []
    invalidos = []
    for user_id in asignaciones:
        if user_id in valid_user_ids_in_department:
            usuarios_a_asignar_validos.append(user_id)
        else:
            invalidos.append(user_id)
    
    if invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Los siguientes usuarios no pertenecen a tu departamento o son inválidos: {invalidos}"
        )
    
    nuevos_asignados_count = 0
    updated_assigned_to = list(usuarios_asignados_actuales) # Copia la lista actual
    for user_id in usuarios_a_asignar_validos:
        if user_id not in usuarios_asignados_actuales:
            updated_assigned_to.append(user_id)
            nuevos_asignados_count += 1
    
    if nuevos_asignados_count == 0:
        raise HTTPException(status_code=400, detail="El usuario ya estaba asignado al ticket o no se proporcionaron nuevos usuarios válidos.")
    
    # Actualizar el campo 'assigned_to' en el documento del ticket
    updated_ticket = await tickets_model.actualizar_ticket(db, ticket_id, {"assigned_to": updated_assigned_to})
    if not updated_ticket:
        raise HTTPException(status_code=500, detail="Error al actualizar la asignación de usuarios en el ticket.")

    return {"message": f"{nuevos_asignados_count} usuario(s) asignado(s) correctamente"}

@router.delete("/{ticket_id}/quitar-usuarios")
async def quitar_usuarios_de_ticket(
    ticket_id: str, # ID de MongoDB es string
    usuarios_a_quitar: List[str], # Lista de IDs de usuario (strings)
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    current_ticket_status_int = int(ticket_data.get("status", 0))
    if current_ticket_status_int in {0, 5}: # 0: Cancelado, 5: Completado
        raise HTTPException(status_code=400, detail="No se pueden modificar usuarios de un ticket cancelado o completado")
    
    if str(ticket_data.get("assigned_department_id")) != str(current_user.department_id):
        raise HTTPException(status_code=403, detail="Solo el departamento asignado al ticket puede modificar usuarios")
    
    usuarios_asignados_actuales = set(ticket_data.get("assigned_to", []))
    
    # Validar que los usuarios a quitar realmente están asignados y pertenecen al departamento del usuario actual
    valid_users_in_department = await obtener_users_by_department_id(db, str(current_user.department_id))
    valid_user_ids_in_department = {str(u["_id"]) for u in valid_users_in_department}

    usuarios_a_quitar_validos = []
    invalidos = []
    for user_id in usuarios_a_quitar:
        if user_id in usuarios_asignados_actuales and user_id in valid_user_ids_in_department:
            usuarios_a_quitar_validos.append(user_id)
        else:
            invalidos.append(user_id)
    
    if invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Los siguientes usuarios no están asignados al ticket, no pertenecen a tu departamento o son inválidos: {invalidos}"
        )
    
    if not usuarios_a_quitar_validos:
        raise HTTPException(status_code=400, detail="No se proporcionaron usuarios válidos para quitar.")

    updated_assigned_to = [uid for uid in usuarios_asignados_actuales if uid not in usuarios_a_quitar_validos]
    
    updated_ticket = await tickets_model.actualizar_ticket(db, ticket_id, {"assigned_to": updated_assigned_to})
    if not updated_ticket:
        raise HTTPException(status_code=500, detail="Error al actualizar la asignación de usuarios en el ticket.")

    return {"message": f"{len(usuarios_a_quitar_validos)} usuario(s) quitado(s) correctamente"}

# 8. Obtener tickets asignados al usuario actual
@router.get("/asignados-a-mi/", response_model=List[TicketResponse])
async def get_tickets_asignados_a_mi(db: AsyncIOMotorDatabase = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    tickets_data = await tickets_model.obtener_tickets_asignados_a_usuario(db, str(current_user.id))

    if not tickets_data:
        return []

    response_tickets = []
    for ticket_doc in tickets_data:
        response_tickets.append(await build_ticket_response(ticket_doc, db))
    
    return response_tickets

# 9. Obtener tickets asignados al departamento del usuario
@router.get("/asignados-departamento/", response_model=List[TicketResponse])
async def get_tickets_departamento(db: AsyncIOMotorDatabase = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    if not current_user.department_id:
        return []

    tickets_collection = db["tickets"]
    tickets_data = await tickets_collection.find({"assigned_department_id": str(current_user.department_id)}).to_list(None)

    if not tickets_data:
        return []

    response_tickets = []
    for ticket_doc in tickets_data:
        response_tickets.append(await build_ticket_response(ticket_doc, db))
    
    return response_tickets

# 10. Obtener tickets creados por el usuario y su departamento
@router.get("/creados/", response_model=dict)
async def get_tickets_creados(db: AsyncIOMotorDatabase = Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    tickets_collection = db["tickets"]

    # Tickets creados por el usuario
    mios_data = await tickets_collection.find({"created_by": str(current_user.id)}).to_list(None)
    
    mios_response = []
    for ticket_doc in mios_data:
        mios_response.append(await build_ticket_response(ticket_doc, db))

    # Tickets creados por otros pero asignados al departamento del usuario
    departamento_response = []
    if current_user.department_id:
        departamento_data = await tickets_collection.find({
            "assigned_department_id": str(current_user.department_id),
            "created_by": {"$ne": str(current_user.id)}
        }).to_list(None)
        
        for ticket_doc in departamento_data:
            departamento_response.append(await build_ticket_response(ticket_doc, db))
    
    return {
        "mios": mios_response,
        "departamento": departamento_response
    }

# 11. Agregar mensaje a un ticket
@router.post("/{ticket_id}/mensajes/", response_model=dict)
async def crear_mensaje_ticket(
    ticket_id: str,
    data: MessageCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    is_creator = str(current_user.id) == str(ticket_data.get("created_by"))
    is_assigned_to_department = str(current_user.department_id) == str(ticket_data.get("assigned_department_id"))

    if not (is_creator or is_assigned_to_department):
        raise HTTPException(status_code=403, detail="No tienes permiso para escribir en este ticket")
    
    message_dict = data.dict()
    message_dict["ticket_id"] = ticket_id
    message_dict["created_by_id"] = str(current_user.id)
    
    created_message = await crear_message(db, message_dict)
    if not created_message:
        raise HTTPException(status_code=500, detail="Error al crear el mensaje en la base de datos.")

    return {
        "message": "Mensaje enviado correctamente",
        "mensaje": created_message
    }

# 12. Ruta para agregar un archivo a un ticket
@router.post("/{ticket_id}/attachments", response_model=dict)
async def subir_attachment(
    ticket_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    upload_folder = "app/uploads"
    os.makedirs(upload_folder, exist_ok=True)
    
    nombre_archivo_base = file.filename.rsplit(".", 1)[0].replace(" ", "_")
    extension = file.filename.rsplit(".", 1)[-1].lower()
    
    nombre_final = generar_nombre_incremental(nombre_archivo_base, extension, upload_folder)
    relative_path = f"/uploads/{nombre_final}"
    save_path = os.path.join(upload_folder, nombre_final)
    
    try:
        content = await file.read()
        with open(save_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")
    
    attachment_dict = {
        "file_name": nombre_final,
        "file_path": relative_path,
        "file_extension": extension,
        "ticket_id": ticket_id,
        "uploaded_by": str(current_user.id)
    }
    
    new_attachment_data = await crear_attachment(db, attachment_dict)
    if not new_attachment_data:
        raise HTTPException(status_code=500, detail="Error al guardar el attachment en la base de datos.")

    base_url = str(request.base_url).rstrip("/")
    file_url = f"{base_url}{relative_path}"
    
    return JSONResponse(
        status_code=201,
        content={
            "message": "Archivo subido exitosamente",
            "attachment_id": str(new_attachment_data["_id"]),
            "file_name": new_attachment_data["file_name"],
            "file_path": new_attachment_data["file_path"],
            "file_extension": new_attachment_data["file_extension"],
            "file_url": file_url
        }
    )

# 13. Obtener todos los tickets creados por usuarios del mismo departamento
@router.get("/todos-creados-por-mi-departamento/", response_model=List[TicketResponse])
async def get_all_tickets_by_department_users(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    if not current_user.department_id:
        return []

    users_in_department = await obtener_users_by_department_id(db, str(current_user.department_id))
    user_ids_in_department = [str(u["_id"]) for u in users_in_department]

    tickets_collection = db["tickets"]
    tickets_data = await tickets_collection.find({
        "created_by": {"$in": user_ids_in_department}
    }).to_list(None)

    if not tickets_data:
        return []

    response_tickets = []
    for ticket_doc in tickets_data:
        response_tickets.append(await build_ticket_response(ticket_doc, db))
    
    return response_tickets
