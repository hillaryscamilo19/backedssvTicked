import traceback
from typing import List
from urllib import request
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from app.auth.dependencies import get_current_user
from app.db.dbp import get_db
from app.models.tickets_model import Ticket, obtener_tickets, ticket_helper
from app.models.ticket_assigned_user_model import TicketAssignedUser
from app.models.user_model import User
from app.models.messages_model import Message
from app.Schemas.Ticket import TicketCreate, TicketUpdate
from app.Schemas.Message import MessageCreate
from app.models.attachments_model import Attachment
from app.models.messages_model import messages_helper
from fastapi import UploadFile, File
import os
from app.utils.email_utils import send_email  

router = APIRouter()

# Generar nombre con base en el nombre original y numeración de 4 dígitos
def generar_nombre_incremental(nombre_base, extension, carpeta="app/uploads"):
    archivos = os.listdir(carpeta)
    # Filtrar los archivos que empiezan con el nombre_base
    numeros = []
    for f in archivos:
        if f.startswith(nombre_base + "_") and f.endswith("." + extension):
            parte = f[len(nombre_base) + 1 : -(len(extension) + 1)]  # Extrae el número
            if parte.isdigit():
                numeros.append(int(parte))
    siguiente = max(numeros, default=0) + 1
    numero_formateado = f"{siguiente:04d}"
    return f"{nombre_base}_{numero_formateado}.{extension}"


def chunked_list(lst, chunk_size=100):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

# 1. Obtener todos los tickets
@router.get("/")
async def get_tickets(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await obtener_tickets(db)

# 2. Obtener ticket por ID
@router.get("/{ticket_id}")
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Ticket)
        .options(
            selectinload(Ticket.category),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.created_user).selectinload(User.department),
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user),
            selectinload(Ticket.messages).selectinload(Message.user),
            selectinload(Ticket.attachments) 
        )
        .filter(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket_helper(ticket)

# 3. Crear ticket
@router.post("/")
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data_dict = data.model_dump()
    data_dict["created_user_id"] = current_user.id

    if data_dict.get("category_id") == 0:
        data_dict["category_id"] = None
    if data_dict.get("assigned_department_id") in (None, 0, ""):
        data_dict["assigned_department_id"] = None

    new_ticket = Ticket(**data_dict)
    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)

    # ✅ Obtener usuarios del departamento asignado
    if new_ticket.assigned_department_id:
        result = await db.execute(
            select(User).filter(
                User.department_id == new_ticket.assigned_department_id,
                User.status == True
            )
        )
        dept_users = result.scalars().all()

    """ for user in dept_users:
            send_email(
                to=user.email,
                subject="Nuevo ticket asignado a tu departamento",
                body=f"Hola {user.fullname},\n\nSe ha creado un nuevo ticket #{new_ticket.id} asignado a tu departamento.\n\nPor favor revisa el sistema."
            )  """

    # Retornar ticket
    result = await db.execute(
        select(Ticket)
        .filter(Ticket.id == new_ticket.id)
        .options(
            selectinload(Ticket.category),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.created_user).selectinload(User.department),
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user),
            selectinload(Ticket.messages).selectinload(Message.user),
            selectinload(Ticket.attachments),
        )
    )
    ticket = result.scalar_one_or_none()
    return ticket_helper(ticket)



