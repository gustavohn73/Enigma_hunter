# src/game_state.py
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

class PlayerProgress:
    """
    Classe que representa o progresso de um jogador na história.
    Mantém o controle de localizações, áreas, níveis de personagens,
    objetos coletados, pistas descobertas, etc.
    """
    
    def __init__(self, player_id: str, story_id: str):
        self.player_id = player_id
        self.story_id = story_id
        self.session_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.last_activity = time.time()
        
        # Estado atual
        self.current_location_id: Optional[int] = None
        self.current_area_id: Optional[int] = None
        
        # Controle de progresso
        self.discovered_locations: Set[int] = set()
        self.discovered_areas: Dict[int, Set[int]] = {}  # location_id -> {area_id1, area_id2, ...}
        self.location_exploration_level: Dict[int, int] = {}  # location_id -> level
        self.area_exploration_level: Dict[int, int] = {}  # area_id -> level
        
        # Inventário e conhecimento
        self.inventory: Set[int] = set()  # object_ids
        self.object_level: Dict[int, int] = {}  # object_id -> level
        
        # Personagens e interações
        self.character_level: Dict[int, int] = {}  # character_id -> level
        self.dialogue_history: Dict[int, List[Dict]] = {}  # character_id -> [diálogos]
        
        # Pistas
        self.discovered_clues: Set[int] = set()  # clue_ids
        
        # QR Codes escaneados
        self.scanned_qr_codes: Set[str] = set()  # uuids
        
        # Histórico de ações
        self.action_history: List[Dict] = []

        # Atributos para o sistema de especialização
        self.specialization_points: Dict[str, int] = {}  # categoria_id -> pontos
        self.specialization_levels: Dict[str, int] = {}  # categoria_id -> nível
        self.completed_interactions: Dict[str, Set[str]] = {
            "objetos": set(),      # object_id:action (ex: "10:examine")
            "personagens": set(),  # character_id:keyword (ex: "3:ervas")
            "areas": set(),        # area_id:action (ex: "7:explore")
            "pistas": set(),       # clue_id:action (ex: "5:descoberta")
            "combinacoes": set()   # combinação_id (ex: "diario_paginas")
        }
        
    def add_specialization_points(self, category_id: str, points: int, 
                            interaction_type: str, interaction_id: str) -> Tuple[bool, int]:
        """
        Adiciona pontos de especialização em uma categoria específica.
        
        Args:
            category_id: ID da categoria de especialização
            points: Número de pontos a adicionar
            interaction_type: Tipo de interação ("objetos", "personagens", "areas", "pistas", "combinacoes")
            interaction_id: ID da interação específica
            
        Returns:
            Tupla (nível evoluiu, novo nível) indicando se houve evolução de nível
        """
        # Verifica se esta interação já foi completada
        interactions = self.completed_interactions.get(interaction_type, set())
        if interaction_id in interactions:
            return False, self.get_specialization_level(category_id)
            
        # Inicializa a categoria se não existir
        if category_id not in self.specialization_points:
            self.specialization_points[category_id] = 0
            self.specialization_levels[category_id] = 0
        
        # Adiciona os pontos
        previous_points = self.specialization_points[category_id]
        previous_level = self.specialization_levels[category_id]
        
        self.specialization_points[category_id] += points
        
        # Registra a interação como completada
        if interaction_type in self.completed_interactions:
            self.completed_interactions[interaction_type].add(interaction_id)
        
        # Recalcula o nível com base nos novos pontos
        new_level = self._calculate_specialization_level(category_id)
        
        # Registra a ação
        self._log_action("add_specialization", {
            "category_id": category_id,
            "points_added": points,
            "previous_points": previous_points,
            "new_points": self.specialization_points[category_id],
            "previous_level": previous_level,
            "new_level": new_level,
            "interaction_type": interaction_type,
            "interaction_id": interaction_id
        })
        
        # Retorna se houve evolução de nível
        return new_level > previous_level, new_level
    
    def _calculate_specialization_level(self, category_id: str) -> int:
        """
        Calcula o nível de especialização baseado nos pontos acumulados.
        
        Args:
            category_id: ID da categoria de especialização

        Returns:
            int: Nível atualizado
        """
        points = self.specialization_points.get(category_id, 0)
        
        # Calcula o nível baseado em limiares predefinidos
        if points < 20:
            nivel = 0
        elif points < 50:
            nivel = 1
        elif points < 100:
            nivel = 2
        elif points < 200:
            nivel = 3
        else:
            nivel = 4

        self.specialization_levels[category_id] = nivel
        return nivel

    def get_specialization_level(self, category_id: str) -> int:
        """
        Retorna o nível atual em uma categoria de especialização.
        
        Args:
            category_id: ID da categoria de especialização
            
        Returns:
            Nível atual na categoria
        """
        return self.specialization_levels.get(category_id, 0)

    def check_specialization_requirement(self, requirements: Dict[str, int]) -> bool:
        """
        Verifica se o jogador atende aos requisitos de especialização.
        
        Args:
            requirements: Dicionário de requisitos (categoria_id -> nível mínimo)
            
        Returns:
            True se todos os requisitos forem atendidos, False caso contrário
        """
        for category_id, required_level in requirements.items():
            current_level = self.get_specialization_level(category_id)
            if current_level < required_level:
                return False
        
        return True

    def can_interact(self, interaction_type: str, interaction_id: str,
                    requisitos: Dict[str, int] = None) -> bool:
        """
        Verifica se o jogador pode interagir com um objeto, NPC ou pista.

        Args:
            interaction_type (str): Tipo de interação ("objetos", "personagens", "areas", "pistas").
            interaction_id (str): ID do elemento a ser interagido.
            requisitos (Dict): Requisitos de especialização para a interação.

        Returns:
            bool: True se o jogador puder interagir, False caso contrário.
        """
        if not requisitos:
            return True
        
        return self.check_specialization_requirement(requisitos)

    def combine_objects(self, object_ids: List[int], combination_id: str, 
                    category_id: str, points: int) -> bool:
        """
        Registra a combinação de objetos e concede pontos de especialização.
        
        Args:
            object_ids: Lista de IDs dos objetos combinados
            combination_id: ID único da combinação
            category_id: Categoria de especialização a receber pontos
            points: Quantidade de pontos a conceder
            
        Returns:
            True se a combinação foi bem-sucedida, False caso contrário
        """
        # Verifica se todos os objetos estão no inventário
        for obj_id in object_ids:
            if obj_id not in self.inventory:
                return False
            
        # Adiciona pontos e registra a combinação
        evolved, _ = self.add_specialization_points(
            category_id, points, "combinacoes", combination_id
        )
        
        # Registra a ação
        self._log_action("combine_objects", {
            "object_ids": object_ids,
            "combination_id": combination_id,
            "category_id": category_id,
            "points": points,
            "success": True
        })
        
        return True

    def enter_location(self, location_id: int) -> None:
        """
        Registra a entrada do jogador em uma localização.
        Atualiza a localização atual e adiciona à lista de locais descobertos.
        """
        self.current_location_id = location_id
        self.current_area_id = None  # Reset da área atual ao mudar de localização
        self.discovered_locations.add(location_id)
        self.last_activity = time.time()
        
        # Inicializa o nível de exploração se for a primeira vez
        if location_id not in self.location_exploration_level:
            self.location_exploration_level[location_id] = 0
            
        # Inicializa o conjunto de áreas descobertas para esta localização
        if location_id not in self.discovered_areas:
            self.discovered_areas[location_id] = set()
            
        # Registra a ação
        self._log_action("enter_location", {"location_id": location_id})
    
    def enter_area(self, area_id: int) -> None:
        """
        Registra a entrada do jogador em uma área específica dentro da localização atual.
        """
        if self.current_location_id is None:
            raise ValueError("Não é possível entrar em uma área sem estar em uma localização")
            
        self.current_area_id = area_id
        
        # Adiciona à lista de áreas descobertas desta localização
        if self.current_location_id in self.discovered_areas:
            self.discovered_areas[self.current_location_id].add(area_id)
        else:
            self.discovered_areas[self.current_location_id] = {area_id}
        
        # Inicializa o nível de exploração da área se for a primeira vez
        if area_id not in self.area_exploration_level:
            self.area_exploration_level[area_id] = 0
            
        # Registra a ação
        self._log_action("enter_area", {"location_id": self.current_location_id, "area_id": area_id})
    
    def collect_object(self, object_id: int) -> None:
        """
        Adiciona um objeto ao inventário do jogador.
        """
        self.inventory.add(object_id)
        
        # Inicializa o nível do objeto se for a primeira vez
        if object_id not in self.object_level:
            self.object_level[object_id] = 0
            
        # Registra a ação
        self._log_action("collect_object", {"object_id": object_id})
    
    def discover_clue(self, clue_id: int) -> None:
        """
        Registra a descoberta de uma pista pelo jogador.
        """
        self.discovered_clues.add(clue_id)
        
        # Registra a ação
        self._log_action("discover_clue", {"clue_id": clue_id})
    
    def update_character_level(self, character_id: int, new_level: int) -> None:
        """
        Atualiza o nível de relacionamento com um personagem.
        """
        # Só atualiza se o novo nível for maior que o atual
        current_level = self.character_level.get(character_id, 0)
        if new_level > current_level:
            self.character_level[character_id] = new_level
            
            # Registra a ação
            self._log_action("character_evolution", {
                "character_id": character_id, 
                "old_level": current_level,
                "new_level": new_level
            })
    
    def update_object_level(self, object_id: int, new_level: int) -> None:
        """
        Atualiza o nível de conhecimento de um objeto.
        """
        # Verifica se o objeto está no inventário
        if object_id not in self.inventory:
            raise ValueError(f"Objeto {object_id} não está no inventário do jogador")
            
        # Só atualiza se o novo nível for maior que o atual
        current_level = self.object_level.get(object_id, 0)
        if new_level > current_level:
            self.object_level[object_id] = new_level
            
            # Registra a ação
            self._log_action("object_evolution", {
                "object_id": object_id, 
                "old_level": current_level,
                "new_level": new_level
            })
    
    def update_location_exploration(self, location_id: int, new_level: int) -> None:
        """
        Atualiza o nível de exploração de uma localização.
        """
        # Só atualiza se o novo nível for maior que o atual
        current_level = self.location_exploration_level.get(location_id, 0)
        if new_level > current_level:
            self.location_exploration_level[location_id] = new_level
            
            # Registra a ação
            self._log_action("location_evolution", {
                "location_id": location_id, 
                "old_level": current_level,
                "new_level": new_level
            })
    
    def update_area_exploration(self, area_id: int, new_level: int) -> None:
        """
        Atualiza o nível de exploração de uma área.
        """
        # Só atualiza se o novo nível for maior que o atual
        current_level = self.area_exploration_level.get(area_id, 0)
        if new_level > current_level:
            self.area_exploration_level[area_id] = new_level
            
            # Registra a ação
            self._log_action("area_evolution", {
                "area_id": area_id, 
                "old_level": current_level,
                "new_level": new_level
            })
    
    def add_dialogue(self, character_id: int, player_input: str, character_response: str, 
                    detected_keywords: List[str] = None) -> None:
        """
        Registra um diálogo entre o jogador e um personagem.
        """
        if character_id not in self.dialogue_history:
            self.dialogue_history[character_id] = []
            
        dialogue_entry = {
            "timestamp": time.time(),
            "player_input": player_input,
            "character_response": character_response,
            "detected_keywords": detected_keywords or [],
            "character_level": self.character_level.get(character_id, 0)
        }
        
        self.dialogue_history[character_id].append(dialogue_entry)
        
        # Registra a ação
        self._log_action("dialogue", {
            "character_id": character_id,
            "player_input_length": len(player_input),
            "response_length": len(character_response)
        })
    
    def scan_qr_code(self, uuid: str) -> None:
        """
        Registra o escaneamento de um QR code.
        """
        self.scanned_qr_codes.add(uuid)
        
        # Registra a ação
        self._log_action("scan_qr", {"uuid": uuid})
    
    def _log_action(self, action_type: str, details: Dict) -> None:
        """
        Registra uma ação no histórico.
        """
        action = {
            "timestamp": time.time(),
            "action_type": action_type,
            "details": details
        }
        
        self.action_history.append(action)
        self.last_activity = time.time()
    
    def to_dict(self) -> Dict:
        """
        Converte o progresso do jogador para um dicionário para serialização.
        """
        return {
            "player_id": self.player_id,
            "story_id": self.story_id,
            "session_id": self.session_id,
            "start_time": self.start_time,
            "last_activity": self.last_activity,
            "current_location_id": self.current_location_id,
            "current_area_id": self.current_area_id,
            "discovered_locations": list(self.discovered_locations),
            "discovered_areas": {str(k): list(v) for k, v in self.discovered_areas.items()},
            "location_exploration_level": {str(k): v for k, v in self.location_exploration_level.items()},
            "area_exploration_level": {str(k): v for k, v in self.area_exploration_level.items()},
            "inventory": list(self.inventory),
            "object_level": {str(k): v for k, v in self.object_level.items()},
            "character_level": {str(k): v for k, v in self.character_level.items()},
            "dialogue_history": self.dialogue_history,
            "discovered_clues": list(self.discovered_clues),
            "scanned_qr_codes": list(self.scanned_qr_codes),
            "action_history": self.action_history,
            "specialization_points": self.specialization_points,
            "specialization_levels": self.specialization_levels,
            "completed_interactions": {
                k: list(v) for k, v in self.completed_interactions.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PlayerProgress':
        """
        Cria uma instância de PlayerProgress a partir de um dicionário serializado.
        """
        progress = cls(data["player_id"], data["story_id"])
        progress.session_id = data["session_id"]
        progress.start_time = data["start_time"]
        progress.last_activity = data["last_activity"]
        progress.current_location_id = data["current_location_id"]
        progress.current_area_id = data["current_area_id"]
        progress.discovered_locations = set(data["discovered_locations"])
        progress.discovered_areas = {int(k): set(v) for k, v in data["discovered_areas"].items()}
        progress.location_exploration_level = {int(k): v for k, v in data["location_exploration_level"].items()}
        progress.area_exploration_level = {int(k): v for k, v in data["area_exploration_level"].items()}
        progress.inventory = set(data["inventory"])
        progress.object_level = {int(k): v for k, v in data["object_level"].items()}
        progress.character_level = {int(k): v for k, v in data["character_level"].items()}
        progress.dialogue_history = data["dialogue_history"]
        progress.discovered_clues = set(data["discovered_clues"])
        progress.scanned_qr_codes = set(data["scanned_qr_codes"])
        progress.action_history = data["action_history"]

        # Carrega os dados de especialização
        progress.specialization_points = data.get("specialization_points", {})
        progress.specialization_levels = data.get("specialization_levels", {})

        # Converte listas de volta para conjuntos
        completed_interactions = data.get("completed_interactions", {})
        progress.completed_interactions = {
            k: set(v) for k, v in completed_interactions.items()
        }
        return progress


class GameStateManager:
    """
    Gerencia o estado global do jogo, incluindo sessões ativas,
    progresso dos jogadores e persistência dos dados.
    """
    
    def __init__(self, db: Session, save_dir: str = "database"):
        self.db = db
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True, parents=True)
        self.active_sessions = {}
    
    def create_session(self, player_id: str, story_id: int) -> Dict[str, Any]:
        """
        Cria uma nova sessão de jogo para um jogador.
        
        Args:
            player_id: ID do jogador
            story_id: ID da história
            
        Returns:
            Informações sobre a sessão criada
        """
        try:
            # Cria o objeto de progresso do jogador
            progress = PlayerProgress(player_id, str(story_id))
            session_id = progress.session_id
            
            # Adiciona aos dados em memória
            self.active_sessions[session_id] = progress
            
            # Persiste os dados iniciais
            self._save_progress(progress)
            
            # Cria a entrada no banco de dados
            self._create_db_session(session_id, player_id, story_id)
            
            return {
                "session_id": session_id,
                "player_id": player_id,
                "story_id": story_id,
                "created_at": progress.start_time
            }
        except Exception as e:
            self.db.rollback()
            return {
                "error": str(e),
                "success": False
            }
    
    def load_session(self, session_id: str) -> Optional[PlayerProgress]:
        """
        Carrega uma sessão existente.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Objeto de progresso do jogador ou None se não encontrado
        """
        # Verifica se a sessão já está em memória
        if session_id in self.active_sessions:
            # Atualiza o timestamp de última atividade
            self.active_sessions[session_id].last_activity = time.time()
            return self.active_sessions[session_id]
        
        # Tenta carregar do arquivo
        progress = self._load_progress(session_id)
        if progress:
            # Adiciona aos dados em memória
            self.active_sessions[session_id] = progress
            
            # Atualiza o timestamp de última atividade no banco
            self._update_db_last_activity(session_id)
            
            return progress
            
        return None
    
    def save_session(self, session_id: str) -> bool:
        """
        Salva o estado de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se salvou com sucesso
        """
        if session_id not in self.active_sessions:
            return False
            
        progress = self.active_sessions[session_id]
        
        # Persiste os dados
        self._save_progress(progress)
        
        # Atualiza o timestamp de última atividade no banco
        self._update_db_last_activity(session_id)
        
        return True
    
    def update_session_state(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza o estado de uma sessão com base nas ações do jogador.
        
        Args:
            session_id: ID da sessão
            updates: Dicionário com atualizações a serem aplicadas
            
        Returns:
            Resultado da atualização
        """
        progress = self.load_session(session_id)
        if not progress:
            return {"success": False, "error": "Sessão não encontrada"}
        
        # Processa cada tipo de atualização
        try:
            for update_type, update_data in updates.items():
                if update_type == "location":
                    # Atualiza localização
                    location_id = update_data.get("location_id")
                    if location_id:
                        progress.enter_location(location_id)
                        
                elif update_type == "area":
                    # Atualiza área
                    area_id = update_data.get("area_id")
                    if area_id:
                        progress.enter_area(area_id)
                        
                elif update_type == "collect_object":
                    # Coleta objeto
                    object_id = update_data.get("object_id")
                    if object_id:
                        progress.collect_object(object_id)
                        
                elif update_type == "discover_clue":
                    # Descobre pista
                    clue_id = update_data.get("clue_id")
                    if clue_id:
                        progress.discover_clue(clue_id)
                        
                elif update_type == "character_level":
                    # Atualiza nível de personagem
                    character_id = update_data.get("character_id")
                    level = update_data.get("level")
                    if character_id is not None and level is not None:
                        progress.update_character_level(character_id, level)
                        
                elif update_type == "object_level":
                    # Atualiza nível de objeto
                    object_id = update_data.get("object_id")
                    level = update_data.get("level")
                    if object_id is not None and level is not None:
                        progress.update_object_level(object_id, level)
                        
                elif update_type == "location_exploration":
                    # Atualiza nível de exploração de localização
                    location_id = update_data.get("location_id")
                    level = update_data.get("level")
                    if location_id is not None and level is not None:
                        progress.update_location_exploration(location_id, level)
                        
                elif update_type == "area_exploration":
                    # Atualiza nível de exploração de área
                    area_id = update_data.get("area_id")
                    level = update_data.get("level")
                    if area_id is not None and level is not None:
                        progress.update_area_exploration(area_id, level)
                        
                elif update_type == "add_dialogue":
                    # Adiciona diálogo
                    character_id = update_data.get("character_id")
                    player_input = update_data.get("player_input")
                    character_response = update_data.get("character_response")
                    detected_keywords = update_data.get("detected_keywords")
                    
                    if character_id is not None and player_input and character_response:
                        progress.add_dialogue(character_id, player_input, character_response, detected_keywords)
                        
                elif update_type == "scan_qr_code":
                    # Escaneia QR code
                    uuid = update_data.get("uuid")
                    if uuid:
                        progress.scan_qr_code(uuid)
                        
                elif update_type == "specialization":
                    # Atualiza especialização
                    category_id = update_data.get("category_id")
                    points = update_data.get("points")
                    interaction_type = update_data.get("interaction_type")
                    interaction_id = update_data.get("interaction_id")
                    
                    if category_id and points and interaction_type and interaction_id:
                        progress.add_specialization_points(category_id, points, interaction_type, interaction_id)
                        
                elif update_type == "combine_objects":
                    # Combina objetos
                    object_ids = update_data.get("object_ids")
                    combination_id = update_data.get("combination_id")
                    category_id = update_data.get("category_id")
                    points = update_data.get("points")
                    
                    if object_ids and combination_id and category_id and points:
                        progress.combine_objects(object_ids, combination_id, category_id, points)
            
            # Salva as alterações
            self.save_session(session_id)
            
            return {
                "success": True,
                "session_id": session_id,
                "updates_applied": list(updates.keys())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def close_session(self, session_id: str) -> bool:
        """
        Fecha uma sessão de jogo.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se fechada com sucesso
        """
        if session_id not in self.active_sessions:
            return False
            
        # Salva o estado final
        self.save_session(session_id)
        
        # Atualiza o status no banco
        self._update_db_status(session_id, 'completed')
        
        # Remove da memória
        del self.active_sessions[session_id]
        
        return True
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém o estado atual de uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dicionário com o estado atual ou None se a sessão não for encontrada
        """
        progress = self.load_session(session_id)
        if not progress:
            return None
            
        return progress.to_dict()
    
    def list_player_sessions(self, player_id: str) -> List[Dict[str, Any]]:
        """
        Lista todas as sessões de um jogador.
        
        Args:
            player_id: ID do jogador
            
        Returns:
            Lista de informações sobre as sessões
        """
        # Busca as sessões no banco de dados
        from src.models.db_models import PlayerSession
        
        sessions = self.db.query(PlayerSession).filter(
            PlayerSession.player_id == player_id
        ).all()
        
        result = []
        for session in sessions:
            # Tenta carregar mais detalhes da memória ou do arquivo
            active_session = None
            if session.session_id in self.active_sessions:
                active_session = self.active_sessions[session.session_id]
            
            session_data = {
                "session_id": session.session_id,
                "player_id": player_id,
                "story_id": session.story_id,
                "start_time": session.start_time,
                "last_activity": session.last_activity,
                "status": session.game_status
            }
            
            if active_session:
                session_data.update({
                    "current_location": active_session.current_location_id,
                    "inventory_size": len(active_session.inventory),
                    "discovered_clues": len(active_session.discovered_clues)
                })
                
            result.append(session_data)
            return result
    
    def clean_inactive_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessões inativas da memória.
        
        Args:
            max_age_hours: Idade máxima em horas para considerar uma sessão inativa
            
        Returns:
            Número de sessões removidas
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        sessions_to_remove = []
        
        for session_id, progress in self.active_sessions.items():
            # Verifica se a sessão está inativa por muito tempo
            if current_time - progress.last_activity > max_age_seconds:
                sessions_to_remove.append(session_id)
        
        # Remove as sessões inativas
        for session_id in sessions_to_remove:
            # Salva o estado antes de remover
            self.save_session(session_id)
            del self.active_sessions[session_id]
        
        return len(sessions_to_remove)
    
    # Métodos auxiliares privados
    
    def _save_progress(self, progress: PlayerProgress) -> bool:
        """
        Salva o progresso em arquivo.
        
        Args:
            progress: Objeto PlayerProgress
            
        Returns:
            True se salvou com sucesso
        """
        try:
            # Transforma em dicionário
            data = progress.to_dict()
            
            # Define o caminho do arquivo
            file_path = self.save_dir / f"{progress.session_id}.json"
            
            # Salva no arquivo
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"Erro ao salvar progresso: {str(e)}")
            return False
    
    def _load_progress(self, session_id: str) -> Optional[PlayerProgress]:
        """
        Carrega o progresso de um arquivo.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Objeto PlayerProgress ou None se não encontrado
        """
        try:
            # Define o caminho do arquivo
            file_path = self.save_dir / f"{session_id}.json"
            
            # Verifica se o arquivo existe
            if not file_path.exists():
                return None
                
            # Carrega do arquivo
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Cria o objeto PlayerProgress
            return PlayerProgress.from_dict(data)
        except Exception as e:
            print(f"Erro ao carregar progresso: {str(e)}")
            return None
    
    def _create_db_session(self, session_id: str, player_id: str, story_id: int) -> None:
        """
        Cria uma entrada para a sessão no banco de dados.
        
        Args:
            session_id: ID da sessão
            player_id: ID do jogador
            story_id: ID da história
        """
        from src.models.db_models import PlayerSession
        
        try:
            # Cria a sessão no banco
            db_session = PlayerSession(
                session_id=session_id,
                player_id=player_id,
                story_id=story_id,
                start_time=datetime.now(),
                last_activity=datetime.now(),
                game_status='active',
                solution_submitted=False
            )
            
            self.db.add(db_session)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao criar sessão no banco: {str(e)}")
    
    def _update_db_last_activity(self, session_id: str) -> None:
        """
        Atualiza o timestamp de última atividade no banco.
        
        Args:
            session_id: ID da sessão
        """
        from src.models.db_models import PlayerSession
        
        try:
            # Busca a sessão no banco
            db_session = self.db.query(PlayerSession).filter(
                PlayerSession.session_id == session_id
            ).first()
            
            if db_session:
                # Atualiza o timestamp
                db_session.last_activity = datetime.now()
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao atualizar última atividade no banco: {str(e)}")
    
    def _update_db_status(self, session_id: str, status: str) -> None:
        """
        Atualiza o status de uma sessão no banco.
        
        Args:
            session_id: ID da sessão
            status: Novo status
        """
        from src.models.db_models import PlayerSession
        
        try:
            # Busca a sessão no banco
            db_session = self.db.query(PlayerSession).filter(
                PlayerSession.session_id == session_id
            ).first()
            
            if db_session:
                # Atualiza o status
                db_session.game_status = status
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Erro ao atualizar status no banco: {str(e)}")

class GameProgressService:
    """
    Serviço para gerenciar a lógica de evolução e progresso do jogo.
    Centraliza os cálculos relacionados à progressão de níveis e regras de negócio.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_specialization_level(self, points: int, thresholds: Dict[str, int] = None) -> int:
        """
        Calcula o nível de especialização com base nos pontos acumulados.
        
        Args:
            points: Pontos acumulados
            thresholds: Dicionário com limiares para cada nível (opcional)
            
        Returns:
            Nível calculado
        """
        # Limiares padrão se não fornecidos
        if not thresholds:
            thresholds = {
                "0": 0,
                "1": 20,
                "2": 50,
                "3": 100,
                "4": 200
            }
        
        # Encontra o nível apropriado
        level = 0
        for level_str, min_points in sorted(thresholds.items(), key=lambda x: int(x[0])):
            if points >= min_points:
                level = int(level_str)
            else:
                break
                
        return level
    
    def evaluate_character_evolution(self, session_id: str, character_id: int, 
                                  trigger_id: int, response: str, 
                                  evidence_ids: List[int] = None) -> Dict[str, Any]:
        """
        Avalia se um personagem deve evoluir com base na resposta a um gatilho.
        
        Args:
            session_id: ID da sessão
            character_id: ID do personagem
            trigger_id: ID do gatilho
            response: Resposta do jogador
            evidence_ids: IDs de evidências apresentadas
            
        Returns:
            Resultado da avaliação
        """
        from src.models.db_models import EvolutionTrigger, EvidenceRequirement
        
        try:
            # Busca o gatilho
            trigger = self.db.query(EvolutionTrigger).filter(
                EvolutionTrigger.trigger_id == trigger_id
            ).first()
            
            if not trigger:
                return {
                    "success": False,
                    "evolve": False,
                    "reason": "Gatilho não encontrado"
                }
            
            # Busca os requisitos
            requirements = self.db.query(EvidenceRequirement).filter(
                EvidenceRequirement.trigger_id == trigger_id
            ).all()
            
            # Verifica cada requisito
            missing_requirements = []
            
            for req in requirements:
                if req.requirement_type == "object" and evidence_ids:
                    required_object_id = self._get_required_object_id(req)
                    
                    if required_object_id not in evidence_ids:
                        missing_requirements.append({
                            "type": "object",
                            "id": required_object_id,
                            "hint": req.hint_if_incorrect
                        })
                elif req.requirement_type == "knowledge":
                    # Implementação simplificada para verificar conhecimento
                    # Em um sistema real, seria mais sofisticado
                    required_keywords = self._get_required_knowledge_keywords(req)
                    
                    if not any(keyword.lower() in response.lower() for keyword in required_keywords):
                        missing_requirements.append({
                            "type": "knowledge",
                            "hint": req.hint_if_incorrect
                        })
            
            # Determina se deve evoluir
            should_evolve = len(missing_requirements) == 0
            
            if should_evolve:
                return {
                    "success": True,
                    "evolve": True,
                    "response": trigger.success_response
                }
            else:
                return {
                    "success": True,
                    "evolve": False,
                    "response": trigger.fail_response,
                    "missing_requirements": missing_requirements
                }
        except Exception as e:
            return {
                "success": False,
                "evolve": False,
                "reason": str(e)
            }
    
    def evaluate_object_evolution(self, session_id: str, object_id: int, 
                               current_level: int) -> Dict[str, Any]:
        """
        Avalia se um objeto pode evoluir para o próximo nível.
        
        Args:
            session_id: ID da sessão
            object_id: ID do objeto
            current_level: Nível atual do objeto
            
        Returns:
            Resultado da avaliação
        """
        from src.models.db_models import ObjectLevel
        
        try:
            # Busca o próximo nível
            next_level_data = self.db.query(ObjectLevel).filter(
                ObjectLevel.object_id == object_id,
                ObjectLevel.level_number == current_level + 1
            ).first()
            
            if not next_level_data:
                return {
                    "success": True,
                    "can_evolve": False,
                    "reason": "Objeto já está no nível máximo"
                }
                
            # Verifica se há requisitos para evolução
            # Em um sistema real, verificaria condições específicas
            
            return {
                "success": True,
                "can_evolve": True,
                "next_level": current_level + 1,
                "requirements": {
                    "evolution_trigger": next_level_data.evolution_trigger
                }
            }
        except Exception as e:
            return {
                "success": False,
                "can_evolve": False,
                "reason": str(e)
            }
    
    def evaluate_location_evolution(self, session_id: str, location_id: int, 
                                 current_level: int) -> Dict[str, Any]:
        """
        Avalia se uma localização pode evoluir para o próximo nível.
        
        Args:
            session_id: ID da sessão
            location_id: ID da localização
            current_level: Nível atual da localização
            
        Returns:
            Resultado da avaliação
        """
        # Em um sistema real, verificaria descobertas na localização, 
        # interações com objetos e NPCs, etc.
        
        # Implementação simplificada
        return {
            "success": True,
            "can_evolve": True,
            "next_level": current_level + 1
        }
    
    # Métodos auxiliares privados
    
    def _get_required_object_id(self, requirement: Any) -> Optional[int]:
        """
        Extrai o ID do objeto necessário de um requisito.
        
        Args:
            requirement: Objeto EvidenceRequirement
            
        Returns:
            ID do objeto ou None
        """
        if hasattr(requirement, 'required_object_id'):
            if isinstance(requirement.required_object_id, int):
                return requirement.required_object_id
            elif isinstance(requirement.required_object_id, str):
                try:
                    # Pode estar armazenado como JSON
                    data = json.loads(requirement.required_object_id)
                    if isinstance(data, int):
                        return data
                    elif isinstance(data, list) and data:
                        return data[0]  # Retorna o primeiro se for lista
                except json.JSONDecodeError:
                    # Tenta converter diretamente
                    try:
                        return int(requirement.required_object_id)
                    except ValueError:
                        pass
        
        return None
    
    def _get_required_knowledge_keywords(self, requirement: Any) -> List[str]:
        """
        Extrai palavras-chave de conhecimento necessárias.
        
        Args:
            requirement: Objeto EvidenceRequirement
            
        Returns:
            Lista de palavras-chave
        """
        keywords = []
        
        if hasattr(requirement, 'required_knowledge'):
            data = requirement.required_knowledge
            
            if isinstance(data, str):
                try:
                    # Pode estar armazenado como JSON
                    json_data = json.loads(data)
                    if isinstance(json_data, dict) and 'keywords' in json_data:
                        keywords = json_data['keywords']
                    elif isinstance(json_data, list):
                        keywords = json_data
                except json.JSONDecodeError:
                    # Se não for JSON, adiciona como string
                    keywords = [data]
            elif isinstance(data, dict) and 'keywords' in data:
                keywords = data['keywords']
            elif isinstance(data, list):
                keywords = data
        
        return keywords