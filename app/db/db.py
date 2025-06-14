from motor.motor_asyncio import AsyncIOMotorClient # Mongo

#Conexion Con Mongo 
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["tzy"]
attachments_collection = db["attachments"]
categories_collection = db["categories"]
departments_collection = db["departments"]
messages_collection = db["messages"]
tickets_collection = db["tickets"]
user_collection = db["users"]