# 4. Actualizar ticket estado
@router.put("/{ticket_id}/estado")
async def actualizar_estado_ticket(
    ticket_id: int,
    estado_id: int,
    db: AsyncSession = Depends(get_db),
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

        estado_str = str(estado_id)
        estado_nombre = ESTADOS[estado_id]

        result = await db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user),
                selectinload(Ticket.category),
                selectinload(Ticket.assigned_department),
                selectinload(Ticket.created_user).selectinload(User.department),
                selectinload(Ticket.messages).selectinload(Message.user),
                selectinload(Ticket.attachments)
            )
            .filter(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")

        if ticket.status in {"0", "5"}:
            raise HTTPException(status_code=400, detail="No se puede cambiar el estado de un ticket que ya está cancelado o completado")

        es_creador = current_user.id == ticket.created_user_id
        es_asignado = current_user.id in [u.user_id for u in ticket.assigned_users]

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

        if estado_id == 5 and not (es_creador or current_user.department_id == ticket.assigned_department_id):
            raise HTTPException(status_code=403, detail="Solo el creador o miembros del departamento asignado pueden marcarlo como completado")


        ticket.status = estado_str
        await db.commit()
        await db.refresh(ticket)

        return {
            "message": f"Estado actualizado correctamente a código {estado_str} ({estado_nombre})",
            "ticket": ticket_helper(ticket)
        }

    except HTTPException:
        raise  # <- Deja pasar excepciones HTTP personalizadas

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error interno al actualizar el estado del ticket")



# 7. Asignar usuarios al ticket
@router.post("/{ticket_id}/asignar-usuarios")
async def asignar_usuarios_a_ticket(
    ticket_id: int,
    asignaciones: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    if ticket.status in {"0", "5"}:
        raise HTTPException( status_code=400, detail="No se pueden asignar usuarios a un ticket cancelado o completado")

    if ticket.assigned_department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Solo el departamento asignado al ticket puede asignar usuarios")

    result = await db.execute(
        select(TicketAssignedUser.user_id).filter(TicketAssignedUser.ticket_id == ticket_id)
    )
    usuarios_asignados_actuales = set(result.scalars().all())

    result = await db.execute(
        select(User.id).filter(User.id.in_(asignaciones), User.department_id == current_user.department_id)
    )
    usuarios_validos = set(result.scalars().all())

    invalidos = set(asignaciones) - usuarios_validos
    if invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Los siguientes usuarios no pertenecen a tu departamento: {invalidos}"
        )

    nuevos_asignados = 0

    for user_id in usuarios_validos:
        if user_id not in usuarios_asignados_actuales:
            asignado = TicketAssignedUser(ticket_id=ticket_id, user_id=user_id)
            db.add(asignado)
            nuevos_asignados += 1

    if nuevos_asignados == 0:
        raise HTTPException( status_code=400, detail="El usuario ya estaba asignado al ticket")

    await db.commit()
    return {"message": f"{nuevos_asignados} usuario(s) asignado(s) correctamente"}


@router.delete("/{ticket_id}/quitar-usuarios")
async def quitar_usuarios_de_ticket(
    ticket_id: int,
    usuarios_a_quitar: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que el ticket exista
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    # Validar estado del ticket
    if ticket.status in {"0", "5"}:
        raise HTTPException(status_code=400, detail="No se pueden modificar usuarios de un ticket cancelado o completado")

    # Validar departamento asignado
    if ticket.assigned_department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Solo el departamento asignado al ticket puede modificar usuarios")

    # Verificar que los usuarios a quitar pertenecen al departamento del usuario actual
    result = await db.execute(
        select(User.id).filter(User.id.in_(usuarios_a_quitar), User.department_id == current_user.department_id)
    )
    usuarios_validos = set(result.scalars().all())

    invalidos = set(usuarios_a_quitar) - usuarios_validos
    if invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Los siguientes usuarios no pertenecen a tu departamento o no pueden ser quitados: {invalidos}"
        )

    # Ejecutar la eliminación
    delete_stmt = delete(TicketAssignedUser).where(
        TicketAssignedUser.ticket_id == ticket_id,
        TicketAssignedUser.user_id.in_(usuarios_validos)
    )
    await db.execute(delete_stmt)
    await db.commit()

    return {"message": f"{len(usuarios_validos)} usuario(s) quitado(s) correctamente"}



# 8. Obtener tickets asignados al usuario actual
@router.get("/asignados-a-mi/")
async def get_tickets_asignados_a_mi(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Ticket)
        .join(Ticket.assigned_users)
        .filter(TicketAssignedUser.user_id == current_user.id)
        .order_by(desc(Ticket.id))
        .options(
            selectinload(Ticket.category),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.created_user).selectinload(User.department),
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user),
            selectinload(Ticket.messages).selectinload(Message.user),
            selectinload(Ticket.attachments) 
        )
    )
    tickets = result.scalars().all()
    return [ticket_helper(t) for t in tickets]


# 9. Obtener tickets asignados al departamento del usuario
@router.get("/asignados-departamento/")
async def get_tickets_departamento(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Ticket)
        .filter(Ticket.assigned_department_id == current_user.department_id)
        .order_by(desc(Ticket.id))
        .options(
            selectinload(Ticket.category),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.created_user).selectinload(User.department),
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user),
            selectinload(Ticket.messages).selectinload(Message.user),
            selectinload(Ticket.attachments) 

        )
    )
    tickets = result.scalars().all()
    return [ticket_helper(t) for t in tickets]


