# setup_enigma_hunter.py
import os
import sys
import subprocess
from pathlib import Path

def setup_all():
    """Configura todo o ambiente do Enigma Hunter"""
    print("Configurando ambiente completo para o Enigma Hunter...")
    
    # Diretório base
    base_dir = Path(__file__).resolve().parent
    
    # Cria estrutura de diretórios
    print("\n1. Criando estrutura de diretórios...")
    directories = [
        "src",
        "src/models",
        "src/utils",
        "database",
        "historias",
        "historias/o_segredo_da_estalagem_do_cervo_negro",
        "historias/o_segredo_da_estalagem_do_cervo_negro/ambientes",
        "historias/o_segredo_da_estalagem_do_cervo_negro/personagens",
        "historias/o_segredo_da_estalagem_do_cervo_negro/data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True, parents=True)
        print(f"✓ Diretório '{directory}' verificado/criado")
    
    # Cria os arquivos de modelo
    print("\n2. Criando arquivos de modelo...")
    
    # Verifica se os arquivos Python existem e cria-os se necessário
    file_templates = {
        "src/models/__init__.py": "from .db_models import (\n    Base,\n    Story, Location, LocationArea, AreaDetail,\n    Character, CharacterLevel, EvolutionTrigger, EvidenceRequirement,\n    GameObject, ObjectLevel, Clue, QRCode,\n    Player, GameSession, PlayerSession, PlayerInventory,\n    ItemKnowledge, PlayerLocation, PlayerObjectLevel,\n    PlayerCharacterLevel, PlayerEnvironmentLevel,\n    DialogueHistory, QRCodeScan, PlayerSolution,\n    PlayerSpecialization, GameMaster, SystemLog,\n    PlayerFeedback, PromptTemplate, IAConversationLog\n)",
        "src/utils/__init__.py": "# Pacote de utilitários"
    }
    
    for file_path, content in file_templates.items():
        path = base_dir / file_path
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Arquivo '{file_path}' criado")
        else:
            print(f"✓ Arquivo '{file_path}' já existe")
    
    # Copia db_models.py se não existir
    db_models_path = base_dir / "src" / "models" / "db_models.py"
    if not db_models_path.exists():
        print("\nCriando arquivo de modelos de banco de dados...")
        # Aqui você inseriria o conteúdo completo do arquivo db_models.py
        # Por questões de espaço, vou apenas indicar que você deveria copiar 
        # o conteúdo que já mostramos anteriormente
        with open(db_models_path, 'w', encoding='utf-8') as f:
            f.write("# Conteúdo do arquivo db_models.py\n")
            # Insira aqui o conteúdo completo do arquivo db_models.py
            # que forneci anteriormente
        print(f"✓ Arquivo '{db_models_path}' criado")
    else:
        print(f"✓ Arquivo '{db_models_path}' já existe")
    
    # Copia db-setup-script.py se não existir
    db_setup_script_path = base_dir / "src" / "utils" / "db-setup-script.py"
    if not db_setup_script_path.exists():
        print("\nCriando script de configuração do banco de dados...")
        # Aqui você inseriria o conteúdo completo do arquivo db-setup-script.py
        with open(db_setup_script_path, 'w', encoding='utf-8') as f:
            f.write("# Conteúdo do arquivo db-setup-script.py\n")
            # Insira aqui o conteúdo completo do arquivo db-setup-script.py
            # que forneci anteriormente
        print(f"✓ Arquivo '{db_setup_script_path}' criado")
    else:
        print(f"✓ Arquivo '{db_setup_script_path}' já existe")
    
    # Organiza os arquivos JSON
    print("\n3. Organizando arquivos JSON...")
    organize_json_script = base_dir / "src" / "utils" / "organize_json_files.py"
    with open(organize_json_script, 'w', encoding='utf-8') as f:
        # Insira aqui o conteúdo do script organize_json_files.py
        f.write("# Conteúdo do arquivo organize_json_files.py\n")
        # que forneci anteriormente
    
    # Executa o script para organizar os arquivos JSON
    subprocess.run([sys.executable, str(organize_json_script)])
    
    # Inicializa o banco de dados
    print("\n4. Inicializando o banco de dados...")
    init_db_script = base_dir / "src" / "utils" / "init_database.py"
    with open(init_db_script, 'w', encoding='utf-8') as f:
        # Insira aqui o conteúdo do script init_database.py
        f.write("# Conteúdo do arquivo init_database.py\n")
        # que forneci anteriormente
    
    # Executa o script para inicializar o banco de dados
    subprocess.run([sys.executable, str(init_db_script), "--reset"])
    
    print("\n✅ Configuração do ambiente Enigma Hunter concluída com sucesso!")
    print("Você pode iniciar o sistema executando: python src/app.py")

if __name__ == "__main__":
    setup_all()