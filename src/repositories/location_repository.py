# src/repositories/location_repository.py
from typing import List, Optional, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
import logging
import json

from src.models.db_models import Location, LocationArea, AreaDetail, Story
from src.repositories.base_repository import BaseRepository

class LocationRepository(BaseRepository[Location]):
    """
    Repositório para operações de banco de dados relacionadas a localizações.
    Gerencia localizações, áreas dentro de localizações e detalhes específicos de área.
    """
    
    def __init__(self):
        super().__init__(Location)
        self.logger = logging.getLogger(__name__)
    
    def get_by_id(self, db: Session, location_id: int) -> Optional[Location]:
        """
        Busca uma localização pelo ID.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Localização encontrada ou None
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(Location).filter(Location.location_id == location_id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar localização por ID {location_id}: {str(e)}")
            raise
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[Location]:
        """
        Busca todas as localizações de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de localizações da história
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(Location).join(
                Location.stories
            ).filter(
                Story.story_id == story_id
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar localizações da história {story_id}: {str(e)}")
            raise
    
    def get_starting_location(self, db: Session, story_id: int) -> Optional[Location]:
        """
        Obtém a localização inicial de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Localização inicial ou None
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(Location).join(
                Location.stories
            ).filter(
                Story.story_id == story_id,
                Location.is_starting_location == True
            ).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar localização inicial da história {story_id}: {str(e)}")
            raise
    
    def get_location_with_areas(self, db: Session, location_id: int) -> Dict[str, Any]:
        """
        Obtém uma localização com todas as suas áreas.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Dicionário com a localização e suas áreas
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Usar joinedload para evitar o problema N+1
            location = db.query(Location).options(
                joinedload(Location.areas)
            ).filter(
                Location.location_id == location_id
            ).first()
            
            if not location:
                return {"location": None, "areas": []}
            
            # Construir o dicionário de resposta com dados formatados
            return {
                "location": {
                    "location_id": location.location_id,
                    "name": location.name,
                    "description": location.description,
                    "is_locked": location.is_locked,
                    "unlock_condition": location.unlock_condition,
                    "navigation_map": self._parse_json_field(location.navigation_map),
                    "is_starting_location": location.is_starting_location
                },
                "areas": [
                    {
                        "area_id": area.area_id,
                        "name": area.name,
                        "description": area.description,
                        "initially_visible": area.initially_visible,
                        "connected_areas": self._parse_json_field(area.connected_areas),
                        "discovery_level_required": area.discovery_level_required
                    } for area in location.areas
                ]
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar localização com áreas para ID {location_id}: {str(e)}")
            raise
    
    def get_connected_locations(self, db: Session, location_id: int) -> List[Location]:
        """
        Obtém as localizações conectadas a uma localização específica.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Lista de localizações conectadas
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            location = self.get_by_id(db, location_id)
            
            if not location or not location.navigation_map:
                return []
                
            # Obtém os IDs de localizações conectadas
            connected_ids = self._get_connected_location_ids(location)
            
            if not connected_ids:
                return []
                
            # Busca as localizações conectadas
            return db.query(Location).filter(
                Location.location_id.in_(connected_ids)
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar localizações conectadas para ID {location_id}: {str(e)}")
            raise
    
    def get_area_by_id(self, db: Session, area_id: int) -> Optional[LocationArea]:
        """
        Busca uma área específica pelo ID.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Área encontrada ou None
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(LocationArea).filter(LocationArea.area_id == area_id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar área por ID {area_id}: {str(e)}")
            raise
    
    def get_areas_by_location(self, db: Session, location_id: int, 
                            discovery_level: Optional[int] = None) -> List[LocationArea]:
        """
        Obtém as áreas de uma localização, com filtro opcional por nível de descoberta.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            discovery_level: Nível mínimo de descoberta necessário (opcional)
            
        Returns:
            Lista de áreas
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(LocationArea).filter(LocationArea.location_id == location_id)
            
            if discovery_level is not None:
                query = query.filter(LocationArea.discovery_level_required <= discovery_level)
                
            return query.all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar áreas da localização {location_id}: {str(e)}")
            raise
    
    def get_initially_visible_areas(self, db: Session, location_id: int) -> List[LocationArea]:
        """
        Obtém áreas inicialmente visíveis em uma localização.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Lista de áreas inicialmente visíveis
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(LocationArea).filter(
                LocationArea.location_id == location_id,
                LocationArea.initially_visible == True
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar áreas inicialmente visíveis da localização {location_id}: {str(e)}")
            raise
    
    def get_connected_areas(self, db: Session, area_id: int) -> List[LocationArea]:
        """
        Obtém as áreas conectadas a uma área específica.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de áreas conectadas
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            area = self.get_area_by_id(db, area_id)
            
            if not area or not area.connected_areas:
                return []
                
            connected_ids = self._parse_json_field(area.connected_areas)
            
            if not connected_ids:
                return []
                
            return db.query(LocationArea).filter(
                LocationArea.area_id.in_(connected_ids)
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar áreas conectadas para área {area_id}: {str(e)}")
            raise
    
    def get_area_details(self, db: Session, area_id: int, 
                       discovery_level: Optional[int] = None) -> List[AreaDetail]:
        """
        Obtém os detalhes de uma área, com filtro opcional por nível de descoberta.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            discovery_level: Nível mínimo de descoberta necessário (opcional)
            
        Returns:
            Lista de detalhes da área
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(AreaDetail).filter(AreaDetail.area_id == area_id)
            
            if discovery_level is not None:
                query = query.filter(AreaDetail.discovery_level_required <= discovery_level)
                
            return query.all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar detalhes da área {area_id}: {str(e)}")
            raise
    
    def get_area_detail_by_id(self, db: Session, detail_id: int) -> Optional[AreaDetail]:
        """
        Busca um detalhe específico pelo ID.
        
        Args:
            db: Sessão do banco de dados
            detail_id: ID do detalhe
            
        Returns:
            Detalhe encontrado ou None
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(AreaDetail).filter(AreaDetail.detail_id == detail_id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar detalhe por ID {detail_id}: {str(e)}")
            raise
    
    def get_area_details_with_clues(self, db: Session, area_id: int) -> List[AreaDetail]:
        """
        Obtém os detalhes de uma área que contêm pistas.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de detalhes com pistas
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(AreaDetail).filter(
                AreaDetail.area_id == area_id,
                AreaDetail.has_clue == True
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar detalhes com pistas da área {area_id}: {str(e)}")
            raise
    
    def get_environment_hierarchy(self, db: Session, location_id: int, 
                              discovery_level: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtém a hierarquia completa de uma localização (localização -> áreas -> detalhes).
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            discovery_level: Nível mínimo de descoberta necessário (opcional)
            
        Returns:
            Hierarquia completa do ambiente
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Busca a localização com join otimizado
            location = db.query(Location).options(
                joinedload(Location.areas).joinedload(LocationArea.details)
            ).filter(
                Location.location_id == location_id
            ).first()
            
            if not location:
                return {"location": None, "areas": []}
            
            # Filtra áreas e detalhes com base no nível de descoberta
            areas_with_details = []
            for area in location.areas:
                # Inclui apenas áreas que atendem ao requisito de nível
                if discovery_level is None or area.discovery_level_required <= discovery_level:
                    details = [
                        {
                            "detail_id": detail.detail_id,
                            "name": detail.name,
                            "description": detail.description,
                            "discovery_level_required": detail.discovery_level_required,
                            "has_clue": detail.has_clue,
                            "clue_id": detail.clue_id
                        } for detail in area.details
                        if discovery_level is None or detail.discovery_level_required <= discovery_level
                    ]
                    
                    areas_with_details.append({
                        "area": {
                            "area_id": area.area_id,
                            "name": area.name,
                            "description": area.description,
                            "initially_visible": area.initially_visible,
                            "connected_areas": self._parse_json_field(area.connected_areas),
                            "discovery_level_required": area.discovery_level_required
                        },
                        "details": details
                    })
            
            return {
                "location": {
                    "location_id": location.location_id,
                    "name": location.name,
                    "description": location.description,
                    "is_locked": location.is_locked,
                    "unlock_condition": location.unlock_condition,
                    "navigation_map": self._parse_json_field(location.navigation_map),
                    "is_starting_location": location.is_starting_location
                },
                "areas": areas_with_details
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar hierarquia da localização {location_id}: {str(e)}")
            raise
    
    def check_location_accessible(self, db: Session, location_id: int, 
                               player_progress: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifica se uma localização está acessível com base nas condições de desbloqueio e progresso do jogador.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            player_progress: Dicionário com o progresso do jogador
            
        Returns:
            Dicionário indicando se o acesso é permitido e o motivo
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            location = self.get_by_id(db, location_id)
            
            if not location:
                return {
                    "accessible": False, 
                    "reason": "Localização não encontrada"
                }
                
            # Se a localização não estiver bloqueada, está sempre acessível
            if not location.is_locked:
                return {
                    "accessible": True,
                    "reason": "Localização desbloqueada"
                }
                
            # Obtém e processa a condição de desbloqueio
            unlock_condition = location.unlock_condition
            
            # Verifica requisitos específicos
            if not unlock_condition:
                return {
                    "accessible": False,
                    "reason": "Localização bloqueada sem condição de desbloqueio"
                }
            
            # Verifica condições baseadas em nível
            if "level_required" in unlock_condition:
                player_level = player_progress.get("specialization_level", 0)
                level_required = unlock_condition.get("level_required", 1)
                
                if player_level < level_required:
                    return {
                        "accessible": False,
                        "reason": f"Nível insuficiente. Necessário: {level_required}, Atual: {player_level}"
                    }
            
            # Verifica requisitos de objeto
            if "required_objects" in unlock_condition:
                required_objects = unlock_condition.get("required_objects", [])
                player_inventory = set(player_progress.get("inventory", []))
                
                missing_objects = [obj for obj in required_objects if obj not in player_inventory]
                
                if missing_objects:
                    return {
                        "accessible": False,
                        "reason": f"Itens necessários ausentes: {missing_objects}"
                    }
            
            # Verifica requisitos de localização prévia
            if "required_locations" in unlock_condition:
                required_locations = unlock_condition.get("required_locations", [])
                visited_locations = set(player_progress.get("discovered_locations", []))
                
                missing_locations = [loc for loc in required_locations if loc not in visited_locations]
                
                if missing_locations:
                    return {
                        "accessible": False,
                        "reason": f"Localizações anteriores necessárias: {missing_locations}"
                    }
            
            # Se passou por todas as verificações, o acesso é permitido
            return {
                "accessible": True,
                "reason": "Requisitos atendidos"
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao verificar acesso à localização {location_id}: {str(e)}")
            raise
    
    def find_path_between_areas(self, db: Session, start_area_id: int, 
                             target_area_id: int) -> List[int]:
        """
        Encontra um caminho entre duas áreas através de suas conexões.
        
        Args:
            db: Sessão do banco de dados
            start_area_id: ID da área de início
            target_area_id: ID da área alvo
            
        Returns:
            Lista de IDs de áreas formando o caminho ou lista vazia se não houver caminho
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Implementa um algoritmo BFS (Busca em Largura) para encontrar o caminho
            if start_area_id == target_area_id:
                return [start_area_id]
                
            # Fila para BFS
            queue = [(start_area_id, [start_area_id])]
            # Conjunto para marcar áreas já visitadas
            visited = {start_area_id}
            
            while queue:
                current_area_id, path = queue.pop(0)
                
                # Obtém as áreas conectadas
                current_area = self.get_area_by_id(db, current_area_id)
                if not current_area or not current_area.connected_areas:
                    continue
                
                connected_ids = self._parse_json_field(current_area.connected_areas)
                
                for connected_id in connected_ids:
                    if connected_id == target_area_id:
                        # Caminho encontrado
                        return path + [connected_id]
                    
                    if connected_id not in visited:
                        visited.add(connected_id)
                        queue.append((connected_id, path + [connected_id]))
            
            # Se saiu do loop, não há caminho
            return []
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar caminho entre áreas {start_area_id} e {target_area_id}: {str(e)}")
            raise
    
    def get_accessible_areas(self, db: Session, location_id: int, 
                           player_discovery_level: int) -> List[LocationArea]:
        """
        Obtém todas as áreas acessíveis em uma localização com base no nível de descoberta do jogador.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            player_discovery_level: Nível atual de descoberta do jogador
            
        Returns:
            Lista de áreas acessíveis
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Obtém áreas que o jogador pode acessar com seu nível atual
            return db.query(LocationArea).filter(
                LocationArea.location_id == location_id,
                LocationArea.discovery_level_required <= player_discovery_level
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar áreas acessíveis da localização {location_id}: {str(e)}")
            raise
    
    def get_unexplored_details(self, db: Session, area_id: int, 
                             player_discovery_level: int) -> List[AreaDetail]:
        """
        Obtém detalhes ainda não exploráveis de uma área baseado no nível atual do jogador.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            player_discovery_level: Nível atual de descoberta do jogador
            
        Returns:
            Lista de detalhes ainda não exploráveis
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Obtém detalhes que o jogador ainda não pode acessar
            return db.query(AreaDetail).filter(
                AreaDetail.area_id == area_id,
                AreaDetail.discovery_level_required > player_discovery_level
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar detalhes inexploráveis da área {area_id}: {str(e)}")
            raise
    
    def unlock_location(self, db: Session, location_id: int) -> bool:
        """
        Desbloqueia uma localização.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            True se desbloqueada com sucesso
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            location = self.get_by_id(db, location_id)
            
            if not location:
                return False
                
            location.is_locked = False
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao desbloquear localização {location_id}: {str(e)}")
            raise
    
    def add_area(self, db: Session, location_id: int, area_data: Dict[str, Any]) -> Optional[LocationArea]:
        """
        Adiciona uma nova área a uma localização.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            area_data: Dados da nova área
            
        Returns:
            Nova área criada ou None se a localização não existir
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Verifica se a localização existe
            if not self.exists(db, location_id):
                self.logger.warning(f"Tentativa de adicionar área a localização inexistente: {location_id}")
                return None
            
            # Processa o campo connected_areas
            connected_areas = area_data.get('connected_areas', [])
            if isinstance(connected_areas, list):
                connected_areas_json = json.dumps(connected_areas)
            else:
                connected_areas_json = json.dumps([])
            
            # Cria a nova área
            area = LocationArea(
                location_id=location_id,
                name=area_data.get('name', 'Nova Área'),
                description=area_data.get('description', ''),
                initially_visible=area_data.get('initially_visible', True),
                connected_areas=connected_areas_json,
                discovery_level_required=area_data.get('discovery_level_required', 0)
            )
            
            db.add(area)
            db.commit()
            db.refresh(area)
            
            self.logger.info(f"Área '{area.name}' adicionada à localização {location_id}")
            return area
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar área à localização {location_id}: {str(e)}")
            raise
    
    def add_detail(self, db: Session, area_id: int, detail_data: Dict[str, Any]) -> Optional[AreaDetail]:
        """
        Adiciona um novo detalhe a uma área.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            detail_data: Dados do novo detalhe
            
        Returns:
            Novo detalhe criado ou None se a área não existir
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Verifica se a área existe
            area = self.get_area_by_id(db, area_id)
            if not area:
                self.logger.warning(f"Tentativa de adicionar detalhe a área inexistente: {area_id}")
                return None
            
            # Cria o novo detalhe
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
            
            self.logger.info(f"Detalhe '{detail.name}' adicionado à área {area_id}")
            return detail
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar detalhe à área {area_id}: {str(e)}")
            raise
    
    def update_area(self, db: Session, area_id: int, area_data: Dict[str, Any]) -> Optional[LocationArea]:
        """
        Atualiza uma área existente.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            area_data: Dados atualizados
            
        Returns:
            Área atualizada ou None se não existir
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            area = self.get_area_by_id(db, area_id)
            if not area:
                self.logger.warning(f"Tentativa de atualizar área inexistente: {area_id}")
                return None
            
            # Atualiza os campos fornecidos
            if 'name' in area_data:
                area.name = area_data['name']
            if 'description' in area_data:
                area.description = area_data['description']
            if 'initially_visible' in area_data:
                area.initially_visible = area_data['initially_visible']
            if 'connected_areas' in area_data:
                connected_areas = area_data['connected_areas']
                if isinstance(connected_areas, list):
                    area.connected_areas = json.dumps(connected_areas)
                else:
                    area.connected_areas = json.dumps([])
            if 'discovery_level_required' in area_data:
                area.discovery_level_required = area_data['discovery_level_required']
            
            db.commit()
            db.refresh(area)
            
            self.logger.info(f"Área {area_id} atualizada com sucesso")
            return area
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar área {area_id}: {str(e)}")
            raise
    
    def connect_areas(self, db: Session, area_id: int, connected_area_id: int) -> bool:
        """
        Estabelece uma conexão bidirecional entre duas áreas.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da primeira área
            connected_area_id: ID da segunda área
            
        Returns:
            True se a conexão foi estabelecida com sucesso
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Busca as duas áreas
            area1 = self.get_area_by_id(db, area_id)
            area2 = self.get_area_by_id(db, connected_area_id)
            
            if not area1 or not area2:
                return False
            
            # Atualiza as conexões da primeira área
            connected_areas1 = self._parse_json_field(area1.connected_areas) or []
            if connected_area_id not in connected_areas1:
                connected_areas1.append(connected_area_id)
                area1.connected_areas = json.dumps(connected_areas1)
            
            # Atualiza as conexões da segunda área
            connected_areas2 = self._parse_json_field(area2.connected_areas) or []
            if area_id not in connected_areas2:
                connected_areas2.append(area_id)
                area2.connected_areas = json.dumps(connected_areas2)
            
            db.commit()
            self.logger.info(f"Áreas {area_id} e {connected_area_id} conectadas com sucesso")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao conectar áreas {area_id} e {connected_area_id}: {str(e)}")
            raise
    
def disconnect_areas(self, db: Session, area_id: int, connected_area_id: int) -> bool:
        """
        Remove a conexão bidirecional entre duas áreas.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da primeira área
            connected_area_id: ID da segunda área
            
        Returns:
            True se a desconexão foi realizada com sucesso
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Busca as duas áreas
            area1 = self.get_area_by_id(db, area_id)
            area2 = self.get_area_by_id(db, connected_area_id)
            
            if not area1 or not area2:
                return False
            
            # Remove a conexão da primeira área
            connected_areas1 = self._parse_json_field(area1.connected_areas) or []
            if connected_area_id in connected_areas1:
                connected_areas1.remove(connected_area_id)
                area1.connected_areas = json.dumps(connected_areas1)
            
            # Remove a conexão da segunda área
            connected_areas2 = self._parse_json_field(area2.connected_areas) or []
            if area_id in connected_areas2:
                connected_areas2.remove(area_id)
                area2.connected_areas = json.dumps(connected_areas2)
            
            db.commit()
            self.logger.info(f"Conexão entre áreas {area_id} e {connected_area_id} removida com sucesso")
            return True
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao desconectar áreas {area_id} e {connected_area_id}: {str(e)}")
            raise
    
def get_location_stats(self, db: Session, location_id: int) -> Dict[str, Any]:
    """
    Obtém estatísticas sobre uma localização, incluindo número de áreas, detalhes e pistas.
    
    Args:
        db: Sessão do banco de dados
        location_id: ID da localização
        
    Returns:
        Dicionário com estatísticas da localização
    
    Raises:
        SQLAlchemyError: Erro ao acessar o banco de dados
    """
    try:
        # Contagem de áreas
        area_count = db.query(func.count(LocationArea.area_id)).filter(
            LocationArea.location_id == location_id
        ).scalar() or 0
        
        # Contagem de áreas visíveis inicialmente
        visible_area_count = db.query(func.count(LocationArea.area_id)).filter(
            LocationArea.location_id == location_id,
            LocationArea.initially_visible == True
        ).scalar() or 0
        
        # Busca todas as áreas para processar detalhes
        areas = self.get_areas_by_location(db, location_id)
        
        area_ids = [area.area_id for area in areas]
        
        # Contagem de detalhes
        detail_count = 0
        clue_count = 0
        
        if area_ids:
            detail_count = db.query(func.count(AreaDetail.detail_id)).filter(
                AreaDetail.area_id.in_(area_ids)
            ).scalar() or 0
            
            clue_count = db.query(func.count(AreaDetail.detail_id)).filter(
                AreaDetail.area_id.in_(area_ids),
                AreaDetail.has_clue == True
            ).scalar() or 0
        
        # Obtém a localização para informações básicas
        location = self.get_by_id(db, location_id)
        
        return {
            "location_id": location_id,
            "name": location.name if location else "Localização desconhecida",
            "is_locked": location.is_locked if location else True,
            "area_count": area_count,
            "visible_area_count": visible_area_count,
            "detail_count": detail_count,
            "clue_count": clue_count
        }
    except SQLAlchemyError as e:
        self.logger.error(f"Erro ao obter estatísticas da localização {location_id}: {str(e)}")
        raise

def get_areas_by_discovery_level(self, db: Session, location_id: int) -> Dict[int, List[LocationArea]]:
    """
    Agrupa as áreas de uma localização por nível de descoberta necessário.
    
    Args:
        db: Sessão do banco de dados
        location_id: ID da localização
        
    Returns:
        Dicionário com áreas agrupadas por nível de descoberta
    
    Raises:
        SQLAlchemyError: Erro ao acessar o banco de dados
    """
    try:
        areas = self.get_areas_by_location(db, location_id)
        
        # Agrupa áreas por nível de descoberta
        result = {}
        for area in areas:
            level = area.discovery_level_required
            if level not in result:
                result[level] = []
            result[level].append(area)
        
        return result
    except SQLAlchemyError as e:
        self.logger.error(f"Erro ao agrupar áreas por nível de descoberta para localização {location_id}: {str(e)}")
        raise

def get_location_progress(self, db: Session, location_id: int, 
                        player_discovery_level: int) -> Dict[str, Any]:
    """
    Calcula o progresso de exploração de uma localização para o nível atual do jogador.
    
    Args:
        db: Sessão do banco de dados
        location_id: ID da localização
        player_discovery_level: Nível de descoberta do jogador
        
    Returns:
        Dicionário com informações de progresso
    
    Raises:
        SQLAlchemyError: Erro ao acessar o banco de dados
    """
    try:
        # Obtém todas as áreas da localização
        all_areas = self.get_areas_by_location(db, location_id)
        total_areas = len(all_areas)
        
        # Obtém áreas acessíveis com o nível atual
        accessible_areas = [area for area in all_areas 
                            if area.discovery_level_required <= player_discovery_level]
        accessible_area_count = len(accessible_areas)
        
        # Calcula o percentual de completude
        completion_percentage = 0
        if total_areas > 0:
            completion_percentage = (accessible_area_count / total_areas) * 100
        
        # Obtém próximas áreas a serem desbloqueadas
        next_level_areas = [area for area in all_areas 
                            if area.discovery_level_required == player_discovery_level + 1]
        
        return {
            "location_id": location_id,
            "player_level": player_discovery_level,
            "total_areas": total_areas,
            "accessible_areas": accessible_area_count,
            "completion_percentage": completion_percentage,
            "next_level_areas_count": len(next_level_areas),
            "max_discovery_level": max([area.discovery_level_required for area in all_areas]) if all_areas else 0
        }
    except SQLAlchemyError as e:
        self.logger.error(f"Erro ao calcular progresso da localização {location_id}: {str(e)}")
        raise

# Métodos auxiliares privados

def _parse_json_field(self, field_value: Any) -> Any:
    """
    Analisa um campo que pode estar armazenado como JSON.
    
    Args:
        field_value: Valor do campo que pode ser string JSON ou outra coisa
        
    Returns:
        Valor decodificado ou o valor original
    """
    if not field_value:
        return None
        
    if isinstance(field_value, str):
        try:
            return json.loads(field_value)
        except json.JSONDecodeError:
            return field_value
    
    return field_value

def _get_connected_location_ids(self, location: Location) -> List[int]:
    """
    Extrai os IDs de localizações conectadas do campo navigation_map.
    
    Args:
        location: Objeto Location
        
    Returns:
        Lista de IDs de localizações conectadas
    """
    nav_map = self._parse_json_field(location.navigation_map)
    
    if not nav_map:
        return []
        
    connected_locations = nav_map.get('connected_locations', [])
    
    if isinstance(connected_locations, list):
        return connected_locations
    
    return []