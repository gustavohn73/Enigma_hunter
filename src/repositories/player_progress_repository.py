# src/repositories/player_progress_repository.py
from sqlalchemy import func, text
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import logging
from datetime import datetime
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError  # Adicionar esta importação no topo do arquivo

from src.models.db_models import (
    PlayerProgress,
    Story,
    Player,
    PlayerSpecialization,
    PlayerInventory,
    PlayerObjectLevel,
    PlayerEnvironmentLevel,
    PlayerCharacterLevel,
    GameObject,
    Location,
    LocationArea,
    Clue,
    Character,
    ObjectLevel
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
        """Busca o progresso do jogador pelo ID da sessão."""
        if isinstance(session_id, dict):
            self.logger.error("session_id inválido (dicionário recebido): %s", session_id)
            return None
        
        try:
            return db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
        except SQLAlchemyError as e:
            self.logger.error("Erro ao buscar progresso para sessão %s: %s", session_id, e)
            return None

    def create_player_session(self, db: Session, player_id: str, story_id: int) -> Dict[str, Any]:
        """
        Cria uma nova sessão para o jogador.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            story_id: ID da história
            
        Returns:
            Dict com resultado da operação
        """
        try:
            # Buscar localização inicial da história
            initial_location = db.query(Location).filter(
                Location.story_id == story_id,
                Location.is_starting_location == True
            ).first()
            
            if not initial_location:
                return {"success": False, "error": "Localização inicial não encontrada"}
            
            # Criar nova sessão
            current_time = datetime.now()
            session_id = str(uuid4())
            
            # Criar objeto PlayerProgress com valores diretamente
            progress = PlayerProgress(
                session_id=session_id,
                player_id=player_id,
                story_id=story_id,
                current_location_id=initial_location.location_id,
                game_status='active',
                start_time=current_time,
                last_activity=current_time,
                created_at=current_time,
                updated_at=current_time,
                # Campos JSON como strings vazias ou valores padrão
                discovered_areas='{}',
                discovered_clues='[]',
                inventory='[]',
                location_exploration_level='{}',
                area_exploration_level='{}',
                object_level='{}',
                character_level='{}',
                dialogue_history='{}',
                specialization_points='{}',
                specialization_levels='{}',
                completed_interactions='{"objetos":[],"personagens":[],"areas":[],"pistas":[],"combinacoes":[]}',
                locations_visited='[]',
                objects_collected='[]',
                clues_discovered='[]',
                action_history='[]',
                scanned_qr_codes='[]',
                achievements='[]',
                # Campos numéricos
                completion_percentage=0.0,
                total_time_played=0,
                current_score=0
            )
            
            db.add(progress)
            db.commit()
            
            return {
                "success": True,
                "session_id": session_id,
                "location_id": initial_location.location_id
            }
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao criar sessão: {e}")
            return {"success": False, "error": str(e)}
    
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
        Registra uma área como descoberta pelo jogador e gerencia seu nível de exploração.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            area_id: ID da área
        """
        try:
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {"success": False, "message": "Sessão não encontrada"}
            
            area = db.query(LocationArea).filter(LocationArea.area_id == area_id).first()
            if not area:
                return {"success": False, "message": "Área não encontrada"}
            
            # Registrar área como descoberta
            discovered_areas = self._ensure_dict(progress.discovered_areas)
            location_id = str(area.location_id)
            is_new_discovery = False
            
            if location_id not in discovered_areas:
                discovered_areas[location_id] = {
                    "areas": [],
                    "last_visit": datetime.now().isoformat()
                }
                is_new_discovery = True
            
            if area_id not in discovered_areas[location_id]["areas"]:
                discovered_areas[location_id]["areas"].append(area_id)
                is_new_discovery = True
            
            # Atualizar níveis de exploração
            area_levels = self._ensure_dict(progress.area_exploration_level)
            current_level = area_levels.get(str(area_id), 0)
            
            if is_new_discovery:
                # Inicializar com nível 1 se for descoberta nova
                area_levels[str(area_id)] = 1
            else:
                # Incrementar nível baseado em visitas repetidas (máximo 5)
                visits = discovered_areas[location_id].get("visits", 0) + 1
                new_level = min(5, current_level + (1 if visits % 3 == 0 else 0))
                area_levels[str(area_id)] = new_level
            
            # Atualizar contagem de visitas
            discovered_areas[location_id]["visits"] = discovered_areas[location_id].get("visits", 0) + 1
            discovered_areas[location_id]["last_visit"] = datetime.now().isoformat()
            
            # Atualizar progresso
            progress.discovered_areas = discovered_areas
            progress.area_exploration_level = area_levels
            progress.current_area_id = area_id
            progress.last_activity = datetime.now()
            
            # Registrar no histórico
            self._add_action_to_history(progress, "discover_area", {
                "area_id": area_id,
                "location_id": location_id,
                "is_new": is_new_discovery,
                "current_level": area_levels[str(area_id)],
                "visits": discovered_areas[location_id]["visits"]
            })
            
            # Atualizar sistema tradicional
            env_progress = db.query(PlayerEnvironmentLevel).filter(
                PlayerEnvironmentLevel.session_id == session_id,
                PlayerEnvironmentLevel.location_id == location_id
            ).first()
            
            if not env_progress:
                env_progress = PlayerEnvironmentLevel(
                    session_id=session_id,
                    location_id=location_id,
                    exploration_level=1,
                    discovered_areas=[area_id],
                    last_exploration=datetime.now()
                )
                db.add(env_progress)
            else:
                if area_id not in env_progress.discovered_areas:
                    discovered = self._ensure_list(env_progress.discovered_areas)
                    discovered.append(area_id)
                    env_progress.discovered_areas = discovered
                env_progress.last_exploration = datetime.now()
            
            db.commit()
            
            return {
                "success": True,
                "message": "Área descoberta" if is_new_discovery else "Área revisitada",
                "is_new_discovery": is_new_discovery,
                "area_name": area.name,
                "area_id": area_id,
                "location_id": area.location_id,
                "exploration_level": area_levels[str(area_id)],
                "visits": discovered_areas[location_id]["visits"]
            }
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao descobrir área: {e}")
            return {"success": False, "message": str(e)}
    
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
            ).scalar() if inventory else None
            
            story_id = story if story else progress.story_id
            
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
            total_locations = db.query(func.count).select_from(Location).join(
                Location.stories
            ).filter(
                Location.stories.any(story_id=story_id)
            ).scalar() or 0
            
            total_clues = db.query(func.count).filter(Clue.story_id == story_id).scalar() or 0
            
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
    
    #===== MÉTODOS AUXILIARES =====
    
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

    def get_session_state(self, db: Session, session_id: str) -> Dict[str, Any]:
        """Obtém o estado atual da sessão do jogador."""
        try:
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {"success": False, "error": "Sessão não encontrada"}
                
            current_location = None
            current_area = None
            available_areas = []
            available_objects = []
            available_npcs = []
            
            # Buscar localização atual
            if progress.current_location_id:
                location = db.query(Location).filter(
                    Location.location_id == progress.current_location_id
                ).first()
                if location:
                    current_location = {
                        "id": location.location_id,
                        "name": location.name,
                        "description": location.description,
                    }
                    
                    # Buscar áreas disponíveis
                    areas = db.query(LocationArea).filter(
                        LocationArea.location_id == location.location_id
                    ).all()
                    available_areas = [{
                        "id": area.area_id,
                        "name": area.name,
                        "description": area.description
                    } for area in areas]
            
            # Buscar área atual e seus objetos/NPCs
            if progress.current_area_id:
                area = db.query(LocationArea).filter(
                    LocationArea.area_id == progress.current_area_id
                ).first()
                if area:
                    current_area = {
                        "id": area.area_id,
                        "name": area.name,
                        "description": area.description,
                    }
                    
                    # Buscar objetos na área usando initial_area_id
                    self.logger.info(f"Buscando objetos para área {area.area_id}")
                    objects = db.query(GameObject).filter(
                        GameObject.initial_area_id == area.area_id,
                        GameObject.story_id == progress.story_id
                    ).all()
                    
                    self.logger.info(f"Encontrados {len(objects)} objetos")
                    available_objects = [{
                        "id": obj.object_id,
                        "name": obj.name,
                        "description": obj.base_description,
                        "is_collectible": obj.is_collectible
                    } for obj in objects]
                    
                    # Buscar NPCs na área
                    npcs = db.query(Character).filter(
                        Character.area_id == area.area_id
                    ).all()
                    available_npcs = [{
                        "id": npc.character_id,
                        "name": npc.name,
                        "description": npc.base_description
                    } for npc in npcs]
            
            return {
                "success": True,
                "session_id": session_id,
                "current_location": current_location,
                "current_area": current_area,
                "available_areas": available_areas,
                "available_objects": available_objects,
                "available_npcs": available_npcs,
                "session": {
                    "player_id": progress.player_id,
                    "story_id": progress.story_id,
                    "game_status": progress.game_status
                }
            }
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar estado da sessão {session_id}: {e}")
            return {"success": False, "error": str(e)}

    def _get_default_state(self, error_message: str) -> Dict[str, Any]:
        """Retorna um estado padrão com mensagem de erro."""
        return {
            "success": False,
            "error": error_message,
            "current_location_id": None,
            "current_area_id": None,
            "inventory": [],
            "discovered_locations": [],
            "discovered_areas": {},
            "discovered_clues": []
        }

    def get_or_create_player(self, db: Session, username: str) -> Dict[str, Any]:
        """
        Busca um jogador pelo nome ou cria um novo se não existir.
        
        Args:
            db: Sessão do banco de dados
            username: Nome do jogador
            
        Returns:
            Dict com informações do jogador
        """
        try:

            current_time = datetime.now()

            # Buscar jogador existente
            player = db.query(Player).filter(Player.username == username).first()
            
            
            # Se não existe, criar novo
            if not player:
                player = Player(
                    player_id=str(uuid4()),
                    username=username,
                    created_at=current_time,
                    last_login=current_time,
                    updated_at=current_time,
                    games_played=0,
                    games_completed=0,
                    is_deleted=False
                )
                db.add(player)
            else:
                # Atualizar último login
                player.last_login = current_time
                player.updated_at = current_time
            
            db.commit()
            
            return {
                "success": True,
                "player": player,
                "player_id": player.player_id,
                "username": player.username,
                "is_new": player is None
            }
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao buscar/criar jogador: {e}")
            return {"success": False, "error": str(e)}

    def move_to_area(self, db: Session, session_id: str, area_id: int) -> Dict[str, Any]:
        """
        Move o jogador para uma área específica.

        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            area_id: ID da área de destino
            
        Returns:
            Dict indicando sucesso/falha da operação
        """
        try:
            # Buscar sessão do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {"success": False, "message": "Sessão não encontrada"}
                
            # Buscar a área
            area = db.query(LocationArea).filter(
                LocationArea.area_id == area_id
            ).first()
            
            if not area:
                return {"success": False, "message": "Área não encontrada"}
                
            current_time = datetime.now()
                
            # Atualizar área atual e timestamps
            progress.current_area_id = area_id
            progress.last_activity = current_time
            progress.updated_at = current_time
            
            # Registrar área como descoberta se necessário
            discovered_areas = json.loads(progress.discovered_areas) if progress.discovered_areas else {}
            location_id = str(area.location_id)
            
            if location_id not in discovered_areas:
                discovered_areas[location_id] = {
                    "areas": [],
                    "visits": 0,
                    "last_visit": current_time.isoformat()
                }
                
            if area_id not in discovered_areas[location_id]["areas"]:
                discovered_areas[location_id]["areas"].append(area_id)
            
            # Atualizar contagem de visitas
            discovered_areas[location_id]["visits"] = discovered_areas[location_id].get("visits", 0) + 1
            discovered_areas[location_id]["last_visit"] = current_time.isoformat()
            
            # Salvar alterações
            progress.discovered_areas = json.dumps(discovered_areas)
            
            # Registrar no histórico
            action_history = json.loads(progress.action_history) if progress.action_history else []
            action_history.append({
                "action": "move_to_area",
                "area_id": area_id,
                "timestamp": current_time.isoformat()
            })
            
            progress.action_history = json.dumps(action_history)
            
            # Realizar update diretamente com os valores corretos
            db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).update({
                "current_area_id": area_id,
                "discovered_areas": json.dumps(discovered_areas),
                "action_history": json.dumps(action_history),
                "last_activity": current_time,
                "updated_at": current_time
            })
            
            db.commit()
            
            return {
                "success": True,
                "message": f"Movido para {area.name}",
                "area_name": area.name,
                "area_description": area.description
            }
                
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao mover para área {area_id}: {e}")
            return {"success": False, "message": str(e)}

    def list_player_sessions(self, db: Session, player_name: str) -> List[Dict[str, Any]]:
        """
Lista todas as sessões de um jogador.
        
        Args:
            db: Sessão do banco de dados
            player_name: Nome do jogador
            
        Returns:
            Lista de sessões do jogador
"""
        try:
            # Buscar o jogador
            player = db.query(Player).filter(Player.username == player_name).first()
            if not player:
                return []
            
            # Buscar todas as sessões do jogador com join na história
            sessions = db.query(
                PlayerProgress, Story
            ).join(
                Story, Story.story_id == PlayerProgress.story_id
            ).filter(
                PlayerProgress.player_id == player.player_id
            ).all()
            
            # Converter para dicionários
            session_list = []
            for progress, story in sessions:
                session_list.append({
                    'session_id': progress.session_id,
                    'story_id': progress.story_id,
                    'story_title': story.title if story else "História Desconhecida",
                    'created_at': progress.created_at,
                    'game_status': progress.game_status
                })
                
            return session_list
            
        except Exception as e:
            self.logger.error(f"Erro ao listar sessões do jogador {player_name}: {e}")
            return []

    def update_player_location(self, db: Session, session_id: str, 
                             current_location_id: Optional[int] = None,
                             current_area_id: Optional[int] = None) -> Dict[str, Any]:
        """Atualiza a localização atual do jogador."""
        try:
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {"success": False, "error": "Sessão não encontrada"}
            
            if current_location_id is not None:
                progress.current_location_id = current_location_id
            if current_area_id is not None:
                progress.current_area_id = current_area_id
                
            progress.last_activity = datetime.now()
            db.commit()
            
            return {"success": True}
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar localização: {e}")
            return {"success": False, "error": str(e)}

    def save_game_state(self, db: Session, session_id: str) -> Dict[str, Any]:
        """Salva o estado atual do jogo."""
        try:
            current_time = datetime.now()
            
            # Fazer update direto com valores primitivos
            db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).update({
                PlayerProgress.game_status: "saved",
                PlayerProgress.updated_at: current_time,
                PlayerProgress.last_activity: current_time
            }, synchronize_session=False)
            
            db.commit()
            
            return {
                "success": True,
                "message": "Jogo salvo com sucesso"
            }
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao salvar jogo: {e}")
            return {"success": False, "error": str(e)}