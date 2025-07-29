import asyncio
from app.db.base import Base
from app.models.user_model import User 
from app.models.departments_model import Department, user_supervision_departments
from app.models.attachments_model import Attachment 
from app.models.categories_model import Category 
from app.models.category_department_model import CategoryDepartment 
from app.models.messages_model import Message 
from app.models.ticket_assigned_user_model import TicketAssignedUser 
from app.models.tickets_model import Ticket 

from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:%40VisualSalud.2025%23@127.0.0.1:5432/tyz2"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())