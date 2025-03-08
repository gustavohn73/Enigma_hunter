# src/repositories/dialogue_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import json
import logging

from src.models.db_models import (
    DialogueHistory,
    PlayerSession,
    CharacterLevel
)
from src.repositories.base_repository import BaseRepository

class DialogueRepository(BaseRepository[DialogueHistory]):
    """
    Repositório para operações de banco de dados relacionadas a diálogos.
    Responsável pelo armazenamento e recuperação do histórico de diálogos entre jogadores e personagens.
    """
    
    def __init__(self):
        super().__init__(DialogueHistory)
        self.logger = logging.getLogger(__name__)
    
    def get_by_id(self, db: Session, dialogue_id: int) -> Optional[DialogueHistory]:
        """
        Busca um diálogo pelo ID.
        
        Args:
            db: Sessão do banco de dados
            dialogue_id: ID do diálogo
            
        Returns:
            Diálogo encontrado ou None
        """
        try:
            return db.query(DialogueHistory).filter(
                DialogueHistory.dialogue_id == dialogue_id
            ).first()
        except Exception as e:
            self.logger.error(f"Erro ao buscar diálogo por ID {dialogue_id}: {str(e)}")
            return None
    
    def get_dialogue_history(self, db: Session, session_id: str, character_id: int, 
                           limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de diálogo entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            limit: Número máximo de mensagens
            
        Returns:
            Lista de mensagens do histórico
        """
        try:
            dialogue_history = db.query(DialogueHistory).filter(
                DialogueHistory.session_id == session_id,
                DialogueHistory.character_id == character_id
            ).order_by(DialogueHistory.timestamp.desc()).limit(limit).all()
            
            result = []
            for entry in reversed(dialogue_history):
                result.append({
                    "dialogue_id": entry.dialogue_id,
                    "role": "user" if entry.player_statement else "assistant",
                    "content": entry.player_statement or entry.character_response,
                    "timestamp": entry.timestamp,
                    "detected_keywords": self._parse_json_field(entry.detected_keywords),
                    "character_level": entry.character_level
                })
                
            return result
        except Exception as e:
            self.logger.error(f"Erro ao obter histórico de diálogo: {str(e)}")
            return []
    
    def add_dialogue_entry(self, db: Session, session_id: str, character_id: int,
                          player_statement: str, character_response: str,
                          detected_keywords: List[str] = None,
                          character_level: int = 0,
                          is_key_interaction: bool = False) -> Optional[DialogueHistory]:
        """
        Adiciona uma entrada ao histórico de diálogo.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            player_statement: Mensagem do jogador
            character_response: Resposta do personagem
            detected_keywords: Palavras-chave detectadas
            character_level: Nível atual do personagem
            is_key_interaction: Se é uma interação importante
            
        Returns:
            Objeto DialogueHistory criado ou None em caso de erro
        """
        try:
            # Garantir que keywords sejam armazenadas corretamente
            keywords_json = json.dumps(detected_keywords or [])
            
            entry = DialogueHistory(
                session_id=session_id,
                character_id=character_id,
                player_statement=player_statement,
                character_response=character_response,
                detected_keywords=keywords_json,
                character_level=character_level,
                timestamp=datetime.utcnow(),
                is_key_interaction=is_key_interaction
            )
            
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar diálogo: {str(e)}")
            return None
    
    def get_key_interactions(self, db: Session, session_id: str, character_id: int) -> List[DialogueHistory]:
        """
        Obtém interações importantes com um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            
        Returns:
            Lista de interações importantes
        """
        try:
            return db.query(DialogueHistory).filter(
                DialogueHistory.session_id == session_id,
                DialogueHistory.character_id == character_id,
                DialogueHistory.is_key_interaction == True
            ).order_by(DialogueHistory.timestamp).all()
        except Exception as e:
            self.logger.error(f"Erro ao buscar interações importantes: {str(e)}")
            return []
    
    def get_keyword_mentions(self, db: Session, session_id: str, character_id: int, 
                           keyword: str) -> List[DialogueHistory]:
        """
        Busca diálogos que mencionam uma palavra-chave específica.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            keyword: Palavra-chave a ser buscada
            
        Returns:
            Lista de diálogos que mencionam a palavra-chave
        """
        try:
            # Busca em player_statement
            player_mentions = db.query(DialogueHistory).filter(
                DialogueHistory.session_id == session_id,
                DialogueHistory.character_id == character_id,
                DialogueHistory.player_statement.ilike(f"%{keyword}%")
            ).all()
            
            # Busca em character_response
            character_mentions = db.query(DialogueHistory).filter(
                DialogueHistory.session_id == session_id,
                DialogueHistory.character_id == character_id,
                DialogueHistory.character_response.ilike(f"%{keyword}%")
            ).all()
            
            # Busca em detected_keywords
            keyword_mentions = db.query(DialogueHistory).filter(
                DialogueHistory.session_id == session_id,
                DialogueHistory.character_id == character_id,
                DialogueHistory.detected_keywords.like(f"%{keyword}%")
            ).all()
            
            # Combina os resultados sem duplicatas
            result = list(set(player_mentions + character_mentions + keyword_mentions))
            
            # Ordena por timestamp
            result.sort(key=lambda x: x.timestamp)
            
            return result
        except Exception as e:
            self.logger.error(f"Erro ao buscar menções da palavra-chave '{keyword}': {str(e)}")
            return []
    
    def get_last_dialogue(self, db: Session, session_id: str, character_id: int) -> Optional[DialogueHistory]:
        """
        Obtém o diálogo mais recente entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            
        Returns:
            Diálogo mais recente ou None
        """
        try:
            return db.query(DialogueHistory).filter(
                DialogueHistory.session_id == session_id,
                DialogueHistory.character_id == character_id
            ).order_by(DialogueHistory.timestamp.desc()).first()
        except Exception as e:
            self.logger.error(f"Erro ao obter último diálogo: {str(e)}")
            return None
    
    def get_dialogue_count(self, db: Session, session_id: str, character_id: int) -> int:
        """
        Conta o número de interações entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            
        Returns:
            Número de interações
        """
        try:
            return db.query(func.count(DialogueHistory.dialogue_id)).filter(
                DialogueHistory.session_id == session_id,
                DialogueHistory.character_id == character_id
            ).scalar() or 0
        except Exception as e:
            self.logger.error(f"Erro ao contar diálogos: {str(e)}")
            return 0
    
    def get_character_dialogue_context(self, db: Session, session_id: str, character_id: int, 
                                     max_entries: int = 10) -> Dict[str, Any]:
        """
        Obtém o contexto atual de diálogo entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            max_entries: Número máximo de entradas no histórico
            
        Returns:
            Dicionário com o contexto do diálogo
        """
        try:
            # Busca o nível atual do personagem 
            from src.models.db_models import PlayerCharacterLevel
            
            character_level_record = db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id,
                PlayerCharacterLevel.character_id == character_id
            ).first()
            
            character_level = character_level_record.current_level if character_level_record else 0
            
            # Busca os últimos diálogos
            recent_dialogues = self.get_dialogue_history(db, session_id, character_id, max_entries)
            
            # Conta o total de interações
            total_interactions = self.get_dialogue_count(db, session_id, character_id)
            
            last_interaction = None
            if recent_dialogues:
                last_interaction = recent_dialogues[0].get("timestamp")
            
            return {
                "character_id": character_id,
                "character_level": character_level,
                "recent_dialogues": recent_dialogues,
                "last_interaction": last_interaction,
                "total_interactions": total_interactions
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter contexto de diálogo: {str(e)}")
            return {
                "character_id": character_id,
                "character_level": 0,
                "recent_dialogues": [],
                "last_interaction": None,
                "total_interactions": 0
            }
    
    def update_dialogue(self, db: Session, dialogue_id: int, updates: Dict[str, Any]) -> Optional[DialogueHistory]:
        """
        Atualiza um diálogo existente.
        
        Args:
            db: Sessão do banco de dados
            dialogue_id: ID do diálogo
            updates: Campos a serem atualizados
            
        Returns:
            Diálogo atualizado ou None em caso de erro
        """
        try:
            dialogue = self.get_by_id(db, dialogue_id)
            if not dialogue:
                return None
                
            for key, value in updates.items():
                if hasattr(dialogue, key):
                    # Tratamento especial para detected_keywords se for uma lista
                    if key == 'detected_keywords' and isinstance(value, list):
                        setattr(dialogue, key, json.dumps(value))
                    else:
                        setattr(dialogue, key, value)
                    
            db.commit()
            db.refresh(dialogue)
            
            return dialogue
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar diálogo {dialogue_id}: {str(e)}")
            return None
    
    def register_evolution(self, db: Session, session_id: str, character_id: int, 
                         old_level: int, new_level: int, 
                         trigger_id: Optional[int] = None) -> Optional[DialogueHistory]:
        """
        Registra uma evolução de personagem no histórico de diálogos.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            character_id: ID do personagem
            old_level: Nível anterior do personagem
            new_level: Novo nível do personagem
            trigger_id: ID do gatilho que causou a evolução (opcional)
            
        Returns:
            Registro de evolução criado ou None em caso de erro
        """
        try:
            # Cria um registro especial de evolução
            evolution_record = DialogueHistory(
                session_id=session_id,
                character_id=character_id,
                player_statement="[Evolução de Personagem]",
                character_response=f"[Personagem evoluiu do nível {old_level} para o nível {new_level}]",
                character_level=old_level,
                is_key_interaction=True,
                trigger_id=trigger_id,
                timestamp=datetime.utcnow()
            )
            
            db.add(evolution_record)
            db.commit()
            db.refresh(evolution_record)
            
            return evolution_record
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao registrar evolução: {str(e)}")
            return None
    
    def get_all_by_session(self, db: Session, session_id: str) -> List[DialogueHistory]:
        """
        Obtém todos os diálogos de uma sessão de jogo.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Lista de todos os diálogos da sessão
        """
        try:
            return db.query(DialogueHistory).filter(
                DialogueHistory.session_id == session_id
            ).order_by(DialogueHistory.timestamp).all()
        except Exception as e:
            self.logger.error(f"Erro ao buscar todos os diálogos da sessão {session_id}: {str(e)}")
            return []
    
    def delete_dialogue(self, db: Session, dialogue_id: int) -> bool:
        """
        Remove um diálogo do histórico.
        
        Args:
            db: Sessão do banco de dados
            dialogue_id: ID do diálogo
            
        Returns:
            True se removido com sucesso, False caso contrário
        """
        try:
            dialogue = self.get_by_id(db, dialogue_id)
            if not dialogue:
                return False
                
            db.delete(dialogue)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao remover diálogo {dialogue_id}: {str(e)}")
            return False
    
    def _parse_json_field(self, field_value: Any) -> Any:
        """
        Método auxiliar para converter campos JSON armazenados como string.
        
        Args:
            field_value: Campo que pode ser uma string JSON
            
        Returns:
            Objeto Python convertido ou o valor original
        """
        if not field_value:
            return []
            
        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except json.JSONDecodeError:
                return field_value
        
        return field_value