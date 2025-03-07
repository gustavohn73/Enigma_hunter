# src/repositories/clue_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.models.db_models import Clue, AreaDetail, GameObject, ObjectLevel
from src.repositories.base_repository import BaseRepository

class ClueRepository(BaseRepository[Clue]):
    """
    Repositório para operações de banco de dados relacionadas a pistas.
    Gerencia pistas, suas localizações e relacionamentos com objetos e personagens.
    """
    
    def __init__(self):
        super().__init__(Clue)
    
    def get_by_id(self, db: Session, clue_id: int) -> Optional[Clue]:
        """
        Busca uma pista pelo ID.
        
        Args:
            db: Sessão do banco de dados
            clue_id: ID da pista
            
        Returns:
            Pista encontrada ou None
        """
        return db.query(Clue).filter(Clue.clue_id == clue_id).first()
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[Clue]:
        """
        Busca todas as pistas de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de pistas da história
        """
        return db.query(Clue).filter(Clue.story_id == story_id).all()
    
    def get_key_evidence(self, db: Session, story_id: int) -> List[Clue]:
        """
        Busca todas as pistas marcadas como evidências-chave em uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de pistas marcadas como evidências-chave
        """
        return db.query(Clue).filter(
            Clue.story_id == story_id,
            Clue.is_key_evidence == True
        ).all()
    
    def get_clues_by_type(self, db: Session, story_id: int, clue_type: str) -> List[Clue]:
        """
        Busca pistas por tipo específico (física, testemunho, etc).
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            clue_type: Tipo de pista
            
        Returns:
            Lista de pistas do tipo especificado
        """
        return db.query(Clue).filter(
            Clue.story_id == story_id,
            Clue.type == clue_type
        ).all()
    
    def get_clues_by_aspect(self, db: Session, story_id: int, related_aspect: str) -> List[Clue]:
        """
        Busca pistas relacionadas a um aspecto específico (culpado, método, motivo).
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            related_aspect: Aspecto relacionado
            
        Returns:
            Lista de pistas relacionadas ao aspecto
        """
        return db.query(Clue).filter(
            Clue.story_id == story_id,
            Clue.related_aspect == related_aspect
        ).all()
    
    def get_clues_by_relevance(self, db: Session, story_id: int, min_relevance: int = 1) -> List[Clue]:
        """
        Busca pistas com relevância igual ou superior a um valor mínimo.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            min_relevance: Relevância mínima
            
        Returns:
            Lista de pistas relevantes
        """
        return db.query(Clue).filter(
            Clue.story_id == story_id,
            Clue.relevance >= min_relevance
        ).order_by(Clue.relevance.desc()).all()
    
    def get_clues_in_area(self, db: Session, area_id: int) -> List[Clue]:
        """
        Busca pistas disponíveis em uma área específica.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de pistas na área
        """
        return db.query(Clue).join(
            AreaDetail
        ).filter(
            AreaDetail.area_id == area_id,
            AreaDetail.has_clue == True,
            AreaDetail.clue_id == Clue.clue_id
        ).all()
    
    def get_clues_from_objects(self, db: Session, object_ids: List[int]) -> List[Clue]:
        """
        Busca pistas relacionadas a objetos específicos.
        
        Args:
            db: Sessão do banco de dados
            object_ids: Lista de IDs de objetos
            
        Returns:
            Lista de pistas relacionadas aos objetos
        """
        return db.query(Clue).join(
            ObjectLevel, 
            ObjectLevel.related_clue_id == Clue.clue_id
        ).filter(
            ObjectLevel.object_id.in_(object_ids)
        ).distinct().all()
    
    def get_clue_discovery_locations(self, db: Session, clue_id: int) -> List[Dict[str, Any]]:
        """
        Obtém todas as localizações onde uma pista pode ser descoberta.
        
        Args:
            db: Sessão do banco de dados
            clue_id: ID da pista
            
        Returns:
            Lista de localizações onde a pista pode ser encontrada
        """
        # Busca em áreas que contêm a pista diretamente
        area_details = db.query(AreaDetail).filter(
            AreaDetail.clue_id == clue_id,
            AreaDetail.has_clue == True
        ).all()
        
        # Busca em objetos que revelam esta pista
        object_levels = db.query(ObjectLevel).filter(
            ObjectLevel.related_clue_id == clue_id
        ).all()
        
        discovery_locations = []
        
        # Adiciona localizações de área
        for detail in area_details:
            discovery_locations.append({
                "type": "area_detail",
                "detail_id": detail.detail_id,
                "area_id": detail.area_id,
                "name": detail.name,
                "discovery_level_required": detail.discovery_level_required
            })
        
        # Adiciona localizações de objeto
        for level in object_levels:
            object_data = db.query(GameObject).filter(
                GameObject.object_id == level.object_id
            ).first()
            
            if object_data:
                discovery_locations.append({
                    "type": "object",
                    "object_id": object_data.object_id,
                    "name": object_data.name,
                    "level_number": level.level_number,
                    "initial_location_id": object_data.initial_location_id,
                    "initial_area_id": object_data.initial_area_id
                })
        
        return discovery_locations
    
    def check_discovery_condition(self, db: Session, clue_id: int, condition_data: Dict[str, Any]) -> bool:
        """
        Verifica se as condições para descoberta de uma pista foram atendidas.
        
        Args:
            db: Sessão do banco de dados
            clue_id: ID da pista
            condition_data: Dados para verificação da condição (depende do tipo de condição)
            
        Returns:
            True se a condição foi atendida, False caso contrário
        """
        clue = self.get_by_id(db, clue_id)
        
        if not clue or not clue.discovery_conditions:
            return False
            
        # Implementação simplificada; em um sistema real, 
        # verificaríamos condições específicas definidas em clue.discovery_conditions
        # Pode envolver verificação de inventário, progresso, nível de especialização, etc.
        
        # Por exemplo, para uma pista que requer um nível mínimo de especialização:
        specialization_req = clue.discovery_conditions.get('specialization_required', {})
        if specialization_req:
            category = specialization_req.get('category')
            level = specialization_req.get('level', 0)
            
            if category and 'player_specializations' in condition_data:
                player_level = condition_data['player_specializations'].get(category, 0)
                if player_level < level:
                    return False
        
        # Para uma pista que requer certos objetos no inventário:
        required_objects = clue.discovery_conditions.get('required_objects', [])
        if required_objects and 'player_inventory' in condition_data:
            inventory = condition_data['player_inventory']
            if not all(obj_id in inventory for obj_id in required_objects):
                return False
        
        return True
    
    def create_clue(self, db: Session, clue_data: Dict[str, Any]) -> Clue:
        """
        Cria uma nova pista no jogo.
        
        Args:
            db: Sessão do banco de dados
            clue_data: Dados da nova pista
            
        Returns:
            Pista criada
        """
        clue = Clue(
            story_id=clue_data.get("story_id"),
            name=clue_data.get("name"),
            description=clue_data.get("description"),
            type=clue_data.get("type"),
            relevance=clue_data.get("relevance", 1),
            is_key_evidence=clue_data.get("is_key_evidence", False),
            related_aspect=clue_data.get("related_aspect"),
            discovery_conditions=clue_data.get("discovery_conditions", {})
        )
        
        db.add(clue)
        db.commit()
        db.refresh(clue)
        
        return clue
    
    def get_related_clues(self, db: Session, clue_id: int) -> List[Clue]:
        """
        Busca pistas relacionadas a uma pista específica (por aspecto ou tipo).
        
        Args:
            db: Sessão do banco de dados
            clue_id: ID da pista
            
        Returns:
            Lista de pistas relacionadas
        """
        clue = self.get_by_id(db, clue_id)
        
        if not clue:
            return []
            
        # Busca pistas do mesmo aspecto (culpado, método, motivo)
        return db.query(Clue).filter(
            Clue.story_id == clue.story_id,
            Clue.related_aspect == clue.related_aspect,
            Clue.clue_id != clue_id
        ).order_by(Clue.relevance.desc()).all()