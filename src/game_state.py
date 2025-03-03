# src/game_state.py
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

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
        
        # Histório de ações
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
        # Gera uma chave única para esta interação
        interaction_key = str(interaction_id)
        
        # Verifica se esta interação já foi completada
        if interaction_key in self.completed_interactions.get(interaction_type, set()):
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
            self.completed_interactions[interaction_type].add(interaction_key)
        
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
    
    def _calculate_specialization_level(self, category_id: str, data_loader) -> int:
        """
        🆕 Calcula o nível de especialização baseado nos pontos acumulados e na configuração carregada do jogo.
        
        Args:
            category_id: ID da categoria de especialização
            data_loader: Instância do DataLoader para obter os limites reais

        Returns:
            int: Nível atualizado
        """
        points = self.specialization_points.get(category_id, 0)
        
        # Obtém os limites reais do DataLoader
        categoria = data_loader.get_especializacao(category_id)
        if not categoria:
            return 0  # Se não há categoria registrada, mantém nível 0

        niveis = categoria.get("niveis", {})

        # Determina o nível máximo atingido com base nos pontos
        novo_nivel = 0
        for nivel, minimo in sorted(niveis.items(), key=lambda x: int(x[0])):
            if points >= minimo:
                novo_nivel = int(nivel)
            else:
                break

        self.specialization_levels[category_id] = novo_nivel
        return novo_nivel

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

    def can_interact(self, interaction_type: str, interaction_id: str, data_loader) -> bool:
        """
        🆕 Verifica se o jogador pode interagir com um objeto, NPC ou pista, considerando requisitos de especialização.

        Args:
            interaction_type (str): Tipo de interação ("objetos", "personagens", "areas", "pistas").
            interaction_id (str): ID do elemento a ser interagido.
            data_loader (DataLoader): Instância do DataLoader para acessar os requisitos.

        Returns:
            bool: True se o jogador puder interagir, False caso contrário.
        """
        requisitos = data_loader.data["especializacao"].get("interacoes", {}).get(interaction_type, {}).get(interaction_id, {}).get("requisitos_nivel", {})
        
        if not requisitos:
            return True  # Se não há requisitos, a interação é permitida
        
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
        # Só atualiza se for um nível maior que o atual
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
            
        # Só atualiza se for um nível maior que o atual
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
        # Só atualiza se for um nível maior que o atual
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
        # Só atualiza se for um nível maior que o atual
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
    
    def __init__(self, save_dir: str = "database"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True, parents=True)
        
        self.active_sessions: Dict[str, PlayerProgress] = {}
    
    def create_session(self, player_id: str, story_id: str) -> PlayerProgress:
        """
        Cria uma nova sessão de jogo para um jogador.
        """
        progress = PlayerProgress(player_id, story_id)
        self.active_sessions[progress.session_id] = progress
        return progress
    
    def load_session(self, session_id: str) -> Optional[PlayerProgress]:
        """
        Carrega uma sessão existente pelo ID.
        """
        # Verifica se a sessão já está ativa na memória
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Tenta carregar a sessão do disco
        session_file = self.save_dir / f"session_{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    progress = PlayerProgress.from_dict(data)
                    self.active_sessions[session_id] = progress
                    return progress
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Erro ao carregar a sessão {session_id}: {e}")
        
        return None
    
    def save_session(self, session_id: str) -> bool:
        """
        Salva uma sessão ativa no disco.
        """
        if session_id not in self.active_sessions:
            return False
        
        progress = self.active_sessions[session_id]
        session_file = self.save_dir / f"session_{session_id}.json"
        
        with open(session_file, 'w', encoding='utf-8') as file:
            json.dump(progress.to_dict(), file, indent=2)
        
        return True
    
    def close_session(self, session_id: str) -> bool:
        """
        Fecha uma sessão ativa, salvando-a antes.
        """
        if session_id not in self.active_sessions:
            return False
        
        # Salva a sessão antes de fechá-la
        self.save_session(session_id)
        
        # Remove da lista de sessões ativas
        del self.active_sessions[session_id]
        
        return True
    
    def list_player_sessions(self, player_id: str) -> List[str]:
        """
        Lista todas as sessões de um jogador específico.
        """
        # Verifica as sessões ativas na memória
        active_sessions = [
            session_id for session_id, progress in self.active_sessions.items()
            if progress.player_id == player_id
        ]
        
        # Verifica as sessões salvas no disco
        saved_sessions = []
        for file_path in self.save_dir.glob("session_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if data.get("player_id") == player_id:
                        saved_sessions.append(data.get("session_id"))
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Combina as sessões (removendo duplicatas)
        all_sessions = list(set(active_sessions + saved_sessions))
        return all_sessions
    
    def auto_save_all(self) -> int:
        """
        Salva automaticamente todas as sessões ativas.
        Retorna o número de sessões salvas.
        """
        count = 0
        for session_id in self.active_sessions:
            if self.save_session(session_id):
                count += 1
        return count

# Exemplo de uso
if __name__ == "__main__":
    manager = GameStateManager()
    
    # Cria uma nova sessão
    progress = manager.create_session("player123", "estalagem_cervo_negro")
    session_id = progress.session_id
    
    # Simula algumas ações do jogador
    progress.enter_location(1)  # Saguão Principal
    progress.enter_area(2)      # Área de Mesas
    progress.collect_object(10) # Taça de Vinho
    progress.discover_clue(2)   # Resíduos Estranhos
    
    # Registra um diálogo
    progress.add_dialogue(3, "Você sabe algo sobre ervas venenosas?", 
                         "Bem, eu cultivo algumas plantas medicinais no jardim, mas preciso ter cuidado com o Suspiro da Viúva...")
    
    # Salva a sessão
    manager.save_session(session_id)
    print(f"Sessão criada e salva: {session_id}")

    # Adicionando pontos de especialização
    evoluiu, novo_nivel = progress.add_specialization_points("cat_1", 20)
    print(f"Nova especialização em Análise de Evidências: Nível {novo_nivel} (Evoluiu: {evoluiu})")
    
    # Carrega a sessão
    loaded_progress = manager.load_session(session_id)
    print(f"Sessão carregada: {loaded_progress.session_id}")
    print(f"Local atual: {loaded_progress.current_location_id}, Área: {loaded_progress.current_area_id}")
    print(f"Inventário: {loaded_progress.inventory}")
    print(f"Pistas descobertas: {loaded_progress.discovered_clues}")


    
