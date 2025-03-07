# src/repositories/location_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.models.db_models import Location, LocationArea, AreaDetail, Story
from src.repositories.base_repository import BaseRepository

class LocationRepository(BaseRepository[Location]):
    """
    Repositório para operações de banco de dados relacionadas a localizações.
    Gerencia localizações, áreas dentro de localizações e detalhes específicos de área.
    """
    
    def __init__(self):
        super().__init__(Location)
    
    def get_by_id(self, db: Session, location_id: int) -> Optional[Location]:
        """
        Busca uma localização pelo ID.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Localização encontrada ou None
        """
        return db.query(Location).filter(Location.location_id == location_id).first()
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[Location]:
        """
        Busca todas as localizações de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de localizações da história
        """
        return db.query(Location).join(
            Location.stories
        ).filter(
            Story.story_id == story_id
        ).all()
    
    def get_starting_location(self, db: Session, story_id: int) -> Optional[Location]:
        """
        Obtém a localização inicial de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Localização inicial ou None
        """
        return db.query(Location).join(
            Location.stories
        ).filter(
            Story.story_id == story_id,
            Location.is_starting_location == True
        ).first()
    
    def get_location_with_areas(self, db: Session, location_id: int) -> Dict[str, Any]:
        """
        Obtém uma localização com todas as suas áreas.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Dicionário com a localização e suas áreas
        """
        location = db.query(Location).filter(Location.location_id == location_id).first()
        
        if not location:
            return None
            
        areas = db.query(LocationArea).filter(LocationArea.location_id == location_id).all()
        
        return {
            "location": location,
            "areas": areas
        }
    
    def get_connected_locations(self, db: Session, location_id: int) -> List[Location]:
        """
        Obtém as localizações conectadas a uma localização específica.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Lista de localizações conectadas
        """
        location = db.query(Location).filter(Location.location_id == location_id).first()
        
        if not location or not location.navigation_map:
            return []
            
        connected_ids = location.navigation_map.get('connected_locations', [])
        
        return db.query(Location).filter(Location.location_id.in_(connected_ids)).all()
    
    def get_area_by_id(self, db: Session, area_id: int) -> Optional[LocationArea]:
        """
        Busca uma área específica pelo ID.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Área encontrada ou None
        """
        return db.query(LocationArea).filter(LocationArea.area_id == area_id).first()
    
    def get_areas_by_location(self, db: Session, location_id: int, 
                           discovery_level: int = None) -> List[LocationArea]:
        """
        Obtém as áreas de uma localização, com filtro opcional por nível de descoberta.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            discovery_level: Nível mínimo de descoberta necessário (opcional)
            
        Returns:
            Lista de áreas
        """
        query = db.query(LocationArea).filter(LocationArea.location_id == location_id)
        
        if discovery_level is not None:
            query = query.filter(LocationArea.discovery_level_required <= discovery_level)
            
        return query.all()
    
    def get_initially_visible_areas(self, db: Session, location_id: int) -> List[LocationArea]:
        """
        Obtém áreas inicialmente visíveis em uma localização.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Lista de áreas inicialmente visíveis
        """
        return db.query(LocationArea).filter(
            LocationArea.location_id == location_id,
            LocationArea.initially_visible == True
        ).all()
    
    def get_connected_areas(self, db: Session, area_id: int) -> List[LocationArea]:
        """
        Obtém as áreas conectadas a uma área específica.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de áreas conectadas
        """
        area = db.query(LocationArea).filter(LocationArea.area_id == area_id).first()
        
        if not area or not area.connected_areas:
            return []
            
        connected_ids = area.connected_areas
        
        return db.query(LocationArea).filter(LocationArea.area_id.in_(connected_ids)).all()
    
    def get_area_details(self, db: Session, area_id: int, 
                       discovery_level: int = None) -> List[AreaDetail]:
        """
        Obtém os detalhes de uma área, com filtro opcional por nível de descoberta.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            discovery_level: Nível mínimo de descoberta necessário (opcional)
            
        Returns:
            Lista de detalhes da área
        """
        query = db.query(AreaDetail).filter(AreaDetail.area_id == area_id)
        
        if discovery_level is not None:
            query = query.filter(AreaDetail.discovery_level_required <= discovery_level)
            
        return query.all()
    
    def get_area_detail_by_id(self, db: Session, detail_id: int) -> Optional[AreaDetail]:
        """
        Busca um detalhe específico pelo ID.
        
        Args:
            db: Sessão do banco de dados
            detail_id: ID do detalhe
            
        Returns:
            Detalhe encontrado ou None
        """
        return db.query(AreaDetail).filter(AreaDetail.detail_id == detail_id).first()
    
    def get_area_details_with_clues(self, db: Session, area_id: int) -> List[AreaDetail]:
        """
        Obtém os detalhes de uma área que contêm pistas.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de detalhes com pistas
        """
        return db.query(AreaDetail).filter(
            AreaDetail.area_id == area_id,
            AreaDetail.has_clue == True
        ).all()
    
    def get_environment_hierarchy(self, db: Session, location_id: int, 
                               discovery_level: int = None) -> Dict[str, Any]:
        """
        Obtém a hierarquia completa de uma localização (localização -> áreas -> detalhes).
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            discovery_level: Nível mínimo de descoberta necessário (opcional)
            
        Returns:
            Hierarquia completa do ambiente
        """
        location = self.get_by_id(db, location_id)
        
        if not location:
            return None
            
        areas = self.get_areas_by_location(db, location_id, discovery_level)
        
        areas_with_details = []
        for area in areas:
            details = self.get_area_details(db, area.area_id, discovery_level)
            areas_with_details.append({
                "area": area,
                "details": details
            })
        
        return {
            "location": location,
            "areas": areas_with_details
        }
    
    def check_location_accessible(self, db: Session, location_id: int, player_level: int = 0) -> bool:
        """
        Verifica se uma localização está acessível com base nas condições de desbloqueio.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            player_level: Nível atual do jogador
            
        Returns:
            True se a localização estiver acessível
        """
        location = self.get_by_id(db, location_id)
        
        if not location:
            return False
            
        # Se a localização não estiver bloqueada, está sempre acessível
        if not location.is_locked:
            return True
            
        # Implementar lógica de verificação da condição de desbloqueio
        # Esta é uma verificação simplificada; implementações reais verificariam
        # condições específicas definidas em location.unlock_condition
        
        # Por enquanto, assumimos uma verificação simples de nível
        return player_level >= 1
    
    def unlock_location(self, db: Session, location_id: int) -> bool:
        """
        Desbloqueia uma localização.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            True se desbloqueada com sucesso
        """
        location = self.get_by_id(db, location_id)
        
        if not location:
            return False
            
        location.is_locked = False
        self.update(db, location)
        return True
    
    def add_area_to_location(self, db: Session, location_id: int, area_data: Dict[str, Any]) -> LocationArea:
        """
        Adiciona uma nova área a uma localização.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            area_data: Dados da nova área
            
        Returns:
            Nova área criada
        """
        location = self.get_by_id(db, location_id)
        
        if not location:
            return None
            
        area = LocationArea(
            location_id=location_id,
            name=area_data.get('name', 'Nova Área'),
            description=area_data.get('description', ''),
            initially_visible=area_data.get('initially_visible', True),
            connected_areas=area_data.get('connected_areas', []),
            discovery_level_required=area_data.get('discovery_level_required', 0)
        )
        
        db.add(area)
        db.commit()
        db.refresh(area)
        
        return area
    
    def add_detail_to_area(self, db: Session, area_id: int, detail_data: Dict[str, Any]) -> AreaDetail:
        """
        Adiciona um novo detalhe a uma área.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            detail_data: Dados do novo detalhe
            
        Returns:
            Novo detalhe criado
        """
        area = self.get_area_by_id(db, area_id)
        
        if not area:
            return None
            
        detail = AreaDetail(
            area_id=area_id,
            name=detail_data.get('name', 'Novo Detalhe'),
            description=detail_data.get('description', ''),
            discovery_level_required=detail_data.get('discovery_level_required', 0),
            has_clue=detail_data.get('has_clue', False),
            clue_id=detail_data.get('clue_id')
        )
        
        db.add(detail)
        db.commit()
        db.refresh(detail)
        
        return detail