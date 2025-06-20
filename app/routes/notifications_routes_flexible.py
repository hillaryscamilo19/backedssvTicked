from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear router para notificaciones
router = APIRouter()

# Configuraciones múltiples para probar
EMAIL_CONFIGS = [
    {
        "name": "SSV SSL 465",
        "SMTP_SERVER": "shared70.accountservergroup.com",
        "SMTP_PORT": 465,
        "USE_SSL": True,
        "USE_TLS": False
    },
    {
        "name": "SSV STARTTLS 587",
        "SMTP_SERVER": "shared70.accountservergroup.com", 
        "SMTP_PORT": 587,
        "USE_SSL": False,
        "USE_TLS": True
    },
    {
        "name": "Mail SSV SSL 465",
        "SMTP_SERVER": "mail.ssv.com.do",
        "SMTP_PORT": 465,
        "USE_SSL": True,
        "USE_TLS": False
    },
    {
        "name": "Mail SSV STARTTLS 587",
        "SMTP_SERVER": "mail.ssv.com.do",
        "SMTP_PORT": 587,
        "USE_SSL": False,
        "USE_TLS": True
    }
]

# Configuración por defecto
DEFAULT_CONFIG = {
    "EMAIL_USER": os.getenv("EMAIL_USER", "soportetecnico@ssv.com.do"),
    "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD", "")
}

# Modelos Pydantic

class ConfigTestResult(BaseModel):
    config_name: str
    success: bool
    message: str
    details: Dict[str, Any]

class EmailRequest(BaseModel):
    from_email: EmailStr = "soportetecnico@ssv.com.do"
    to: List[EmailStr]
    subject: str
    html: str
    text: str

class TicketNotification(BaseModel):
    ticket_id: str
    title: str
    description: str
    category_id: Optional[int]
    assigned_department_id: Optional[int]
    created_user_id: Optional[int]
    status: Optional[str] = "1"
    recipient_emails: List[EmailStr]  # <-- Agregado

class User(BaseModel):
    id: str
    email: EmailStr
    fullname: Optional[str] = None
    department_id: Optional[str] = None
    status: bool = True

class EmailResponse(BaseModel):
    success: bool
    message: str
    emails_sent: int
    failed_emails: List[str] = []
    config_used: Optional[str] = None  # <-- Agregado para indicar config usada


# Funciones auxiliares

async def test_smtp_config(config: dict) -> ConfigTestResult:
    try:
        if config["USE_SSL"]:
            server = smtplib.SMTP_SSL(config["SMTP_SERVER"], config["SMTP_PORT"], timeout=30)
        else:
            server = smtplib.SMTP(config["SMTP_SERVER"], config["SMTP_PORT"], timeout=30)
            if config["USE_TLS"]:
                server.starttls()
        
        if DEFAULT_CONFIG["EMAIL_PASSWORD"]:
            server.login(DEFAULT_CONFIG["EMAIL_USER"], DEFAULT_CONFIG["EMAIL_PASSWORD"])
        
        server.quit()
        
        return ConfigTestResult(
            config_name=config["name"],
            success=True,
            message="Configuración exitosa",
            details={
                "server": config["SMTP_SERVER"],
                "port": config["SMTP_PORT"],
                "ssl": config["USE_SSL"],
                "tls": config["USE_TLS"]
            }
        )
        
    except Exception as e:
        return ConfigTestResult(
            config_name=config["name"],
            success=False,
            message=str(e),
            details={
                "server": config["SMTP_SERVER"],
                "port": config["SMTP_PORT"],
                "ssl": config["USE_SSL"],
                "tls": config["USE_TLS"]
            }
        )


