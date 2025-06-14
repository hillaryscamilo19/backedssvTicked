from sqlalchemy import Column, Integer, ForeignKey
from app.db.base import Base
from sqlalchemy.orm import relationship
import app.models

class TicketAssignedUser(Base):
    __tablename__ = "ticket_assigned_users"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    ticket = relationship("Ticket", back_populates="assigned_users")
    user = relationship("User", back_populates="assigned_tickets")
