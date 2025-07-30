from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import os
import traceback
from bson import ObjectId
from app.db.dbp import get_db
from app.Schemas.Esquema import TicketCreate, TicketUpdate, TicketResponse, UserInDB, CategoryResponse, DepartmentResponse, MessageCreate, AttachmentCreate, AttachmentResponse, MessageResponse
from app.auth.dependencies import get_current_user
from app.models import tickets_model, categories_model
from app.models.user_model import obtener_user_por_id, obtener_users_by_department_id
from app.models.attachments_model import crear_attachment
from app.models.messages_model import crear_message, obtener_mensaje_por_id
from fastapi import BackgroundTasks
from fastapi import UploadFile, File

router = APIRouter()



# Convierte ObjectId y otros tipos no serializables a strings
def serialize_doc(doc: dict) -> dict:

    if not doc:
        return doc
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, list):
            doc[k] = [str(x) if isinstance(x, ObjectId) else x for x in v]
    return doc


# --- Función auxiliar para construir respuesta de usuario (CORREGIDA) ---
async def build_user_response_for_ticket(user_doc: dict, db: AsyncIOMotorDatabase) -> dict:
    """
    Función auxiliar para construir respuesta de usuario específicamente para tickets.
    Mapea los campos de MongoDB a los nombres esperados por Pydantic.
    """
    if not user_doc:
        return None
    
    # Mapear _id a id
    user_id_str = str(user_doc["_id"]) if "_id" in user_doc else None

    # Mapear phone_ext a string si es int
    phone_ext_str = str(user_doc['phone_ext']) if 'phone_ext' in user_doc and isinstance(user_doc['phone_ext'], int) else user_doc.get('phone_ext')

    # Mapear 'department' (ObjectId) a 'department_id' (string)
    department_id_from_db = user_doc.get("department")
    department_id_str = str(department_id_from_db) if isinstance(department_id_from_db, ObjectId) else department_id_from_db

    # Obtener información del departamento si existe
    department_info = None
    if department_id_str:
        from app.models.departments_model import obtener_department_por_id
        department = await obtener_department_por_id(db, department_id_str)
        if department:
            # Mapear fechas del departamento si son camelCase
            dept_created_at = department.get("createdAt") or department.get("created_at")
            dept_updated_at = department.get("updatedAt") or department.get("updated_at")
            
            department_info = {
                "id": str(department["_id"]),
                "name": department.get("name"),
                "created_at": dept_created_at,
                "updated_at": dept_updated_at
            }

    # Construir el diccionario de respuesta del usuario
    user_response_data = {
        "id": user_id_str,
        "username": user_doc.get("username"),
        "email": user_doc.get("email"),
        "fullname": user_doc.get("fullname"),
        "phone_ext": phone_ext_str,
        "department": department_id_str,
        "status": user_doc.get("status"),
        "role": user_doc.get("role"),
        "created_at": user_doc.get("createdAt"), # Usar 'createdAt' de MongoDB
        "updated_at": user_doc.get("updatedAt"), # Usar 'updatedAt' de MongoDB
        "department": department_info,
    }
    
    return user_response_data

