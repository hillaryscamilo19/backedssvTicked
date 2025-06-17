"""
Configuración de correo electrónico para diferentes proveedores
"""
import os
from typing import Dict, Any

# Configuraciones para diferentes proveedores de correo
EMAIL_PROVIDERS = {
    "gmail": {
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": 465,
        "USE_TLS": True,
        "USE_SSL": False
    },
    "outlook": {
        "SMTP_SERVER": "smtp-mail.outlook.com", 
        "SMTP_PORT": 465,
        "USE_TLS": True,
        "USE_SSL": False
    },
    "yahoo": {
        "SMTP_SERVER": "smtp.mail.yahoo.com",
        "SMTP_PORT": 465,
        "USE_TLS": True,
        "USE_SSL": False
    },
    "custom": {
        "SMTP_SERVER": os.getenv("CUSTOM_SMTP_SERVER", "mail.ssv.com.do"),
        "SMTP_PORT": int(os.getenv("CUSTOM_SMTP_PORT", "465")),
        "USE_TLS": os.getenv("CUSTOM_USE_TLS", "true").lower() == "true",
        "USE_SSL": os.getenv("CUSTOM_USE_SSL", "false").lower() == "true"
    }
}

def get_email_config(provider: str = "custom") -> Dict[str, Any]:
    """
    Obtiene la configuración de correo para el proveedor especificado
    """
    config = EMAIL_PROVIDERS.get(provider, EMAIL_PROVIDERS["custom"])
    
    return {
        **config,
        "EMAIL_USER": os.getenv("EMAIL_USER", "soportetecnico@ssv.com.do"),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD", ""),
        "EMAIL_FROM_NAME": os.getenv("EMAIL_FROM_NAME", "Sistema de Tickets SSV")
    }

# Configuración por defecto
DEFAULT_EMAIL_CONFIG = get_email_config("custom")
