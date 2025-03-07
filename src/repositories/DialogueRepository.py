# src/repositories/dialogue_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
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
    EvidenceRequirement
)
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class DialogueRepository(BaseRepository[DialogueHistory]):
    """
    Repositório para operações de banco de dados relacionadas a diálogos.
    Gerencia históricos de diálogos, detecção de gatilhos e evolução de personagens.
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
            "detected_keywords": json.loads(entry.detected_keywords) if isinstance(entry.detected_keywords, str) else entry.detected_keywords,
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
            
            # Garantir que keywords sejam armazenadas como JSON se o campo for string
            keywords_data = detected_keywords or []
            
            entry = DialogueHistory(
                session_id=session.session_id,
                character_id=character_id,
                player_statement=player_statement,
                character_response=character_response,
                detected_keywords=json.dumps(keywords_data) if isinstance(DialogueHistory.detected_keywords.property.columns[0].type, str) else keywords_data,
                character_level=character_level,
                timestamp=datetime.utcnow(),
                is_key_interaction=bool(detected_keywords)
            )
            
            db.add(entry)
            db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao adicionar diálogo: {str(e)}")
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
            DialogueHistory.detected_keywords != '[]',
            DialogueHistory.detected_keywords.is_not(None)
        ).order_by(DialogueHistory.timestamp).all()
        
        results = []
        for dialogue in dialogues:
            try:
                keywords = json.loads(dialogue.detected_keywords) if isinstance(dialogue.detected_keywords, str) else dialogue.detected_keywords
                if keywords:
                    results.append({
                        "timestamp": dialogue.timestamp,
                        "keywords": keywords,
                        "level": dialogue.character_level,
                        "context": {
                            "player_statement": dialogue.player_statement,
                            "character_response": dialogue.character_response
                        }
                    })
            except (json.JSONDecodeError, TypeError):
                # Ignora entradas com formato inválido
                pass
                
        return results
    
    def get_key_interactions(self, db: Session, player_id: int, character_id: int) -> List[DialogueHistory]:
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
        session = self.get_active_session(db, player_id)
        if not session:
            return []
            
        query = db.query(DialogueHistory).filter(DialogueHistory.session_id == session.session_id)
        
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
        session = self.get_active_session(db, player_id)
        if not session:
            return {
                "character_level": 0,
                "recent_dialogues": [],
                "last_interaction": None,
                "total_interactions": 0
            }
            
        # Busca o nível atual do personagem para este jogador
        character_level_record = db.query(PlayerCharacterLevel).filter(
            PlayerCharacterLevel.session_id == session.session_id,
            PlayerCharacterLevel.character_id == character_id
        ).first()
        
        character_level = character_level_record.current_level if character_level_record else 0
        
        # Busca os últimos diálogos
        recent_dialogues = db.query(DialogueHistory).filter(
            DialogueHistory.session_id == session.session_id,
            DialogueHistory.character_id == character_id
        ).order_by(DialogueHistory.timestamp.desc()).limit(5).all()
        
        total_interactions = db.query(func.count(DialogueHistory.dialogue_id)).filter(
            DialogueHistory.session_id == session.session_id,
            DialogueHistory.character_id == character_id
        ).scalar() or 0
        
        return {
            "character_level": character_level,
            "recent_dialogues": recent_dialogues,
            "last_interaction": recent_dialogues[0].timestamp if recent_dialogues else None,
            "total_interactions": total_interactions
        }
    
    def create_dialogue(self, db: Session, dialogue_data: Dict[str, Any]) -> DialogueHistory:
        """
        Cria uma nova entrada de diálogo.
        
        Args:
            db: Sessão do banco de dados
            dialogue_data: Dados do diálogo
            
        Returns:
            Diálogo criado
        """
        try:
            dialogue = DialogueHistory(
                session_id=dialogue_data.get("session_id"),
                character_id=dialogue_data.get("character_id"),
                player_statement=dialogue_data.get("player_statement"),
                character_response=dialogue_data.get("character_response"),
                detected_keywords=dialogue_data.get("detected_keywords", []),
                character_level=dialogue_data.get("character_level", 0),
                timestamp=dialogue_data.get("timestamp", datetime.utcnow()),
                is_key_interaction=dialogue_data.get("is_key_interaction", False),
                trigger_id=dialogue_data.get("trigger_id")
            )
            
            db.add(dialogue)
            db.commit()
            db.refresh(dialogue)
            
            return dialogue
        except Exception as e:
            self.logger.error(f"Erro ao criar diálogo: {str(e)}")
            db.rollback()
            raise
    
    def update_dialogue(self, db: Session, dialogue_id: int, dialogue_data: Dict[str, Any]) -> Optional[DialogueHistory]:
        """
        Atualiza um diálogo existente.
        
        Args:
            db: Sessão do banco de dados
            dialogue_id: ID do diálogo
            dialogue_data: Dados a serem atualizados
            
        Returns:
            Diálogo atualizado ou None
        """
        dialogue = self.get_by_id(db, dialogue_id)
        if not dialogue:
            return None
            
        try:
            for key, value in dialogue_data.items():
                if hasattr(dialogue, key):
                    setattr(dialogue, key, value)
                    
            db.commit()
            db.refresh(dialogue)
            
            return dialogue
        except Exception as e:
            self.logger.error(f"Erro ao atualizar diálogo: {str(e)}")
            db.rollback()
            return None
    
    def check_triggers(self, db: Session, player_id: int, character_id: int, message: str) -> List[Dict[str, Any]]:
        """
        Verifica se uma mensagem ativa algum gatilho para o personagem.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            message: Mensagem do jogador
            
        Returns:
            Lista de gatilhos ativados
        """
        try:
            session = self.get_active_session(db, player_id)
            if not session:
                return []
                
            # Obtém o nível atual do personagem
            character_level_record = db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session.session_id,
                PlayerCharacterLevel.character_id == character_id
            ).first()
            
            current_level = character_level_record.current_level if character_level_record else 0
            
            # Busca informações do nível atual do personagem
            character_level = db.query(CharacterLevel).filter(
                CharacterLevel.character_id == character_id,
                CharacterLevel.level_number == current_level
            ).first()
            
            if not character_level:
                return []
            
            # Busca gatilhos para este nível
            triggers = db.query(EvolutionTrigger).filter(
                EvolutionTrigger.level_id == character_level.level_id
            ).all()
            
            activated_triggers = []
            message_lower = message.lower()
            
            for trigger in triggers:
                trigger_keyword = trigger.trigger_keyword.lower() if trigger.trigger_keyword else ""
                if trigger_keyword and trigger_keyword in message_lower:
                    activated_triggers.append({
                        "trigger_id": trigger.trigger_id,
                        "keyword": trigger.trigger_keyword,
                        "defensive_response": trigger.defensive_response,
                        "challenge_question": trigger.challenge_question,
                        "level_id": trigger.level_id
                    })
            
            return activated_triggers
        except Exception as e:
            self.logger.error(f"Erro ao verificar triggers: {str(e)}")
            return []

    def check_evolution_requirements(self, db: Session, player_id: int, trigger_id: int) -> Dict[str, Any]:
        """
        Verifica se os requisitos para evolução do personagem foram atendidos.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            trigger_id: ID do gatilho
            
        Returns:
            Resultado da verificação
        """
        try:
            session = self.get_active_session(db, player_id)
            if not session:
                return {"met": False, "missing": ["Sessão não encontrada"]}
                
            # Busca os requisitos do gatilho
            requirements = db.query(EvidenceRequirement).filter(
                EvidenceRequirement.trigger_id == trigger_id
            ).all()
            
            if not requirements:
                # Se não há requisitos específicos, assume-se que foi atendido
                return {"met": True, "missing": []}
            
            # Verifica cada requisito
            missing_requirements = []
            for req in requirements:
                if req.requirement_type == "object":
                    # Verifica se o jogador tem o objeto necessário no inventário
                    required_object_id = self._get_required_object_id(req)
                    if required_object_id:
                        has_object = db.query(PlayerInventory).filter(
                            PlayerInventory.session_id == session.session_id,
                            PlayerInventory.object_id == required_object_id
                        ).first() is not None
                        
                        if not has_object:
                            missing_requirements.append({
                                "type": "object",
                                "id": required_object_id,
                                "hint": req.hint_if_incorrect
                            })
                elif req.requirement_type == "knowledge" and req.required_knowledge:
                    # Verifica conhecimentos específicos (implementação simplificada)
                    # A implementação real dependeria da estrutura exata do jogo
                    missing_requirements.append({
                        "type": "knowledge",
                        "description": "Conhecimento específico necessário",
                        "hint": req.hint_if_incorrect
                    })
                
            return {
                "met": len(missing_requirements) == 0,
                "missing": missing_requirements
            }
        except Exception as e:
            self.logger.error(f"Erro ao verificar requisitos de evolução: {str(e)}")
            return {"met": False, "missing": [f"Erro interno: {str(e)}"]}
    
    def _get_required_object_id(self, requirement: EvidenceRequirement) -> Optional[int]:
        """
        Obtém o ID do objeto necessário de um requisito.
        Trata diferentes formatos possíveis.
        
        Args:
            requirement: Requisito a ser processado
            
        Returns:
            ID do objeto ou None
        """
        if hasattr(requirement, 'required_object_id'):
            if isinstance(requirement.required_object_id, int):
                return requirement.required_object_id
            elif isinstance(requirement.required_object_id, str):
                try:
                    # Tenta interpretar como JSON
                    obj_data = json.loads(requirement.required_object_id)
                    if isinstance(obj_data, int):
                        return obj_data
                    elif isinstance(obj_data, list) and obj_data:
                        return obj_data[0]  # Retorna o primeiro da lista
                except json.JSONDecodeError:
                    # Se não for JSON, tenta converter diretamente para int
                    try:
                        return int(requirement.required_object_id)
                    except ValueError:
                        return None
        return None

    def get_dialogue_by_trigger(self, db: Session, trigger_id: int) -> List[DialogueHistory]:
        """
        Obtém diálogos relacionados a um gatilho específico.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            
        Returns:
            Lista de diálogos relacionados ao gatilho
        """
        return db.query(DialogueHistory).filter(
            DialogueHistory.trigger_id == trigger_id
        ).order_by(DialogueHistory.timestamp).all()
    
    def register_evolution(self, db: Session, player_id: int, character_id: int, 
                         trigger_id: int, old_level: int, new_level: int) -> bool:
        """
        Registra a evolução de um personagem após um gatilho bem-sucedido.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            trigger_id: ID do gatilho que causou a evolução
            old_level: Nível anterior
            new_level: Novo nível
            
        Returns:
            True se registrado com sucesso
        """
        try:
            session = self.get_active_session(db, player_id)
            if not session:
                return False
                
            # Atualiza o nível do personagem
            character_level = db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session.session_id,
                PlayerCharacterLevel.character_id == character_id
            ).first()
            
            if not character_level:
                character_level = PlayerCharacterLevel(
                    session_id=session.session_id,
                    character_id=character_id,
                    current_level=new_level,
                    last_interaction=datetime.utcnow()
                )
                db.add(character_level)
            else:
                character_level.current_level = new_level
                character_level.last_interaction = datetime.utcnow()
            
            # Cria um registro de evolução no histórico de diálogos
            evolution_record = DialogueHistory(
                session_id=session.session_id,
                character_id=character_id,
                player_statement="[Evolução de Personagem]",
                character_response=f"[Personagem evoluiu do nível {old_level} para o nível {new_level}]",
                character_level=old_level,
                is_key_interaction=True,
                evolution_event=True,
                trigger_id=trigger_id,
                timestamp=datetime.utcnow()
            )
            
            db.add(evolution_record)
            db.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao registrar evolução: {str(e)}")
            db.rollback()
            return False