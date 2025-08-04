from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, desc, func,select
from sqlalchemy.orm import relationship, selectinload
from app.models.messages_model import Message
from app.models.ticket_assigned_user_model import TicketAssignedUser
from app.db.base import Base
from sqlalchemy.ext.asyncio import AsyncSession
import app.models
from app.models.user_model import User
from app.models.departments_model import Department


class Ticket:
    def __init__(self, **kwargs):
        self.id = str(kwargs.get("_id"))  # Convertir ObjectId a string
        self.title = kwargs.get("title")
        self.description = kwargs.get("description")
        self.category_id = kwargs.get("category_id")
        self.assigned_department_id = kwargs.get("assigned_department_id")
        self.created_user_id = kwargs.get("created_user_id")
        self.status = kwargs.get("status")
        self.created_at = kwargs.get("createdAt")
        self.updated_at = kwargs.get("updatedAt")
        self.category = kwargs.get("category")
        self.assigned_department = kwargs.get("assigned_department")
        self.created_user = kwargs.get("created_user")
        self.assigned_users = kwargs.get("assigned_users", [])
        self.messages = kwargs.get("messages", [])
        self.attachments = kwargs.get("attachments", [])

def ticket_helper(ticket) -> dict:
    return {
        "id": str(ticket["_id"]),  # Convertir ObjectId a string
        "title": ticket["title"],
        "description": ticket["description"],
        "category": {
            "id": str(ticket.get("category")),  # Convertir ObjectId a string
            "name": None  # Si tienes un nombre de categoría, deberías obtenerlo de otra manera
        } if ticket.get("category") else None,
        "assigned_department": {
            "id": str(ticket.get("assigned_department")),  # Convertir ObjectId a string
            "name": None  # Si tienes un nombre de departamento, deberías obtenerlo de otra manera
        } if ticket.get("assigned_department") else None,
        "created_user": {
            "id": str(ticket.get("created_user")),  # Convertir ObjectId a string
            "fullname": ticket.get("created_user_fullname"),  # Asegúrate de que este campo esté disponible
            "email": ticket.get("created_user_email"),  # Asegúrate de que este campo esté disponible
            "phone_ext": ticket.get("created_user_phone_ext"),  # Asegúrate de que este campo esté disponible
            "department": {
                "id": str(ticket.get("created_user_department", {}).get("_id")),
                "name": ticket.get("created_user_department_name")  # Asegúrate de que este campo esté disponible
            } if ticket.get("created_user_department") else None
        } if ticket.get("created_user") else None,
        "assigned_users": [
            {
                "id": str(u.get("_id")),  # Convertir ObjectId a string
                "fullname": u.get("fullname"),
                "email": u.get("email"),
                "phone_ext": u.get("phone_ext"),
            } for u in ticket.get("assigned_users", [])
        ],
        "attachments": [
            {
                "id": str(a.get("_id")),  # Convertir ObjectId a string
                "file_name": a.get("file_name"),
                "file_path": a.get("file_path"),
                "file_extension": a.get("file_extension"),
            } for a in ticket.get("attachments", [])
        ],
        "messages": [
            {
                "id": str(msg.get("_id")),  # Convertir ObjectId a string
                "content": msg.get("message"),
                "created_at": msg.get("createdAt"),
                "user": {
                    "id": str(msg.get("user", {}).get("_id")),
                    "fullname": msg.get("user", {}).get("fullname")
                } if msg.get("user") else None
            } for msg in ticket.get("messages", [])
        ],
        "status": ticket["status"],
        "createdAt": ticket.get("createdAt"),
        "updatedAt": ticket.get("updatedAt")
    }

async def obtener_tickets(db):
    tickets = await db["tickets"].find().to_list(length=None)
    return [ticket_helper(ticket) for ticket in tickets]

