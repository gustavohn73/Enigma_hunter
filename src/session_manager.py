# session_manager.py
import os
import json
import time
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from data_loader import DataLoader
from game_state import PlayerProgress, GameStateManager

class SessionManager:
    """
    Gerenciador de sessões e estado de jogo para o Enigma Hunter.
    
    Esta classe integra e coordena os diferentes componentes do jogo,
    gerenciando o ciclo de vida completo de uma sessão de jogo.
    """
    
    def __init__(self, data_loader: DataLoader, storage_dir: str = "database/sessions"):
        """
        Inicializa o gerenciador de sessões.
        
        Args:
            data_loader: Instância do DataLoader para acesso aos dados do jogo
            storage_dir: Diretório para armazenamento das sessões
        """
        self.data_loader = data_loader
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        
        self.game_state_manager = GameStateManager(str(self.storage_dir))
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Configura handler de log se não existir
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        self.logger.info("SessionManager inicializado.")
        
    def create_session(self, player_id: str, story_id: str) -> Dict[str, Any]:
        """
        Cria uma nova sessão de jogo para um jogador.
        
        Args:
            player_id: ID único do jogador
            story_id: ID da história/caso a ser jogado
            
        Returns:
            Dicionário com dados da sessão criada
        """
        # Verifica se a história existe
        if not self._verify_story_exists(story_id):
            self.logger.error(f"História {story_id} não encontrada. Não foi possível criar sessão.")
            return {"success": False, "error": "História não encontrada"}
        
        # Cria a sessão no GameStateManager
        progress = self.game_state_manager.create_session(player_id, story_id)
        session_id = progress.session_id
        
        # Inicializa o jogador na localização inicial da história
        starting_location = self._get_starting_location(story_id)
        if starting_location:
            progress.enter_location(starting_location)
            self.logger.info(f"Jogador posicionado na localização inicial {starting_location}")
        
        # Salva a sessão
        self.game_state_manager.save_session(session_id)
        
        # Cria entrada de metadados
        session_meta = {
            "session_id": session_id,
            "player_id": player_id,
            "story_id": story_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "status": "active"
        }
        
        # Armazena na lista de sessões ativas
        self.active_sessions[session_id] = session_meta
        
        self.logger.info(f"Sessão {session_id} criada para jogador {player_id}, história {story_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "created_at": session_meta["created_at"],
            "initial_location": starting_location
        }
        
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """
        Carrega uma sessão existente.
        
        Args:
            session_id: ID da sessão a ser carregada
            
        Returns:
            Dicionário com dados da sessão carregada ou erro
        """
        # Verifica se a sessão já está ativa
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = time.time()
            return {
                "success": True,
                "session_id": session_id,
                "session_data": self.active_sessions[session_id]
            }
        
        # Tenta carregar a sessão
        progress = self.game_state_manager.load_session(session_id)
        if not progress:
            self.logger.warning(f"Sessão {session_id} não encontrada.")
            return {"success": False, "error": "Sessão não encontrada"}
        
        # Recria os metadados
        session_meta = {
            "session_id": session_id,
            "player_id": progress.player_id,
            "story_id": progress.story_id,
            "created_at": progress.start_time,
            "last_activity": time.time(),
            "status": "active",
            "current_location": progress.current_location_id,
            "current_area": progress.current_area_id
        }
        
        # Armazena na lista de sessões ativas
        self.active_sessions[session_id] = session_meta
        
        self.logger.info(f"Sessão {session_id} carregada com sucesso.")
        
        return {
            "success": True,
            "session_id": session_id,
            "session_data": session_meta
        }
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém o estado atual de uma sessão de jogo.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Estado completo da sessão
        """
        # Carrega a sessão se não estiver ativa
        if session_id not in self.active_sessions:
            result = self.load_session(session_id)
            if not result["success"]:
                return {"success": False, "error": "Sessão não encontrada"}
        
        # Obtém o progresso do jogador
        progress = self.game_state_manager.load_session(session_id)
        if not progress:
            return {"success": False, "error": "Sessão corrompida"}
        
        # Atualiza timestamp de atividade
        self.active_sessions[session_id]["last_activity"] = time.time()
        
        # Constrói o estado completo
        state = self._build_session_state(progress)
        
        return {
            "success": True,
            "session_id": session_id,
            "state": state
        }
    
    def update_session_state(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza o estado de uma sessão com base nas ações do jogador.
        
        Args:
            session_id: ID da sessão
            updates: Dicionário com atualizações a serem aplicadas
            
        Returns:
            Estado atualizado da sessão
        """
        # Carrega a sessão
        progress = self.game_state_manager.load_session(session_id)
        if not progress:
            return {"success": False, "error": "Sessão não encontrada"}
        
        # Processa cada tipo de atualização
        for update_type, update_data in updates.items():
            if update_type == "location":
                progress.enter_location(update_data["location_id"])
                self.logger.info(f"Jogador moveu para localização {update_data['location_id']}")
                
            elif update_type == "area":
                progress.enter_area(update_data["area_id"])
                self.logger.info(f"Jogador entrou na área {update_data['area_id']}")
                
            elif update_type == "collect_object":
                progress.collect_object(update_data["object_id"])
                self.logger.info(f"Jogador coletou objeto {update_data['object_id']}")
                
            elif update_type == "discover_clue":
                progress.discover_clue(update_data["clue_id"])
                self.logger.info(f"Jogador descobriu pista {update_data['clue_id']}")
                
            elif update_type == "character_level":
                progress.update_character_level(
                    update_data["character_id"], 
                    update_data["level"]
                )
                self.logger.info(
                    f"Nível do personagem {update_data['character_id']} "
                    f"atualizado para {update_data['level']}"
                )
                
            elif update_type == "object_level":
                progress.update_object_level(
                    update_data["object_id"], 
                    update_data["level"]
                )
                self.logger.info(
                    f"Nível do objeto {update_data['object_id']} "
                    f"atualizado para {update_data['level']}"
                )
                
            elif update_type == "exploration_level":
                if "location_id" in update_data:
                    progress.update_location_exploration(
                        update_data["location_id"], 
                        update_data["level"]
                    )
                    self.logger.info(
                        f"Nível de exploração da localização {update_data['location_id']} "
                        f"atualizado para {update_data['level']}"
                    )
                elif "area_id" in update_data:
                    progress.update_area_exploration(
                        update_data["area_id"], 
                        update_data["level"]
                    )
                    self.logger.info(
                        f"Nível de exploração da área {update_data['area_id']} "
                        f"atualizado para {update_data['level']}"
                    )
            
            elif update_type == "dialogue":
                progress.add_dialogue(
                    update_data["character_id"],
                    update_data["player_input"],
                    update_data["character_response"],
                    update_data.get("detected_keywords", [])
                )
                self.logger.info(
                    f"Diálogo registrado com personagem {update_data['character_id']}"
                )
            
            elif update_type == "specialization":
                category_id = update_data["category_id"]
                points = update_data["points"]
                interaction_type = update_data["interaction_type"]
                interaction_id = update_data["interaction_id"]
                
                evolution, new_level = progress.add_specialization_points(
                    category_id, points, interaction_type, interaction_id
                )
                
                if evolution:
                    self.logger.info(
                        f"Jogador evoluiu em {category_id} para nível {new_level}"
                    )
        
        # Salva as alterações
        self.game_state_manager.save_session(session_id)
        
        # Atualiza timestamp de atividade
        self.active_sessions[session_id]["last_activity"] = time.time()
        
        # Retorna o estado atualizado
        return {
            "success": True,
            "session_id": session_id,
            "state": self._build_session_state(progress)
        }
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """
        Fecha uma sessão de jogo.
        
        Args:
            session_id: ID da sessão a ser fechada
            
        Returns:
            Status da operação
        """
        # Verifica se a sessão existe
        if session_id not in self.active_sessions:
            exists = self.game_state_manager.load_session(session_id) is not None
            if not exists:
                return {"success": False, "error": "Sessão não encontrada"}
        
        # Fecha a sessão no GameStateManager
        success = self.game_state_manager.close_session(session_id)
        
        # Remove da lista de sessões ativas
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
        if success:
            self.logger.info(f"Sessão {session_id} fechada com sucesso.")
            return {"success": True, "message": "Sessão fechada com sucesso"}
        else:
            self.logger.error(f"Erro ao fechar sessão {session_id}.")
            return {"success": False, "error": "Erro ao fechar sessão"}
            
    def list_player_sessions(self, player_id: str) -> Dict[str, Any]:
        """
        Lista todas as sessões de um jogador.
        
        Args:
            player_id: ID do jogador
            
        Returns:
            Lista de sessões do jogador
        """
        # Obtém lista de IDs de sessão do GameStateManager
        session_ids = self.game_state_manager.list_player_sessions(player_id)
        
        # Coleta metadados de cada sessão
        sessions = []
        for session_id in session_ids:
            # Verifica se está na lista de sessões ativas
            if session_id in self.active_sessions:
                sessions.append(self.active_sessions[session_id])
            else:
                # Tenta carregar a sessão
                progress = self.game_state_manager.load_session(session_id)
                if progress:
                    session_meta = {
                        "session_id": session_id,
                        "player_id": progress.player_id,
                        "story_id": progress.story_id,
                        "created_at": progress.start_time,
                        "last_activity": progress.last_activity,
                        "status": "inactive"
                    }
                    sessions.append(session_meta)
        
        return {
            "success": True,
            "player_id": player_id,
            "sessions": sessions
        }
    
    def clean_inactive_sessions(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Limpa sessões inativas da memória.
        
        Args:
            max_age_hours: Idade máxima em horas para manter sessões inativas
            
        Returns:
            Resultado da operação
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        
        sessions_to_remove = []
        for session_id, meta in self.active_sessions.items():
            if now - meta["last_activity"] > max_age_seconds:
                sessions_to_remove.append(session_id)
        
        # Remove as sessões inativas
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            
        self.logger.info(f"Removidas {len(sessions_to_remove)} sessões inativas.")
        
        return {
            "success": True,
            "removed_count": len(sessions_to_remove),
            "remaining_count": len(self.active_sessions)
        }
    
    def submit_solution(self, session_id: str, solution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submete uma solução para o mistério.
        
        Args:
            session_id: ID da sessão
            solution_data: Dados da solução (culpado, método, motivo, evidências)
            
        Returns:
            Resultado da verificação da solução
        """
        # Carrega a sessão
        progress = self.game_state_manager.load_session(session_id)
        if not progress:
            return {"success": False, "error": "Sessão não encontrada"}
        
        # Carrega os critérios de solução da história
        story_data = self.data_loader.data["historias"].get(progress.story_id, {})
        solution_criteria = story_data.get("solution_criteria", {})
        
        if not solution_criteria:
            self.logger.error(f"Critérios de solução não encontrados para história {progress.story_id}")
            return {"success": False, "error": "Critérios de solução não encontrados"}
        
        # Verifica a solução
        correct_culprit = solution_data.get("culprit_id") == solution_criteria.get("culprit_id")
        
        # Verifica palavras-chave para método e motivo
        method_keywords = solution_criteria.get("method_keywords", [])
        motive_keywords = solution_criteria.get("motive_keywords", [])
        
        method_text = solution_data.get("method", "").lower()
        motive_text = solution_data.get("motive", "").lower()
        
        method_correct = any(keyword.lower() in method_text for keyword in method_keywords)
        motive_correct = any(keyword.lower() in motive_text for keyword in motive_keywords)
        
        # Verifica se as evidências adequadas foram apresentadas
        evidences = solution_data.get("evidences", [])
        key_evidences = [
            clue["clue_id"] for clue in self.data_loader.data["pistas"]
            if clue.get("is_key_evidence") and clue["clue_id"] in progress.discovered_clues
        ]
        
        evidence_correct = all(ev in evidences for ev in key_evidences)
        
        # Determina o resultado final
        is_correct = correct_culprit and method_correct and motive_correct and evidence_correct
        
        # Marca a solução na sessão
        if "solutions" not in progress.session_data:
            progress.session_data["solutions"] = []
            
        solution_record = {
            "timestamp": time.time(),
            "culprit_id": solution_data.get("culprit_id"),
            "method": solution_data.get("method"),
            "motive": solution_data.get("motive"),
            "evidences": evidences,
            "is_correct": is_correct,
            "culprit_correct": correct_culprit,
            "method_correct": method_correct,
            "motive_correct": motive_correct,
            "evidence_correct": evidence_correct
        }
        
        progress.session_data["solutions"].append(solution_record)
        progress.session_data["solution_submitted"] = True
        progress.session_data["solution_correct"] = is_correct
        
        # Salva a sessão
        self.game_state_manager.save_session(session_id)
        
        # Gera feedback com base nos resultados
        feedback = self._generate_solution_feedback(
            is_correct, 
            correct_culprit, 
            method_correct, 
            motive_correct, 
            evidence_correct
        )
        
        result = {
            "success": True,
            "session_id": session_id,
            "is_correct": is_correct,
            "feedback": feedback,
            "details": {
                "culprit_correct": correct_culprit,
                "method_correct": method_correct,
                "motive_correct": motive_correct,
                "evidence_correct": evidence_correct
            }
        }
        
        if is_correct:
            # Adiciona a conclusão da história para solução correta
            result["conclusion"] = story_data.get("conclusion", "")
            self.logger.info(f"Solução correta submetida para sessão {session_id}!")
        else:
            self.logger.info(f"Solução incorreta submetida para sessão {session_id}")
            
        return result
    
    def get_available_hints(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém dicas disponíveis para o jogador com base no progresso atual.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Lista de dicas disponíveis
        """
        # Carrega a sessão
        progress = self.game_state_manager.load_session(session_id)
        if not progress:
            return {"success": False, "error": "Sessão não encontrada"}
        
        # Lógica para gerar dicas contextuais aqui...
        # Esta é apenas uma implementação de exemplo
        hints = []
        
        # Dica sobre localização atual
        if progress.current_location_id:
            location = self.data_loader.get_ambiente(progress.current_location_id)
            if location:
                areas_inexploradas = [
                    area for area in location.get("areas", [])
                    if area.get("area_id") not in progress.discovered_areas.get(progress.current_location_id, set())
                ]
                
                if areas_inexploradas:
                    hints.append({
                        "hint_type": "exploration",
                        "hint_level": 1,
                        "hint_text": f"Há {len(areas_inexploradas)} áreas que você ainda não explorou neste local."
                    })
        
        # Dica sobre objetos não coletados
        if progress.current_location_id and progress.current_area_id:
            objetos_area = [
                obj for obj in self.data_loader.data["objetos"]
                if obj.get("initial_location_id") == progress.current_location_id
                and obj.get("initial_area_id") == progress.current_area_id
                and obj.get("object_id") not in progress.inventory
            ]
            
            if objetos_area:
                hints.append({
                    "hint_type": "object",
                    "hint_level": 1,
                    "hint_text": f"Há {len(objetos_area)} objetos para examinar nesta área."
                })
        
        # Dica sobre personagens
        personagens_conhecidos = [p_id for p_id in progress.character_level.keys()]
        if personagens_conhecidos:
            personagens_nivel_baixo = [
                p_id for p_id in personagens_conhecidos
                if progress.character_level[p_id] < 2
            ]
            
            if personagens_nivel_baixo:
                hints.append({
                    "hint_type": "character",
                    "hint_level": 2,
                    "hint_text": "Alguns personagens podem saber mais do que revelaram até agora. Tente apresentar evidências relevantes durante as conversas."
                })
        
        return {
            "success": True,
            "session_id": session_id,
            "hints": hints
        }
    
    def _verify_story_exists(self, story_id: str) -> bool:
        """Verifica se uma história existe nos dados carregados"""
        return story_id in self.data_loader.data["historias"]
    
    def _get_starting_location(self, story_id: str) -> Optional[int]:
        """Obtém a localização inicial de uma história"""
        for location_id, location in self.data_loader.data["ambientes"].get(story_id, {}).items():
            if location.get("is_starting_location", False):
                return int(location_id)
        
        # Se nenhuma localização for marcada como inicial, usa a primeira
        locations = self.data_loader.data["ambientes"].get(story_id, {})
        if locations:
            return int(next(iter(locations.keys())))
        
        return None
    
    def _build_session_state(self, progress: PlayerProgress) -> Dict[str, Any]:
        """Constrói o estado completo da sessão para retornar ao cliente"""
        # Constrói o objeto de estado a partir do progresso
        state = {
            "player_id": progress.player_id,
            "story_id": progress.story_id,
            "session_id": progress.session_id,
            "start_time": progress.start_time,
            "last_activity": progress.last_activity,
            "current_location": progress.current_location_id,
            "current_area": progress.current_area_id,
            "inventory": list(progress.inventory),
            "discovered_clues": list(progress.discovered_clues),
            "character_levels": {str(k): v for k, v in progress.character_level.items()},
            "object_levels": {str(k): v for k, v in progress.object_level.items()},
            "exploration_levels": {
                "locations": {str(k): v for k, v in progress.location_exploration_level.items()},
                "areas": {str(k): v for k, v in progress.area_exploration_level.items()}
            },
            "specializations": {
                "points": progress.specialization_points,
                "levels": progress.specialization_levels
            },
            "solution_submitted": progress.session_data.get("solution_submitted", False),
            "solution_correct": progress.session_data.get("solution_correct", False)
        }
        
        # Adiciona dados enriquecidos (nomes de objetos, descrições, etc.)
        # se necessário para a interface
        
        return state
    
    def _generate_solution_feedback(self, is_correct: bool, culprit_correct: bool, 
                                   method_correct: bool, motive_correct: bool, 
                                   evidence_correct: bool) -> str:
        """Gera feedback personalizado para a solução submetida"""
        if is_correct:
            return "Parabéns! Sua solução está correta em todos os aspectos. Você resolveu o mistério completamente!"
        
        feedback = "Sua solução não está completamente correta.\n\n"
        
        if not culprit_correct:
            feedback += "- Você não identificou corretamente o culpado.\n"
        
        if not method_correct:
            feedback += "- Sua explicação sobre o método do crime não está precisa.\n"
        
        if not motive_correct:
            feedback += "- Sua compreensão do motivo não capturou a essência do caso.\n"
        
        if not evidence_correct:
            feedback += "- Você não apresentou todas as evidências-chave necessárias para sustentar sua teoria.\n"
        
        feedback += "\nContinue investigando e revise cuidadosamente as pistas que encontrou."
        
        return feedback