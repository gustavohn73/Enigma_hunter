from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime
import json
import logging

from src.models.db_models import (
    DialogueHistory,
    Character,
    PlayerSession,
    CharacterLevel,
    EvolutionTrigger,
    PlayerInventory,
    PlayerDiscoveredClues,
    ActiveTrigger,
    EvidenceRequirement
)
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class DialogueRepository(BaseRepository[DialogueHistory]):
    """
    Repositório para operações de banco de dados relacionadas a diálogos.
    """
    
    def __init__(self):
        super().__init__(DialogueHistory)
        self.logger = logger
    
    def get_active_session(self, db: Session, player_id: int) -> Optional[PlayerSession]:
        """
        Obtém a sessão ativa de um jogador.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            
        Returns:
            Sessão ativa ou None
        """
        return db.query(PlayerSession).filter(
            PlayerSession.player_id == player_id,
            PlayerSession.game_status == 'active'
        ).order_by(PlayerSession.start_time.desc()).first()
    
    def get_dialogue_history(self, db: Session, player_id: int, character_id: int, 
                           limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de diálogo entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            limit: Número máximo de mensagens
            
        Returns:
            Lista de mensagens do histórico
        """
        session = self.get_active_session(db, player_id)
        if not session:
            return []
        
        dialogue_history = db.query(DialogueHistory).filter(
            DialogueHistory.session_id == session.session_id,
            DialogueHistory.character_id == character_id
        ).order_by(DialogueHistory.timestamp.desc()).limit(limit).all()
        
        return [{
            "role": "user" if entry.player_statement else "assistant",
            "content": entry.player_statement or entry.character_response,
            "timestamp": entry.timestamp,
            "detected_keywords": entry.detected_keywords,
            "character_level": entry.character_level
        } for entry in reversed(dialogue_history)]
    
    def add_dialogue_entry(self, db: Session, player_id: int, character_id: int,
                          player_statement: str, character_response: str,
                          detected_keywords: List[str] = None,
                          character_level: int = 0) -> bool:
        """
        Adiciona uma entrada ao histórico de diálogo.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            player_statement: Mensagem do jogador
            character_response: Resposta do personagem
            detected_keywords: Palavras-chave detectadas
            character_level: Nível atual do personagem
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            session = self.get_active_session(db, player_id)
            if not session:
                return False
            
            entry = DialogueHistory(
                session_id=session.session_id,
                character_id=character_id,
                player_statement=player_statement,
                character_response=character_response,
                detected_keywords=detected_keywords or [],
                character_level=character_level,
                timestamp=datetime.utcnow()
            )
            
            db.add(entry)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            return False
    
    def get_trigger_history(self, db: Session, player_id: int, character_id: int) -> List[Dict[str, Any]]:
        """
        Obtém histórico de gatilhos ativados em diálogos.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            
        Returns:
            Lista de gatilhos ativados
        """
        session = self.get_active_session(db, player_id)
        if not session:
            return []
        
        dialogues = db.query(DialogueHistory).filter(
            DialogueHistory.session_id == session.session_id,
            DialogueHistory.character_id == character_id,
            DialogueHistory.detected_keywords != []
        ).order_by(DialogueHistory.timestamp).all()
        
        return [{
            "timestamp": dialogue.timestamp,
            "keywords": dialogue.detected_keywords,
            "level": dialogue.character_level,
            "context": {
                "player_statement": dialogue.player_statement,
                "character_response": dialogue.character_response
            }
        } for dialogue in dialogues]
    
    def get_key_interactions(self, db: Session, player_id: int, character_id: int) -> List[Dict[str, Any]]:
        """
        Obtém interações importantes com gatilhos ou evoluções.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            
        Returns:
            Lista de interações importantes
        """
        session = self.get_active_session(db, player_id)
        if not session:
            return []
        
        return db.query(DialogueHistory).filter(
            DialogueHistory.session_id == session.session_id,
            DialogueHistory.character_id == character_id,
            DialogueHistory.is_key_interaction == True
        ).order_by(DialogueHistory.timestamp).all()
    
    def get_by_id(self, db: Session, dialogue_id: int) -> Optional[DialogueHistory]:
        """
        Busca um diálogo pelo ID.
        
        Args:
            db: Sessão do banco de dados
            dialogue_id: ID do diálogo
            
        Returns:
            Diálogo encontrado ou None
        """
        return db.query(DialogueHistory).filter(DialogueHistory.dialogue_id == dialogue_id).first()
    
    def get_player_dialogue_history(self, db: Session, player_id: int, character_id: Optional[int] = None) -> List[DialogueHistory]:
        """
        Busca o histórico de diálogos de um jogador.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem (opcional)
            
        Returns:
            Lista de diálogos do jogador
        """
        query = db.query(DialogueHistory).filter(DialogueHistory.player_id == player_id)
        
        if character_id:
            query = query.filter(DialogueHistory.character_id == character_id)
            
        return query.order_by(DialogueHistory.timestamp.desc()).all()
    
    def get_character_dialogue_context(self, db: Session, character_id: int, player_id: int) -> Dict[str, Any]:
        """
        Obtém o contexto de diálogo atual entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            player_id: ID do jogador
            
        Returns:
            Dicionário com o contexto do diálogo
        """
        # Busca o nível atual do personagem para este jogador
        character_level = db.query(CharacterLevel).filter(
            CharacterLevel.character_id == character_id
        ).order_by(CharacterLevel.level_number.desc()).first()
        
        # Busca os últimos diálogos
        recent_dialogues = db.query(DialogueHistory).filter(
            DialogueHistory.character_id == character_id,
            DialogueHistory.player_id == player_id
        ).order_by(DialogueHistory.timestamp.desc()).limit(5).all()
        
        return {
            "character_level": character_level.level_number if character_level else 0,
            "recent_dialogues": recent_dialogues,
            "last_interaction": recent_dialogues[0].timestamp if recent_dialogues else None,
            "total_interactions": db.query(func.count(DialogueHistory.dialogue_id)).filter(
                DialogueHistory.character_id == character_id,
                DialogueHistory.player_id == player_id
            ).scalar()
        }
    
    def create_dialogue(self, db: Session, dialogue_data: Dict[str, Any]) -> DialogueHistory:
        """Corrigindo player_message para player_statement"""
        dialogue = DialogueHistory(
            player_id=dialogue_data["player_id"],
            character_id=dialogue_data["character_id"],
            player_statement=dialogue_data.get("player_statement"),  # Corrigido
            character_response=dialogue_data.get("character_response"),
            detected_keywords=dialogue_data.get("detected_keywords", []),
            context_level=dialogue_data.get("context_level", 0),
            timestamp=dialogue_data.get("timestamp", datetime.utcnow()),
            is_key_interaction=dialogue_data.get("is_key_interaction", False),
            trigger_id=dialogue_data.get("trigger_id")  # Corrigido
        )
        
        db.add(dialogue)
        db.commit()
        db.refresh(dialogue)
        
        return dialogue
    
    def update_dialogue_context(self, db: Session, dialogue_id: int, context_data: Dict[str, Any]) -> Optional[DialogueHistory]:
        """
        Atualiza o contexto de um diálogo.
        
        Args:
            db: Sessão do banco de dados
            dialogue_id: ID do diálogo
            context_data: Dados do contexto a serem atualizados
            
        Returns:
            Diálogo atualizado ou None
        """
        dialogue = self.get_by_id(db, dialogue_id)
        if not dialogue:
            return None
            
        for key, value in context_data.items():
            setattr(dialogue, key, value)
            
        db.commit()
        db.refresh(dialogue)
        
        return dialogue
    
    def get_evolution_triggers(self, db: Session, dialogue_id: int) -> List[Dict[str, Any]]:
        """
        Obtém os gatilhos de evolução detectados em um diálogo.
        
        Args:
            db: Sessão do banco de dados
            dialogue_id: ID do diálogo
            
        Returns:
            Lista de gatilhos de evolução
        """
        dialogue = self.get_by_id(db, dialogue_id)
        if not dialogue:
            return []
            
        return dialogue.evolution_triggers
    
    def check_triggers(self, db: Session, player_id: int, character_id: int, message: str) -> List[Dict[str, Any]]:
        """Adicionando tratamento de erros"""
        try:
            triggers = db.query(EvolutionTrigger).join(
                CharacterLevel, 
                CharacterLevel.level_id == EvolutionTrigger.level_id
            ).filter(
                CharacterLevel.character_id == character_id
            ).all()
            
            activated_triggers = []
            message_lower = message.lower()
            
            for trigger in triggers:
                if trigger.trigger_keyword.lower() in message_lower:
                    activated_triggers.append({
                        "trigger_id": trigger.trigger_id,
                        "keyword": trigger.trigger_keyword,
                        "defensive_response": trigger.defensive_response,
                        "challenge_question": trigger.challenge_question,
                        "level_id": trigger.level_id
                    })
            
            return activated_triggers
        except Exception as e:
            logging.error(f"Erro ao verificar triggers: {str(e)}")
            return []

    def check_evolution_requirements(self, db: Session, player_id: int, character_id: int, 
                                trigger_id: int) -> Dict[str, bool]:
        """
        Verifica se os requisitos para evolução do personagem foram atendidos.
        """
        # Busca os requisitos do gatilho
        requirements = db.query(EvidenceRequirement).filter(
            EvidenceRequirement.trigger_id == trigger_id
        ).all()
        
        if not requirements:
            return {"met": True, "missing": []}
        
        # Verifica cada requisito
        missing_requirements = []
        for req in requirements:
            if req.requirement_type == "object":
                # Verifica se o jogador tem o objeto necessário
                has_object = db.query(PlayerInventory).filter(
                    PlayerInventory.player_id == player_id,
                    PlayerInventory.object_id == req.required_object_id
                ).first() is not None
                
                if not has_object:
                    missing_requirements.append({
                        "type": "object",
                        "id": req.required_object_id,
                        "hint": req.hint_if_incorrect
                    })
                    
            elif req.requirement_type == "knowledge":
                # Verifica se o jogador descobriu as pistas necessárias
                required_knowledge = json.loads(req.required_knowledge)
                for clue_id in required_knowledge.get("required_clues", []):
                    has_clue = db.query(PlayerDiscoveredClues).filter(
                        PlayerDiscoveredClues.player_id == player_id,
                        PlayerDiscoveredClues.clue_id == clue_id
                    ).first() is not None
                    
                    if not has_clue:
                        missing_requirements.append({
                            "type": "knowledge",
                            "clue_id": clue_id,
                            "hint": req.hint_if_incorrect
                        })
        
        return {
            "met": len(missing_requirements) == 0,
            "missing": missing_requirements
        }

    def get_evolution_history(self, db: Session, player_id: int, character_id: int) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de evolução do relacionamento entre jogador e personagem.
        """
        history = db.query(DialogueHistory).filter(
            DialogueHistory.player_id == player_id,
            DialogueHistory.character_id == character_id,
            DialogueHistory.evolution_event == True
        ).order_by(DialogueHistory.timestamp).all()
        
        return [{
            "timestamp": entry.timestamp,
            "old_level": entry.character_level,
            "new_level": entry.character_level + 1,
            "trigger_id": entry.trigger_id,
            "dialogue_context": {
                "player_statement": entry.player_statement,
                "character_response": entry.character_response
            }
        } for entry in history]

    def get_dialogue_state(self, db: Session, player_id: int, character_id: int) -> Dict[str, Any]:
        """
        Obtém o estado atual do diálogo, incluindo contexto e flags importantes.
        """
        # Busca a última interação
        last_interaction = db.query(DialogueHistory).filter(
            DialogueHistory.player_id == player_id,
            DialogueHistory.character_id == character_id
        ).order_by(DialogueHistory.timestamp.desc()).first()
        
        # Busca o nível atual
        current_level = db.query(PlayerCharacterLevel).filter(
            PlayerCharacterLevel.player_id == player_id,
            PlayerCharacterLevel.character_id == character_id
        ).first()
        
        # Busca gatilhos ativos
        active_triggers = db.query(ActiveTrigger).filter(
            ActiveTrigger.player_id == player_id,
            ActiveTrigger.character_id == character_id,
            ActiveTrigger.is_resolved == False
        ).all()
        
        return {
            "current_level": current_level.level if current_level else 0,
            "last_interaction_time": last_interaction.timestamp if last_interaction else None,
            "active_triggers": [trigger.trigger_id for trigger in active_triggers],
            "defensive_state": bool(active_triggers),
            "total_interactions": db.query(DialogueHistory).filter(
                DialogueHistory.player_id == player_id,
                DialogueHistory.character_id == character_id
            ).count()
        }

    def analyze_interaction_patterns(self, db: Session, player_id: int, character_id: int) -> Dict[str, Any]:
        """Corrigindo referência ao campo id para dialogue_id"""
        keyword_frequency = db.query(
            DialogueHistory.detected_keywords,
            func.count(DialogueHistory.dialogue_id).label('count')  # Corrigido
        ).filter(
            DialogueHistory.player_id == player_id,
            DialogueHistory.character_id == character_id
        ).group_by(DialogueHistory.detected_keywords).all()
        
        # Análise de tópicos recorrentes
        topic_patterns = db.query(
            DialogueHistory.topic,
            func.count(DialogueHistory.id).label('frequency')
        ).filter(
            DialogueHistory.player_id == player_id,
            DialogueHistory.character_id == character_id
        ).group_by(DialogueHistory.topic).all()
        
        # Análise de gatilhos ativados
        triggered_events = db.query(
            DialogueHistory
        ).filter(
            DialogueHistory.player_id == player_id,
            DialogueHistory.character_id == character_id,
            DialogueHistory.trigger_id.isnot(None)
        ).order_by(DialogueHistory.timestamp).all()
        
        return {
            "keyword_patterns": [
                {"keyword": k, "frequency": c} for k, c in keyword_frequency
            ],
            "topic_patterns": [
                {"topic": t, "frequency": f} for t, f in topic_patterns
            ],
            "trigger_history": [
                {
                    "trigger_id": event.trigger_id,
                    "timestamp": event.timestamp,
                    "success": event.evolution_event
                } for event in triggered_events
            ],
            "interaction_frequency": {
                "total": len(triggered_events),
                "successful": sum(1 for e in triggered_events if e.evolution_event)
            }
        }

