# setup_environment.py
import subprocess
import sys
import os
from pathlib import Path

def setup_environment():
    """Configura o ambiente de desenvolvimento para o Enigma Hunter"""
    print("Configurando ambiente para o Enigma Hunter...")
    
    # Cria a estrutura de diretórios
    directories = [
        "src",
        "src/models",
        "src/utils",
        "database",
        "database/sessions",
        "historias",
        "frontend",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True, parents=True)
        print(f"✓ Diretório '{directory}' verificado/criado")
    
    # Lista de pacotes necessários
    packages = [
        "flask",
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "python-multipart",
        "requests",
        "aiohttp",
        "pytest",
        "qrcode",
        "pillow",
        "pyzbar"  # Para leitura de QR codes
    ]
    
    # Instala os pacotes necessários
    print("\nInstalando pacotes necessários...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ Pacote '{package}' instalado com sucesso")
        except subprocess.CalledProcessError:
            print(f"✗ Erro ao instalar o pacote '{package}'")
    
    print("\nConfiguração do ambiente concluída!")
    print("Para inicializar o banco de dados, execute: python src/utils/db-setup-script.py")

if __name__ == "__main__":
    setup_environment()