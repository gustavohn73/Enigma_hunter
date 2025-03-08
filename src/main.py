# src/main.py
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Optional
import logging
from pathlib import Path
import sys

# Configurando o path para importações relativas
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Importações de módulos da aplicação
from src.models.db_models import Base, PlayerProgress
from src.repositories.story_repository import StoryRepository
from src.repositories.character_repository import CharacterRepository
from src.repositories.location_repository import LocationRepository
from src.repositories.object_repository import ObjectRepository
from src.repositories.clue_repository import ClueRepository
from src.repositories.qrcode_repository import QRCodeRepository
from src.repositories.player_progress_repository import PlayerProgressRepository
from src.data_loader import DataLoader
from src.qr_code_processor import QRCodeProcessor
from src.managers.character_manager import CharacterManager
from src.utils.init_database import init_database
from src.utils.db_setup_script import DATABASE_DIR

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enigma_hunter")

# Configuração do banco de dados
DATABASE_URL = f'sqlite:///{DATABASE_DIR}/enigma_hunter.db'
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Criação da aplicação FastAPI
app = FastAPI(title="Enigma Hunter API")

# Middleware para CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, defina apenas origens específicas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency para obter uma sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inicialização dos repositórios
def get_repositories(db: Session = Depends(get_db)):
    return {
        "story_repository": StoryRepository(),
        "character_repository": CharacterRepository(),
        "location_repository": LocationRepository(),
        "object_repository": ObjectRepository(),
        "clue_repository": ClueRepository(),
        "qrcode_repository": QRCodeRepository(),
        "player_progress_repository": PlayerProgressRepository()
    }

# Dependency para obter o processador de QR Code
def get_qr_processor(db: Session = Depends(get_db), repos=Depends(get_repositories)):
    return QRCodeProcessor(
        db=db,
        qrcode_repository=repos["qrcode_repository"],
        player_progress_repository=repos["player_progress_repository"],
        location_repository=repos["location_repository"],
        object_repository=repos["object_repository"],
        clue_repository=repos["clue_repository"]
    )

# Dependency para obter o gerenciador de personagens
def get_character_manager(db: Session = Depends(get_db), repos=Depends(get_repositories)):
    return CharacterManager(
        character_repository=repos["character_repository"],
        dialogue_repository=repos.get("dialogue_repository")
    )

# Dependency para obter a sessão do jogador a partir do ID de sessão
def get_player_session(session_id: str, db: Session = Depends(get_db)):
    player_progress = db.query(PlayerProgress).filter(
        PlayerProgress.session_id == session_id
    ).first()
    
    if not player_progress:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return player_progress

# Middleware para captura de exceções
@app.middleware("http")
async def db_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except SQLAlchemyError as e:
        logger.error(f"Erro de banco de dados: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno no banco de dados"}
        )
    except Exception as e:
        logger.error(f"Erro não tratado: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno no servidor"}
        )

# Evento de inicialização da aplicação
@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando aplicação Enigma Hunter")
    try:
        # Inicializa o banco de dados
        init_database(db_url=DATABASE_URL, reset=False)
        # Garante que todas as tabelas estão criadas
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar o banco de dados: {str(e)}")
        # Não lança exceção para permitir que a aplicação inicie mesmo com erros no banco

# Rota para verificar status da API
@app.get("/status")
async def check_status():
    return {"status": "online"}

# Rota para escanear QR codes
@app.post("/api/scan_qr")
async def scan_qr(
    session_id: str,
    qr_uuid: str,
    qr_processor: QRCodeProcessor = Depends(get_qr_processor)
):
    """
    Processa um QR code escaneado pelo jogador.
    
    Args:
        session_id: ID da sessão do jogador
        qr_uuid: UUID do QR code escaneado
        
    Returns:
        Resultado do processamento do QR code
    """
    try:
        result = qr_processor.processar_qr_code(session_id, qr_uuid)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao processar QR code: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao processar QR code")