# 10. Obtener tickets creados por el usuario y su departamento
@router.get("/creados/")
async def get_tickets_creados(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Tickets creados por el usuario
    result_mios = await db.execute(
        select(Ticket)
        .filter(Ticket.created_user_id == current_user.id)
        .options(
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user), 
            selectinload(Ticket.created_user).selectinload(User.department),
            selectinload(Ticket.category),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.messages).selectinload(Message.user),
            selectinload(Ticket.attachments) 

        )
    )
    mios = result_mios.scalars().all()

    # Tickets creados por otros pero asignados al departamento del usuario
    result_departamento = await db.execute(
        select(Ticket)
        .filter(
            (Ticket.assigned_department_id == current_user.department_id) &
            (Ticket.created_user_id != current_user.id)
        )
        .options(
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user), 
            selectinload(Ticket.created_user).selectinload(User.department),
            selectinload(Ticket.category),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.messages).selectinload(Message.user),
            selectinload(Ticket.attachments) 

        )
    )
    departamento = result_departamento.scalars().all()

    return {
        "mios": [ticket_helper(t) for t in mios],
        "departamento": [ticket_helper(t) for t in departamento]
    }

# 11. Agregar mensaje a un ticket
@router.post("/{ticket_id}/mensajes/")
async def crear_mensaje_ticket(
    ticket_id: int,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Ticket)
        .filter(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user).selectinload(User.department),
            selectinload(Ticket.messages).selectinload(Message.user),
        )
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    # Validación corregida
    if current_user.id != ticket.created_user_id and not any(
        assignment.user and assignment.user.department_id == current_user.department_id
        for assignment in ticket.assigned_users
    ):
        raise HTTPException(status_code=403, detail="No tienes permiso para escribir en este ticket")

    nuevo_mensaje = Message(
        ticket_id=ticket_id,
        created_by_id=current_user.id,
        message=data.message
    )
    db.add(nuevo_mensaje)
    await db.commit()
    await db.refresh(nuevo_mensaje)

    return {
        "message": "Mensaje enviado correctamente",
        "mensaje": messages_helper(nuevo_mensaje)
    }

# 12. Ruta para agregar un archivo a un ticket
@router.post("/{ticket_id}/attachments")
async def subir_attachment(
    ticket_id: int,
    request: Request ,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar ticket
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    # Preparar carpeta
    upload_folder = "app/uploads"
    os.makedirs(upload_folder, exist_ok=True)

    # Separar nombre y extensión
    nombre_archivo = file.filename.rsplit(".", 1)[0].replace(" ", "_")
    extension = file.filename.rsplit(".", 1)[-1].lower()

    # Generar nombre incremental
    nombre_final = generar_nombre_incremental(nombre_archivo, extension, upload_folder)

    relative_path = f"/uploads/{nombre_final}"
    save_path = os.path.join(upload_folder, nombre_final)

    # Leer y guardar archivo
    try:
        content = await file.read()  # ✅ Leer antes de abrir archivo
        with open(save_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {str(e)}")

    # Guardar en DB
    new_attachment = Attachment(
        file_name=nombre_final,
        file_path=relative_path,
        file_extension=extension,
        ticket_id=ticket_id
    )

    db.add(new_attachment)
    await db.commit()
    await db.refresh(new_attachment)

    # Construir URL completa
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Obtener todos los usuarios que pertenecen al mismo departamento
    result_users = await db.execute(
        select(User.id).filter(User.department_id == current_user.department_id)
    )
    user_ids = result_users.scalars().all()

    # Buscar todos los tickets creados por esos usuarios
    result_tickets = await db.execute(
        select(Ticket)
        .filter(Ticket.created_user_id.in_(user_ids))
        .order_by(desc(Ticket.id))
        .options(
            selectinload(Ticket.created_user).selectinload(User.department),
            selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user),
            selectinload(Ticket.category),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.messages).selectinload(Message.user),
            selectinload(Ticket.attachments) 

        )
    )
    tickets = result_tickets.scalars().all()
    return [ticket_helper(ticket) for ticket in tickets]
