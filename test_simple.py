"""
Prueba simple y rápida del correo SSV
"""
import smtplib
from email.mime.text import MIMEText

def test_ssv_email():
    print("🧪 PRUEBA SIMPLE DE CORREO SSV")
    print("=" * 40)
    
    # Configuración
    email_user = "soportetecnico@ssv.com.do"
    email_password = input("Ingresa la contraseña del correo: ")
    
    if not email_password:
        print("❌ No se ingresó contraseña")
        return
    
    # Lista de configuraciones a probar
    configs = [
        {
            "name": "SSL 465 - shared70",
            "server": "shared70.accountservergroup.com",
            "port": 465,
            "use_ssl": True
        },
        {
            "name": "STARTTLS 587 - shared70", 
            "server": "shared70.accountservergroup.com",
            "port": 587,
            "use_ssl": False
        },
        {
            "name": "SSL 465 - mail.ssv",
            "server": "mail.ssv.com.do",
            "port": 465,
            "use_ssl": True
        },
        {
            "name": "STARTTLS 587 - mail.ssv",
            "server": "mail.ssv.com.do", 
            "port": 587,
            "use_ssl": False
        }
    ]
    
    for config in configs:
        print(f"\n🔍 Probando: {config['name']}")
        print(f"   Servidor: {config['server']}:{config['port']}")
        
        try:
            # Establecer conexión
            if config['use_ssl']:
                server = smtplib.SMTP_SSL(config['server'], config['port'], timeout=15)
            else:
                server = smtplib.SMTP(config['server'], config['port'], timeout=15)
                server.starttls()
            
            # Intentar autenticación
            server.login(email_user, email_password)
            
            print(f"   ✅ ÉXITO: {config['name']}")
            
            # Intentar enviar un correo de prueba
            try:
                msg = MIMEText("Prueba de configuración SMTP - SSV")
                msg['Subject'] = "Prueba SMTP SSV"
                msg['From'] = email_user
                msg['To'] = email_user  # Enviar a sí mismo
                
                server.send_message(msg)
                print(f"   📧 Correo de prueba enviado exitosamente")
                
            except Exception as e:
                print(f"   ⚠️  Autenticación OK, pero error enviando: {str(e)}")
            
            server.quit()
            
            # Si llegamos aquí, esta configuración funciona
            print(f"\n🎉 CONFIGURACIÓN EXITOSA: {config['name']}")
            print("   Usa esta configuración en tu .env:")
            print(f"   SMTP_SERVER={config['server']}")
            print(f"   SMTP_PORT={config['port']}")
            print(f"   USE_SSL={'true' if config['use_ssl'] else 'false'}")
            print(f"   USE_TLS={'false' if config['use_ssl'] else 'true'}")
            break
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"   ❌ Error de autenticación: {str(e)}")
        except Exception as e:
            print(f"   ❌ Error de conexión: {str(e)}")
    
    else:
        print("\n❌ NINGUNA CONFIGURACIÓN FUNCIONÓ")
        print("\n💡 Posibles soluciones:")
        print("1. Verificar contraseña en el panel de hosting")
        print("2. Probar login en https://webmail.ssv.com.do")
        print("3. Contactar soporte de hosting para configuración SMTP")
        print("4. Verificar si requiere contraseña de aplicación")

if __name__ == "__main__":
    test_ssv_email()
