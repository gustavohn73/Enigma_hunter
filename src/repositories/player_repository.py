# src/repositories/player_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import json

from src.models.db_models import Player, PlayerSession, PlayerInventory, PlayerSpecialization
from src.models.db_models import PlayerCharacterLevel, PlayerObjectLevel, PlayerEnvironmentLevel
from src.repositories.base_repository import BaseRepository

class PlayerRepository(BaseRepository[Player]):
    """
    Repositório para operações de banco de dados relacionadas a jogadores.
    Gerencia jogadores, sessões de jogo e progresso relacionado.
    """
    
    def __init__(self):
        super().__init__(Player)
    
    def get_by_id(self, db: Session, player_id: int) -> Optional[Player]:
        """
        Busca um jogador pelo ID.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            
        Returns:
            Jogador encontrado ou None
        """
        return db.query(Player).filter(Player.player_id == player_id).first()
    
    def get_by_username(self, db: Session, username: str) -> Optional[Player]:
        """
        Busca um jogador pelo nome de usuário.
        
        Args:
            db: Sessão do banco de dados
            username: Nome de usuário
            
        Returns:
            Jogador encontrado ou None
        """
        return db.query(Player).filter(Player.username == username).first()
    
    def get_active_sessions(self, db: Session, player_id: int) -> List[PlayerSession]:
        """
        Obtém todas as sessões ativas de um jogador.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            
        Returns:
            Lista de sessões ativas
        """
        return db.query(PlayerSession).filter(
            PlayerSession.player_id == player_id,
            PlayerSession.game_status == 'active'
        ).order_by(PlayerSession.start_time.desc()).all()
    
    def get_latest_session(self, db: Session, player_id: int) -> Optional[PlayerSession]:
        """
        Obtém a sessão mais recente de um jogador.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            
        Returns:
            Sessão mais recente ou None
        """
        return db.query(PlayerSession).filter(
            PlayerSession.player_id == player_id
        ).order_by(PlayerSession.start_time.desc()).first()
    
    def create_session(self, db: Session, player_id: int, game_session_id: int, story_id: int = None) -> PlayerSession:
        """
        Cria uma nova sessão para um jogador.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            game_session_id: ID da sessão de jogo
            story_id: ID da história (opcional)
            
        Returns:
            Nova sessão criada
        """
        session = PlayerSession(
            player_id=player_id,
            game_session_id=game_session_id,
            game_status='active',
            session_data=json.dumps({
                'story_id': story_id,
                'created_at': func.now(),
                'solution_submitted': False,
                'solution_correct': False
            })
        )
        return self.create(db, session)
    
    def close_session(self, db: Session, session_id: int) -> bool:
        """
        Fecha uma sessão de jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            
        Returns:
            True se fechada com sucesso
        """
        session = db.query(PlayerSession).filter(PlayerSession.session_id == session_id).first()
        if not session:
            return False
            
        session.game_status = 'completed'
        self.update(db, session)
        return True
    
    def get_player_inventory(self, db: Session, session_id: int) -> List[PlayerInventory]:
        """
        Obtém o inventário de um jogador em uma sessão específica.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            
        Returns:
            Lista de itens no inventário
        """
        return db.query(PlayerInventory).filter(
            PlayerInventory.session_id == session_id
        ).all()
    
    def add_to_inventory(self, db: Session, session_id: int, object_id: int, 
                        acquisition_method: str = 'discovered') -> PlayerInventory:
        """
        Adiciona um objeto ao inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_id: ID do objeto a adicionar
            acquisition_method: Como o objeto foi adquirido
            
        Returns:
            Novo item do inventário
        """
        # Verifica se o item já está no inventário
        existing_item = db.query(PlayerInventory).filter(
            PlayerInventory.session_id == session_id,
            PlayerInventory.object_id == object_id
        ).first()
        
        if existing_item:
            return existing_item
            
        inventory_item = PlayerInventory(
            session_id=session_id,
            object_id=object_id,
            acquisition_method=acquisition_method
        )
        
        return self.create(db, inventory_item)
    
    def remove_from_inventory(self, db: Session, inventory_id: int) -> bool:
        """
        Remove um item do inventário.
        
        Args:
            db: Sessão do banco de dados
            inventory_id: ID do item no inventário
            
        Returns:
            True se removido com sucesso
        """
        inventory_item = db.query(PlayerInventory).filter(
            PlayerInventory.inventory_id == inventory_id
        ).first()
        
        if not inventory_item:
            return False
            
        return self.delete(db, inventory_item)
    
    def get_player_specializations(self, db: Session, session_id: int) -> List[PlayerSpecialization]:
        """
        Obtém as especializações de um jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            
        Returns:
            Lista de especializações
        """
        return db.query(PlayerSpecialization).filter(
            PlayerSpecialization.session_id == session_id
        ).all()
    
    def update_specialization(self, db: Session, session_id: int, category_id: str, 
                            points: int, level: int = None) -> PlayerSpecialization:
        """
        Atualiza a especialização de um jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            category_id: ID da categoria de especialização
            points: Pontos a adicionar
            level: Nível a definir (opcional)
            
        Returns:
            Especialização atualizada
        """
        specialization = db.query(PlayerSpecialization).filter(
            PlayerSpecialization.session_id == session_id,
            PlayerSpecialization.category_id == category_id
        ).first()
        
        if not specialization:
            specialization = PlayerSpecialization(
                session_id=session_id,
                category_id=category_id,
                points=points,
                level=level or 0
            )
            return self.create(db, specialization)
        
        specialization.points += points
        if level is not None:
            specialization.level = level
            
        return self.update(db, specialization)
    
    def get_character_progress(self, db: Session, session_id: int, character_id: int = None) -> List[PlayerCharacterLevel]:
        """
        Obtém o progresso do jogador com personagens.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem específico (opcional)
            
        Returns:
            Lista de progresso com personagens
        """
        query = db.query(PlayerCharacterLevel).filter(
            PlayerCharacterLevel.session_id == session_id
        )
        
        if character_id is not None:
            query = query.filter(PlayerCharacterLevel.character_id == character_id)
            
        return query.all()
    
    def update_character_progress(self, db: Session, session_id: int, character_id: int, 
                                level: int) -> PlayerCharacterLevel:
        """
        Atualiza o progresso do jogador com um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            level: Novo nível
            
        Returns:
            Progresso atualizado
        """
        progress = db.query(PlayerCharacterLevel).filter(
            PlayerCharacterLevel.session_id == session_id,
            PlayerCharacterLevel.character_id == character_id
        ).first()
        
        if not progress:
            progress = PlayerCharacterLevel(
                session_id=session_id,
                character_id=character_id,
                current_level=level
            )
            return self.create(db, progress)
        
        # Só atualiza se o novo nível for maior
        if level > progress.current_level:
            progress.current_level = level
            progress.last_interaction = func.now()
            
        return self.update(db, progress)
    
    def get_object_progress(self, db: Session, session_id: int, object_id: int = None) -> List[PlayerObjectLevel]:
        """
        Obtém o progresso do jogador com objetos.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_id: ID do objeto específico (opcional)
            
        Returns:
            Lista de progresso com objetos
        """
        query = db.query(PlayerObjectLevel).filter(
            PlayerObjectLevel.session_id == session_id
        )
        
        if object_id is not None:
            query = query.filter(PlayerObjectLevel.object_id == object_id)
            
        return query.all()
    
    def update_object_progress(self, db: Session, session_id: int, object_id: int, 
                            level: int) -> PlayerObjectLevel:
        """
        Atualiza o progresso do jogador com um objeto.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_id: ID do objeto
            level: Novo nível
            
        Returns:
            Progresso atualizado
        """
        progress = db.query(PlayerObjectLevel).filter(
            PlayerObjectLevel.session_id == session_id,
            PlayerObjectLevel.object_id == object_id
        ).first()
        
        if not progress:
            progress = PlayerObjectLevel(
                session_id=session_id,
                object_id=object_id,
                current_level=level
            )
            return self.create(db, progress)
        
        # Só atualiza se o novo nível for maior
        if level > progress.current_level:
            progress.current_level = level
            progress.last_interaction = func.now()
            
        return self.update(db, progress)
    
    def get_environment_progress(self, db: Session, session_id: int, location_id: int = None) -> List[PlayerEnvironmentLevel]:
        """
        Obtém o progresso do jogador com ambientes.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            location_id: ID da localização específica (opcional)
            
        Returns:
            Lista de progresso com ambientes
        """
        query = db.query(PlayerEnvironmentLevel).filter(
            PlayerEnvironmentLevel.session_id == session_id
        )
        
        if location_id is not None:
            query = query.filter(PlayerEnvironmentLevel.location_id == location_id)
            
        return query.all()
    
    def update_environment_progress(self, db: Session, session_id: int, location_id: int, 
                                  level: int) -> PlayerEnvironmentLevel:
        """
        Atualiza o progresso do jogador com um ambiente.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            location_id: ID da localização
            level: Novo nível
            
        Returns:
            Progresso atualizado
        """
        progress = db.query(PlayerEnvironmentLevel).filter(
            PlayerEnvironmentLevel.session_id == session_id,
            PlayerEnvironmentLevel.location_id == location_id
        ).first()
        
        if not progress:
            progress = PlayerEnvironmentLevel(
                session_id=session_id,
                location_id=location_id,
                exploration_level=level
            )
            return self.create(db, progress)
        
        # Só atualiza se o novo nível for maior
        if level > progress.exploration_level:
            progress.exploration_level = level
            progress.last_exploration = func.now()
            
        return self.update(db, progress)
    
    def get_all_progress(self, db: Session, session_id: int) -> Dict[str, Any]:
        """
        Obtém todo o progresso de um jogador em uma sessão.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            
        Returns:
            Dicionário com todo o progresso
        """
        session = db.query(PlayerSession).filter(
            PlayerSession.session_id == session_id
        ).first()
        
        if not session:
            return None
            
        inventory = self.get_player_inventory(db, session_id)
        specializations = self.get_player_specializations(db, session_id)
        character_progress = self.get_character_progress(db, session_id)
        object_progress = self.get_object_progress(db, session_id)
        environment_progress = self.get_environment_progress(db, session_id)
        
        return {
            "session": session,
            "inventory": inventory,
            "specializations": specializations,
            "character_progress": character_progress,
            "object_progress": object_progress,
            "environment_progress": environment_progress
        }