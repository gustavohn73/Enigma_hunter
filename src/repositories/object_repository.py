# src/repositories/object_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.models.db_models import GameObject, ObjectLevel, Clue
from src.repositories.base_repository import BaseRepository

class ObjectRepository(BaseRepository[GameObject]):
    """
    Repositório para operações de banco de dados relacionadas a objetos do jogo.
    Gerencia objetos, seus diferentes níveis de conhecimento e relacionamentos com pistas.
    """
    
    def __init__(self):
        super().__init__(GameObject)
    
    def get_by_id(self, db: Session, object_id: int) -> Optional[GameObject]:
        """
        Busca um objeto pelo ID.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            
        Returns:
            Objeto encontrado ou None
        """
        return db.query(GameObject).filter(GameObject.object_id == object_id).first()
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[GameObject]:
        """
        Busca todos os objetos de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de objetos da história
        """
        return db.query(GameObject).filter(GameObject.story_id == story_id).all()
    
    def get_by_location(self, db: Session, location_id: int, area_id: int = None) -> List[GameObject]:
        """
        Busca objetos por localização e, opcionalmente, por área específica.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            area_id: ID da área (opcional)
            
        Returns:
            Lista de objetos na localização/área
        """
        query = db.query(GameObject).filter(GameObject.initial_location_id == location_id)
        
        if area_id is not None:
            query = query.filter(GameObject.initial_area_id == area_id)
            
        return query.all()
    
    def get_object_with_levels(self, db: Session, object_id: int) -> Dict[str, Any]:
        """
        Obtém um objeto com todos os seus níveis de conhecimento.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            
        Returns:
            Dicionário com dados do objeto e seus níveis
        """
        game_object = self.get_by_id(db, object_id)
        
        if not game_object:
            return None
            
        levels = db.query(ObjectLevel).filter(
            ObjectLevel.object_id == object_id
        ).order_by(
            ObjectLevel.level_number
        ).all()
        
        return {
            "object": game_object,
            "levels": levels
        }
    
    def get_object_level(self, db: Session, object_id: int, level_number: int) -> Optional[ObjectLevel]:
        """
        Obtém um nível específico de conhecimento sobre um objeto.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            level_number: Número do nível
            
        Returns:
            Nível do objeto ou None
        """
        return db.query(ObjectLevel).filter(
            ObjectLevel.object_id == object_id,
            ObjectLevel.level_number == level_number
        ).first()
    
    def get_next_level_requirements(self, db: Session, object_id: int, current_level: int) -> Dict[str, Any]:
        """
        Obtém os requisitos para evoluir um objeto para o próximo nível.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            current_level: Nível atual do objeto
            
        Returns:
            Dicionário com requisitos para evolução ou None se não houver próximo nível
        """
        next_level = current_level + 1
        
        next_level_data = db.query(ObjectLevel).filter(
            ObjectLevel.object_id == object_id,
            ObjectLevel.level_number == next_level
        ).first()
        
        if not next_level_data:
            return None
            
        # Se houver uma pista relacionada, a obtemos
        related_clue = None
        if next_level_data.related_clue_id:
            related_clue = db.query(Clue).filter(
                Clue.clue_id == next_level_data.related_clue_id
            ).first()
        
        return {
            "level": next_level_data,
            "evolution_trigger": next_level_data.evolution_trigger,
            "related_clue": related_clue
        }
    
    def get_collectible_objects(self, db: Session, story_id: int) -> List[GameObject]:
        """
        Obtém todos os objetos coletáveis de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de objetos coletáveis
        """
        return db.query(GameObject).filter(
            GameObject.story_id == story_id,
            GameObject.is_collectible == True
        ).all()
    
    def get_objects_related_to_clue(self, db: Session, clue_id: int) -> List[GameObject]:
        """
        Obtém objetos relacionados a uma pista específica.
        
        Args:
            db: Sessão do banco de dados
            clue_id: ID da pista
            
        Returns:
            Lista de objetos relacionados à pista
        """
        return db.query(GameObject).join(
            ObjectLevel
        ).filter(
            ObjectLevel.related_clue_id == clue_id
        ).distinct().all()
    
    def check_object_evolution(self, db: Session, object_id: int, current_level: int, 
                             trigger_value: str = None) -> bool:
        """
        Verifica se um objeto pode evoluir para o próximo nível com base no gatilho.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            current_level: Nível atual do objeto
            trigger_value: Valor do gatilho a verificar (opcional)
            
        Returns:
            True se o objeto pode evoluir, False caso contrário
        """
        next_level_requirements = self.get_next_level_requirements(db, object_id, current_level)
        
        if not next_level_requirements:
            return False
            
        # Se não há trigger_value e não há evolution_trigger definido, 
        # assumimos que o objeto pode evoluir automaticamente
        if not trigger_value and not next_level_requirements["evolution_trigger"]:
            return True
            
        # Se há evolution_trigger, verificamos se o trigger_value corresponde
        if trigger_value and next_level_requirements["evolution_trigger"]:
            # Implementação simplificada; em um sistema real, 
            # poderíamos ter verificações mais complexas
            return trigger_value == next_level_requirements["evolution_trigger"]
            
        return False
    
    def create_object(self, db: Session, object_data: Dict[str, Any]) -> GameObject:
        """
        Cria um novo objeto no jogo.
        
        Args:
            db: Sessão do banco de dados
            object_data: Dados do novo objeto
            
        Returns:
            Objeto criado
        """
        game_object = GameObject(
            story_id=object_data.get("story_id"),
            name=object_data.get("name"),
            base_description=object_data.get("base_description"),
            is_collectible=object_data.get("is_collectible", True),
            initial_location_id=object_data.get("initial_location_id"),
            initial_area_id=object_data.get("initial_area_id"),
            discovery_condition=object_data.get("discovery_condition")
        )
        
        db.add(game_object)
        db.commit()
        db.refresh(game_object)
        
        return game_object
    
    def add_object_level(self, db: Session, object_id: int, level_data: Dict[str, Any]) -> ObjectLevel:
        """
        Adiciona um novo nível a um objeto.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            level_data: Dados do novo nível
            
        Returns:
            Nível do objeto criado
        """
        object_level = ObjectLevel(
            object_id=object_id,
            level_number=level_data.get("level_number"),
            level_description=level_data.get("level_description"),
            level_attributes=level_data.get("level_attributes"),
            evolution_trigger=level_data.get("evolution_trigger"),
            related_clue_id=level_data.get("related_clue_id")
        )
        
        db.add(object_level)
        db.commit()
        db.refresh(object_level)
        
        return object_level