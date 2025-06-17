#!/usr/bin/env python3
"""
Health check script para verificar se o serviço está operacional.
Usado pelo Dockerfile e pode ser executado manualmente.
"""
import sys
import requests
import os


def check_health(host="localhost", port=8080):
    """
    Verifica o health endpoint do serviço.
    
    Args:
        host: Host do serviço
        port: Porta do serviço
        
    Returns:
        0 se saudável, 1 se não saudável
    """
    url = f"http://{host}:{port}/health"
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print(f"✓ Service is healthy: {data}")
                return 0
            else:
                print(f"✗ Service unhealthy: {data}")
                return 1
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            return 1
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to service at {url}")
        return 1
    except requests.exceptions.Timeout:
        print(f"✗ Health check timeout")
        return 1
    except Exception as e:
        print(f"✗ Health check error: {e}")
        return 1


if __name__ == "__main__":
    # Permite override via variáveis de ambiente
    host = os.getenv("HEALTH_CHECK_HOST", "localhost")
    port = int(os.getenv("PORT", "8080"))
    
    exit_code = check_health(host, port)
    sys.exit(exit_code)