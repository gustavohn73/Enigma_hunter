# src/repositories/story_repository.py
from typing import List, Optional, Dict, Any, Tuple, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime
import json

from src.models.db_models import (
    Story, Location, Character, GameObject, Clue, PromptTemplate,
    story_location_association, story_character_association
)
from src.repositories.base_repository import BaseRepository

class StoryRepository(BaseRepository[Story]):
    """
    Repositório para operações de banco de dados relacionadas a histórias/casos.
    Gerencia histórias e seus componentes relacionados como localizações, personagens, objetos e pistas.
    """
    
    def __init__(self):
        super().__init__(Story)
        self.logger = logging.getLogger(__name__)
    
    def get_by_id(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Busca uma história pelo ID.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com os dados da história ou dicionário vazio se não encontrada
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada: ID {story_id}")
                return {}
                
            return self._story_to_dict(story)
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar história ID {story_id}: {str(e)}")
            raise
    
    def get_by_title(self, db: Session, title: str) -> Dict[str, Any]:
        """
        Busca uma história pelo título.
        
        Args:
            db: Sessão do banco de dados
            title: Título da história
            
        Returns:
            Dicionário com os dados da história ou dicionário vazio se não encontrada
        """
        try:
            story = db.query(Story).filter(func.lower(Story.title) == title.lower()).first()
            
            if not story:
                self.logger.warning(f"História não encontrada: título '{title}'")
                return {}
                
            return self._story_to_dict(story)
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar história por título '{title}': {str(e)}")
            raise
    
    def get_all(self, db: Session, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Obtém todas as histórias, com opção de filtrar apenas por ativas.
        
        Args:
            db: Sessão do banco de dados
            include_inactive: Se True, inclui histórias inativas
            
        Returns:
            Lista de dicionários com dados das histórias
        """
        try:
            query = db.query(Story)
            
            if not include_inactive:
                query = query.filter(Story.is_active == True)
                
            stories = query.order_by(Story.created_at.desc()).all()
            
            return [self._story_to_dict(story) for story in stories]
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar todas as histórias: {str(e)}")
            raise
    
    def get_story_with_details(self, db: Session, story_id: int, 
                            include_relationships: bool = True) -> Dict[str, Any]:
        """
        Obtém uma história com todos os seus detalhes relacionados.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            include_relationships: Se True, inclui relacionamentos (localizações, personagens, etc.)
            
        Returns:
            Dicionário com a história e seus detalhes
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada: ID {story_id}")
                return {}
            
            result = self._story_to_dict(story)
            
            if include_relationships:
                # Obter localizações
                locations = db.query(Location).join(
                    story_location_association,
                    Location.location_id == story_location_association.c.location_id
                ).filter(
                    story_location_association.c.story_id == story_id
                ).all()
                
                result["locations"] = [self._location_to_dict(location) for location in locations]
                
                # Obter personagens
                characters = db.query(Character).join(
                    story_character_association,
                    Character.character_id == story_character_association.c.character_id
                ).filter(
                    story_character_association.c.story_id == story_id
                ).all()
                
                result["characters"] = [self._character_to_dict(character) for character in characters]
                
                # Obter objetos
                objects = db.query(GameObject).filter(GameObject.story_id == story_id).all()
                result["objects"] = [self._object_to_dict(obj) for obj in objects]
                
                # Obter pistas
                clues = db.query(Clue).filter(Clue.story_id == story_id).all()
                result["clues"] = [self._clue_to_dict(clue) for clue in clues]
                
                # Obter templates de prompt
                prompts = db.query(PromptTemplate).filter(PromptTemplate.story_id == story_id).all()
                result["prompt_templates"] = [self._prompt_template_to_dict(template) for template in prompts]
            
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar história com detalhes ID {story_id}: {str(e)}")
            raise
    
    def get_story_solution_criteria(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém os critérios de solução de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com critérios de solução ou vazio se não encontrada
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada: ID {story_id}")
                return {}
                
            return self._parse_json_field(story.solution_criteria)
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar critérios de solução da história ID {story_id}: {str(e)}")
            raise
    
    def get_story_specialization_config(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém a configuração de especialização de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com configuração de especialização ou vazio se não encontrada
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada: ID {story_id}")
                return {}
                
            return self._parse_json_field(story.specialization_config)
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar configuração de especialização da história ID {story_id}: {str(e)}")
            raise
    
    def get_story_locations(self, db: Session, story_id: int) -> List[Dict[str, Any]]:
        """
        Obtém todas as localizações de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de dicionários com dados das localizações
        """
        try:
            locations = db.query(Location).join(
                story_location_association,
                Location.location_id == story_location_association.c.location_id
            ).filter(
                story_location_association.c.story_id == story_id
            ).all()
            
            return [self._location_to_dict(location) for location in locations]
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar localizações da história ID {story_id}: {str(e)}")
            raise
    
    def get_starting_location(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém a localização inicial de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com dados da localização inicial ou vazio se não encontrada
        """
        try:
            location = db.query(Location).join(
                story_location_association,
                Location.location_id == story_location_association.c.location_id
            ).filter(
                story_location_association.c.story_id == story_id,
                Location.is_starting_location == True
            ).first()
            
            if not location:
                self.logger.warning(f"Localização inicial não encontrada para história ID {story_id}")
                return {}
                
            return self._location_to_dict(location)
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar localização inicial da história ID {story_id}: {str(e)}")
            raise
    
    def get_story_characters(self, db: Session, story_id: int) -> List[Dict[str, Any]]:
        """
        Obtém todos os personagens de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de dicionários com dados dos personagens
        """
        try:
            characters = db.query(Character).join(
                story_character_association,
                Character.character_id == story_character_association.c.character_id
            ).filter(
                story_character_association.c.story_id == story_id
            ).all()
            
            return [self._character_to_dict(character) for character in characters]
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar personagens da história ID {story_id}: {str(e)}")
            raise
    
    def get_culprit(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém o culpado de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com dados do personagem culpado ou vazio se não encontrado
        """
        try:
            character = db.query(Character).join(
                story_character_association,
                Character.character_id == story_character_association.c.character_id
            ).filter(
                story_character_association.c.story_id == story_id,
                Character.is_culprit == True
            ).first()
            
            if not character:
                self.logger.warning(f"Culpado não encontrado para história ID {story_id}")
                return {}
                
            return self._character_to_dict(character)
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar culpado da história ID {story_id}: {str(e)}")
            raise
    
    def get_story_objects(self, db: Session, story_id: int) -> List[Dict[str, Any]]:
        """
        Obtém todos os objetos de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de dicionários com dados dos objetos
        """
        try:
            objects = db.query(GameObject).filter(GameObject.story_id == story_id).all()
            
            return [self._object_to_dict(obj) for obj in objects]
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos da história ID {story_id}: {str(e)}")
            raise
    
    def get_story_clues(self, db: Session, story_id: int, 
                     is_key_evidence: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Obtém todas as pistas de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            is_key_evidence: Filtrar por pistas-chave (opcional)
            
        Returns:
            Lista de dicionários com dados das pistas
        """
        try:
            query = db.query(Clue).filter(Clue.story_id == story_id)
            
            if is_key_evidence is not None:
                query = query.filter(Clue.is_key_evidence == is_key_evidence)
                
            clues = query.all()
            
            return [self._clue_to_dict(clue) for clue in clues]
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar pistas da história ID {story_id}: {str(e)}")
            raise
    
    def get_story_prompt_templates(self, db: Session, story_id: int, 
                                template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtém todos os templates de prompt de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            template_type: Tipo de template (opcional)
            
        Returns:
            Lista de dicionários com dados dos templates
        """
        try:
            query = db.query(PromptTemplate).filter(PromptTemplate.story_id == story_id)
            
            if template_type:
                query = query.filter(PromptTemplate.template_type == template_type)
                
            templates = query.all()
            
            return [self._prompt_template_to_dict(template) for template in templates]
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar templates de prompt da história ID {story_id}: {str(e)}")
            raise
    
    def create_story(self, db: Session, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma nova história.
        
        Args:
            db: Sessão do banco de dados
            story_data: Dados da nova história
            
        Returns:
            Dicionário com dados da história criada
        """
        try:
            # Processar campos JSON
            solution_criteria = story_data.get('solution_criteria', {})
            specialization_config = story_data.get('specialization_config', {})
            
            # Criar a história
            story = Story(
                title=story_data.get('title', 'Nova História'),
                description=story_data.get('description', ''),
                introduction=story_data.get('introduction', ''),
                conclusion=story_data.get('conclusion', ''),
                difficulty_level=story_data.get('difficulty_level', 1),
                solution_criteria=solution_criteria,
                specialization_config=specialization_config,
                is_active=story_data.get('is_active', True),
                created_at=datetime.now()
            )
            
            db.add(story)
            db.commit()
            db.refresh(story)
            
            self.logger.info(f"História criada: ID {story.story_id}, Título: {story.title}")
            
            return self._story_to_dict(story)
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar história: {str(e)}")
            raise
    
    def update_story(self, db: Session, story_id: int, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza uma história existente.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            story_data: Dados atualizados
            
        Returns:
            Dicionário com dados da história atualizada
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada para atualização: ID {story_id}")
                return {}
            
            # Atualizar campos fornecidos
            if 'title' in story_data:
                story.title = story_data['title']
            if 'description' in story_data:
                story.description = story_data['description']
            if 'introduction' in story_data:
                story.introduction = story_data['introduction']
            if 'conclusion' in story_data:
                story.conclusion = story_data['conclusion']
            if 'difficulty_level' in story_data:
                story.difficulty_level = story_data['difficulty_level']
            if 'solution_criteria' in story_data:
                story.solution_criteria = story_data['solution_criteria']
            if 'specialization_config' in story_data:
                story.specialization_config = story_data['specialization_config']
            if 'is_active' in story_data:
                story.is_active = story_data['is_active']
            
            db.commit()
            db.refresh(story)
            
            self.logger.info(f"História atualizada: ID {story.story_id}, Título: {story.title}")
            
            return self._story_to_dict(story)
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar história ID {story_id}: {str(e)}")
            raise
    
    def set_story_status(self, db: Session, story_id: int, is_active: bool) -> Dict[str, Any]:
        """
        Ativa ou desativa uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            is_active: True para ativar, False para desativar
            
        Returns:
            Dicionário com resultado da operação
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada para alterar status: ID {story_id}")
                return {
                    "success": False,
                    "message": "História não encontrada"
                }
            
            story.is_active = is_active
            db.commit()
            
            status = "ativada" if is_active else "desativada"
            self.logger.info(f"História {status}: ID {story.story_id}, Título: {story.title}")
            
            return {
                "success": True,
                "message": f"História {status} com sucesso",
                "story_id": story_id,
                "is_active": is_active
            }
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao alterar status da história ID {story_id}: {str(e)}")
            raise
    
    def update_solution_criteria(self, db: Session, story_id: int, 
                             solution_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza os critérios de solução de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            solution_criteria: Novos critérios de solução
            
        Returns:
            Dicionário com resultado da operação
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada para atualizar critérios: ID {story_id}")
                return {
                    "success": False,
                    "message": "História não encontrada"
                }
            
            story.solution_criteria = solution_criteria
            db.commit()
            
            self.logger.info(f"Critérios de solução atualizados: História ID {story_id}")
            
            return {
                "success": True,
                "message": "Critérios de solução atualizados com sucesso",
                "story_id": story_id,
                "solution_criteria": solution_criteria
            }
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar critérios de solução da história ID {story_id}: {str(e)}")
            raise
    
    def update_specialization_config(self, db: Session, story_id: int, 
                                  specialization_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza a configuração de especialização de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            specialization_config: Nova configuração de especialização
            
        Returns:
            Dicionário com resultado da operação
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada para atualizar especialização: ID {story_id}")
                return {
                    "success": False,
                    "message": "História não encontrada"
                }
            
            story.specialization_config = specialization_config
            db.commit()
            
            self.logger.info(f"Configuração de especialização atualizada: História ID {story_id}")
            
            return {
                "success": True,
                "message": "Configuração de especialização atualizada com sucesso",
                "story_id": story_id,
                "specialization_config": specialization_config
            }
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar configuração de especialização da história ID {story_id}: {str(e)}")
            raise
    
    def delete_story(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Remove uma história do banco de dados.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com resultado da operação
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada para exclusão: ID {story_id}")
                return {
                    "success": False,
                    "message": "História não encontrada"
                }
            
            # Armazenar informações para o log
            story_title = story.title
            
            # Remover a história
            db.delete(story)
            db.commit()
            
            self.logger.info(f"História excluída: ID {story_id}, Título: {story_title}")
            
            return {
                "success": True,
                "message": "História excluída com sucesso",
                "story_id": story_id
            }
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao excluir história ID {story_id}: {str(e)}")
            raise
    
    def get_story_stats(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém estatísticas detalhadas sobre uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com estatísticas da história
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada para estatísticas: ID {story_id}")
                return {
                    "success": False,
                    "message": "História não encontrada"
                }
            
            # Contar componentes
            locations_count = db.query(func.count(story_location_association.c.location_id)).filter(
                story_location_association.c.story_id == story_id
            ).scalar() or 0
            
            characters_count = db.query(func.count(story_character_association.c.character_id)).filter(
                story_character_association.c.story_id == story_id
            ).scalar() or 0
            
            objects_count = db.query(func.count(GameObject.object_id)).filter(
                GameObject.story_id == story_id
            ).scalar() or 0
            
            clues_count = db.query(func.count(Clue.clue_id)).filter(
                Clue.story_id == story_id
            ).scalar() or 0
            
            key_evidence_count = db.query(func.count(Clue.clue_id)).filter(
                Clue.story_id == story_id,
                Clue.is_key_evidence == True
            ).scalar() or 0
            
            prompt_templates_count = db.query(func.count(PromptTemplate.template_id)).filter(
                PromptTemplate.story_id == story_id
            ).scalar() or 0
            
            # Verificar a complexidade da história
            complexity_score = self._calculate_complexity_score(
                locations_count, 
                characters_count, 
                objects_count, 
                clues_count
            )
            
            return {
                "success": True,
                "story_id": story_id,
                "title": story.title,
                "difficulty_level": story.difficulty_level,
                "locations_count": locations_count,
                "characters_count": characters_count,
                "objects_count": objects_count,
                "clues_count": clues_count,
                "key_evidence_count": key_evidence_count,
                "prompt_templates_count": prompt_templates_count,
                "complexity_score": complexity_score,
                "complexity_category": self._get_complexity_category(complexity_score),
                "has_culprit": self._has_culprit(db, story_id),
                "has_starting_location": self._has_starting_location(db, story_id)
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao obter estatísticas da história ID {story_id}: {str(e)}")
            raise
    
    def check_story_consistency(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Verifica a consistência de uma história para identificar possíveis problemas.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com resultados da verificação
        """
        try:
            story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not story:
                self.logger.warning(f"História não encontrada para verificação: ID {story_id}")
                return {
                    "success": False,
                    "message": "História não encontrada"
                }
            
            issues = []
            
            # Verificar se há localização inicial
            if not self._has_starting_location(db, story_id):
                issues.append("A história não possui localização inicial")
            
            # Verificar se há culpado
            if not self._has_culprit(db, story_id):
                issues.append("A história não possui culpado definido")
            
            # Verificar se há critérios de solução
            solution_criteria = self._parse_json_field(story.solution_criteria)
            if not solution_criteria:
                issues.append("A história não possui critérios de solução definidos")
            
            # Verificar se há pistas suficientes
            clues_count = db.query(func.count(Clue.clue_id)).filter(
                Clue.story_id == story_id
            ).scalar() or 0
            
            if clues_count < 3:
                issues.append(f"A história possui poucas pistas ({clues_count})")
            
            # Verificar se há templates de prompt
            prompt_templates_count = db.query(func.count(PromptTemplate.template_id)).filter(
                PromptTemplate.story_id == story_id
            ).scalar() or 0
            
            if prompt_templates_count == 0:
                issues.append("A história não possui templates de prompt")
            
            return {
                "success": True,
                "story_id": story_id,
                "title": story.title,
                "has_issues": len(issues) > 0,
                "issues": issues
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao verificar consistência da história ID {story_id}: {str(e)}")
            raise
    
    def clone_story(self, db: Session, story_id: int, new_title: str = None) -> Dict[str, Any]:
        """
        Cria uma cópia de uma história existente.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história a ser clonada
            new_title: Novo título (opcional)
            
        Returns:
            Dicionário com dados da nova história
        """
        try:
            # Obter a história original
            original_story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not original_story:
                self.logger.warning(f"História não encontrada para clonagem: ID {story_id}")
                return {
                    "success": False,
                    "message": "História original não encontrada"
                }
            
            # Criar nova história
            new_story = Story(
                title=new_title or f"{original_story.title} (Cópia)",
                description=original_story.description,
                introduction=original_story.introduction,
                conclusion=original_story.conclusion,
                difficulty_level=original_story.difficulty_level,
                solution_criteria=original_story.solution_criteria,
                specialization_config=original_story.specialization_config,
                is_active=True,
                created_at=datetime.now()
            )
            
            db.add(new_story)
            db.flush()
            
            # Copiar associações com localizações
            for location in original_story.locations:
                new_story.locations.append(location)
            
            # Copiar associações com personagens
            for character in original_story.characters:
                new_story.characters.append(character)
            
            # Copiar objetos
            for obj in db.query(GameObject).filter(GameObject.story_id == story_id).all():
                new_obj = GameObject(
                    story_id=new_story.story_id,
                    name=obj.name,
                    base_description=obj.base_description,
                    is_collectible=obj.is_collectible,
                    initial_location_id=obj.initial_location_id,
                    initial_area_id=obj.initial_area_id,
                    discovery_condition=obj.discovery_condition
                )
                db.add(new_obj)
            
            # Copiar pistas
            for clue in db.query(Clue).filter(Clue.story_id == story_id).all():
                new_clue = Clue(
                    story_id=new_story.story_id,
                    name=clue.name,
                    description=clue.description,
                    type=clue.type,
                    relevance=clue.relevance,
                    is_key_evidence=clue.is_key_evidence,
                    related_aspect=clue.related_aspect,
                    discovery_conditions=clue.discovery_conditions
                )
                db.add(new_clue)
            
            # Copiar templates de prompt
            for template in db.query(PromptTemplate).filter(PromptTemplate.story_id == story_id).all():
                new_template = PromptTemplate(
                    story_id=new_story.story_id,
                    template_name=template.template_name,
                    template_type=template.template_type,
                    context_level=template.context_level,
                    prompt_structure=template.prompt_structure,
                    variables=template.variables,
                    purpose=template.purpose,
                    usage_instructions=template.usage_instructions
                )
                db.add(new_template)
            
            db.commit()
            db.refresh(new_story)
            
            self.logger.info(f"História clonada: Original ID {story_id}, Nova ID {new_story.story_id}")
            
            return {
                "success": True,
                "message": "História clonada com sucesso",
                "original_id": story_id,
                "new_story": self._story_to_dict(new_story)
            }
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao clonar história ID {story_id}: {str(e)}")
            raise
    
    def create_story_version(self, db: Session, story_id: int, 
                          version_name: str, version_notes: str = None) -> Dict[str, Any]:
        """
        Cria uma nova versão da história, preservando a original.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história original
            version_name: Nome da versão
            version_notes: Notas sobre as alterações (opcional)
            
        Returns:
            Dicionário com dados da nova versão
        """
        try:
            # Esta é uma implementação simplificada de versionamento
            # Em um sistema real, seria necessário uma tabela específica para versões
            
            # Obter a história original
            original_story = db.query(Story).filter(Story.story_id == story_id).first()
            
            if not original_story:
                self.logger.warning(f"História não encontrada para versionamento: ID {story_id}")
                return {
                    "success": False,
                    "message": "História original não encontrada"
                }
            
            # Clonar a história
            clone_result = self.clone_story(db, story_id, f"{original_story.title} - {version_name}")
            
            if not clone_result.get("success", False):
                return clone_result
            
            # Adicionar metadados de versão
            new_story_id = clone_result["new_story"]["story_id"]
            new_story = db.query(Story).filter(Story.story_id == new_story_id).first()
            
            # Em um sistema real, esses metadados estariam em uma tabela separada
            version_metadata = {
                "is_version": True,
                "original_story_id": story_id,
                "version_name": version_name,
                "version_date": datetime.now().isoformat(),
                "version_notes": version_notes or ""
            }
            
            # Como não temos uma tabela específica, armazenamos no campo de descrição
            if new_story.description:
                new_story.description += f"\n\nVERSION METADATA: {json.dumps(version_metadata)}"
            else:
                new_story.description = f"VERSION METADATA: {json.dumps(version_metadata)}"
            
            db.commit()
            
            self.logger.info(f"Versão criada: Original ID {story_id}, Nova versão ID {new_story_id}, Nome: {version_name}")
            
            return {
                "success": True,
                "message": "Versão criada com sucesso",
                "original_id": story_id,
                "version_id": new_story_id,
                "version_name": version_name,
                "version_date": version_metadata["version_date"]
            }
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar versão da história ID {story_id}: {str(e)}")
            raise
    
    # Métodos auxiliares privados
    
    def _story_to_dict(self, story: Story) -> Dict[str, Any]:
        """
        Converte um objeto Story para um dicionário.
        
        Args:
            story: Objeto Story
            
        Returns:
            Dicionário com dados da história
        """
        return {
            "story_id": story.story_id,
            "title": story.title,
            "description": story.description,
            "introduction": story.introduction,
            "conclusion": story.conclusion,
            "difficulty_level": story.difficulty_level,
            "created_at": story.created_at,
            "solution_criteria": self._parse_json_field(story.solution_criteria),
            "specialization_config": self._parse_json_field(story.specialization_config),
            "is_active": story.is_active
        }
    
    def _location_to_dict(self, location: Location) -> Dict[str, Any]:
        """
        Converte um objeto Location para um dicionário.
        
        Args:
            location: Objeto Location
            
        Returns:
            Dicionário com dados da localização
        """
        return {
            "location_id": location.location_id,
            "name": location.name,
            "description": location.description,
            "is_locked": location.is_locked,
            "unlock_condition": location.unlock_condition,
            "navigation_map": self._parse_json_field(location.navigation_map),
            "is_starting_location": location.is_starting_location
        }
    
    def _character_to_dict(self, character: Character) -> Dict[str, Any]:
        """
        Converte um objeto Character para um dicionário.
        
        Args:
            character: Objeto Character
            
        Returns:
            Dicionário com dados do personagem
        """
        return {
            "character_id": character.character_id,
            "name": character.name,
            "base_description": character.base_description,
            "personality": character.personality,
            "appearance": character.appearance,
            "is_culprit": character.is_culprit,
            "motive": character.motive,
            "location_schedule": self._parse_json_field(character.location_schedule)
        }
    
    def _object_to_dict(self, obj: GameObject) -> Dict[str, Any]:
        """
        Converte um objeto GameObject para um dicionário.
        
        Args:
            obj: Objeto GameObject
            
        Returns:
            Dicionário com dados do objeto
        """
        return {
            "object_id": obj.object_id,
            "story_id": obj.story_id,
            "name": obj.name,
            "base_description": obj.base_description,
            "is_collectible": obj.is_collectible,
            "initial_location_id": obj.initial_location_id,
            "initial_area_id": obj.initial_area_id,
            "discovery_condition": obj.discovery_condition
        }
    
    def _clue_to_dict(self, clue: Clue) -> Dict[str, Any]:
        """
        Converte um objeto Clue para um dicionário.
        
        Args:
            clue: Objeto Clue
            
        Returns:
            Dicionário com dados da pista
        """
        return {
            "clue_id": clue.clue_id,
            "story_id": clue.story_id,
            "name": clue.name,
            "description": clue.description,
            "type": clue.type,
            "relevance": clue.relevance,
            "is_key_evidence": clue.is_key_evidence,
            "related_aspect": clue.related_aspect,
            "discovery_conditions": self._parse_json_field(clue.discovery_conditions)
        }
    
    def _prompt_template_to_dict(self, template: PromptTemplate) -> Dict[str, Any]:
        """
        Converte um objeto PromptTemplate para um dicionário.
        
        Args:
            template: Objeto PromptTemplate
            
        Returns:
            Dicionário com dados do template
        """
        return {
            "template_id": template.template_id,
            "story_id": template.story_id,
            "template_name": template.template_name,
            "template_type": template.template_type,
            "context_level": template.context_level,
            "prompt_structure": template.prompt_structure,
            "variables": self._parse_json_field(template.variables),
            "purpose": template.purpose,
            "usage_instructions": template.usage_instructions
        }
    
    def _parse_json_field(self, value: Any) -> Any:
        """
        Analisa um campo que pode estar armazenado como JSON.
        
        Args:
            value: Valor que pode ser string JSON ou outra coisa
            
        Returns:
            Valor decodificado ou o valor original
        """
        if value is None:
            return {}
            
        if isinstance(value, (dict, list)):
            return value
            
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        return value
    
    def _calculate_complexity_score(self, locations_count: int, characters_count: int, 
                                 objects_count: int, clues_count: int) -> float:
        """
        Calcula uma pontuação de complexidade para a história com base em seus componentes.
        
        Args:
            locations_count: Número de localizações
            characters_count: Número de personagens
            objects_count: Número de objetos
            clues_count: Número de pistas
            
        Returns:
            Pontuação de complexidade
        """
        # Fórmula simples para calcular complexidade
        # Cada componente tem um peso diferente
        location_weight = 1.5
        character_weight = 2.0
        object_weight = 1.0
        clue_weight = 1.2
        
        # Calcular a pontuação
        score = (
            locations_count * location_weight +
            characters_count * character_weight + 
            objects_count * object_weight + 
            clues_count * clue_weight
        )
        
        return round(score, 2)
    
    def _get_complexity_category(self, score: float) -> str:
        """
        Determina a categoria de complexidade com base na pontuação.
        
        Args:
            score: Pontuação de complexidade
            
        Returns:
            Categoria de complexidade
        """
        if score < 20:
            return "Simples"
        elif score < 40:
            return "Moderada"
        elif score < 60:
            return "Complexa"
        elif score < 80:
            return "Muito Complexa"
        else:
            return "Extremamente Complexa"
    
    def _has_culprit(self, db: Session, story_id: int) -> bool:
        """
        Verifica se a história tem um culpado definido.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            True se a história tem um culpado
        """
        try:
            return db.query(func.count(Character.character_id)).join(
                story_character_association,
                Character.character_id == story_character_association.c.character_id
            ).filter(
                story_character_association.c.story_id == story_id,
                Character.is_culprit == True
            ).scalar() > 0
        except SQLAlchemyError:
            return False
    
    def _has_starting_location(self, db: Session, story_id: int) -> bool:
        """
        Verifica se a história tem uma localização inicial definida.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            True se a história tem uma localização inicial
        """
        try:
            return db.query(func.count(Location.location_id)).join(
                story_location_association,
                Location.location_id == story_location_association.c.location_id
            ).filter(
                story_location_association.c.story_id == story_id,
                Location.is_starting_location == True
            ).scalar() > 0
        except SQLAlchemyError:
            return False