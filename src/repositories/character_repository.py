# src/repositories/character_repository.py
from typing import List, Optional, Dict, Any, Union, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
import json
import logging

from src.models.db_models import Character, CharacterLevel, EvolutionTrigger, EvidenceRequirement
from src.repositories.base_repository import BaseRepository

class CharacterRepository(BaseRepository[Character]):
    """
    Repositório para operações de banco de dados relacionadas a personagens.
    Encapsula todas as consultas SQL relacionadas aos personagens e seus componentes.
    """
    
    def __init__(self):
        super().__init__(Character)
        self.logger = logging.getLogger(__name__)
    
    def get_by_id(self, db: Session, character_id: int) -> Optional[Character]:
        """
        Busca um personagem pelo ID.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            
        Returns:
            Personagem encontrado ou None
        """
        try:
            return db.query(Character).filter(Character.character_id == character_id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar personagem por ID {character_id}: {str(e)}")
            return None
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[Character]:
        """
        Busca todos os personagens de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de personagens da história
        """
        try:
            characters = db.query(Character).join(
                Character.stories
            ).filter(
                Character.stories.any(story_id=story_id)
            ).all()
            
            self.logger.info(f"Recuperados {len(characters)} personagens para a história {story_id}")
            return characters
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar personagens da história {story_id}: {str(e)}")
            return []
    
    def get_character_with_levels(self, db: Session, character_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém um personagem com todos os seus níveis e gatilhos.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            
        Returns:
            Dicionário com dados do personagem e seus níveis
        """
        try:
            # Busca o personagem
            character = self.get_by_id(db, character_id)
            
            if not character:
                self.logger.warning(f"Personagem não encontrado com ID {character_id}")
                return None
            
            # Busca os níveis do personagem
            levels = self.get_character_levels(db, character_id)
            
            # Constrói o dicionário de resposta
            character_data = {
                "id": character.character_id,
                "name": character.name,
                "base_description": character.base_description,
                "personality": character.personality,
                "appearance": character.appearance,
                "is_culprit": character.is_culprit,
                "motive": character.motive,
                "location_schedule": self._parse_json_field(character.location_schedule),
                "levels": []
            }
            
            # Adiciona dados de cada nível
            for level in levels:
                level_data = self._get_level_data_with_triggers(db, level)
                character_data["levels"].append(level_data)
            
            self.logger.info(f"Recuperados dados completos do personagem {character.name} (ID: {character_id})")
            return character_data
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao recuperar personagem com níveis para ID {character_id}: {str(e)}")
            return None
    
    def get_character_levels(self, db: Session, character_id: int) -> List[CharacterLevel]:
        """
        Obtém todos os níveis de um personagem.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            
        Returns:
            Lista de níveis do personagem ordenados por número
        """
        try:
            levels = db.query(CharacterLevel).filter(
                CharacterLevel.character_id == character_id
            ).order_by(
                CharacterLevel.level_number
            ).all()
            
            return levels
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar níveis do personagem {character_id}: {str(e)}")
            return []
    
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
        try:
            return db.query(CharacterLevel).filter(
                CharacterLevel.character_id == character_id,
                CharacterLevel.level_number == level_number
            ).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar nível {level_number} do personagem {character_id}: {str(e)}")
            return None
    
    def get_character_triggers(self, db: Session, level_id: int) -> List[EvolutionTrigger]:
        """
        Obtém todos os gatilhos de um nível de personagem.
        
        Args:
            db: Sessão do banco de dados
            level_id: ID do nível
            
        Returns:
            Lista de gatilhos
        """
        try:
            triggers = db.query(EvolutionTrigger).filter(
                EvolutionTrigger.level_id == level_id
            ).all()
            
            return triggers
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar gatilhos do nível {level_id}: {str(e)}")
            return []
    
    def get_trigger_requirements(self, db: Session, trigger_id: int) -> List[EvidenceRequirement]:
        """
        Obtém todos os requisitos de um gatilho.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            
        Returns:
            Lista de requisitos
        """
        try:
            requirements = db.query(EvidenceRequirement).filter(
                EvidenceRequirement.trigger_id == trigger_id
            ).all()
            
            return requirements
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar requisitos do gatilho {trigger_id}: {str(e)}")
            return []
    
    def get_trigger_by_id(self, db: Session, trigger_id: int) -> Optional[EvolutionTrigger]:
        """
        Obtém um gatilho pelo ID.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            
        Returns:
            Gatilho ou None
        """
        try:
            return db.query(EvolutionTrigger).filter(
                EvolutionTrigger.trigger_id == trigger_id
            ).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar gatilho por ID {trigger_id}: {str(e)}")
            return None
    
    def add_level(self, db: Session, character_id: int, level_data: Dict[str, Any]) -> Optional[CharacterLevel]:
        """
        Adiciona um novo nível a um personagem.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            level_data: Dados do nível
            
        Returns:
            Nível criado ou None em caso de erro
        """
        try:
            # Verifica se o personagem existe
            if not self.exists(db, character_id):
                self.logger.error(f"Tentativa de adicionar nível a personagem inexistente: {character_id}")
                return None
            
            # Prepara dados do campo JSON
            ia_instruction_set = level_data.get("ia_instruction_set", {})
            if isinstance(ia_instruction_set, dict):
                ia_instruction_set = json.dumps(ia_instruction_set)
            
            # Cria o nível
            level = CharacterLevel(
                character_id=character_id,
                level_number=level_data.get("level_number", 0),
                knowledge_scope=level_data.get("knowledge_scope", ""),
                narrative_stance=level_data.get("narrative_stance", ""),
                is_defensive=level_data.get("is_defensive", False),
                dialogue_parameters=level_data.get("dialogue_parameters", ""),
                ia_instruction_set=ia_instruction_set
            )
            
            db.add(level)
            db.commit()
            db.refresh(level)
            
            self.logger.info(f"Nível {level.level_number} adicionado ao personagem {character_id}")
            return level
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar nível ao personagem {character_id}: {str(e)}")
            return None
    
    def add_trigger(self, db: Session, level_id: int, trigger_data: Dict[str, Any]) -> Optional[EvolutionTrigger]:
        """
        Adiciona um novo gatilho a um nível de personagem.
        
        Args:
            db: Sessão do banco de dados
            level_id: ID do nível
            trigger_data: Dados do gatilho
            
        Returns:
            Gatilho criado ou None em caso de erro
        """
        try:
            # Verifica se o nível existe
            level = db.query(CharacterLevel).filter(CharacterLevel.level_id == level_id).first()
            if not level:
                self.logger.error(f"Tentativa de adicionar gatilho a nível inexistente: {level_id}")
                return None
            
            # Cria o gatilho
            trigger = EvolutionTrigger(
                level_id=level_id,
                trigger_keyword=trigger_data.get("trigger_keyword", ""),
                contextual_condition=trigger_data.get("contextual_condition", ""),
                defensive_response=trigger_data.get("defensive_response", ""),
                challenge_question=trigger_data.get("challenge_question", ""),
                success_response=trigger_data.get("success_response", ""),
                fail_response=trigger_data.get("fail_response", ""),
                multi_step_verification=trigger_data.get("multi_step_verification", False)
            )
            
            db.add(trigger)
            db.commit()
            db.refresh(trigger)
            
            self.logger.info(f"Gatilho adicionado ao nível {level_id}, personagem {level.character_id}")
            return trigger
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar gatilho ao nível {level_id}: {str(e)}")
            return None
    
    def add_requirement(self, db: Session, trigger_id: int, req_data: Dict[str, Any]) -> Optional[EvidenceRequirement]:
        """
        Adiciona um novo requisito a um gatilho.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            req_data: Dados do requisito
            
        Returns:
            Requisito criado ou None em caso de erro
        """
        try:
            # Verifica se o gatilho existe
            trigger = db.query(EvolutionTrigger).filter(EvolutionTrigger.trigger_id == trigger_id).first()
            if not trigger:
                self.logger.error(f"Tentativa de adicionar requisito a gatilho inexistente: {trigger_id}")
                return None
            
            # Prepara dados dos campos JSON
            required_knowledge = req_data.get("required_knowledge", {})
            if isinstance(required_knowledge, dict):
                required_knowledge = json.dumps(required_knowledge)
            
            # Garante que required_object_id seja serializado como JSON se for uma lista ou dict
            required_object_id = req_data.get("required_object_id")
            if isinstance(required_object_id, (list, dict)):
                required_object_id = json.dumps(required_object_id)
            
            # Cria o requisito
            requirement = EvidenceRequirement(
                trigger_id=trigger_id,
                requirement_type=req_data.get("requirement_type", ""),
                required_object_id=required_object_id,
                required_knowledge=required_knowledge,
                verification_method=req_data.get("verification_method", ""),
                hint_if_incorrect=req_data.get("hint_if_incorrect", ""),
                minimum_presentation_level=req_data.get("minimum_presentation_level", 0)
            )
            
            db.add(requirement)
            db.commit()
            db.refresh(requirement)
            
            self.logger.info(f"Requisito adicionado ao gatilho {trigger_id}")
            return requirement
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar requisito ao gatilho {trigger_id}: {str(e)}")
            return None
    
    def update_level(self, db: Session, level_id: int, level_data: Dict[str, Any]) -> Optional[CharacterLevel]:
        """
        Atualiza um nível existente.
        
        Args:
            db: Sessão do banco de dados
            level_id: ID do nível
            level_data: Dados atualizados
            
        Returns:
            Nível atualizado ou None em caso de erro
        """
        try:
            # Busca o nível
            level = db.query(CharacterLevel).filter(CharacterLevel.level_id == level_id).first()
            if not level:
                self.logger.error(f"Tentativa de atualizar nível inexistente: {level_id}")
                return None
            
            # Atualiza campos
            if "level_number" in level_data:
                level.level_number = level_data["level_number"]
            if "knowledge_scope" in level_data:
                level.knowledge_scope = level_data["knowledge_scope"]
            if "narrative_stance" in level_data:
                level.narrative_stance = level_data["narrative_stance"]
            if "is_defensive" in level_data:
                level.is_defensive = level_data["is_defensive"]
            if "dialogue_parameters" in level_data:
                level.dialogue_parameters = level_data["dialogue_parameters"]
            if "ia_instruction_set" in level_data:
                ia_instruction_set = level_data["ia_instruction_set"]
                if isinstance(ia_instruction_set, dict):
                    level.ia_instruction_set = json.dumps(ia_instruction_set)
                else:
                    level.ia_instruction_set = ia_instruction_set
            
            db.commit()
            db.refresh(level)
            
            self.logger.info(f"Nível {level_id} atualizado com sucesso")
            return level
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível {level_id}: {str(e)}")
            return None
    
    def update_trigger(self, db: Session, trigger_id: int, trigger_data: Dict[str, Any]) -> Optional[EvolutionTrigger]:
        """
        Atualiza um gatilho existente.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            trigger_data: Dados atualizados
            
        Returns:
            Gatilho atualizado ou None em caso de erro
        """
        try:
            # Busca o gatilho
            trigger = db.query(EvolutionTrigger).filter(EvolutionTrigger.trigger_id == trigger_id).first()
            if not trigger:
                self.logger.error(f"Tentativa de atualizar gatilho inexistente: {trigger_id}")
                return None
            
            # Atualiza campos
            for key, value in trigger_data.items():
                if hasattr(trigger, key):
                    setattr(trigger, key, value)
            
            db.commit()
            db.refresh(trigger)
            
            self.logger.info(f"Gatilho {trigger_id} atualizado com sucesso")
            return trigger
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar gatilho {trigger_id}: {str(e)}")
            return None
    
    def delete_level(self, db: Session, level_id: int) -> bool:
        """
        Remove um nível e todos os seus gatilhos e requisitos.
        
        Args:
            db: Sessão do banco de dados
            level_id: ID do nível
            
        Returns:
            True se removido com sucesso
        """
        try:
            # Busca gatilhos para remover seus requisitos
            triggers = self.get_character_triggers(db, level_id)
            for trigger in triggers:
                # Remove requisitos
                db.query(EvidenceRequirement).filter(
                    EvidenceRequirement.trigger_id == trigger.trigger_id
                ).delete()
            
            # Remove gatilhos
            db.query(EvolutionTrigger).filter(
                EvolutionTrigger.level_id == level_id
            ).delete()
            
            # Remove o nível
            deleted = db.query(CharacterLevel).filter(
                CharacterLevel.level_id == level_id
            ).delete()
            
            db.commit()
            
            if deleted:
                self.logger.info(f"Nível {level_id} e seus componentes removidos com sucesso")
                return True
            else:
                self.logger.warning(f"Nível {level_id} não encontrado para remoção")
                return False
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao remover nível {level_id}: {str(e)}")
            return False
    
    def delete_trigger(self, db: Session, trigger_id: int) -> bool:
        """
        Remove um gatilho e todos os seus requisitos.
        
        Args:
            db: Sessão do banco de dados
            trigger_id: ID do gatilho
            
        Returns:
            True se removido com sucesso
        """
        try:
            # Remove requisitos
            db.query(EvidenceRequirement).filter(
                EvidenceRequirement.trigger_id == trigger_id
            ).delete()
            
            # Remove o gatilho
            deleted = db.query(EvolutionTrigger).filter(
                EvolutionTrigger.trigger_id == trigger_id
            ).delete()
            
            db.commit()
            
            if deleted:
                self.logger.info(f"Gatilho {trigger_id} e seus requisitos removidos com sucesso")
                return True
            else:
                self.logger.warning(f"Gatilho {trigger_id} não encontrado para remoção")
                return False
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao remover gatilho {trigger_id}: {str(e)}")
            return False
    
    def get_character_by_name(self, db: Session, name: str, story_id: Optional[int] = None) -> Optional[Character]:
        """
        Busca um personagem pelo nome, opcionalmente filtrando por história.
        
        Args:
            db: Sessão do banco de dados
            name: Nome do personagem
            story_id: ID da história (opcional)
            
        Returns:
            Personagem encontrado ou None
        """
        try:
            query = db.query(Character).filter(func.lower(Character.name) == name.lower())
            
            if story_id is not None:
                query = query.join(Character.stories).filter(
                    Character.stories.any(story_id=story_id)
                )
                
            return query.first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar personagem pelo nome '{name}': {str(e)}")
            return None
    
    def get_culprit(self, db: Session, story_id: int) -> Optional[Character]:
        """
        Obtém o personagem culpado de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Personagem culpado ou None
        """
        try:
            culprit = db.query(Character).join(
                Character.stories
            ).filter(
                Character.stories.any(story_id=story_id),
                Character.is_culprit == True
            ).first()
            
            return culprit
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar culpado da história {story_id}: {str(e)}")
            return None
    
    def get_characters_in_location(self, db: Session, location_id: int) -> List[Dict[str, Any]]:
        """
        Obtém os personagens presentes em uma localização.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Lista de personagens na localização
        """
        try:
            # Buscar personagens na localização
            characters = db.query(Character).filter(
                Character.location_id == location_id,
                Character.is_active == True
            ).all()
            
            # Converter para dicionários
            result = []
            for char in characters:
                result.append({
                    "id": char.character_id,
                    "name": char.name,
                    "description": char.description,
                    "type": char.character_type,
                    "location_id": char.location_id,
                    "dialogue_state": char.dialogue_state,
                    "is_active": char.is_active,
                    "importance_level": char.importance_level
                })
            
            self.logger.debug(f"Encontrados {len(result)} personagens na localização {location_id}")
            return result
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar personagens na localização {location_id}: {e}")
            return []
    
    def get_characters_in_area(self, db: Session, area_id: int) -> List[Dict[str, Any]]:
        """
        Obtém os personagens presentes em uma área específica.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de personagens na área
        """
        try:
            characters = db.query(Character).filter(
                Character.area_id == area_id,
                Character.is_active == True
            ).all()
            
            result = []
            for char in characters:
                result.append({
                    "id": char.character_id,
                    "name": char.name,
                    "description": char.description,
                    "type": char.character_type,
                    "area_id": char.area_id,
                    "dialogue_state": char.dialogue_state,
                    "importance_level": char.importance_level
                })
            
            self.logger.debug(f"Encontrados {len(result)} personagens na área {area_id}")
            return result
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar personagens na área {area_id}: {e}")
            return []
    
    def _get_level_data_with_triggers(self, db: Session, level: CharacterLevel) -> Dict[str, Any]:
        """
        Constrói um dicionário com dados de um nível e seus gatilhos.
        
        Args:
            db: Sessão do banco de dados
            level: Objeto CharacterLevel
            
        Returns:
            Dicionário com dados do nível e gatilhos
        """
        try:
            # Busca os gatilhos deste nível
            triggers = self.get_character_triggers(db, level.level_id)
            
            level_data = {
                "level_id": level.level_id,
                "level_number": level.level_number,
                "knowledge_scope": level.knowledge_scope,
                "narrative_stance": level.narrative_stance,
                "is_defensive": level.is_defensive,
                "dialogue_parameters": level.dialogue_parameters,
                "ia_instruction_set": self._parse_json_field(level.ia_instruction_set),
                "triggers": []
            }
            
            # Adiciona dados de cada gatilho
            for trigger in triggers:
                # Busca os requisitos do gatilho
                requirements = self.get_trigger_requirements(db, trigger.trigger_id)
                
                trigger_data = {
                    "trigger_id": trigger.trigger_id,
                    "trigger_keyword": trigger.trigger_keyword,
                    "contextual_condition": trigger.contextual_condition,
                    "defensive_response": trigger.defensive_response,
                    "challenge_question": trigger.challenge_question,
                    "success_response": trigger.success_response,
                    "fail_response": trigger.fail_response,
                    "multi_step_verification": trigger.multi_step_verification,
                    "requirements": []
                }
                
                # Adiciona dados de cada requisito
                for req in requirements:
                    req_data = {
                        "req_id": req.req_id,
                        "requirement_type": req.requirement_type,
                        "required_object_id": self._parse_json_field(req.required_object_id),
                        "required_knowledge": self._parse_json_field(req.required_knowledge),
                        "verification_method": req.verification_method,
                        "hint_if_incorrect": req.hint_if_incorrect,
                        "minimum_presentation_level": req.minimum_presentation_level
                    }
                    
                    trigger_data["requirements"].append(req_data)
                
                level_data["triggers"].append(trigger_data)
            
            return level_data
        except Exception as e:
            self.logger.error(f"Erro ao processar dados do nível {level.level_id}: {str(e)}")
            # Retorna dados básicos do nível sem gatilhos em caso de erro
            return {
                "level_id": level.level_id,
                "level_number": level.level_number,
                "knowledge_scope": level.knowledge_scope,
                "narrative_stance": level.narrative_stance,
                "is_defensive": level.is_defensive,
                "dialogue_parameters": level.dialogue_parameters,
                "ia_instruction_set": {},
                "triggers": []
            }
    
    def _parse_json_field(self, field_value: Any) -> Any:
        """
        Analisa um campo que pode estar armazenado como JSON.
        
        Args:
            field_value: Valor do campo que pode ser string JSON ou outra coisa
            
        Returns:
            Valor decodificado ou o valor original
        """
        if not field_value:
            return {}
            
        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except json.JSONDecodeError:
                return field_value
        
        return field_value