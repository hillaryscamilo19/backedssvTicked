from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, selectinload
from app.db.base import Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select 
import app.models

class Attachment(Base):
    __tablename__ = 'attachments'
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String)
    file_path = Column(String, index=True)
    file_extension = Column(String)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))

    ticket = relationship("Ticket", back_populates="attachments")

def attachments_to_dict(attachment):
    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "file_path": attachment.file_path,
        "file_extension": attachment.file_extension,
        "ticket_id": attachment.ticket_id,
    }

async def obtener_attachments(db: AsyncSession):
    try:
        result = await db.execute(
            select(Attachment).options(selectinload(Attachment.ticket))
        )
        attachments = result.scalars().all()
        return [attachments_to_dict(att) for att in attachments]
    except Exception as e:
        raise e
