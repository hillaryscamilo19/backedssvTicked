from app.db.db import tickets_collection, categories_collection, departments_collection, user_collection, messages_collection
from bson import ObjectId

async def obtener_tickets():
    try:
        # Usamos un agregador para optimizar la carga de datos
        pipeline = [
            {
                "$lookup": {
                    "from": "categories", 
                    "localField": "category", 
                    "foreignField": "_id", 
                    "as": "category_info"
                }
            },
            {
                "$lookup": {
                    "from": "departments", 
                    "localField": "assigned_department", 
                    "foreignField": "_id", 
                    "as": "department_info"
                }
            },
            {
                "$lookup": {
                    "from": "users", 
                    "localField": "assigned_users", 
                    "foreignField": "_id", 
                    "as": "assigned_users_info"
                }
            },
            {
                "$lookup": {
                    "from": "messages", 
                    "localField": "messages", 
                    "foreignField": "_id", 
                    "as": "messages_info"
                }
            },
            {
                "$lookup": {
                    "from": "users", 
                    "localField": "created_user", 
                    "foreignField": "_id", 
                    "as": "created_user_info"
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "description": 1,
                    "status": 1,
                    "createdAt": 1,
                    "updatedAt": 1,
                    "category_info.name": 1,
                    "department_info.name": 1,
                    "assigned_users_info.name": 1,
                    "assigned_users_info.email": 1,
                    "messages_info.message": 1,
                    "created_user_info.name": 1,
                    "created_user_info.email": 1,
                }
            }
        ]
        
        # Ejecutamos el pipeline de agregación para obtener los datos optimizados
        tickets_list = []
        async for ticket in tickets_collection.aggregate(pipeline):
            # Procesamos los resultados del pipeline
            ticket_info = {
                "id": str(ticket["_id"]),
                "title": ticket.get("title"),
                "description": ticket.get("description"),
                "category": {"name": ticket["category_info"][0]["name"]} if ticket["category_info"] else None,
                "assigned_department": {"name": ticket["department_info"][0]["name"]} if ticket["department_info"] else None,
                "assigned_users": [
                    {"id": str(user["_id"]), "name": user.get("name"), "email": user.get("email")}
                    for user in ticket["assigned_users_info"]
                ],
                "created_user": {
                    "id": str(ticket["created_user_info"][0]["_id"]),
                    "name": ticket["created_user_info"][0].get("name"),
                    "email": ticket["created_user_info"][0].get("email")
                } if ticket["created_user_info"] else None,
                "mensajes": [
                    {"id": str(mensaje["_id"]), "message": mensaje.get("message")}
                    for mensaje in ticket["messages_info"]
                ],
                "status": ticket.get("status"),
                "createdAt": ticket.get("createdAt"),
                "updatedAt": ticket.get("updatedAt"),
            }
            tickets_list.append(ticket_info)
        
        return tickets_list
    except Exception as e:
        return {"error": str(e)}

