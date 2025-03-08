# src/repositories/player_progress_repository.py
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import logging
from datetime import datetime

from src.models.db_models import (
    PlayerProgress,
    PlayerSession,
    PlayerSpecialization,
    PlayerInventory,
    PlayerObjectLevel,
    PlayerEnvironmentLevel,
    PlayerCharacterLevel,
    GameObject,
    Location,
    LocationArea,
    Clue
)
from src.repositories.base_repository import BaseRepository

class PlayerProgressRepository(BaseRepository[PlayerProgress]):
    """
    Repositório para operações relacionadas ao progresso dos jogadores.
    Gerencia o acesso a dados de progresso, inventário, especialização e descobertas.
    """
    
    def __init__(self):
        super().__init__(PlayerProgress)
        self.logger = logging.getLogger(__name__)
    
    def get_by_session_id(self, db: Session, session_id: str) -> Optional[PlayerProgress]:
        """
        Obtém o progresso de um jogador pelo ID da sessão.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Objeto PlayerProgress ou None se não encontrado
        """
        try:
            return db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
        except Exception as e:
            self.logger.error(f"Erro ao buscar progresso para sessão {session_id}: {e}")
            return None
    
    def create_player_session(self, db: Session, player_name: str, story_id: int) -> Optional[str]:
        """
        Cria uma nova sessão de jogador com progresso inicial.
        
        Args:
            db: Sessão do banco de dados
            player_name: Nome do jogador
            story_id: ID da história
            
        Returns:
            ID da sessão criada ou None em caso de erro
        """
        try:
            session_id = str(func.uuid_generate_v4()) if hasattr(func, 'uuid_generate_v4') else str(func.uuid())
            
            # Criar a entrada de progresso
            progress = PlayerProgress(
                player_id=player_name,
                story_id=story_id,
                session_id=session_id,
                start_time=datetime.now(),
                last_activity=datetime.now(),
                current_location_id=None,
                current_area_id=None,
                discovered_locations=[],
                discovered_areas={},
                location_exploration_level={},
                area_exploration_level={},
                inventory=[],
                object_level={},
                character_level={},
                dialogue_history={},
                discovered_clues=[],
                scanned_qr_codes=[],
                action_history=[],
                specialization_points={},
                specialization_levels={},
                completed_interactions={"objetos": [], "personagens": [], "areas": [], "pistas": [], "combinacoes": []}
            )
            
            db.add(progress)
            db.commit()
            
            return session_id
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao criar sessão de jogador: {e}")
            return None
    
    # ===== MÉTODOS DE INVENTÁRIO =====
    
    def get_inventory(self, db: Session, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtém o inventário do jogador com detalhes dos objetos.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Lista de objetos no inventário com detalhes
        """
        try:
            # Obter o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return []
            
            # Converter para lista Python se estiver em JSON
            inventory_ids = self._ensure_list(progress.inventory)
            
            if not inventory_ids:
                return []
            
            # Buscar detalhes dos objetos
            result = []
            for obj_id in inventory_ids:
                game_object = db.query(GameObject).filter(GameObject.object_id == obj_id).first()
                if game_object:
                    # Buscar nível do objeto para este jogador
                    object_level_data = self._get_object_level_data(db, session_id, obj_id)
                    
                    result.append({
                        "object_id": obj_id,
                        "name": game_object.name,
                        "description": game_object.base_description,
                        "level": object_level_data.get("level", 0),
                        "level_description": object_level_data.get("description", "")
                    })
            
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar inventário: {e}")
            return []
    
    def add_to_inventory(self, db: Session, session_id: str, object_id: int, 
                      acquisition_method: str = "discovered") -> Dict[str, Any]:
        """
        Adiciona um objeto ao inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            object_id: ID do objeto
            acquisition_method: Como o objeto foi adquirido
            
        Returns:
            Resultado da operação
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se o objeto existe
                game_object = db.query(GameObject).filter(GameObject.object_id == object_id).first()
                if not game_object:
                    return {"success": False, "message": "Objeto não encontrado"}
                
                # Converter inventário para lista Python
                inventory = self._ensure_list(progress.inventory)
                
                # Verificar se o objeto já está no inventário
                if object_id in inventory:
                    return {
                        "success": True,
                        "message": "Objeto já está no inventário",
                        "is_new": False
                    }
                
                # Adicionar ao inventário
                inventory.append(object_id)
                
                # Atualizar o progresso
                progress.inventory = inventory
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "collect_object", {
                    "object_id": object_id,
                    "acquisition_method": acquisition_method
                })
                
                # Criar registro no sistema de inventário tradicional também
                inventory_item = PlayerInventory(
                    session_id=session_id,
                    object_id=object_id,
                    acquisition_method=acquisition_method,
                    acquired_time=datetime.now()
                )
                db.add(inventory_item)
                
            db.commit()
            
            return {
                "success": True,
                "message": f"Objeto {game_object.name} adicionado ao inventário",
                "is_new": True
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar objeto ao inventário: {e}")
            return {"success": False, "error": str(e)}
    
    def remove_from_inventory(self, db: Session, session_id: str, object_id: int) -> Dict[str, Any]:
        """
        Remove um objeto do inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            object_id: ID do objeto
            
        Returns:
            Resultado da operação
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Converter inventário para lista Python
                inventory = self._ensure_list(progress.inventory)
                
                # Verificar se o objeto está no inventário
                if object_id not in inventory:
                    return {
                        "success": False,
                        "message": "Objeto não está no inventário"
                    }
                
                # Remover do inventário
                inventory.remove(object_id)
                
                # Atualizar o progresso
                progress.inventory = inventory
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "remove_object", {
                    "object_id": object_id
                })
                
                # Remover do sistema de inventário tradicional também
                db.query(PlayerInventory).filter(
                    PlayerInventory.session_id == session_id,
                    PlayerInventory.object_id == object_id
                ).delete()
                
            db.commit()
            
            return {
                "success": True,
                "message": "Objeto removido do inventário"
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao remover objeto do inventário: {e}")
            return {"success": False, "error": str(e)}
    
    # ===== MÉTODOS DE LOCALIZAÇÃO =====
    
    def discover_location(self, db: Session, session_id: str, location_id: int) -> Dict[str, Any]:
        """
        Registra uma localização como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            location_id: ID da localização
            
        Returns:
            Resultado da operação
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se a localização existe
                location = db.query(Location).filter(Location.location_id == location_id).first()
                if not location:
                    return {"success": False, "message": "Localização não encontrada"}
                
                # Atualizar a localização atual
                progress.current_location_id = location_id
                progress.current_area_id = None  # Reset da área ao mudar de localização
                
                # Converter locations para lista Python
                discovered_locations = self._ensure_list(progress.discovered_locations)
                
                # Verificar se a localização já foi descoberta
                is_new_discovery = location_id not in discovered_locations
                
                if is_new_discovery:
                    # Adicionar à lista de localizações descobertas
                    discovered_locations.append(location_id)
                    progress.discovered_locations = discovered_locations
                    
                    # Inicializar nível de exploração se for primeira visita
                    location_levels = self._ensure_dict(progress.location_exploration_level)
                    location_levels[str(location_id)] = 1
                    progress.location_exploration_level = location_levels
                    
                    # Inicializar áreas descobertas para esta localização
                    discovered_areas = self._ensure_dict(progress.discovered_areas)
                    discovered_areas[str(location_id)] = []
                    progress.discovered_areas = discovered_areas
                
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "discover_location", {
                    "location_id": location_id,
                    "is_new": is_new_discovery
                })
                
                # Criar ou atualizar registro de ambiente no sistema tradicional
                env_progress = db.query(PlayerEnvironmentLevel).filter(
                    PlayerEnvironmentLevel.session_id == session_id,
                    PlayerEnvironmentLevel.location_id == location_id
                ).first()
                
                if not env_progress:
                    env_progress = PlayerEnvironmentLevel(
                        session_id=session_id,
                        location_id=location_id,
                        exploration_level=1,
                        discovered_areas=[],
                        discovered_details=[],
                        last_exploration=datetime.now()
                    )
                    db.add(env_progress)
                else:
                    env_progress.last_exploration = datetime.now()
                
            db.commit()
            
            return {
                "success": True,
                "message": "Localização descoberta" if is_new_discovery else "Localização já descoberta",
                "is_new_discovery": is_new_discovery,
                "location_name": location.name,
                "location_id": location_id
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao descobrir localização: {e}")
            return {"success": False, "error": str(e)}
    
    def discover_area(self, db: Session, session_id: str, area_id: int) -> Dict[str, Any]:
        """
        Registra uma área como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            area_id: ID da área
            
        Returns:
            Resultado da operação
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se a área existe
                area = db.query(LocationArea).filter(LocationArea.area_id == area_id).first()
                if not area:
                    return {"success": False, "message": "Área não encontrada"}
                
                location_id = area.location_id
                
                # Atualizar a área atual
                progress.current_area_id = area_id
                
                # Atualizar áreas descobertas
                discovered_areas = self._ensure_dict(progress.discovered_areas)
                
                # Inicializar a lista para esta localização se for a primeira área
                if str(location_id) not in discovered_areas:
                    discovered_areas[str(location_id)] = []
                
                # Verificar se a área já foi descoberta
                is_new_discovery = area_id not in discovered_areas[str(location_id)]
                
                if is_new_discovery:
                    # Adicionar à lista de áreas descobertas
                    discovered_areas[str(location_id)].append(area_id)
                    progress.discovered_areas = discovered_areas
                    
                    # Inicializar nível de exploração para esta área
                    area_levels = self._ensure_dict(progress.area_exploration_level)
                    area_levels[str(area_id)] = 1
                    progress.area_exploration_level = area_levels
                
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "discover_area", {
                    "area_id": area_id,
                    "location_id": location_id,
                    "is_new": is_new_discovery
                })
                
                # Atualizar registro de ambiente no sistema tradicional
                env_progress = db.query(PlayerEnvironmentLevel).filter(
                    PlayerEnvironmentLevel.session_id == session_id,
                    PlayerEnvironmentLevel.location_id == location_id
                ).first()
                
                if env_progress:
                    discovered_areas_list = self._ensure_list(env_progress.discovered_areas)
                    if area_id not in discovered_areas_list:
                        discovered_areas_list.append(area_id)
                        env_progress.discovered_areas = discovered_areas_list
                        env_progress.last_exploration = datetime.now()
                
            db.commit()
            
            return {
                "success": True,
                "message": "Área descoberta" if is_new_discovery else "Área já descoberta",
                "is_new_discovery": is_new_discovery,
                "area_name": area.name,
                "area_id": area_id,
                "location_id": location_id
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao descobrir área: {e}")
            return {"success": False, "error": str(e)}
    
    # ===== MÉTODOS DE PISTAS =====
    
    def discover_clue(self, db: Session, session_id: str, clue_id: int) -> Dict[str, Any]:
        """
        Registra uma pista como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            clue_id: ID da pista
            
        Returns:
            Resultado da operação
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se a pista existe
                clue = db.query(Clue).filter(Clue.clue_id == clue_id).first()
                if not clue:
                    return {"success": False, "message": "Pista não encontrada"}
                
                # Converter pistas para lista Python
                discovered_clues = self._ensure_list(progress.discovered_clues)
                
                # Verificar se a pista já foi descoberta
                is_new_discovery = clue_id not in discovered_clues
                
                if is_new_discovery:
                    # Adicionar à lista de pistas descobertas
                    discovered_clues.append(clue_id)
                    progress.discovered_clues = discovered_clues
                    
                    # Conceder pontos de especialização se for uma nova descoberta
                    specialization_category = "analise"  # Categoria padrão para pistas
                    specialization_points = 10  # Pontos padrão
                    
                    # Atualizar especialização
                    self.update_specialization(
                        db,
                        session_id,
                        specialization_category,
                        specialization_points,
                        "pistas",
                        str(clue_id)
                    )
                
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "discover_clue", {
                    "clue_id": clue_id,
                    "is_new": is_new_discovery
                })
                
            db.commit()
            
            return {
                "success": True,
                "message": "Pista descoberta" if is_new_discovery else "Pista já descoberta",
                "is_new_discovery": is_new_discovery,
                "clue_name": clue.name,
                "clue_id": clue_id
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao descobrir pista: {e}")
            return {"success": False, "error": str(e)}
    
    # ===== MÉTODOS DE ESPECIALIZAÇÃO =====
    
    def get_specializations(self, db: Session, session_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Obtém as especializações do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Dicionário com especializações por categoria
        """
        try:
            # Obter o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {}
            
            # Obter pontos e níveis de especialização
            specialization_points = self._ensure_dict(progress.specialization_points)
            specialization_levels = self._ensure_dict(progress.specialization_levels)
            
            # Combinar dados em um único dicionário
            result = {}
            
            # Unir todas as chaves de ambos os dicionários
            all_categories = set(specialization_points.keys()) | set(specialization_levels.keys())
            
            for category in all_categories:
                result[category] = {
                    "points": specialization_points.get(category, 0),
                    "level": specialization_levels.get(category, 0),
                }
            
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar especializações: {e}")
            return {}
    
    def update_specialization(self, db: Session, session_id: str, category_id: str, 
                          points: int, interaction_type: str = None, 
                          interaction_id: str = None) -> Dict[str, Any]:
        """
        Atualiza os pontos de especialização de um jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            category_id: Categoria de especialização
            points: Pontos a adicionar
            interaction_type: Tipo de interação (opcional)
            interaction_id: ID da interação (opcional)
            
        Returns:
            Resultado da atualização
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se esta interação já foi contabilizada
                if interaction_type and interaction_id:
                    completed_interactions = self._ensure_dict(progress.completed_interactions)
                    
                    # Inicializar categoria se não existir
                    if interaction_type not in completed_interactions:
                        completed_interactions[interaction_type] = []
                    
                    # Verificar se a interação já foi registrada
                    if interaction_id in completed_interactions[interaction_type]:
                        return {
                            "success": True,
                            "message": "Interação já contabilizada",
                            "points_added": 0,
                            "level_up": False
                        }
                    
                    # Registrar a interação
                    completed_interactions[interaction_type].append(interaction_id)
                    progress.completed_interactions = completed_interactions
                
                # Atualizar pontos de especialização
                specialization_points = self._ensure_dict(progress.specialization_points)
                old_points = specialization_points.get(category_id, 0)
                new_points = old_points + points
                specialization_points[category_id] = new_points
                progress.specialization_points = specialization_points
                
                # Calcular o novo nível
                specialization_levels = self._ensure_dict(progress.specialization_levels)
                old_level = specialization_levels.get(category_id, 0)
                new_level = self._calculate_level(new_points)
                
                # Verificar se houve evolução de nível
                level_up = new_level > old_level
                
                if level_up:
                    specialization_levels[category_id] = new_level
                    progress.specialization_levels = specialization_levels
                
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "update_specialization", {
                    "category_id": category_id,
                    "points_added": points,
                    "old_points": old_points,
                    "new_points": new_points,
                    "old_level": old_level,
                    "new_level": new_level,
                    "level_up": level_up,
                    "interaction_type": interaction_type,
                    "interaction_id": interaction_id
                })
                
                # Atualizar no sistema de especialização tradicional também
                spec = db.query(PlayerSpecialization).filter(
                    PlayerSpecialization.session_id == session_id,
                    PlayerSpecialization.category_id == category_id
                ).first()
                
                if not spec:
                    spec = PlayerSpecialization(
                        session_id=session_id,
                        category_id=category_id,
                        points=new_points,
                        level=new_level,
                        bonus_multiplier=1.0,
                        completed_interactions=json.dumps(
                            {interaction_type: [interaction_id]} if interaction_type and interaction_id else {}
                        )
                    )
                    db.add(spec)
                else:
                    spec.points = new_points
                    if level_up:
                        spec.level = new_level
                    
                    # Atualizar interações completadas
                    if interaction_type and interaction_id:
                        completed = self._ensure_dict(spec.completed_interactions)
                        if interaction_type not in completed:
                            completed[interaction_type] = []
                        if interaction_id not in completed[interaction_type]:
                            completed[interaction_type].append(interaction_id)
                        spec.completed_interactions = completed
                
            db.commit()
            
            return {
                "success": True,
                "message": "Especialização atualizada",
                "points_added": points,
                "old_points": old_points,
                "new_points": new_points,
                "old_level": old_level,
                "new_level": new_level,
                "level_up": level_up
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar especialização: {e}")
            return {"success": False, "error": str(e)}
    
    # ===== MÉTODOS DE PROGRESSO =====
    
    def update_character_level(self, db: Session, session_id: str, character_id: int, 
                           level: int) -> Dict[str, Any]:
        """
        Atualiza o nível de conhecimento sobre um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            level: Novo nível
            
        Returns:
            Resultado da atualização
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Atualizar níveis de personagem
                character_levels = self._ensure_dict(progress.character_level)
                old_level = character_levels.get(str(character_id), 0)
                
                # Só atualiza se o novo nível for maior
                if level <= old_level:
                    return {
                        "success": True,
                        "message": "Nível não alterado",
                        "level_up": False
                    }
                
                character_levels[str(character_id)] = level
                progress.character_level = character_levels
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "update_character_level", {
                    "character_id": character_id,
                    "old_level": old_level,
                    "new_level": level
                })
                
                # Atualizar no sistema tradicional também
                char_progress = db.query(PlayerCharacterLevel).filter(
                    PlayerCharacterLevel.session_id == session_id,
                    PlayerCharacterLevel.character_id == character_id
                ).first()
                
                if not char_progress:
                    char_progress = PlayerCharacterLevel(
                        session_id=session_id,
                        character_id=character_id,
                        current_level=level,
                        last_interaction=datetime.now()
                    )
                    db.add(char_progress)
                else:
                    char_progress.current_level = level
                    char_progress.last_interaction = datetime.now()
                
            db.commit()
            
            return {
                "success": True,
                "message": "Nível de personagem atualizado",
                "character_id": character_id,
                "old_level": old_level,
                "new_level": level,
                "level_up": True
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível de personagem: {e}")
            return {"success": False, "error": str(e)}
    
    def update_object_level(self, db: Session, session_id: str, object_id: int, 
                        level: int) -> Dict[str, Any]:
        """
        Atualiza o nível de conhecimento sobre um objeto.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            object_id: ID do objeto
            level: Novo nível
            
        Returns:
            Resultado da atualização
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se o objeto está no inventário
                inventory = self._ensure_list(progress.inventory)
                if object_id not in inventory:
                    return {
                        "success": False,
                        "message": "Objeto não está no inventário"
                    }
                
                # Atualizar níveis de objeto
                object_levels = self._ensure_dict(progress.object_level)
                old_level = object_levels.get(str(object_id), 0)
                
                # Só atualiza se o novo nível for maior
                if level <= old_level:
                    return {
                        "success": True,
                        "message": "Nível não alterado",
                        "level_up": False
                    }
                
                object_levels[str(object_id)] = level
                progress.object_level = object_levels
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "update_object_level", {
                    "object_id": object_id,
                    "old_level": old_level,
                    "new_level": level
                })
                
                # Atualizar no sistema tradicional também
                obj_progress = db.query(PlayerObjectLevel).filter(
                    PlayerObjectLevel.session_id == session_id,
                    PlayerObjectLevel.object_id == object_id
                ).first()
                
                if not obj_progress:
                    obj_progress = PlayerObjectLevel(
                        session_id=session_id,
                        object_id=object_id,
                        current_level=level,
                        last_interaction=datetime.now(),
                        unlocked_details=json.dumps([])
                    )
                    db.add(obj_progress)
                else:
                    obj_progress.current_level = level
                    obj_progress.last_interaction = datetime.now()
                
            db.commit()
            
            return {
                "success": True,
                "message": "Nível de objeto atualizado",
                "object_id": object_id,
                "old_level": old_level,
                "new_level": level,
                "level_up": True
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível de objeto: {e}")
            return {"success": False, "error": str(e)}
    
    def update_location_exploration(self, db: Session, session_id: str, location_id: int, 
                                level: int) -> Dict[str, Any]:
        """
        Atualiza o nível de exploração de uma localização.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            location_id: ID da localização
            level: Novo nível
            
        Returns:
            Resultado da atualização
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se a localização foi descoberta
                discovered_locations = self._ensure_list(progress.discovered_locations)
                if location_id not in discovered_locations:
                    return {
                        "success": False,
                        "message": "Localização não descoberta"
                    }
                
                # Atualizar níveis de exploração
                location_levels = self._ensure_dict(progress.location_exploration_level)
                old_level = location_levels.get(str(location_id), 0)
                
                # Só atualiza se o novo nível for maior
                if level <= old_level:
                    return {
                        "success": True,
                        "message": "Nível não alterado",
                        "level_up": False
                    }
                
                location_levels[str(location_id)] = level
                progress.location_exploration_level = location_levels
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "update_location_exploration", {
                    "location_id": location_id,
                    "old_level": old_level,
                    "new_level": level
                })
                
                # Atualizar no sistema tradicional também
                env_progress = db.query(PlayerEnvironmentLevel).filter(
                    PlayerEnvironmentLevel.session_id == session_id,
                    PlayerEnvironmentLevel.location_id == location_id
                ).first()
                
                if not env_progress:
                    env_progress = PlayerEnvironmentLevel(
                        session_id=session_id,
                        location_id=location_id,
                        exploration_level=level,
                        last_exploration=datetime.now(),
                        discovered_areas=json.dumps([]),
                        discovered_details=json.dumps([])
                    )
                    db.add(env_progress)
                else:
                    env_progress.exploration_level = level
                    env_progress.last_exploration = datetime.now()
                
            db.commit()
            
            return {
                "success": True,
                "message": "Nível de exploração atualizado",
                "location_id": location_id,
                "old_level": old_level,
                "new_level": level,
                "level_up": True
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível de exploração: {e}")
            return {"success": False, "error": str(e)}
    
    def update_area_exploration(self, db: Session, session_id: str, area_id: int, 
                            level: int) -> Dict[str, Any]:
        """
        Atualiza o nível de exploração de uma área.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            area_id: ID da área
            level: Novo nível
            
        Returns:
            Resultado da atualização
        """
        try:
            with db.begin_nested():  # Criar ponto de transação
                # Verificar se o jogador existe
                progress = self.get_by_session_id(db, session_id)
                if not progress:
                    return {"success": False, "message": "Sessão não encontrada"}
                
                # Verificar se a área existe
                area = db.query(LocationArea).filter(LocationArea.area_id == area_id).first()
                if not area:
                    return {"success": False, "message": "Área não encontrada"}
                
                location_id = area.location_id
                
                # Verificar se a área foi descoberta
                discovered_areas = self._ensure_dict(progress.discovered_areas)
                if str(location_id) not in discovered_areas or area_id not in discovered_areas[str(location_id)]:
                    return {
                        "success": False,
                        "message": "Área não descoberta"
                    }
                
                # Atualizar níveis de exploração de área
                area_levels = self._ensure_dict(progress.area_exploration_level)
                old_level = area_levels.get(str(area_id), 0)
                
                # Só atualiza se o novo nível for maior
                if level <= old_level:
                    return {
                        "success": True,
                        "message": "Nível não alterado",
                        "level_up": False
                    }
                
                area_levels[str(area_id)] = level
                progress.area_exploration_level = area_levels
                progress.last_activity = datetime.now()
                
                # Registrar no histórico de ações
                self._add_action_to_history(progress, "update_area_exploration", {
                    "area_id": area_id,
                    "location_id": location_id,
                    "old_level": old_level,
                    "new_level": level
                })
                
            db.commit()
            
            return {
                "success": True,
                "message": "Nível de exploração de área atualizado",
                "area_id": area_id,
                "location_id": location_id,
                "old_level": old_level,
                "new_level": level,
                "level_up": True
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível de exploração de área: {e}")
            return {"success": False, "error": str(e)}
    
    # ===== MÉTODOS DE CONSULTA AGREGADA =====
    
    def get_progress_summary(self, db: Session, session_id: str) -> Dict[str, Any]:
        """
        Obtém um resumo do progresso do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Resumo do progresso
        """
        try:
            # Obter o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {}
            
            # Contar localizações descobertas
            discovered_locations = self._ensure_list(progress.discovered_locations)
            locations_count = len(discovered_locations)
            
            # Contar áreas descobertas
            discovered_areas = self._ensure_dict(progress.discovered_areas)
            areas_count = sum(len(areas) for areas in discovered_areas.values())
            
            # Contar pistas descobertas
            discovered_clues = self._ensure_list(progress.discovered_clues)
            clues_count = len(discovered_clues)
            
            # Contar objetos no inventário
            inventory = self._ensure_list(progress.inventory)
            inventory_count = len(inventory)
            
            # Obter especializações
            specializations = self.get_specializations(db, session_id)
            
            # Calcular pontos totais de especialização
            total_points = sum(spec.get("points", 0) for spec in specializations.values())
            
            # Obter a história
            story = db.query(GameObject.story_id).filter(
                GameObject.object_id.in_(inventory)
            ).first() if inventory else None
            
            story_id = story[0] if story else progress.story_id
            
            return {
                "player_id": progress.player_id,
                "story_id": story_id,
                "session_id": progress.session_id,
                "start_time": progress.start_time,
                "last_activity": progress.last_activity,
                "current_location": progress.current_location_id,
                "current_area": progress.current_area_id,
                "inventory_count": inventory_count,
                "discovered_locations_count": locations_count,
                "discovered_areas_count": areas_count,
                "discovered_clues_count": clues_count,
                "specializations": specializations,
                "total_specialization_points": total_points
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter resumo do progresso: {e}")
            return {}
    
    def get_player_statistics(self, db: Session, session_id: str) -> Dict[str, Any]:
        """
        Obtém estatísticas detalhadas sobre o progresso do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Estatísticas detalhadas
        """
        try:
            # Obter o resumo básico
            summary = self.get_progress_summary(db, session_id)
            if not summary:
                return {}
            
            # Obter o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {}
            
            # Obter ações do jogador
            action_history = self._ensure_list(progress.action_history)
            
            # Contar tipos de ações
            action_counts = {}
            for action in action_history:
                action_type = action.get("action_type", "unknown")
                if action_type not in action_counts:
                    action_counts[action_type] = 0
                action_counts[action_type] += 1
            
            # Calcular tempo de jogo
            start_time = summary.get("start_time")
            last_activity = summary.get("last_activity")
            
            play_time_seconds = 0
            if start_time and last_activity:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                
                play_time_seconds = (last_activity - start_time).total_seconds()
            
            # Calcular estatísticas adicionais
            return {
                **summary,
                "action_counts": action_counts,
                "total_actions": len(action_history),
                "play_time_seconds": play_time_seconds,
                "play_time_minutes": play_time_seconds / 60,
                "play_time_hours": play_time_seconds / 3600,
                "progress_percentage": self._calculate_progress_percentage(db, session_id, progress)
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas do jogador: {e}")
            return {}
    
    def _calculate_progress_percentage(self, db: Session, session_id: str, 
                                   progress: PlayerProgress) -> float:
        """
        Calcula o percentual de completude do jogo.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            progress: Objeto PlayerProgress
            
        Returns:
            Percentual de completude (0-100)
        """
        try:
            # Este cálculo depende dos objetivos específicos do jogo
            # Aqui está uma implementação simples baseada em descobertas
            
            story_id = progress.story_id
            
            # Contar totais disponíveis na história
            total_locations = db.query(func.count(Location.location_id)).join(
                Location.stories
            ).filter(
                Location.stories.any(story_id=story_id)
            ).scalar() or 0
            
            total_clues = db.query(func.count(Clue.clue_id)).filter(
                Clue.story_id == story_id
            ).scalar() or 0
            
            # Contar descobertos pelo jogador
            discovered_locations = len(self._ensure_list(progress.discovered_locations))
            discovered_clues = len(self._ensure_list(progress.discovered_clues))
            
            # Calcular percentuais individuais
            location_percent = (discovered_locations / total_locations * 100) if total_locations > 0 else 0
            clue_percent = (discovered_clues / total_clues * 100) if total_clues > 0 else 0
            
            # Média dos percentuais
            return (location_percent + clue_percent) / 2
        except Exception as e:
            self.logger.error(f"Erro ao calcular percentual de progresso: {e}")
            return 0
    
    # ===== MÉTODOS AUXILIARES =====
    
    def _ensure_list(self, value) -> list:
        """
        Garante que o valor seja uma lista Python.
        
        Args:
            value: Valor que pode ser uma string JSON, lista ou None
            
        Returns:
            Lista Python
        """
        if value is None:
            return []
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            try:
                result = json.loads(value)
                if isinstance(result, list):
                    return result
                return []
            except json.JSONDecodeError:
                return []
        
        return []
    
    def _ensure_dict(self, value) -> dict:
        """
        Garante que o valor seja um dicionário Python.
        
        Args:
            value: Valor que pode ser uma string JSON, dicionário ou None
            
        Returns:
            Dicionário Python
        """
        if value is None:
            return {}
        
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            try:
                result = json.loads(value)
                if isinstance(result, dict):
                    return result
                return {}
            except json.JSONDecodeError:
                return {}
        
        return {}
    
    def _add_action_to_history(self, progress: PlayerProgress, action_type: str, 
                           details: Dict[str, Any]) -> None:
        """
        Adiciona uma ação ao histórico do jogador.
        
        Args:
            progress: Objeto PlayerProgress
            action_type: Tipo de ação
            details: Detalhes da ação
        """
        # Criar registro de ação
        action = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "details": details
        }
        
        # Obter histórico atual
        action_history = self._ensure_list(progress.action_history)
        
        # Adicionar nova ação
        action_history.append(action)
        
        # Atualizar histórico no progresso
        progress.action_history = action_history
    
    def _get_object_level_data(self, db: Session, session_id: str, object_id: int) -> Dict[str, Any]:
        """
        Obtém dados detalhados sobre o nível atual de um objeto.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            object_id: ID do objeto
            
        Returns:
            Dados do nível atual do objeto
        """
        try:
            # Obter o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {"level": 0, "description": ""}
            
            # Obter o nível atual
            object_levels = self._ensure_dict(progress.object_level)
            current_level = object_levels.get(str(object_id), 0)
            
            # Buscar detalhes do nível
            level_data = db.query(ObjectLevel).filter(
                ObjectLevel.object_id == object_id,
                ObjectLevel.level_number == current_level
            ).first()
            
            if level_data:
                return {
                    "level": current_level,
                    "description": level_data.level_description,
                    "attributes": self._ensure_dict(level_data.level_attributes)
                }
            
            return {"level": current_level, "description": ""}
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de nível de objeto: {e}")
            return {"level": 0, "description": ""}
    
    def _calculate_level(self, points: int) -> int:
        """
        Calcula o nível com base nos pontos acumulados.
        
        Args:
            points: Pontos acumulados
            
        Returns:
            Nível calculado
        """
        # Esta é uma lógica simples, pode ser ajustada conforme necessário
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