# --- Funciones auxiliares para construir respuestas anidadas ---
async def build_ticket_response(ticket_doc: dict, db: AsyncIOMotorDatabase) -> TicketResponse:
    # Asegúrate de que _id se mapee a id para el top-level TicketResponse
    ticket_id_str = str(ticket_doc["_id"]) if "_id" in ticket_doc else None
    if not ticket_id_str:
        raise ValueError("Ticket document is missing _id")

    # Mapeo y conversión de IDs de MongoDB a strings para los campos directos del esquema
    # Los campos 'category_id', 'assigned_department_id', 'created_by' en MongoDB son ObjectIds o strings
    category_id_val = ticket_doc.get("category_id")
    category_id_str = str(category_id_val) if category_id_val else None

    assigned_department_id_val = ticket_doc.get("assigned_department_id")
    assigned_department_id_str = str(assigned_department_id_val) if assigned_department_id_val else None

    created_by_val = ticket_doc.get("created_by")
    created_by_str = str(created_by_val) if created_by_val else None
    
    # Manejar assigned_to: lista de ObjectIds en MongoDB a lista de strings en Pydantic
    assigned_to_list_str = []
    if "assigned_to" in ticket_doc and isinstance(ticket_doc["assigned_to"], list):
        for user_oid in ticket_doc["assigned_to"]:
            if isinstance(user_oid, ObjectId):
                assigned_to_list_str.append(str(user_oid))
            elif isinstance(user_oid, str):
                assigned_to_list_str.append(user_oid)

    # Manejar status y priority (asegurar que sean strings)
    final_status = str(ticket_doc.get("status", "0"))
    final_priority = str(ticket_doc.get("priority", "0"))

    # --- Población de objetos anidados ---
    category_info = None
    if category_id_str:
        category = await categories_model.obtener_category_por_id(db, category_id_str)
        if category:
            # Mapear fechas de categoría si son camelCase
            cat_created_at = category.get("createdAt") or category.get("created_at")
            cat_updated_at = category.get("updatedAt") or category.get("updated_at")
            
            category_info = CategoryResponse(
                id=str(category["_id"]),
                name=category.get("name"),
                description=category.get("description"),
                created_at=cat_created_at,
                updated_at=cat_updated_at
            )

    assigned_department_info = None
    if assigned_department_id_str:
        from app.models.departments_model import obtener_department_por_id
        department = await obtener_department_por_id(db, assigned_department_id_str)
        if department:
            # Mapear fechas del departamento si son camelCase
            dept_created_at = department.get("createdAt") or department.get("created_at")
            dept_updated_at = department.get("updatedAt") or department.get("updated_at")
            
            assigned_department_info = DepartmentResponse(
                id=str(department["_id"]),
                name=department.get("name"),
                created_at=dept_created_at,
                updated_at=dept_updated_at
            )

    created_user_info = None
    if created_by_str:
        created_user = await obtener_user_por_id(db, created_by_str)
        if created_user:
            created_user_info = await build_user_response_for_ticket(created_user, db)

    assigned_users_info = []
    for user_id in assigned_to_list_str:
        assigned_user = await obtener_user_por_id(db, user_id)
        if assigned_user:
            user_response = await build_user_response_for_ticket(assigned_user, db)
            if user_response:
                assigned_users_info.append(user_response)
    
    messages_info = []
    if "messages" in ticket_doc and isinstance(ticket_doc["messages"], list):
        for msg_oid in ticket_doc["messages"]:
            if isinstance(msg_oid, ObjectId):
                msg_data = await obtener_mensaje_por_id(db, str(msg_oid))
                if msg_data:
                    messages_info.append(MessageResponse(
                        id=str(msg_data["_id"]),
                        message=msg_data.get("message"),
                        ticket_id=str(msg_data.get("ticket_id")),
                        created_by_id=str(msg_data.get("created_by_id")),
                        created_at=msg_data.get("created_at") if msg_data.get("created_at") else datetime.utcnow()
                    ))

    attachments_info = []
    attachments_collection = db["attachments"]
    ticket_attachments = await attachments_collection.find({"ticket_id": ticket_id_str}).to_list(None)
    for att_doc in ticket_attachments:
        att_doc_id = str(att_doc["_id"]) if "_id" in att_doc else None
        att_ticket_id = str(att_doc["ticket_id"]) if "ticket_id" in att_doc else None
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
        "category_id": category_id_str,
        "assigned_to": assigned_to_list_str,
        "assigned_department_id": assigned_department_id_str,
        "created_by": created_by_str,
        "createdAt": ticket_doc.get("createdAt"), # Usar el nombre de campo de MongoDB 'created_at'
        "updatedAt": ticket_doc.get("updatedAt"), # Usar el nombre de campo de MongoDB 'updated_at'
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
    numeros = []
    for f in archivos:
        if f.startswith(nombre_base + "_") and f.endswith("." + extension):
            parte = f[len(nombre_base) + 1 : -(len(extension) + 1)]
            if parte.isdigit():
                numeros.append(int(parte))
    siguiente = max(numeros, default=0) + 1
    numero_formateado = f"{siguiente:04d}"
    return f"{nombre_base}_{numero_formateado}.{extension}"

def chunked_list(lst, chunk_size=100):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


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
    ticket_dict["created_by"] = str(current_user.id)
    ticket_dict["status"] = str(ticket_dict.get("status", 0))
    ticket_dict["priority"] = str(ticket_dict.get("priority", 0))

    if ticket_dict.get("category_id") == "0" or not ticket_dict.get("category_id"):
        ticket_dict["category_id"] = None
    if ticket_dict.get("assigned_department_id") == "0" or not ticket_dict.get("assigned_department_id"):
        ticket_dict["assigned_department_id"] = None
    
    if "assigned_to" in ticket_dict and ticket_dict["assigned_to"] is not None:
        ticket_dict["assigned_to"] = [str(uid) for uid in ticket_dict["assigned_to"]]
    else:
        ticket_dict["assigned_to"] = []

    created_ticket_data = await tickets_model.crear_ticket(db, ticket_dict)
    if not created_ticket_data:
        raise HTTPException(status_code=500, detail="Error al crear el ticket en la base de datos.")

    recipient_emails = []
    if created_ticket_data.get("assigned_department_id"):
        dept_users_data = await obtener_users_by_department_id(db, created_ticket_data["assigned_department_id"])
        recipient_emails = [user["email"] for user in dept_users_data if user.get("email") and user.get("status") == True]
        
    return await build_ticket_response(created_ticket_data, db)

