from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    message = Column(String)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"))
    createdat = Column(DateTime(timezone=True), server_default=func.now())
    updatedat = Column(DateTime(timezone=True), onupdate=func.now())

    ticket = relationship("Ticket", back_populates="messages")
    user = relationship("User", back_populates="messages", foreign_keys=[created_by_id])


def messages_helper(message: Message):
    return {
        "id": message.id,
        "message": message.message,
        "created_by_id": message.created_by_id,
        "ticket_id": message.ticket_id,
        "created_at": message.createdat,
        "updated_at": message.updatedat,
    }

async def obtener_mensajes(db: AsyncSession):
    result = await db.execute(select(Message))
    mensajes = result.scalars().all()
    return [messages_helper(m) for m in mensajes]
