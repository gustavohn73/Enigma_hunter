# src/repositories/player_progress_repository.py
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import logging

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

logger = logging.getLogger(__name__)

class PlayerProgressRepository(BaseRepository[PlayerProgress]):
    """
    Repositório para operações de banco de dados relacionadas ao progresso dos jogadores.
    Gerencia especializações, inventário, áreas descobertas e outros aspectos do progresso.
    """
    
    def __init__(self):
        super().__init__(PlayerProgress)
        self.logger = logger
    
    def get_by_id(self, db: Session, progress_id: int) -> Optional[PlayerProgress]:
        """
        Busca um progresso pelo ID.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            
        Returns:
            Progresso encontrado ou None
        """
        try:
            return db.query(PlayerProgress).filter(
                PlayerProgress.id == progress_id
            ).first()
        except Exception as e:
            self.logger.error(f"Erro ao buscar progresso por ID: {str(e)}")
            return None
    
    def get_by_session_id(self, db: Session, session_id: str) -> Optional[PlayerProgress]:
        """
        Busca um progresso pelo ID da sessão.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Progresso encontrado ou None
        """
        try:
            return db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
        except Exception as e:
            self.logger.error(f"Erro ao buscar progresso por session_id: {str(e)}")
            return None
    
    def get_active_session(self, db: Session, player_id: str) -> Optional[PlayerSession]:
        """
        Obtém a sessão ativa de um jogador.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            
        Returns:
            Sessão ativa ou None
        """
        try:
            return db.query(PlayerSession).filter(
                PlayerSession.player_id == player_id,
                PlayerSession.game_status == 'active'
            ).order_by(PlayerSession.start_time.desc()).first()
        except Exception as e:
            self.logger.error(f"Erro ao buscar sessão ativa: {str(e)}")
            return None
    
    def get_specializations(self, db: Session, session_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Obtém as especializações do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Dicionário com categorias e detalhes de especialização
        """
        try:
            specializations = db.query(PlayerSpecialization).filter(
                PlayerSpecialization.session_id == session_id
            ).all()
            
            result = {}
            for spec in specializations:
                result[spec.category_id] = {
                    "points": spec.points,
                    "level": spec.level,
                    "bonus_multiplier": spec.bonus_multiplier,
                    "completed_interactions": json.loads(spec.completed_interactions) if isinstance(spec.completed_interactions, str) else spec.completed_interactions
                }
                
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar especializações: {str(e)}")
            return {}
    
    def update_specialization(self, db: Session, session_id: str, category_id: str, 
                           points: int, interaction_type: str = None, 
                           interaction_id: str = None) -> Dict[str, Any]:
        """
        Atualiza os pontos de especialização de um jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            category_id: ID da categoria de especialização
            points: Pontos a adicionar
            interaction_type: Tipo de interação (opcional)
            interaction_id: ID da interação (opcional)
            
        Returns:
            Resultado da atualização
        """
        try:
            # Busca a especialização existente
            specialization = db.query(PlayerSpecialization).filter(
                PlayerSpecialization.session_id == session_id,
                PlayerSpecialization.category_id == category_id
            ).first()
            
            is_new_level = False
            old_level = 0
            
            # Se não existe, cria uma nova
            if not specialization:
                specialization = PlayerSpecialization(
                    session_id=session_id,
                    category_id=category_id,
                    points=points,
                    level=0,  # Será calculado abaixo
                    bonus_multiplier=1.0,
                    completed_interactions=json.dumps({})
                )
                db.add(specialization)
                is_new_level = True
            else:
                old_level = specialization.level
                
                # Verifica se esta interação já foi completada
                if interaction_type and interaction_id:
                    completed = specialization.completed_interactions
                    if isinstance(completed, str):
                        try:
                            completed_dict = json.loads(completed)
                        except json.JSONDecodeError:
                            completed_dict = {}
                    else:
                        completed_dict = completed or {}
                    
                    # Se a interação já foi completada, não adiciona pontos
                    if interaction_type in completed_dict and interaction_id in completed_dict[interaction_type]:
                        return {
                            "success": True,
                            "points_added": 0,
                            "new_points": specialization.points,
                            "old_level": specialization.level,
                            "new_level": specialization.level,
                            "level_up": False
                        }
                    
                    # Marca a interação como completada
                    if interaction_type not in completed_dict:
                        completed_dict[interaction_type] = []
                    
                    if interaction_id not in completed_dict[interaction_type]:
                        completed_dict[interaction_type].append(interaction_id)
                        
                    specialization.completed_interactions = json.dumps(completed_dict)
                
                # Adiciona os pontos
                specialization.points += points
            
            # Calcula o novo nível
            new_level = self._calculate_level(specialization.points)
            if new_level > old_level:
                is_new_level = True
                
            specialization.level = new_level
            
            db.commit()
            
            return {
                "success": True,
                "points_added": points,
                "new_points": specialization.points,
                "old_level": old_level,
                "new_level": new_level,
                "level_up": is_new_level
            }
        except Exception as e:
            self.logger.error(f"Erro ao atualizar especialização: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_inventory(self, db: Session, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtém o inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Lista de objetos no inventário com detalhes
        """
        try:
            inventory_items = db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id
            ).all()
            
            result = []
            for item in inventory_items:
                # Busca informações detalhadas do objeto
                game_object = db.query(GameObject).filter(
                    GameObject.object_id == item.object_id
                ).first()
                
                if game_object:
                    result.append({
                        "inventory_id": item.inventory_id,
                        "object_id": item.object_id,
                        "acquired_time": item.acquired_time,
                        "acquisition_method": item.acquisition_method,
                        "name": game_object.name,
                        "description": game_object.base_description
                    })
                else:
                    result.append({
                        "inventory_id": item.inventory_id,
                        "object_id": item.object_id,
                        "acquired_time": item.acquired_time,
                        "acquisition_method": item.acquisition_method,
                        "name": "Objeto Desconhecido",
                        "description": "Descrição não disponível"
                    })
                    
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar inventário: {str(e)}")
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
            Resultado da adição
        """
        try:
            # Verifica se o objeto já está no inventário
            existing_item = db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id,
                PlayerInventory.object_id == object_id
            ).first()
            
            if existing_item:
                return {
                    "success": True,
                    "message": "Objeto já está no inventário",
                    "inventory_id": existing_item.inventory_id,
                    "is_new": False
                }
                
            # Adiciona o objeto ao inventário
            inventory_item = PlayerInventory(
                session_id=session_id,
                object_id=object_id,
                acquisition_method=acquisition_method,
                acquired_time=func.now()
            )
            
            db.add(inventory_item)
            db.commit()
            db.refresh(inventory_item)
            
            # Atualiza o progresso do jogador para facilitar consultas
            progress = self.get_by_session_id(db, session_id)
            if progress:
                inventory = progress.inventory
                if isinstance(inventory, str):
                    try:
                        inventory_list = json.loads(inventory)
                        if object_id not in inventory_list:
                            inventory_list.append(object_id)
                        progress.inventory = json.dumps(inventory_list)
                    except json.JSONDecodeError:
                        progress.inventory = json.dumps([object_id])
                elif isinstance(inventory, list):
                    if object_id not in inventory:
                        inventory.append(object_id)
                    progress.inventory = inventory
                else:
                    progress.inventory = [object_id]
                
                db.commit()
            
            return {
                "success": True,
                "message": "Objeto adicionado ao inventário",
                "inventory_id": inventory_item.inventory_id,
                "is_new": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao adicionar objeto ao inventário: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def remove_from_inventory(self, db: Session, session_id: str, object_id: int) -> Dict[str, Any]:
        """
        Remove um objeto do inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            object_id: ID do objeto
            
        Returns:
            Resultado da remoção
        """
        try:
            # Busca o item no inventário
            inventory_item = db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id,
                PlayerInventory.object_id == object_id
            ).first()
            
            if not inventory_item:
                return {
                    "success": False,
                    "message": "Objeto não encontrado no inventário"
                }
                
            # Remove o item
            db.delete(inventory_item)
            
            # Atualiza o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if progress:
                inventory = progress.inventory
                if isinstance(inventory, str):
                    try:
                        inventory_list = json.loads(inventory)
                        if object_id in inventory_list:
                            inventory_list.remove(object_id)
                        progress.inventory = json.dumps(inventory_list)
                    except json.JSONDecodeError:
                        pass
                elif isinstance(inventory, list):
                    if object_id in inventory:
                        inventory.remove(object_id)
                    progress.inventory = inventory
            
            db.commit()
            
            return {
                "success": True,
                "message": "Objeto removido do inventário"
            }
        except Exception as e:
            self.logger.error(f"Erro ao remover objeto do inventário: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def discover_location(self, db: Session, session_id: str, location_id: int) -> Dict[str, Any]:
        """
        Registra uma localização como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            location_id: ID da localização
            
        Returns:
            Resultado da descoberta
        """
        try:
            # Obtém o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {
                    "success": False,
                    "message": "Progresso não encontrado"
                }
                
            # Atualiza a localização atual
            progress.current_location_id = location_id
            
            # Adiciona à lista de localizações descobertas
            discovered_locations = progress.discovered_locations
            is_new_discovery = False
            
            if isinstance(discovered_locations, str):
                try:
                    locations_list = json.loads(discovered_locations)
                    if location_id not in locations_list:
                        locations_list.append(location_id)
                        is_new_discovery = True
                    progress.discovered_locations = json.dumps(locations_list)
                except json.JSONDecodeError:
                    progress.discovered_locations = json.dumps([location_id])
                    is_new_discovery = True
            elif isinstance(discovered_locations, list):
                if location_id not in discovered_locations:
                    discovered_locations.append(location_id)
                    is_new_discovery = True
                progress.discovered_locations = discovered_locations
            else:
                progress.discovered_locations = [location_id]
                is_new_discovery = True
            
            db.commit()
            
            # Busca detalhes da localização para retornar
            location_details = db.query(Location).filter(
                Location.location_id == location_id
            ).first()
            
            return {
                "success": True,
                "message": "Localização descoberta" if is_new_discovery else "Localização já descoberta",
                "is_new_discovery": is_new_discovery,
                "location_name": location_details.name if location_details else "Local Desconhecido",
                "location_id": location_id
            }
        except Exception as e:
            self.logger.error(f"Erro ao descobrir localização: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def discover_area(self, db: Session, session_id: str, area_id: int) -> Dict[str, Any]:
        """
        Registra uma área como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            area_id: ID da área
            
        Returns:
            Resultado da descoberta
        """
        try:
            # Obtém o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {
                    "success": False,
                    "message": "Progresso não encontrado"
                }
                
            # Atualiza a área atual
            progress.current_area_id = area_id
            
            # Busca informações da área para saber a localização
            area_details = db.query(LocationArea).filter(
                LocationArea.area_id == area_id
            ).first()
            
            if not area_details:
                return {
                    "success": False,
                    "message": "Área não encontrada"
                }
                
            location_id = area_details.location_id
            
            # Adiciona à lista de áreas descobertas
            discovered_areas = progress.discovered_areas
            is_new_discovery = False
            
            if isinstance(discovered_areas, str):
                try:
                    areas_dict = json.loads(discovered_areas)
                    loc_key = str(location_id)
                    if loc_key not in areas_dict:
                        areas_dict[loc_key] = []
                    if area_id not in areas_dict[loc_key]:
                        areas_dict[loc_key].append(area_id)
                        is_new_discovery = True
                    progress.discovered_areas = json.dumps(areas_dict)
                except json.JSONDecodeError:
                    areas_dict = {str(location_id): [area_id]}
                    progress.discovered_areas = json.dumps(areas_dict)
                    is_new_discovery = True
            elif isinstance(discovered_areas, dict):
                loc_key = str(location_id)
                if loc_key not in discovered_areas:
                    discovered_areas[loc_key] = []
                if area_id not in discovered_areas[loc_key]:
                    discovered_areas[loc_key].append(area_id)
                    is_new_discovery = True
                progress.discovered_areas = discovered_areas
            else:
                progress.discovered_areas = {str(location_id): [area_id]}
                is_new_discovery = True
            
            db.commit()
            
            return {
                "success": True,
                "message": "Área descoberta" if is_new_discovery else "Área já descoberta",
                "is_new_discovery": is_new_discovery,
                "area_name": area_details.name if area_details else "Área Desconhecida",
                "area_id": area_id,
                "location_id": location_id
            }
        except Exception as e:
            self.logger.error(f"Erro ao descobrir área: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def discover_clue(self, db: Session, session_id: str, clue_id: int) -> Dict[str, Any]:
        """
        Registra uma pista como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            clue_id: ID da pista
            
        Returns:
            Resultado da descoberta
        """
        try:
            # Obtém o progresso do jogador
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {
                    "success": False,
                    "message": "Progresso não encontrado"
                }
                
            # Adiciona à lista de pistas descobertas
            discovered_clues = progress.discovered_clues
            is_new_discovery = False
            
            if isinstance(discovered_clues, str):
                try:
                    clues_list = json.loads(discovered_clues)
                    if clue_id not in clues_list:
                        clues_list.append(clue_id)
                        is_new_discovery = True
                    progress.discovered_clues = json.dumps(clues_list)
                except json.JSONDecodeError:
                    progress.discovered_clues = json.dumps([clue_id])
                    is_new_discovery = True
            elif isinstance(discovered_clues, list):
                if clue_id not in discovered_clues:
                    discovered_clues.append(clue_id)
                    is_new_discovery = True
                progress.discovered_clues = discovered_clues
            else:
                progress.discovered_clues = [clue_id]
                is_new_discovery = True
            
            # Busca detalhes da pista
            clue_details = db.query(Clue).filter(
                Clue.clue_id == clue_id
            ).first()
            
            # Se é uma nova descoberta e temos os detalhes da pista, adicionamos pontos de especialização
            if is_new_discovery and clue_details:
                # Busca a categoria de especialização associada à pista (se houver)
                # Este é um exemplo, adapte conforme a estrutura real da sua tabela de pistas
                specialization_category = None
                specialization_points = 0
                
                if hasattr(clue_details, 'specialization_category'):
                    specialization_category = clue_details.specialization_category
                    
                if hasattr(clue_details, 'specialization_points'):
                    specialization_points = clue_details.specialization_points
                    
                # Se temos uma categoria e pontos, atualizamos a especialização
                if specialization_category and specialization_points > 0:
                    self.update_specialization(
                        db, 
                        session_id, 
                        specialization_category, 
                        specialization_points,
                        "pistas",
                        str(clue_id)
                    )
            
            db.commit()
            
            return {
                "success": True,
                "message": "Pista descoberta" if is_new_discovery else "Pista já descoberta",
                "is_new_discovery": is_new_discovery,
                "clue_name": clue_details.name if clue_details else "Pista Desconhecida",
                "clue_id": clue_id
            }
        except Exception as e:
            self.logger.error(f"Erro ao descobrir pista: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_character_progress(self, db: Session, session_id: str, character_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtém o progresso do jogador com personagens.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem específico (opcional)
            
        Returns:
            Lista de progresso com personagens
        """
        try:
            query = db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id
            )
            
            if character_id is not None:
                query = query.filter(PlayerCharacterLevel.character_id == character_id)
                
            characters_progress = query.all()
            
            result = []
            for progress in characters_progress:
                result.append({
                    "character_id": progress.character_id,
                    "current_level": progress.current_level,
                    "last_interaction": progress.last_interaction,
                    "triggered_keywords": json.loads(progress.triggered_keywords) if isinstance(progress.triggered_keywords, str) else progress.triggered_keywords
                })
                
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar progresso de personagens: {str(e)}")
            return []
    
    def update_character_progress(self, db: Session, session_id: str, character_id: int, 
                               level: int) -> Dict[str, Any]:
        """
        Atualiza o progresso do jogador com um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            level: Novo nível
            
        Returns:
            Resultado da atualização
        """
        try:
            progress = db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id,
                PlayerCharacterLevel.character_id == character_id
            ).first()
            
            is_new_level = False
            old_level = 0
            
            if not progress:
                progress = PlayerCharacterLevel(
                    session_id=session_id,
                    character_id=character_id,
                    current_level=level,
                    last_interaction=func.now(),
                    triggered_keywords=json.dumps([])
                )
                db.add(progress)
                is_new_level = True
            else:
                old_level = progress.current_level
                # Só atualiza se o novo nível for maior
                if level > progress.current_level:
                    progress.current_level = level
                    progress.last_interaction = func.now()
                    is_new_level = True
                    
            db.commit()
            
            return {
                "success": True,
                "character_id": character_id,
                "old_level": old_level,
                "new_level": level,
                "level_up": is_new_level
            }
        except Exception as e:
            self.logger.error(f"Erro ao atualizar progresso de personagem: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_object_progress(self, db: Session, session_id: str, object_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtém o progresso do jogador com objetos.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            object_id: ID do objeto específico (opcional)
            
        Returns:
            Lista de progresso com objetos
        """
        try:
            query = db.query(PlayerObjectLevel).filter(
                PlayerObjectLevel.session_id == session_id
            )
            
            if object_id is not None:
                query = query.filter(PlayerObjectLevel.object_id == object_id)
                
            objects_progress = query.all()
            
            result = []
            for progress in objects_progress:
                result.append({
                    "object_id": progress.object_id,
                    "current_level": progress.current_level,
                    "unlocked_details": json.loads(progress.unlocked_details) if isinstance(progress.unlocked_details, str) else progress.unlocked_details,
                    "last_interaction": progress.last_interaction
                })
                
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar progresso de objetos: {str(e)}")
            return []
    
    def update_object_progress(self, db: Session, session_id: str, object_id: int, 
                            level: int) -> Dict[str, Any]:
        """
        Atualiza o progresso do jogador com um objeto.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            object_id: ID do objeto
            level: Novo nível
            
        Returns:
            Resultado da atualização
        """
        try:
            progress = db.query(PlayerObjectLevel).filter(
                PlayerObjectLevel.session_id == session_id,
                PlayerObjectLevel.object_id == object_id
            ).first()
            
            is_new_level = False
            old_level = 0
            
            if not progress:
                progress = PlayerObjectLevel(
                    session_id=session_id,
                    object_id=object_id,
                    current_level=level,
                    unlocked_details=json.dumps([]),
                    last_interaction=func.now(),
                    interaction_history=json.dumps([])
                )
                db.add(progress)
                is_new_level = True
            else:
                old_level = progress.current_level
                # Só atualiza se o novo nível for maior
                if level > progress.current_level:
                    progress.current_level = level
                    progress.last_interaction = func.now()
                    is_new_level = True
                    
            db.commit()
            
            return {
                "success": True,
                "object_id": object_id,
                "old_level": old_level,
                "new_level": level,
                "level_up": is_new_level
            }
        except Exception as e:
            self.logger.error(f"Erro ao atualizar progresso de objeto: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_environment_progress(self, db: Session, session_id: str, location_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtém o progresso do jogador com ambientes.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            location_id: ID da localização específica (opcional)
            
        Returns:
            Lista de progresso com ambientes
        """
        try:
            query = db.query(PlayerEnvironmentLevel).filter(
                PlayerEnvironmentLevel.session_id == session_id
            )
            
            if location_id is not None:
                query = query.filter(PlayerEnvironmentLevel.location_id == location_id)
                
            env_progress = query.all()
            
            result = []
            for progress in env_progress:
                result.append({
                    "location_id": progress.location_id,
                    "exploration_level": progress.exploration_level,
                    "discovered_areas": json.loads(progress.discovered_areas) if isinstance(progress.discovered_areas, str) else progress.discovered_areas,
                    "discovered_details": json.loads(progress.discovered_details) if isinstance(progress.discovered_details, str) else progress.discovered_details,
                    "last_exploration": progress.last_exploration
                })
                
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar progresso de ambientes: {str(e)}")
            return []
    
def update_environment_progress(self, db: Session, session_id: str, location_id: int, 
                                 level: int) -> Dict[str, Any]:
        """
        Atualiza o progresso do jogador com um ambiente.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            location_id: ID da localização
            level: Novo nível
            
        Returns:
            Resultado da atualização
        """
        try:
            progress = db.query(PlayerEnvironmentLevel).filter(
                PlayerEnvironmentLevel.session_id == session_id,
                PlayerEnvironmentLevel.location_id == location_id
            ).first()
            
            is_new_level = False
            old_level = 0
            
            if not progress:
                progress = PlayerEnvironmentLevel(
                    session_id=session_id,
                    location_id=location_id,
                    exploration_level=level,
                    discovered_areas=json.dumps([]),
                    discovered_details=json.dumps([]),
                    last_exploration=func.now()
                )
                db.add(progress)
                is_new_level = True
            else:
                old_level = progress.exploration_level
                # Só atualiza se o novo nível for maior
                if level > progress.exploration_level:
                    progress.exploration_level = level
                    progress.last_exploration = func.now()
                    is_new_level = True
                    
            db.commit()
            
            return {
                "success": True,
                "location_id": location_id,
                "old_level": old_level,
                "new_level": level,
                "level_up": is_new_level
            }
        except Exception as e:
            self.logger.error(f"Erro ao atualizar progresso de ambiente: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_progress_summary(self, db: Session, session_id: str) -> Dict[str, Any]:
        """
        Obtém um resumo do progresso do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Dicionário com resumo do progresso
        """
        try:
            progress = self.get_by_session_id(db, session_id)
            if not progress:
                return {}
            
            # Contagem de itens no inventário
            inventory_count = 0
            if isinstance(progress.inventory, str):
                try:
                    inventory_list = json.loads(progress.inventory)
                    inventory_count = len(inventory_list)
                except json.JSONDecodeError:
                    pass
            elif isinstance(progress.inventory, list):
                inventory_count = len(progress.inventory)
            
            # Contagem de localizações descobertas
            locations_count = 0
            if isinstance(progress.discovered_locations, str):
                try:
                    locations_list = json.loads(progress.discovered_locations)
                    locations_count = len(locations_list)
                except json.JSONDecodeError:
                    pass
            elif isinstance(progress.discovered_locations, list):
                locations_count = len(progress.discovered_locations)
            
            # Contagem de áreas descobertas
            areas_count = 0
            if isinstance(progress.discovered_areas, str):
                try:
                    areas_dict = json.loads(progress.discovered_areas)
                    for loc_key, areas in areas_dict.items():
                        areas_count += len(areas)
                except json.JSONDecodeError:
                    pass
            elif isinstance(progress.discovered_areas, dict):
                for loc_key, areas in progress.discovered_areas.items():
                    areas_count += len(areas)
            
            # Contagem de pistas descobertas
            clues_count = 0
            if isinstance(progress.discovered_clues, str):
                try:
                    clues_list = json.loads(progress.discovered_clues)
                    clues_count = len(clues_list)
                except json.JSONDecodeError:
                    pass
            elif isinstance(progress.discovered_clues, list):
                clues_count = len(progress.discovered_clues)
            
            # Obtém especializações
            specializations = self.get_specializations(db, session_id)
            
            # Calcula pontos totais
            total_points = sum(spec.get("points", 0) for spec in specializations.values())
            
            return {
                "player_id": progress.player_id,
                "story_id": progress.story_id,
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
            self.logger.error(f"Erro ao obter resumo do progresso: {str(e)}")
            return {}
    
    def _calculate_level(self, points: int) -> int:
        """
        Calcula o nível com base nos pontos acumulados.
        
        Args:
            points: Pontos acumulados
            
        Returns:
            Nível calculado
        """
        # Esta é uma implementação simples. Em uma implementação real,
        # você pode definir limiares mais complexos ou buscar os valores do banco de dados.
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