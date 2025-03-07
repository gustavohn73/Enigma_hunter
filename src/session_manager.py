# src/session_manager.py
import os
import uuid
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.repositories.story_repository import StoryRepository
from src.repositories.player_repository import PlayerRepository
from src.repositories.character_repository import CharacterRepository
from src.repositories.location_repository import LocationRepository
from src.repositories.clue_repository import ClueRepository
from src.repositories.object_repository import ObjectRepository
from src.models.db_models import PlayerSession, PlayerProgress, PlayerCharacterLevel, PlayerObjectLevel, PlayerEnvironmentLevel, PlayerInventory, PlayerSpecialization, PlayerDiscoveredClues, PlayerSolution

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Gerenciador de sessões e estado de jogo para o Enigma Hunter.
    
    Esta classe integra e coordena os diferentes componentes do jogo,
    gerenciando o ciclo de vida completo de uma sessão de jogo.
    """
    
    def __init__(
        self,
        db: Session,
        story_repository: StoryRepository,
        player_repository: PlayerRepository,
        character_repository: CharacterRepository,
        location_repository: LocationRepository,
        clue_repository: ClueRepository,
        object_repository: ObjectRepository,
        storage_dir: str = "database/sessions"
    ):
        """
        Inicializa o gerenciador de sessões.
        
        Args:
            db: Sessão do banco de dados
            story_repository: Repositório para acesso a histórias
            player_repository: Repositório para acesso a jogadores
            character_repository: Repositório para acesso a personagens
            location_repository: Repositório para acesso a localizações
            clue_repository: Repositório para acesso a pistas
            object_repository: Repositório para acesso a objetos
            storage_dir: Diretório para armazenamento das sessões
        """
        self.db = db
        self.story_repository = story_repository
        self.player_repository = player_repository
        self.character_repository = character_repository
        self.location_repository = location_repository
        self.clue_repository = clue_repository
        self.object_repository = object_repository
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        
        self.active_sessions = {}
        
        self.logger = logger
        
        # Configuração do logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        self.logger.info("SessionManager inicializado.")
        
    def create_session(self, player_id: str, story_id: int) -> Dict[str, Any]:
        """
        Cria uma nova sessão de jogo para um jogador.
        
        Args:
            player_id: ID único do jogador
            story_id: ID da história/caso a ser jogado
            
        Returns:
            Dicionário com dados da sessão criada
        """
        try:
            # Verifica se a história existe
            story = self.story_repository.get_by_id(self.db, story_id)
            if not story:
                self.logger.error(f"História {story_id} não encontrada. Não foi possível criar sessão.")
                return {"success": False, "error": "História não encontrada"}
            
            # Cria a sessão
            session_id = str(uuid.uuid4())
            
            # Cria a nova sessão no banco de dados
            player_session = PlayerSession(
                session_id=session_id,
                player_id=player_id,
                story_id=story_id,
                start_time=datetime.now(),
                last_activity=datetime.now(),
                game_status='active',
                solution_submitted=False
            )
            
            self.db.add(player_session)
            self.db.commit()
            
            # Inicializa o progresso do jogador
            self._initialize_player_progress(session_id, player_id, story_id)
            
            # Cria entrada de metadados apenas para controle em memória
            session_meta = {
                "session_id": session_id,
                "player_id": player_id,
                "story_id": story_id,
                "created_at": time.time(),
                "last_activity": time.time(),
                "status": "active"
            }
            
            # Armazena na lista de sessões ativas em memória
            self.active_sessions[session_id] = session_meta
            
            self.logger.info(f"Sessão {session_id} criada para jogador {player_id}, história {story_id}")
            
            # Obtém a localização inicial
            starting_location = self._get_starting_location(story_id)
            
            return {
                "success": True,
                "session_id": session_id,
                "created_at": time.time(),
                "initial_location": starting_location
            }
        except Exception as e:
            self.logger.error(f"Erro ao criar sessão: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": f"Erro ao criar sessão: {str(e)}"}
        
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """
        Carrega uma sessão existente.
        
        Args:
            session_id: ID da sessão a ser carregada
            
        Returns:
            Dicionário com dados da sessão carregada ou erro
        """
        try:
            # Verifica se a sessão já está ativa em memória
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["last_activity"] = time.time()
                return {
                    "success": True,
                    "session_id": session_id,
                    "session_data": self.active_sessions[session_id]
                }
            
            # Tenta carregar a sessão do banco de dados
            session = self.db.query(PlayerSession).filter(
                PlayerSession.session_id == session_id
            ).first()
            
            if not session:
                self.logger.warning(f"Sessão {session_id} não encontrada.")
                return {"success": False, "error": "Sessão não encontrada"}
            
            # Atualiza o timestamp de última atividade
            session.last_activity = datetime.now()
            self.db.commit()
            
            # Recria os metadados em memória
            session_meta = {
                "session_id": session_id,
                "player_id": session.player_id,
                "story_id": session.story_id,
                "created_at": session.start_time,
                "last_activity": time.time(),
                "status": session.game_status
            }
            
            # Armazena na lista de sessões ativas
            self.active_sessions[session_id] = session_meta
            
            self.logger.info(f"Sessão {session_id} carregada com sucesso.")
            
            return {
                "success": True,
                "session_id": session_id,
                "session_data": session_meta
            }
        except Exception as e:
            self.logger.error(f"Erro ao carregar sessão: {str(e)}")
            return {"success": False, "error": f"Erro ao carregar sessão: {str(e)}"}
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém o estado atual de uma sessão de jogo.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Estado completo da sessão
        """
        try:
            # Carrega a sessão se não estiver ativa
            if session_id not in self.active_sessions:
                result = self.load_session(session_id)
                if not result["success"]:
                    return {"success": False, "error": "Sessão não encontrada"}
            
            # Obtém o progresso do jogador
            progress = self.db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if not progress:
                return {"success": False, "error": "Progresso não encontrado"}
            
            # Atualiza timestamp de atividade em memória
            self.active_sessions[session_id]["last_activity"] = time.time()
            
            # Constrói o estado completo a partir das tabelas relacionadas
            state = self._build_session_state_from_db(session_id)
            
            return {
                "success": True,
                "session_id": session_id,
                "state": state
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter estado da sessão: {str(e)}")
            return {"success": False, "error": f"Erro ao obter estado da sessão: {str(e)}"}
    
    def update_session_state(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza o estado de uma sessão com base nas ações do jogador.
        
        Args:
            session_id: ID da sessão
            updates: Dicionário com atualizações a serem aplicadas
            
        Returns:
            Estado atualizado da sessão
        """
        try:
            # Carrega o progresso principal
            progress = self.db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if not progress:
                return {"success": False, "error": "Progresso não encontrado"}
            
            # Atualiza o timestamp de última atividade
            session = self.db.query(PlayerSession).filter(
                PlayerSession.session_id == session_id
            ).first()
            
            if session:
                session.last_activity = datetime.now()
            
            # Processa cada tipo de atualização diretamente nas tabelas apropriadas
            for update_type, update_data in updates.items():
                if update_type == "location":
                    location_id = update_data.get("location_id")
                    if location_id:
                        # Atualiza a localização atual no progresso principal
                        progress.current_location_id = location_id
                        progress.current_area_id = None  # Reset da área atual
                        
                        # Registra a descoberta na tabela de progresso de ambiente
                        env_progress = self.db.query(PlayerEnvironmentLevel).filter(
                            PlayerEnvironmentLevel.session_id == session_id,
                            PlayerEnvironmentLevel.location_id == location_id
                        ).first()
                        
                        if not env_progress:
                            # Cria um novo registro de progresso para esta localização
                            env_progress = PlayerEnvironmentLevel(
                                session_id=session_id,
                                location_id=location_id,
                                exploration_level=1,
                                last_exploration=datetime.now()
                            )
                            self.db.add(env_progress)
                
                elif update_type == "area":
                    area_id = update_data.get("area_id")
                    if area_id:
                        # Atualiza a área atual no progresso principal
                        progress.current_area_id = area_id
                        
                        # Adiciona à lista de áreas descobertas (em tabela específica ou através de relação)
                        # Implementação depende da estrutura exata do banco de dados
                
                elif update_type == "collect_object":
                    object_id = update_data.get("object_id")
                    if object_id:
                        # Verifica se o objeto já está no inventário
                        existing_item = self.db.query(PlayerInventory).filter(
                            PlayerInventory.session_id == session_id,
                            PlayerInventory.object_id == object_id
                        ).first()
                        
                        if not existing_item:
                            # Adiciona ao inventário
                            inventory_item = PlayerInventory(
                                session_id=session_id,
                                object_id=object_id,
                                acquisition_method=update_data.get("method", "discovered"),
                                acquired_time=datetime.now()
                            )
                            self.db.add(inventory_item)
                
                elif update_type == "discover_clue":
                    clue_id = update_data.get("clue_id")
                    if clue_id:
                        # Verifica se a pista já foi descoberta
                        existing_clue = self.db.query(PlayerDiscoveredClues).filter(
                            PlayerDiscoveredClues.session_id == session_id,
                            PlayerDiscoveredClues.clue_id == clue_id
                        ).first()
                        
                        if not existing_clue:
                            # Registra a descoberta
                            clue_discovery = PlayerDiscoveredClues(
                                session_id=session_id,
                                clue_id=clue_id,
                                discovery_time=datetime.now(),
                                discovery_method=update_data.get("method", "exploration")
                            )
                            self.db.add(clue_discovery)
                
                elif update_type == "character_level":
                    character_id = update_data.get("character_id")
                    level = update_data.get("level")
                    if character_id and level:
                        # Atualiza o nível do personagem
                        self._update_character_level(session_id, character_id, level)
                
                elif update_type == "object_level":
                    object_id = update_data.get("object_id")
                    level = update_data.get("level")
                    if object_id and level:
                        # Atualiza o nível do objeto
                        self._update_object_level(session_id, object_id, level)
                
                elif update_type == "specialization":
                    category_id = update_data.get("category_id")
                    points = update_data.get("points")
                    if category_id and points:
                        # Atualiza especialização
                        self._update_specialization(
                            session_id, 
                            category_id, 
                            points, 
                            update_data.get("interaction_type"),
                            update_data.get("interaction_id")
                        )
            
            # Salva todas as alterações
            self.db.commit()
            
            # Atualiza metadata em memória
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["last_activity"] = time.time()
            
            # Retorna o estado atualizado
            return self.get_session_state(session_id)
        
        except Exception as e:
            self.logger.error(f"Erro ao atualizar estado da sessão: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": f"Erro ao atualizar estado da sessão: {str(e)}"}
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """
        Fecha uma sessão de jogo.
        
        Args:
            session_id: ID da sessão a ser fechada
            
        Returns:
            Status da operação
        """
        try:
            # Busca a sessão no banco de dados
            session = self.db.query(PlayerSession).filter(
                PlayerSession.session_id == session_id
            ).first()
            
            if not session:
                return {"success": False, "error": "Sessão não encontrada"}
            
            # Marca a sessão como completada
            session.game_status = 'completed'
            
            # Salva as alterações
            self.db.commit()
            
            # Remove da lista de sessões ativas em memória
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            self.logger.info(f"Sessão {session_id} fechada com sucesso.")
            
            return {"success": True, "message": "Sessão fechada com sucesso"}
        except Exception as e:
            self.logger.error(f"Erro ao fechar sessão: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": f"Erro ao fechar sessão: {str(e)}"}
    
    def list_player_sessions(self, player_id: str) -> Dict[str, Any]:
        """
        Lista todas as sessões de um jogador.
        
        Args:
            player_id: ID do jogador
            
        Returns:
            Lista de sessões do jogador
        """
        try:
            # Obtém todas as sessões do jogador do banco de dados
            sessions = self.db.query(PlayerSession).filter(
                PlayerSession.player_id == player_id
            ).all()
            
            result = []
            for session in sessions:
                # Converte para o formato de resposta
                session_data = {
                    "session_id": session.session_id,
                    "player_id": session.player_id,
                    "story_id": session.story_id,
                    "created_at": session.start_time,
                    "last_activity": session.last_activity,
                    "status": session.game_status,
                    "solution_submitted": session.solution_submitted
                }
                
                # Se a sessão estiver ativa em memória, utiliza o timestamp mais recente
                if session.session_id in self.active_sessions:
                    session_data["last_activity_timestamp"] = self.active_sessions[session.session_id]["last_activity"]
                
                result.append(session_data)
            
            return {
                "success": True,
                "player_id": player_id,
                "sessions": result
            }
        except Exception as e:
            self.logger.error(f"Erro ao listar sessões do jogador: {str(e)}")
            return {"success": False, "error": f"Erro ao listar sessões: {str(e)}"}
    
    def clean_inactive_sessions(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Limpa sessões inativas da memória.
        
        Args:
            max_age_hours: Idade máxima em horas para manter sessões inativas
            
        Returns:
            Resultado da operação
        """
        try:
            now = time.time()
            max_age_seconds = max_age_hours * 3600
            
            sessions_to_remove = []
            for session_id, meta in self.active_sessions.items():
                if now - meta["last_activity"] > max_age_seconds:
                    sessions_to_remove.append(session_id)
            
            # Remove as sessões inativas da memória
            for session_id in sessions_to_remove:
                del self.active_sessions[session_id]
                
            self.logger.info(f"Removidas {len(sessions_to_remove)} sessões inativas da memória.")
            
            return {
                "success": True,
                "removed_count": len(sessions_to_remove),
                "remaining_count": len(self.active_sessions)
            }
        except Exception as e:
            self.logger.error(f"Erro ao limpar sessões inativas: {str(e)}")
            return {"success": False, "error": f"Erro ao limpar sessões: {str(e)}"}
    
    def submit_solution(self, session_id: str, solution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submete uma solução para o mistério.
        
        Args:
            session_id: ID da sessão
            solution_data: Dados da solução (culpado, método, motivo, evidências)
            
        Returns:
            Resultado da verificação da solução
        """
        try:
            # Busca a sessão no banco
            session = self.db.query(PlayerSession).filter(
                PlayerSession.session_id == session_id
            ).first()
            
            if not session:
                return {"success": False, "error": "Sessão não encontrada"}
            
            # Busca o progresso do jogador
            progress = self.db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if not progress:
                return {"success": False, "error": "Progresso não encontrado"}
            
            # Obtém a história
            story = self.story_repository.get_by_id(self.db, session.story_id)
            if not story:
                return {"success": False, "error": "História não encontrada"}
            
            # Obtém os critérios de solução
            solution_criteria = self.story_repository.get_story_solution_criteria(self.db, session.story_id)
            
            if not solution_criteria:
                self.logger.error(f"Critérios de solução não encontrados para história {session.story_id}")
                return {"success": False, "error": "Critérios de solução não encontrados"}
            
            # Verifica a solução
            is_correct, details = self._verify_solution(solution_data, solution_criteria)
            
            # Registra a solução no banco de dados
            player_solution = PlayerSolution(
                session_id=session_id,
                accused_character_id=solution_data.get("culprit_id"),
                method_description=solution_data.get("method"),
                motive_explanation=solution_data.get("motive"),
                supporting_evidence=str(solution_data.get("evidences", [])),
                is_correct=is_correct,
                submitted_time=datetime.now(),
                feedback=self._generate_solution_feedback(is_correct, details)
            )
            
            self.db.add(player_solution)
            
            # Atualiza o status da sessão
            session.solution_submitted = True
            
            self.db.commit()
            
            # Gera feedback
            feedback = self._generate_solution_feedback(is_correct, details)
            
            result = {
                "success": True,
                "session_id": session_id,
                "is_correct": is_correct,
                "feedback": feedback,
                "details": details
            }
            
            if is_correct:
                # Adiciona a conclusão da história para solução correta
                result["conclusion"] = story.conclusion
                self.logger.info(f"Solução correta submetida para sessão {session_id}!")
            else:
                self.logger.info(f"Solução incorreta submetida para sessão {session_id}")
                
            return result
        except Exception as e:
            self.logger.error(f"Erro ao submeter solução: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": f"Erro ao submeter solução: {str(e)}"}
    
    def get_available_hints(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém dicas disponíveis para o jogador com base no progresso atual.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Lista de dicas disponíveis
        """
        try:
            # Obtém dados diretamente do banco de dados para gerar dicas personalizadas
            
            # Progresso básico
            progress = self.db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if not progress:
                return {"success": False, "error": "Progresso não encontrado"}
            
            # Localizações descobertas
            locations_explored = self.db.query(PlayerEnvironmentLevel).filter(
                PlayerEnvironmentLevel.session_id == session_id
            ).count()
            
            # Pistas descobertas
            clues_discovered = self.db.query(PlayerDiscoveredClues).filter(
                PlayerDiscoveredClues.session_id == session_id
            ).count()
            
            # Personagens interagidos
            characters_interacted = self.db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id
            ).count()
            
            # Objetos examinados
            objects_examined = self.db.query(PlayerObjectLevel).filter(
                PlayerObjectLevel.session_id == session_id
            ).count()
            
            # Gera dicas personalizadas com base nos dados
            hints = self._generate_context_aware_hints(
                session_id,
                progress,
                locations_explored,
                clues_discovered,
                characters_interacted,
                objects_examined
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "hints": hints
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter dicas: {str(e)}")
            return {"success": False, "error": f"Erro ao obter dicas: {str(e)}"}
    
    # Métodos auxiliares
    
    def _initialize_player_progress(self, session_id: str, player_id: str, story_id: int) -> None:
        """
        Inicializa o progresso do jogador para uma nova sessão.
        
        Args:
            session_id: ID da sessão
            player_id: ID do jogador
            story_id: ID da história
        """
        try:
            # Obtém a localização inicial
            starting_location = self._get_starting_location(story_id)
            
            # Cria o registro de progresso principal
            progress = PlayerProgress(
                session_id=session_id,
                player_id=player_id,
                story_id=story_id,
                current_location_id=starting_location,
                current_area_id=None,
                last_activity=datetime.now()
            )
            
            self.db.add(progress)
            
            # Se tiver localização inicial, cria um registro de exploração para ela
            if starting_location:
                env_progress = PlayerEnvironmentLevel(
                    session_id=session_id,
                    location_id=starting_location,
                    exploration_level=1,
                    last_exploration=datetime.now()
                )
                self.db.add(env_progress)
            
            self.db.commit()
            
            self.logger.info(f"Progresso inicializado para sessão {session_id}")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar progresso: {str(e)}")
            self.db.rollback()
    
    def _get_starting_location(self, story_id: int) -> Optional[int]:
        """
        Obtém a localização inicial de uma história.
        
        Args:
            story_id: ID da história
            
        Returns:
            ID da localização inicial ou None
        """
        try:
            # Utiliza o repositório para obter a localização inicial
            return self.story_repository.get_starting_location(self.db, story_id)
        except Exception as e:
            self.logger.error(f"Erro ao obter localização inicial: {str(e)}")
            return None
    
    def _build_session_state_from_db(self, session_id: str) -> Dict[str, Any]:
        """
        Constrói o estado completo da sessão a partir do banco de dados.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Estado completo da sessão
        """
        try:
            # Obtém o progresso principal
            progress = self.db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if not progress:
                return {"error": "Progresso não encontrado"}
            
            # Obtém a sessão
            session = self.db.query(PlayerSession).filter(
                PlayerSession.session_id == session_id
            ).first()
            
            # Obtém localizações exploradas
            environment_levels = self.db.query(PlayerEnvironmentLevel).filter(
                PlayerEnvironmentLevel.session_id == session_id
            ).all()
            
            location_levels = {}
            discovered_locations = []
            
            for env in environment_levels:
                location_levels[str(env.location_id)] = env.exploration_level
                discovered_locations.append(env.location_id)
            
            # Obtém áreas exploradas
            # Implementação depende da estrutura exata do banco de dados
            
            # Obtém inventário
            inventory_items = self.db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id
            ).all()
            
            inventory = [item.object_id for item in inventory_items]
            
            # Obtém níveis de objetos
            object_levels = self.db.query(PlayerObjectLevel).filter(
                PlayerObjectLevel.session_id == session_id
            ).all()
            
            object_level_dict = {}
            for obj in object_levels:
                object_level_dict[str(obj.object_id)] = obj.current_level
            
            # Obtém níveis de personagens
            character_levels = self.db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id
            ).all()
            
            character_level_dict = {}
            for char in character_levels:
                character_level_dict[str(char.character_id)] = char.current_level
            
            # Obtém pistas descobertas
            discovered_clues = self.db.query(PlayerDiscoveredClues).filter(
                PlayerDiscoveredClues.session_id == session_id
            ).all()
            
            clues = [clue.clue_id for clue in discovered_clues]
            
            # Obtém especializações
            specializations = self.db.query(PlayerSpecialization).filter(
                PlayerSpecialization.session_id == session_id
            ).all()
            
            spec_points = {}
            spec_levels = {}
            
            for spec in specializations:
                spec_points[spec.category_id] = spec.points
                spec_levels[spec.category_id] = spec.level
            
            # Contrói o estado
            state = {
                "player_id": progress.player_id,
                "story_id": progress.story_id,
                "session_id": session_id,
                "start_time": session.start_time if session else None,
                "last_activity": session.last_activity if session else None,
                "current_location": progress.current_location_id,
                "current_area": progress.current_area_id,
                "discovered_locations": discovered_locations,
                "location_exploration_level": location_levels,
                "inventory": inventory,
                "object_level": object_level_dict,
                "character_level": character_level_dict,
                "discovered_clues": clues,
                "specialization": {
                    "points": spec_points,
                    "levels": spec_levels
                },
                "solution_submitted": session.solution_submitted if session else False
            }
            
            return state
        except Exception as e:
            self.logger.error(f"Erro ao construir estado da sessão: {str(e)}")
            return {
                "error": "Erro ao construir estado da sessão",
                "session_id": session_id
            }
    
    def _update_character_level(self, session_id: str, character_id: int, level: int) -> bool:
        """
        Atualiza o nível de um personagem para um jogador.
        
        Args:
            session_id: ID da sessão
            character_id: ID do personagem
            level: Novo nível
        
        Returns:
            True se atualizado com sucesso
        """
        try:
            # Busca o registro existente
            character_level = self.db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id,
                PlayerCharacterLevel.character_id == character_id
            ).first()
            
            # Se não existe, cria um novo
            if not character_level:
                character_level = PlayerCharacterLevel(
                    session_id=session_id,
                    character_id=character_id,
                    current_level=level,
                    last_interaction=datetime.now()
                )
                self.db.add(character_level)
            else:
                # Só atualiza se o novo nível for maior
                if level > character_level.current_level:
                    character_level.current_level = level
                    character_level.last_interaction = datetime.now()
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar nível de personagem: {str(e)}")
            return False
    
    def _update_object_level(self, session_id: str, object_id: int, level: int) -> bool:
        """
        Atualiza o nível de um objeto para um jogador.
        
        Args:
            session_id: ID da sessão
            object_id: ID do objeto
            level: Novo nível
        
        Returns:
            True se atualizado com sucesso
        """
        try:
            # Busca o registro existente
            object_level = self.db.query(PlayerObjectLevel).filter(
                PlayerObjectLevel.session_id == session_id,
                PlayerObjectLevel.object_id == object_id
            ).first()
            
            # Se não existe, cria um novo
            if not object_level:
                object_level = PlayerObjectLevel(
                    session_id=session_id,
                    object_id=object_id,
                    current_level=level,
                    last_interaction=datetime.now()
                )
                self.db.add(object_level)
            else:
                # Só atualiza se o novo nível for maior
                if level > object_level.current_level:
                    object_level.current_level = level
                    object_level.last_interaction = datetime.now()
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar nível de objeto: {str(e)}")
            return False
    
    def _update_specialization(self, session_id: str, category_id: str, points: int, 
                            interaction_type: str = None, interaction_id: str = None) -> bool:
        """
        Atualiza a especialização de um jogador.
        
        Args:
            session_id: ID da sessão
            category_id: ID da categoria de especialização
            points: Pontos a adicionar
            interaction_type: Tipo de interação
            interaction_id: ID da interação
        
        Returns:
            True se atualizado com sucesso
        """
        try:
            # Busca o registro existente
            specialization = self.db.query(PlayerSpecialization).filter(
                PlayerSpecialization.session_id == session_id,
                PlayerSpecialization.category_id == category_id
            ).first()
            
            # Verificar se esta interação já foi registrada
            if interaction_type and interaction_id:
                # Verificar se há um registro para esta interação
                completed_interactions = []
                if specialization and specialization.completed_interactions:
                    if isinstance(specialization.completed_interactions, str):
                        import json
                        try:
                            completed_interactions = json.loads(specialization.completed_interactions)
                        except:
                            completed_interactions = []
                    else:
                        completed_interactions = specialization.completed_interactions
                
                # Se a interação já está registrada, não adiciona pontos
                interaction_key = f"{interaction_type}:{interaction_id}"
                if interaction_key in completed_interactions:
                    return True
            
            # Se não existe, cria um novo
            if not specialization:
                specialization = PlayerSpecialization(
                    session_id=session_id,
                    category_id=category_id,
                    points=points,
                    level=self._calculate_specialization_level(points)
                )
                self.db.add(specialization)
            else:
                # Adiciona pontos e recalcula o nível
                specialization.points += points
                specialization.level = self._calculate_specialization_level(specialization.points)
            
            # Registra a interação se necessário
            if interaction_type and interaction_id:
                interaction_key = f"{interaction_type}:{interaction_id}"
                if isinstance(specialization.completed_interactions, str):
                    import json
                    try:
                        completed_interactions = json.loads(specialization.completed_interactions)
                    except:
                        completed_interactions = []
                else:
                    completed_interactions = specialization.completed_interactions or []
                
                if interaction_key not in completed_interactions:
                    completed_interactions.append(interaction_key)
                    specialization.completed_interactions = completed_interactions
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao atualizar especialização: {str(e)}")
            return False
    
    def _verify_solution(self, solution_data: Dict[str, Any], 
                       solution_criteria: Dict[str, Any]) -> tuple[bool, Dict[str, bool]]:
        """
        Verifica se uma solução está correta.
        
        Args:
            solution_data: Dados da solução submetida
            solution_criteria: Critérios de solução
            
        Returns:
            (is_correct, details) - Se a solução está correta e detalhes
        """
        try:
            # Verifica o culpado
            culprit_correct = solution_data.get("culprit_id") == solution_criteria.get("culprit_id")
            
            # Verifica o método e motivo através de palavras-chave
            method_text = solution_data.get("method", "").lower()
            motive_text = solution_data.get("motive", "").lower()
            
            method_keywords = solution_criteria.get("method_keywords", [])
            motive_keywords = solution_criteria.get("motive_keywords", [])
            
            method_correct = any(keyword.lower() in method_text for keyword in method_keywords)
            motive_correct = any(keyword.lower() in motive_text for keyword in motive_keywords)
            
            # Verifica as evidências
            evidences = solution_data.get("evidences", [])
            required_evidences = solution_criteria.get("required_evidences", [])
            
            evidence_correct = all(ev in evidences for ev in required_evidences)
            
            # Resultado final
            is_correct = culprit_correct and method_correct and motive_correct and evidence_correct
            
            details = {
                "culprit_correct": culprit_correct,
                "method_correct": method_correct,
                "motive_correct": motive_correct,
                "evidence_correct": evidence_correct
            }
            
            return is_correct, details
        except Exception as e:
            self.logger.error(f"Erro ao verificar solução: {str(e)}")
            return False, {"error": str(e)}
    
    def _generate_solution_feedback(self, is_correct: bool, details: Dict[str, bool]) -> str:
        """
        Gera feedback sobre a solução submetida.
        
        Args:
            is_correct: Se a solução está correta
            details: Detalhes da verificação
            
        Returns:
            Feedback formatado
        """
        if is_correct:
            return "Parabéns! Sua solução está correta em todos os aspectos. Você resolveu o mistério completamente!"
        
        feedback = "Sua solução não está completamente correta.\n\n"
        
        if not details.get("culprit_correct", False):
            feedback += "- Você não identificou corretamente o culpado.\n"
        
        if not details.get("method_correct", False):
            feedback += "- Sua explicação sobre o método do crime não está precisa.\n"
        
        if not details.get("motive_correct", False):
            feedback += "- Sua compreensão do motivo não capturou a essência do caso.\n"
        
        if not details.get("evidence_correct", False):
            feedback += "- Você não apresentou todas as evidências-chave necessárias para sustentar sua teoria.\n"
        
        feedback += "\nContinue investigando e revise cuidadosamente as pistas que encontrou."
        
        return feedback
    
    def _generate_context_aware_hints(self, session_id: str, progress, 
                                    locations_explored: int, clues_discovered: int,
                                    characters_interacted: int, objects_examined: int) -> List[Dict[str, Any]]:
        """
        Gera dicas personalizadas com base no progresso do jogador.
        
        Args:
            session_id: ID da sessão
            progress: Progresso do jogador
            locations_explored: Número de localizações exploradas
            clues_discovered: Número de pistas descobertas
            characters_interacted: Número de personagens interagidos
            objects_examined: Número de objetos examinados
            
        Returns:
            Lista de dicas personalizadas
        """
        hints = []
        
        # Dica sobre exploração
        if locations_explored < 3:
            hints.append({
                "hint_type": "exploration",
                "hint_level": 1,
                "hint_text": "Explore mais localizações para descobrir novas pistas e informações."
            })
        
        # Dica sobre personagens
        if characters_interacted < 3:
            hints.append({
                "hint_type": "character",
                "hint_level": 1,
                "hint_text": "Converse com mais personagens para entender melhor os eventos."
            })
        elif characters_interacted >= 3 and clues_discovered < 5:
            hints.append({
                "hint_type": "character",
                "hint_level": 2,
                "hint_text": "Alguns personagens podem revelar mais informações se você apresentar evidências ou fizer as perguntas certas."
            })
        
        # Dica sobre objetos
        if objects_examined < 3:
            hints.append({
                "hint_type": "object",
                "hint_level": 1,
                "hint_text": "Examine objetos ao seu redor. Eles podem conter pistas importantes."
            })
        
        # Dica sobre localização atual
        if progress and progress.current_location_id:
            hints.append({
                "hint_type": "current_location",
                "hint_level": 1,
                "hint_text": "Há mais para ver nesta localização. Procure por áreas ou detalhes que ainda não explorou."
            })
        
        # Limita a 3 dicas por vez para não sobrecarregar o jogador
        return hints[:3]
    
    def _calculate_specialization_level(self, points: int) -> int:
        """
        Calcula o nível de especialização com base nos pontos.
        
        Args:
            points: Pontos acumulados
            
        Returns:
            Nível calculado
        """
        # Implementação básica do cálculo de nível
        if points < 20:
            return 1
        elif points < 50:
            return 2
        elif points < 100:
            return 3
        elif points < 200:
            return 4
        else:
            return 5