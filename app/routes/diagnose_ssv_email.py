"""
Script de diagnóstico completo para el correo SSV
"""
import smtplib
import socket
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

def test_connection_basic():
    """
    Prueba básica de conectividad al servidor
    """
    print("🔍 DIAGNÓSTICO 1: Conectividad básica")
    print("-" * 50)
    
    server = "shared70.accountservergroup.com"
    ports = [465, 587, 25, 993]
    
    for port in ports:
        try:
            print(f"Probando {server}:{port}...")
            sock = socket.create_connection((server, port), timeout=10)
            sock.close()
            print(f"✅ Puerto {port}: ABIERTO")
        except Exception as e:
            print(f"❌ Puerto {port}: CERRADO ({str(e)})")
    
    print()

def test_smtp_ssl_connection():
    """
    Prueba conexión SMTP con SSL
    """
    print("🔍 DIAGNÓSTICO 2: Conexión SMTP SSL")
    print("-" * 50)
    
    server = "shared70.accountservergroup.com"
    port = 465
    
    try:
        print(f"Conectando a {server}:{port} con SSL...")
        smtp_server = smtplib.SMTP_SSL(server, port, timeout=30)
        smtp_server.set_debuglevel(1)  # Mostrar debug completo
        
        print("✅ Conexión SSL establecida")
        
        # Obtener capacidades del servidor
        print("\n📋 Capacidades del servidor:")
        print(smtp_server.ehlo_resp.decode() if smtp_server.ehlo_resp else "No disponible")
        
        smtp_server.quit()
        return True
        
    except Exception as e:
        print(f"❌ Error en conexión SSL: {str(e)}")
        return False

def test_smtp_tls_connection():
    """
    Prueba conexión SMTP con STARTTLS
    """
    print("🔍 DIAGNÓSTICO 3: Conexión SMTP con STARTTLS")
    print("-" * 50)
    
    server = "shared70.accountservergroup.com"
    port = 587
    
    try:
        print(f"Conectando a {server}:{port} con STARTTLS...")
        smtp_server = smtplib.SMTP(server, port, timeout=30)
        smtp_server.set_debuglevel(1)
        
        print("Iniciando STARTTLS...")
        smtp_server.starttls()
        
        print("✅ Conexión STARTTLS establecida")
        
        smtp_server.quit()
        return True
        
    except Exception as e:
        print(f"❌ Error en conexión STARTTLS: {str(e)}")
        return False

def test_authentication_methods():
    """
    Prueba diferentes métodos de autenticación
    """
    print("🔍 DIAGNÓSTICO 4: Métodos de autenticación")
    print("-" * 50)
    
    email_user = os.getenv("EMAIL_USER", "soportetecnico@ssv.com.do")
    email_password = os.getenv("EMAIL_PASSWORD", "")
    
    if not email_password:
        print("❌ EMAIL_PASSWORD no configurado en .env")
        return False
    
    print(f"Usuario: {email_user}")
    print(f"Password: {'*' * len(email_password)}")
    
    # Probar con SSL (puerto 465)
    try:
        print("\n🔐 Probando autenticación SSL (puerto 465)...")
        server = smtplib.SMTP_SSL("shared70.accountservergroup.com", 465, timeout=30)
        server.set_debuglevel(1)
        
        # Intentar login
        server.login(email_user, email_password)
        print("✅ Autenticación SSL exitosa!")
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Error de autenticación SSL: {str(e)}")
        print("💡 Posibles causas:")
        print("   - Contraseña incorrecta")
        print("   - Usuario bloqueado")
        print("   - Requiere autenticación de 2 factores")
        print("   - Configuración de seguridad del servidor")
    except Exception as e:
        print(f"❌ Error SSL: {str(e)}")
    
    # Probar con STARTTLS (puerto 587)
    try:
        print("\n🔐 Probando autenticación STARTTLS (puerto 587)...")
        server = smtplib.SMTP("shared70.accountservergroup.com", 587, timeout=30)
        server.set_debuglevel(1)
        server.starttls()
        
        # Intentar login
        server.login(email_user, email_password)
        print("✅ Autenticación STARTTLS exitosa!")
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Error de autenticación STARTTLS: {str(e)}")
    except Exception as e:
        print(f"❌ Error STARTTLS: {str(e)}")
    
    return False

def test_alternative_servers():
    """
    Prueba servidores alternativos comunes para hosting compartido
    """
    print("🔍 DIAGNÓSTICO 5: Servidores alternativos")
    print("-" * 50)
    
    alternative_servers = [
        ("mail.ssv.com.do", 465),
        ("mail.ssv.com.do", 587),
        ("smtp.ssv.com.do", 465),
        ("smtp.ssv.com.do", 587),
        ("ssv.com.do", 465),
        ("ssv.com.do", 587),
    ]
    
    for server, port in alternative_servers:
        try:
            print(f"Probando {server}:{port}...")
            if port == 465:
                smtp_server = smtplib.SMTP_SSL(server, port, timeout=10)
            else:
                smtp_server = smtplib.SMTP(server, port, timeout=10)
                smtp_server.starttls()
            
            print(f"✅ {server}:{port} - Conexión exitosa")
            smtp_server.quit()
            
        except Exception as e:
            print(f"❌ {server}:{port} - {str(e)}")

def generate_config_suggestions():
    """
    Genera sugerencias de configuración
    """
    print("🔍 DIAGNÓSTICO 6: Sugerencias de configuración")
    print("-" * 50)
    
    print("💡 SUGERENCIAS PARA RESOLVER EL PROBLEMA:")
    print()
    print("1. 🔑 VERIFICAR CREDENCIALES:")
    print("   - Confirmar usuario: soportetecnico@ssv.com.do")
    print("   - Verificar contraseña en el panel de control de hosting")
    print("   - Probar login en webmail: https://webmail.ssv.com.do")
    print()
    print("2. 🛡️ CONFIGURACIÓN DE SEGURIDAD:")
    print("   - Verificar si está habilitado 2FA")
    print("   - Revisar configuración de 'Aplicaciones menos seguras'")
    print("   - Verificar bloqueos por IP")
    print()
    print("3. 🌐 CONFIGURACIONES ALTERNATIVAS:")
    print("   - Probar mail.ssv.com.do en lugar de shared70.accountservergroup.com")
    print("   - Intentar puerto 587 con STARTTLS")
    print("   - Verificar configuración en cPanel/Plesk")
    print()
    print("4. 📞 CONTACTAR SOPORTE:")
    print("   - Contactar al proveedor de hosting")
    print("   - Solicitar configuración SMTP exacta")
    print("   - Verificar estado del servicio de correo")

def main():
    """
    Ejecuta todos los diagnósticos
    """
    print("🏥 DIAGNÓSTICO COMPLETO - CORREO SSV")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Ejecutar todos los diagnósticos
    test_connection_basic()
    test_smtp_ssl_connection()
    test_smtp_tls_connection()
    test_authentication_methods()
    test_alternative_servers()
    generate_config_suggestions()
    
    print("\n" + "=" * 60)
    print("🏁 DIAGNÓSTICO COMPLETADO")
    print("=" * 60)

if __name__ == "__main__":
    main()
