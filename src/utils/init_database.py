# Conteúdo do arquivo init_database.py
# src/utils/init_database.py
import os
import sys
import argparse
from pathlib import Path
from src.utils.db_setup_script import main

# Garante que src esteja no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

def create_directory_structure():
    """Cria a estrutura de diretórios necessária"""
    print("Criando estrutura de diretórios...")
    
    directories = [
        "src",
        "src/models",
        "src/utils",
        "database",
        "historias/o_segredo_da_estalagem_do_cervo_negro",
        "historias/o_segredo_da_estalagem_do_cervo_negro/ambientes",
        "historias/o_segredo_da_estalagem_do_cervo_negro/personagens",
        "historias/o_segredo_da_estalagem_do_cervo_negro/data",
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Diretório '{directory}' verificado/criado")

def init_database():
    """Inicializa o banco de dados do Enigma Hunter e carrega os dados JSON"""
    print("Inicializando banco de dados do Enigma Hunter...")
    
    # Criar estrutura de diretórios
    create_directory_structure()
    
    # Pasta de banco de dados
    db_dir = Path("database")
    db_dir.mkdir(exist_ok=True)
    
    # Verifica se o script db_setup_script.py existe
    setup_script = Path("src/utils/db_setup_script.py")
    if not setup_script.exists():
        print(f"Erro: Script {setup_script} não encontrado!")
        return
    
    # Define os argumentos
    parser = argparse.ArgumentParser(description='Inicializar banco de dados do Enigma Hunter')
    parser.add_argument('--reset', action='store_true', help='Resetar banco de dados existente')
    parser.add_argument('--story-dir', default='historias/o_segredo_da_estalagem_do_cervo_negro', 
                        help='Diretório da história para carregar (padrão: historias/o_segredo_da_estalagem_do_cervo_negro)')
    args = parser.parse_args()
    
    # Verifica se o diretório da história existe
    story_dir = Path(args.story_dir)
    if not story_dir.exists():
        print(f"Aviso: Diretório de história {story_dir} não encontrado!")
        create_dir = input("Deseja criar este diretório? (s/n): ")
        if create_dir.lower() == 's':
            story_dir.mkdir(exist_ok=True, parents=True)
            print(f"Diretório {story_dir} criado. Por favor, adicione os arquivos JSON da história neste diretório.")
            return
    # Monta o comando
    cmd = [sys.executable, str(setup_script)]
    if args.reset:
        cmd.append("--reset")
    cmd.extend(["--story-dir", str(story_dir)])
    
    # Executa o script de setup
    print("\nExecutando script de inicialização do banco de dados...")
    main(db_url=f'sqlite:///{db_dir}/enigma_hunter.db', story_dir=str(story_dir), reset=args.reset)

    print("\nInicialização do banco de dados e carregamento de dados JSON concluídos!")
    print(f"Dados carregados do diretório: {story_dir}")

if __name__ == "__main__":
    init_database()