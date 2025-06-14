import asyncio
from app.db.dbp import engine
from app.models.attachments_model import Base  
from app.models.categories_model import Base  
from app.models.category_department_model import Base  
from app.models.departments_model import Base  
from app.models.messages_model import Base 
from app.models.ticket_assigned_user_model import Base  
from app.models.tickets_model import Base  
from app.models.user_model import Base  

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print(" Migraciones Correctamente !!")

if __name__ == "__main__":
    asyncio.run(init_db())
