from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, desc, func,select
from sqlalchemy.orm import relationship, selectinload
from app.models.messages_model import Message
from app.models.ticket_assigned_user_model import TicketAssignedUser
from app.db.base import Base
from sqlalchemy.ext.asyncio import AsyncSession
import app.models
from app.models.user_model import User


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    assigned_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"))
    created_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(String)
    created_at = Column("createdat", DateTime(timezone=True), server_default=func.now())
    updated_at = Column("updatedat", DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="tickets")
    assigned_department = relationship("Department", back_populates="tickets")
    created_user = relationship("User", back_populates="created_tickets")
    assigned_users = relationship("TicketAssignedUser", back_populates="ticket")
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan")

def ticket_helper(ticket) -> dict:
    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "category": {
            "id": ticket.category.id,
            "name": ticket.category.name
        } if ticket.category else None,
        "assigned_department": {
            "id": ticket.assigned_department.id,
            "name": ticket.assigned_department.name
        } if ticket.assigned_department else None,
        "created_user": {
            "id": ticket.created_user.id,
            "fullname": ticket.created_user.fullname,
            "email": ticket.created_user.email,
            "phone_ext": ticket.created_user.phone_ext,
            "department": {
                "id": ticket.created_user.department.id,
                "name": ticket.created_user.department.name
            } if ticket.created_user.department else None
        } if ticket.created_user else None,
        "assigned_users": [
            {
                "id": u.user.id,
                "fullname": u.user.fullname,
                "email": u.user.email,
                "phone_ext": u.user.phone_ext,
            } for u in ticket.assigned_users if u.user
        ],
          "attachments": [
            {
                "id": a.id,
                "file_name": a.file_name,
                "file_path": a.file_path,
                "file_extension": a.file_extension,
            }
            for a in ticket.attachments
        ],
        "messages": [
            {
                "id": msg.id,
                "content": msg.message,
                "created_at": msg.createdat.isoformat() if msg.createdat else None,
                "user": {
                    "id": msg.user.id,
                    "fullname": msg.user.fullname
                } if msg.user else None
            }
            for msg in ticket.messages
        ],
        "status": ticket.status,
        "createdAt": ticket.created_at.isoformat() if ticket.created_at else None,
        "updatedAt": ticket.updated_at.isoformat() if ticket.updated_at else None
    }


async def obtener_tickets(db: AsyncSession):
    result = await db.execute(
    select(Ticket)
    .order_by(desc(Ticket.id))
    .options(
    selectinload(Ticket.category),
    selectinload(Ticket.assigned_department),
    selectinload(Ticket.created_user).selectinload(User.department),# 👈 aquí debe estar
    selectinload(Ticket.assigned_users).selectinload(TicketAssignedUser.user),
    selectinload(Ticket.messages).selectinload(Message.user),
    selectinload(Ticket.attachments) 

)
)
    tickets = result.scalars().all()
    # print([t.id for t in tickets])   Verifica que esté 2559


    return [ticket_helper(ticket) for ticket in tickets]

