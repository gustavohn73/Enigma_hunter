# src/main.py
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.models.db_models import Base, PlayerProgress
from src.session_manager import get_db, get_player_session
from src.data_loader import DataLoader
from src.qr_code_processor import QRCodeProcessor
from src.gerenciador_personagens import GerenciadorPersonagens
from typing import Dict
from src.utils.init_database import init_database
from src.utils.db_setup_script import DATABASE_DIR
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))


# Configurações do banco de dados (ajuste conforme necessário)
DATABASE_URL = f'sqlite:///{DATABASE_DIR}/enigma_hunter.db'
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# Inicializa o banco de dados e carrega dados estáticos
@app.on_event("startup")
async def startup_event():
    init_database(db_url=DATABASE_URL, reset=True)  # Chamada da função init_database
    Base.metadata.create_all(bind=engine) # Cria as tabelas no banco de dados


# Dependency para obter uma sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

# Inicializa o banco de dados e carrega dados estáticos
@app.on_event("startup")
async def startup_event():
    init_database(db_url=f'sqlite:///{DATABASE_DIR}/enigma_hunter.db', reset=True)  # Chamada da função init_database

def on_startup():
    db_file = "database/enigma_hunter.db"
    if not os.path.exists(db_file):
        create_database(db_file)
    global data_loader
    data_loader = DataLoader()
    data_loader.load_all_data()

# Rota para ler QR codes
@app.post("/scan_qr/")
async def scan_qr(qr_code_data: str, db: Session = Depends(get_db), player_session: Dict = Depends(get_player_session)):
    """
    Processa um QR code escaneado pelo jogador.
    """
    player_id = player_session["player_id"]
    if not player_id:
        raise HTTPException(status_code=400, detail="Player ID is missing in the session.")
    
    qr_processor = QRCodeProcessor(db, data_loader, player_id)
    try:
        result = qr_processor.process_qr_code(qr_code_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result

# Rota para interagir com um personagem
@app.post("/interact_with_character/")
async def interact_with_character(character_id: int, db: Session = Depends(get_db), player_session: Dict = Depends(get_player_session)):
    """
    Inicia ou continua uma interação com um personagem específico.
    """
    player_id = player_session["player_id"]
    if not player_id:
        raise HTTPException(status_code=400, detail="Player ID is missing in the session.")
    
    character_manager = GerenciadorPersonagens(db, data_loader, player_id)
    try:
        response = character_manager.interact_with_character(character_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"response": response}

@app.get("/get_player_progress/")
async def get_player_progress(player_session: Dict = Depends(get_player_session), db: Session = Depends(get_db)):
    """
    Retorna o estado atual do progresso do jogador.
    """
    player_id = player_session["player_id"]
    if not player_id:
        raise HTTPException(status_code=400, detail="Player ID is missing in the session.")

    player = db.query(PlayerProgress).filter_by(player_id=player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player progress not found.")
    
    return player.to_dict()


#Rota para criar jogador
@app.post("/create_player/")
async def create_player(player_name: str, db: Session = Depends(get_db)):
    """Cria um novo jogador."""
    new_player = PlayerProgress(player_name=player_name)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player.to_dict()
