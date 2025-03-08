from pathlib import Path

# Obter caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurar caminho do banco de dados
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR}/enigma_hunter.db"

# Configurar caminho das histórias
STORY_DIR = BASE_DIR / "historias"