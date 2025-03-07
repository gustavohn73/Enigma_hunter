# src/repositories/character_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.models.db_models import Character, CharacterLevel, EvolutionTrigger, EvidenceRequirement
from src.repositories.base_repository import BaseRepository

class CharacterRepository(BaseRepository[Character]):
    """
    Repositório para operações de banco de dados relacionadas a personagens.
    Encapsula todas as consultas SQL relacionadas aos personagens e seus componentes.
    """
    
    def __init__(self):
        super().__init__(Character)
    
    def get_by_id(self, db: Session, character_id: int) -> Optional[Character]:
        """
        Busca um personagem pelo ID.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            
        Returns:
            Personagem encontrado ou None
        """
        return db.query(Character).filter(Character.character_id == character_id).first()
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[Character]:
        """
        Busca todos os personagens de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de personagens da história
        """
        return db.query(Character).join(
            Character.stories
        ).filter(
            Character.stories.any(story_id=story_id)
        ).all()
    
    def get_character_with_levels(self, db: Session, character_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém um personagem com todos os seus níveis e gatilhos.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            
        Returns:
            Dicionário com dados do personagem e seus níveis
        """
        # Busca o personagem
        character = db.query(Character).filter(Character.character_id == character_id).first()
        
        if not character:
            return None
        
        # Busca os níveis do personagem
        levels = db.query(CharacterLevel).filter(
            CharacterLevel.character_id == character_id
        ).order_by(
            CharacterLevel.level_number
        ).all()
        
        # Constrói o dicionário de resposta
        character_data = {
            "id": character.character_id,
            "name": character.name,
            "base_description": character.base_description,
            "personality": character.personality,
            "appearance": character.appearance,
            "is_culprit": character.is_culprit,
            "motive": character.motive,
            "levels": []
        }
        
        # Adiciona dados de cada nível
        for level in levels:
            # Busca os gatilhos deste nível
            triggers = db.query(EvolutionTrigger).filter(
                EvolutionTrigger.level_id == level.level_id
            ).all()
            
            level_data = {
                "level_id": level.level_id,
                "level_number": level.level_number,
                "knowledge_scope": level.knowledge_scope,
                "narrative_stance": level.narrative_stance,
                "is_defensive": level.is_defensive,
                "dialogue_parameters": level.dialogue_parameters,
                "triggers": []
            }
            
            # Adiciona dados de cada gatilho
            for trigger in triggers:
                # Busca os requisitos do gatilho
                requirements = db.query(EvidenceRequirement).filter(
                    EvidenceRequirement.trigger_id == trigger.trigger_id
                ).all()
                
                trigger_data = {
                    "trigger_id": trigger.trigger_id,
                    "trigger_keyword": trigger.trigger_keyword,
                    "contextual_condition": trigger.contextual_condition,
                    "defensive_response": trigger.defensive_response,
                    "challenge_question": trigger.challenge_question,
                    "success_response": trigger.success_response,
                    "fail_response": trigger.fail_response,
                    "requirements": [
                        {
                            "req_id": req.req_id,
                            "requirement_type": req.requirement_type,
                            "required_object_id": req.required_object_id,
                            "required_knowledge": req.required_knowledge,
                            "verification_method": req.verification_method,
                            "hint_if_incorrect": req.hint_if_incorrect
                        }
                        for req in requirements
                    ]
                }
                
                level_data["triggers"].append(trigger_data)
            
            character_data["levels"].append(level_data)
        
        return character_data
    
    def get_character_level(self, db: Session, character_id: int, level_number: int) -> Optional[CharacterLevel]:
        """
        Obtém um nível específico de um personagem.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            level_number: Número do nível
            
        Returns:
            Nível do personagem ou None
        """
        return db.query(CharacterLevel).filter(
            CharacterLevel.character_id == character_id,
            CharacterLevel.level_number == level_number
        ).first()
    
    def get_character_triggers(self, db: Session, level_id: int) -> List[EvolutionTrigger]:
        """
        Obtém todos os gatilhos de um nível de personagem.
        
        Args:
            db: Sessão do banco de dados
            level_id: ID do nível
            
        Returns:
            Lista de gatilhos
        """
        return db.query(EvolutionTrigger).filter(
            EvolutionTrigger.level_id == level_id
        ).all()
    
    def get_trigger_requirements(self, db: Session, trigger_id: int) -> List[EvidenceRequirement]:
        """
        Obtém todos os requisitos de um gatilho.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            
        Returns:
            Lista de requisitos
        """
        return db.query(EvidenceRequirement).filter(
            EvidenceRequirement.trigger_id == trigger_id
        ).all()
    
    def get_trigger_by_id(self, db: Session, trigger_id: int) -> Optional[EvolutionTrigger]:
        """
        Obtém um gatilho pelo ID.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            
        Returns:
            Gatilho ou None
        """
        return db.query(EvolutionTrigger).filter(
            EvolutionTrigger.trigger_id == trigger_id
        ).first()