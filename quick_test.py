"""
Prueba ultra rápida - solo conectividad
"""
import socket
import smtplib

def quick_connectivity_test():
    print("⚡ PRUEBA RÁPIDA DE CONECTIVIDAD")
    print("=" * 35)
    
    servers_to_test = [
        ("shared70.accountservergroup.com", 465),
        ("shared70.accountservergroup.com", 587),
        ("mail.ssv.com.do", 465),
        ("mail.ssv.com.do", 587),
        ("smtp.ssv.com.do", 465),
        ("smtp.ssv.com.do", 587)
    ]
    
    working_servers = []
    
    for server, port in servers_to_test:
        try:
            print(f"🔍 {server}:{port}... ", end="")
            
            # Prueba de socket básica
            sock = socket.create_connection((server, port), timeout=5)
            sock.close()
            
            # Prueba SMTP básica
            if port == 465:
                smtp = smtplib.SMTP_SSL(server, port, timeout=10)
            else:
                smtp = smtplib.SMTP(server, port, timeout=10)
                smtp.starttls()
            
            smtp.quit()
            print("✅ OK")
            working_servers.append((server, port))
            
        except Exception as e:
            print(f"❌ {str(e)[:30]}...")
    
    print(f"\n📊 RESULTADO:")
    if working_servers:
        print(f"✅ {len(working_servers)} servidores disponibles:")
        for server, port in working_servers:
            print(f"   - {server}:{port}")
        
        print(f"\n💡 Prueba autenticación con:")
        print(f"python test_simple.py")
    else:
        print("❌ No hay servidores disponibles")
        print("💡 Verifica tu conexión a internet")

if __name__ == "__main__":
    quick_connectivity_test()
