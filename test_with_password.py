"""
Prueba automática con la contraseña configurada
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_ssv_with_credentials():
    print("🧪 PRUEBA AUTOMÁTICA CON CREDENCIALES SSV")
    print("=" * 45)
    
    # Credenciales
    email_user = "soportetecnico@ssv.com.do"
    email_password = ")*N+}Ndfu.~A"
    
    print(f"Usuario: {email_user}")
    print(f"Password: {'*' * len(email_password)}")
    print()
    
    # Configuraciones a probar
    configs = [
        {
            "name": "🔒 SSL 465 - shared70.accountservergroup.com",
            "server": "shared70.accountservergroup.com",
            "port": 465,
            "use_ssl": True,
            "use_tls": False
        },
        {
            "name": "🔐 STARTTLS 587 - shared70.accountservergroup.com", 
            "server": "shared70.accountservergroup.com",
            "port": 587,
            "use_ssl": False,
            "use_tls": True
        },
        {
            "name": "🔒 SSL 465 - mail.ssv.com.do",
            "server": "mail.ssv.com.do",
            "port": 465,
            "use_ssl": True,
            "use_tls": False
        },
        {
            "name": "🔐 STARTTLS 587 - mail.ssv.com.do",
            "server": "mail.ssv.com.do", 
            "port": 587,
            "use_ssl": False,
            "use_tls": True
        }
    ]
    
    successful_config = None
    
    for i, config in enumerate(configs, 1):
        print(f"🔍 PRUEBA {i}/4: {config['name']}")
        print(f"   📡 Servidor: {config['server']}:{config['port']}")
        
        try:
            # Establecer conexión
            if config['use_ssl']:
                print("   🔌 Conectando con SSL...")
                server = smtplib.SMTP_SSL(config['server'], config['port'], timeout=20)
            else:
                print("   🔌 Conectando con SMTP...")
                server = smtplib.SMTP(config['server'], config['port'], timeout=20)
                if config['use_tls']:
                    print("   🔐 Iniciando STARTTLS...")
                    server.starttls()
            
            print("   🔑 Autenticando...")
            server.login(email_user, email_password)
            
            print("   ✅ AUTENTICACIÓN EXITOSA!")
            
            # Intentar enviar correo de prueba
            try:
                print("   📧 Enviando correo de prueba...")
                
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"✅ Prueba SMTP SSV - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                msg['From'] = email_user
                msg['To'] = email_user
                
                text_content = f"""
PRUEBA DE CONFIGURACIÓN SMTP - SSV
==================================

Configuración exitosa:
- Servidor: {config['server']}
- Puerto: {config['port']}
- SSL: {config['use_ssl']}
- STARTTLS: {config['use_tls']}

Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

¡El sistema de notificaciones está funcionando correctamente!
                """
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Prueba SMTP SSV</title>
                </head>
                <body style="font-family: Arial, sans-serif; background-color: #f0f9ff;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden;">
                        <div style="background-color: #22c55e; color: white; padding: 20px; text-align: center;">
                            <h1 style="margin: 0;">✅ Prueba SMTP Exitosa</h1>
                        </div>
                        <div style="padding: 30px;">
                            <h2>🎉 Configuración Funcionando</h2>
                            <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin: 15px 0;">
                                <p><strong>Servidor:</strong> {config['server']}</p>
                                <p><strong>Puerto:</strong> {config['port']}</p>
                                <p><strong>SSL:</strong> {config['use_ssl']}</p>
                                <p><strong>STARTTLS:</strong> {config['use_tls']}</p>
                                <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                            </div>
                            <div style="background-color: #dcfce7; padding: 15px; border-radius: 6px; border-left: 4px solid #22c55e;">
                                <p style="margin: 0; color: #166534;">
                                    <strong>¡Éxito!</strong> El sistema de notificaciones está funcionando correctamente.
                                </p>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                html_part = MIMEText(html_content, 'html', 'utf-8')
                
                msg.attach(text_part)
                msg.attach(html_part)
                
                server.send_message(msg)
                print("   📬 CORREO ENVIADO EXITOSAMENTE!")
                
            except Exception as e:
                print(f"   ⚠️  Autenticación OK, pero error enviando correo: {str(e)}")
            
            server.quit()
            successful_config = config
            
            print(f"\n🎉 CONFIGURACIÓN EXITOSA ENCONTRADA!")
            print(f"   {config['name']}")
            break
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"   ❌ Error de autenticación: {str(e)}")
            if "535" in str(e):
                print("   💡 Error 535: Credenciales incorrectas o cuenta bloqueada")
        except Exception as e:
            print(f"   ❌ Error de conexión: {str(e)}")
        
        print()
    
    # Resultado final
    print("=" * 45)
    if successful_config:
        print("🎊 RESULTADO: CONFIGURACIÓN ENCONTRADA")
        print("=" * 45)
        print(f"✅ Usar: {successful_config['name']}")
        print()
        print("📝 Configuración para .env:")
        print(f"SMTP_SERVER={successful_config['server']}")
        print(f"SMTP_PORT={successful_config['port']}")
        print(f"USE_SSL={'true' if successful_config['use_ssl'] else 'false'}")
        print(f"USE_TLS={'true' if successful_config['use_tls'] else 'false'}")
        print()
        print("🚀 El sistema de notificaciones está listo para usar!")
        
    else:
        print("❌ RESULTADO: NINGUNA CONFIGURACIÓN FUNCIONÓ")
        print("=" * 45)
        print("💡 Posibles soluciones:")
        print("1. Verificar que la cuenta de correo esté activa")
        print("2. Revisar configuración en el panel de hosting")
        print("3. Contactar soporte técnico del hosting")
        print("4. Verificar si requiere configuración especial")

if __name__ == "__main__":
    test_ssv_with_credentials()