# 4. Actualizar ticket estado
@router.put("/{ticket_id}/estado")
async def actualizar_estado_ticket(
    ticket_id: str,
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
        
        current_ticket_status_int = int(ticket_data.get("status", 0))

        if current_ticket_status_int in {0, 5}:
            raise HTTPException(status_code=400, detail="No se puede cambiar el estado de un ticket que ya está cancelado o completado")
        
        es_creador = str(current_user.id) == str(ticket_data.get("created_by"))
        
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
        if estado_id == 5 and not (es_creador or str(current_user.department) == str(ticket_data.get("assigned_department_id"))):
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
    ticket_id: str,
    asignaciones: List[str],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    current_ticket_status_int = int(ticket_data.get("status", 0))
    if current_ticket_status_int in {0, 5}:
        raise HTTPException(status_code=400, detail="No se pueden asignar usuarios a un ticket cancelado o completado")
    
    if str(ticket_data.get("assigned_department_id")) != str(current_user.department):
        raise HTTPException(status_code=403, detail="Solo el departamento asignado al ticket puede asignar usuarios")
    
    usuarios_asignados_actuales = set(ticket_data.get("assigned_to", []))
    
    valid_users_in_department = await obtener_users_by_department_id(db, str(current_user.department))
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
    updated_assigned_to = list(usuarios_asignados_actuales)
    for user_id in usuarios_a_asignar_validos:
        if user_id not in usuarios_asignados_actuales:
            updated_assigned_to.append(user_id)
            nuevos_asignados_count += 1
    
    if nuevos_asignados_count == 0:
        raise HTTPException(status_code=400, detail="El usuario ya estaba asignado al ticket o no se proporcionaron nuevos usuarios válidos.")
    
    updated_ticket = await tickets_model.actualizar_ticket(db, ticket_id, {"assigned_to": updated_assigned_to})
    if not updated_ticket:
        raise HTTPException(status_code=500, detail="Error al actualizar la asignación de usuarios en el ticket.")

    return {"message": f"{nuevos_asignados_count} usuario(s) asignado(s) correctamente"}

@router.delete("/{ticket_id}/quitar-usuarios")
async def quitar_usuarios_de_ticket(
    ticket_id: str,
    usuarios_a_quitar: List[str],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    ticket_data = await tickets_model.obtener_ticket_por_id(db, ticket_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    current_ticket_status_int = int(ticket_data.get("status", 0))
    if current_ticket_status_int in {0, 5}:
        raise HTTPException(status_code=400, detail="No se pueden modificar usuarios de un ticket cancelado o completado")
    
    if str(ticket_data.get("assigned_department_id")) != str(current_user.department):
        raise HTTPException(status_code=403, detail="Solo el departamento asignado al ticket puede modificar usuarios")
    
    usuarios_asignados_actuales = set(ticket_data.get("assigned_to", []))
    
    valid_users_in_department = await obtener_users_by_department_id(db, str(current_user.department))
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


# 8. 
@router.get("/asignados-a-mi/")
async def obtener_tickets_asignados_a_mi(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user_id: str = None
):
    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Hillarys pon antecion")
    
    tickets_collection = db["tickets"]
    tickets = await tickets_collection.find({"assigned_users": user_obj_id}).to_list(length=None)
    
    # Serializar todos los documentos
    tickets_serializados = [serialize_doc(ticket) for ticket in tickets]
    return tickets_serializados

# 9. Obtener tickets asignados al departamento del usuario
@router.get("/asignados-departamento/")
async def get_tickets_departamento(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: str = None
):
    try:
        user_obj_id = ObjectId(current_user)
    except Exception:
        raise HTTPException(status_code=400, detail="Hillarys pon antecion")

    tickets_collection = db["tickets"]
    tickets_data = await tickets_collection.find({"assigned_department": current_user}).to_list(None)

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
    if current_user.department:
        departamento_data = await tickets_collection.find({
            "assigned_department_id": str(current_user.department),
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
    is_assigned_to_department = str(current_user.department) == str(ticket_data.get("assigned_department_id"))

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
    if not current_user.department:
        return []

    users_in_department = await obtener_users_by_department_id(db, str(current_user.department))
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
