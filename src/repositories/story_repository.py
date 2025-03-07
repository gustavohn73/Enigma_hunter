# src/repositories/story_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.models.db_models import Story, Location, Character, GameObject, Clue, PromptTemplate
from src.repositories.base_repository import BaseRepository

class StoryRepository(BaseRepository[Story]):
    """
    Repositório para operações de banco de dados relacionadas a histórias/casos.
    Gerencia histórias e seus componentes relacionados como localizações, personagens, objetos e pistas.
    """
    
    def __init__(self):
        super().__init__(Story)
    
    def get_by_id(self, db: Session, story_id: int) -> Optional[Story]:
        """
        Busca uma história pelo ID.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            História encontrada ou None
        """
        return db.query(Story).filter(Story.story_id == story_id).first()
    
    def get_by_title(self, db: Session, title: str) -> Optional[Story]:
        """
        Busca uma história pelo título.
        
        Args:
            db: Sessão do banco de dados
            title: Título da história
            
        Returns:
            História encontrada ou None
        """
        return db.query(Story).filter(Story.title == title).first()
    
    def get_active_stories(self, db: Session) -> List[Story]:
        """
        Obtém todas as histórias ativas.
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            Lista de histórias ativas
        """
        return db.query(Story).filter(Story.is_active == True).all()
    
    def get_story_with_details(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém uma história com todos os seus detalhes relacionados.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Dicionário com a história e seus detalhes
        """
        story = db.query(Story).filter(Story.story_id == story_id).first()
        
        if not story:
            return None
        
        locations = db.query(Location).join(Location.stories).filter(Story.story_id == story_id).all()
        characters = db.query(Character).join(Character.stories).filter(Story.story_id == story_id).all()
        objects = db.query(GameObject).filter(GameObject.story_id == story_id).all()
        clues = db.query(Clue).filter(Clue.story_id == story_id).all()
        prompt_templates = db.query(PromptTemplate).filter(PromptTemplate.story_id == story_id).all()
        
        return {
            "story": story,
            "locations": locations,
            "characters": characters,
            "objects": objects,
            "clues": clues,
            "prompt_templates": prompt_templates
        }
    
    def get_story_solution_criteria(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém os critérios de solução de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Critérios de solução
        """
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            return None
            
        return story.solution_criteria
    
    def get_story_specialization_config(self, db: Session, story_id: int) -> Dict[str, Any]:
        """
        Obtém a configuração de especialização de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Configuração de especialização
        """
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            return None
            
        return story.specialization_config
    
    def get_story_locations(self, db: Session, story_id: int) -> List[Location]:
        """
        Obtém todas as localizações de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de localizações
        """
        return db.query(Location).join(Location.stories).filter(Story.story_id == story_id).all()
    
    def get_starting_location(self, db: Session, story_id: int) -> Optional[Location]:
        """
        Obtém a localização inicial de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Localização inicial ou None
        """
        return db.query(Location).join(Location.stories).filter(
            Story.story_id == story_id,
            Location.is_starting_location == True
        ).first()
    
    def get_story_characters(self, db: Session, story_id: int) -> List[Character]:
        """
        Obtém todos os personagens de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de personagens
        """
        return db.query(Character).join(Character.stories).filter(Story.story_id == story_id).all()
    
    def get_culprit(self, db: Session, story_id: int) -> Optional[Character]:
        """
        Obtém o culpado de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Personagem culpado ou None
        """
        return db.query(Character).join(Character.stories).filter(
            Story.story_id == story_id,
            Character.is_culprit == True
        ).first()
    
    def get_story_objects(self, db: Session, story_id: int) -> List[GameObject]:
        """
        Obtém todos os objetos de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de objetos
        """
        return db.query(GameObject).filter(GameObject.story_id == story_id).all()
    
    def get_story_clues(self, db: Session, story_id: int, is_key_evidence: bool = None) -> List[Clue]:
        """
        Obtém todas as pistas de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            is_key_evidence: Filtrar por pistas-chave (opcional)
            
        Returns:
            Lista de pistas
        """
        query = db.query(Clue).filter(Clue.story_id == story_id)
        
        if is_key_evidence is not None:
            query = query.filter(Clue.is_key_evidence == is_key_evidence)
            
        return query.all()
    
    def get_story_prompt_templates(self, db: Session, story_id: int, template_type: str = None) -> List[PromptTemplate]:
        """
        Obtém todos os templates de prompt de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            template_type: Tipo de template (opcional)
            
        Returns:
            Lista de templates de prompt
        """
        query = db.query(PromptTemplate).filter(PromptTemplate.story_id == story_id)
        
        if template_type:
            query = query.filter(PromptTemplate.template_type == template_type)
            
        return query.all()
    
    def activate_story(self, db: Session, story_id: int) -> bool:
        """
        Ativa uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            True se ativada com sucesso
        """
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            return False
            
        story.is_active = True
        self.update(db, story)
        return True
    
    def deactivate_story(self, db: Session, story_id: int) -> bool:
        """
        Desativa uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            True se desativada com sucesso
        """
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            return False
            
        story.is_active = False
        self.update(db, story)
        return True
    
    def update_solution_criteria(self, db: Session, story_id: int, solution_criteria: Dict[str, Any]) -> bool:
        """
        Atualiza os critérios de solução de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            solution_criteria: Novos critérios de solução
            
        Returns:
            True se atualizado com sucesso
        """
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            return False
            
        story.solution_criteria = solution_criteria
        self.update(db, story)
        return True
    
    def update_specialization_config(self, db: Session, story_id: int, specialization_config: Dict[str, Any]) -> bool:
        """
        Atualiza a configuração de especialização de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            specialization_config: Nova configuração de especialização
            
        Returns:
            True se atualizado com sucesso
        """
        story = db.query(Story).filter(Story.story_id == story_id).first()
        if not story:
            return False
            
        story.specialization_config = specialization_config
        self.update(db, story)
        return True