# Rota para interagir com um personagem
@app.post("/api/interact/character")
async def interact_with_character(
    session_id: str,
    character_id: int,
    message: Optional[str] = None,
    character_manager: CharacterManager = Depends(get_character_manager)
):
    """
    Inicia ou continua uma interação com um personagem.
    
    Args:
        session_id: ID da sessão do jogador
        character_id: ID do personagem
        message: Mensagem opcional do jogador
        
    Returns:
        Resposta do personagem
    """
    try:
        # Se não houver mensagem, inicia a conversa
        if not message:
            result = character_manager.start_conversation(
                session_id=session_id,
                character_id=character_id
            )
        else:
            # Se houver mensagem, processa a resposta
            result = character_manager.send_message(
                session_id=session_id,
                character_id=character_id,
                message=message
            )
            
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("message", "Erro na interação"))
            
        return result
    except Exception as e:
        logger.error(f"Erro ao interagir com personagem: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao interagir com personagem")

# Rota para processar resposta de desafio
@app.post("/api/interact/challenge")
async def process_challenge_response(
    session_id: str,
    character_id: int,
    trigger_id: int,
    response: str,
    evidence_ids: Optional[list[int]] = None,
    character_manager: CharacterManager = Depends(get_character_manager)
):
    """
    Processa a resposta do jogador a um desafio de evolução.
    
    Args:
        session_id: ID da sessão do jogador
        character_id: ID do personagem
        trigger_id: ID do gatilho
        response: Resposta do jogador
        evidence_ids: IDs de evidências apresentadas
        
    Returns:
        Resultado do processamento do desafio
    """
    try:
        result = character_manager.process_challenge_response(
            session_id=session_id,
            character_id=character_id,
            trigger_id=trigger_id,
            response=response,
            evidence_ids=evidence_ids
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("message", "Erro ao processar desafio"))
            
        return result
    except Exception as e:
        logger.error(f"Erro ao processar desafio: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao processar desafio")

# Rota para obter o progresso do jogador
@app.get("/api/player/progress")
async def get_player_progress(
    session_id: str, 
    db: Session = Depends(get_db),
    repos=Depends(get_repositories)
):
    """
    Retorna o estado atual do progresso do jogador.
    
    Args:
        session_id: ID da sessão do jogador
        
    Returns:
        Progresso completo do jogador
    """
    try:
        player_progress = repos["player_progress_repository"].get_by_session_id(db, session_id)
        
        if not player_progress:
            raise HTTPException(status_code=404, detail="Progresso não encontrado")
        
        return {
            "success": True, 
            "progress": repos["player_progress_repository"].get_progress_summary(db, session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter progresso do jogador: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao obter progresso do jogador")

# Rota para criar novo jogador
@app.post("/api/player/create")
async def create_player(
    player_name: str, 
    story_id: int,
    db: Session = Depends(get_db),
    repos=Depends(get_repositories)
):
    """
    Cria um novo jogador e inicia uma sessão.
    
    Args:
        player_name: Nome do jogador
        story_id: ID da história a ser jogada
        
    Returns:
        Informações da sessão criada
    """
    try:
        # Verificar se a história existe
        story = repos["story_repository"].get_by_id(db, story_id)
        if not story:
            raise HTTPException(status_code=404, detail="História não encontrada")
        
        # Cria o jogador e a sessão inicial
        player_uuid = repos["player_progress_repository"].create_player_session(
            db, player_name, story_id
        )
        
        if not player_uuid:
            raise HTTPException(status_code=500, detail="Falha ao criar jogador")
        
        # Obtém a localização inicial
        starting_location = repos["story_repository"].get_starting_location(db, story_id)
        
        # Inicializa o progresso do jogador na localização inicial
        if starting_location:
            repos["player_progress_repository"].discover_location(
                db, player_uuid, starting_location
            )
        
        return {
            "success": True,
            "player_uuid": player_uuid,
            "player_name": player_name,
            "story_id": story_id,
            "session_id": player_uuid,  # Por simplicidade, usando mesmo ID
            "starting_location": starting_location
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar jogador: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao criar jogador")

# Execução direta para teste/desenvolvimento
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)