async def send_email_with_fallback(email_data: EmailRequest) -> EmailResponse:
    if not DEFAULT_CONFIG["EMAIL_PASSWORD"]:
        return EmailResponse(
            success=False,
            message="EMAIL_PASSWORD no configurado",
            emails_sent=0,
            failed_emails=email_data.to
        )
    
    for config in EMAIL_CONFIGS:
        try:
            logger.info(f"Probando configuración: {config['name']}")
            
            if config["USE_SSL"]:
                server = smtplib.SMTP_SSL(config["SMTP_SERVER"], config["SMTP_PORT"], timeout=30)
            else:
                server = smtplib.SMTP(config["SMTP_SERVER"], config["SMTP_PORT"], timeout=30)
                if config["USE_TLS"]:
                    server.starttls()
            
            server.login(DEFAULT_CONFIG["EMAIL_USER"], DEFAULT_CONFIG["EMAIL_PASSWORD"])
            
            successful_emails = 0
            failed_emails = []
            
            for recipient in email_data.to:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['From'] = email_data.from_email
                    msg['To'] = recipient
                    msg['Subject'] = email_data.subject
                    
                    text_part = MIMEText(email_data.text, 'plain', 'utf-8')
                    msg.attach(text_part)
                    
                    html_part = MIMEText(email_data.html, 'html', 'utf-8')
                    msg.attach(html_part)
                    
                    server.send_message(msg)
                    successful_emails += 1
                    logger.info(f"Correo enviado a: {recipient}")
                    
                except Exception as e:
                    failed_emails.append(recipient)
                    logger.error(f"Error enviando a {recipient}: {str(e)}")
            
            server.quit()
            
            return EmailResponse(
                success=successful_emails > 0,
                message=f"Correos enviados con {config['name']}: {successful_emails}",
                emails_sent=successful_emails,
                failed_emails=failed_emails,
                config_used=config['name']
            )
            
        except Exception as e:
            logger.warning(f"Configuración {config['name']} falló: {str(e)}")
            continue
    
    return EmailResponse(
        success=False,
        message="Todas las configuraciones SMTP fallaron",
        emails_sent=0,
        failed_emails=email_data.to
    )


# Endpoints

@router.get("/test-all-configs")
async def test_all_configurations():
    results = []
    for config in EMAIL_CONFIGS:
        result = await test_smtp_config(config)
        results.append(result)
    return {
        "timestamp": datetime.now().isoformat(),
        "email_user": DEFAULT_CONFIG["EMAIL_USER"],
        "password_configured": bool(DEFAULT_CONFIG["EMAIL_PASSWORD"]),
        "configurations_tested": len(EMAIL_CONFIGS),
        "results": results
    }

@router.post("/send-email", response_model=EmailResponse)
async def send_email_notification(email_request: EmailRequest):
    try:
        logger.info(f"Enviando correo a {len(email_request.to)} destinatarios")
        if not email_request.to:
            raise HTTPException(status_code=400, detail="No se especificaron destinatarios")
        
        result = await send_email_with_fallback(email_request)
        return result
        
    except Exception as e:
        logger.error(f"Error en send_email_notification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.post("/ticket-created", response_model=EmailResponse)
async def notify_ticket_created(notification_data: TicketNotification):
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Notificación de Ticket SSV</title></head>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <div style="background-color: #22c55e; color: white; padding: 30px 20px; text-align: center;">
                    <h1 style="margin: 0;">🎫 Notificación de Ticket</h1>
                </div>
                <div style="padding: 30px;">
                    <h2>📋 Nuevo ticket asignado al departamento</h2>
                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p><strong>Número de Ticket:</strong> #{notification_data.ticket_id}</p>
                        <p><strong>Título:</strong> "{notification_data.title}"</p>
                        <p><strong>Departamento:</strong> {notification_data.assigned_department_id.name}</p>
                        <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    <div style="background-color: #dbeafe; padding: 15px; border-radius: 8px;">
                        <p style="color: #1e40af; margin: 0;">
                            <strong>Acción requerida:</strong> Se ha creado un nuevo ticket. Favor revisar y proceder según corresponda.
                        </p>
                    </div>
                </div>
                <div style="background-color: #f3f4f6; padding: 20px; text-align: center;">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">
                        Sistema de Tickets - SSV<br>Este es un mensaje automático.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        NOTIFICACIÓN DE TICKET - SSV
        ============================
        
        Número de Ticket: #{notification_data.ticket_id}
        Título: "{notification_data.title}"
        Departamento: {notification_data.assigned_department_id}
        Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        
        Se ha creado un nuevo ticket. Favor revisar y proceder según corresponda.
        
        ---
        Sistema de Tickets - SSV
        """
        
        email_request = EmailRequest(
            to=notification_data.recipient_emails,
            subject="🎫 Notificación de Ticket SSV - Nuevo ticket asignado",
            html=html_content,
            text=text_content
        )
        
        result = await send_email_with_fallback(email_request)
        return result
        
    except Exception as e:
        logger.error(f"Error en notify_ticket_created: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "email_user": DEFAULT_CONFIG["EMAIL_USER"],
        "password_configured": bool(DEFAULT_CONFIG["EMAIL_PASSWORD"]),
        "configurations_available": len(EMAIL_CONFIGS)
    }
