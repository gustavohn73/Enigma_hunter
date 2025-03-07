from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.models.db_models import QRCode, Location, Area, GameObject, Clue
from src.repositories.base_repository import BaseRepository

class QRCodeRepository(BaseRepository[QRCode]):
    """
    Repositório para operações de banco de dados relacionadas a QR codes.
    Gerencia QR codes, suas localizações e relacionamentos com objetos, pistas e áreas.
    """
    
    def __init__(self):
        super().__init__(QRCode)
    
    def get_by_id(self, db: Session, qr_id: int) -> Optional[QRCode]:
        """
        Busca um QR code pelo ID.
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            
        Returns:
            QR code encontrado ou None
        """
        return db.query(QRCode).filter(QRCode.qr_id == qr_id).first()
    
    def get_by_uuid(self, db: Session, uuid: str) -> Optional[QRCode]:
        """
        Busca um QR code pelo UUID.
        
        Args:
            db: Sessão do banco de dados
            uuid: UUID do QR code
            
        Returns:
            QR code encontrado ou None
        """
        return db.query(QRCode).filter(QRCode.uuid == uuid).first()
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[QRCode]:
        """
        Busca todos os QR codes de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de QR codes da história
        """
        return db.query(QRCode).filter(QRCode.story_id == story_id).all()
    
    def get_by_location(self, db: Session, location_id: int) -> List[QRCode]:
        """
        Busca QR codes em uma localização específica.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Lista de QR codes na localização
        """
        return db.query(QRCode).filter(QRCode.location_id == location_id).all()
    
    def get_by_area(self, db: Session, area_id: int) -> List[QRCode]:
        """
        Busca QR codes em uma área específica.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de QR codes na área
        """
        return db.query(QRCode).filter(QRCode.area_id == area_id).all()
    
    def get_by_type(self, db: Session, story_id: int, qr_type: str) -> List[QRCode]:
        """
        Busca QR codes por tipo específico (objeto, pista, área, etc).
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            qr_type: Tipo de QR code
            
        Returns:
            Lista de QR codes do tipo especificado
        """
        return db.query(QRCode).filter(
            QRCode.story_id == story_id,
            QRCode.type == qr_type
        ).all()
    
    def get_linked_content(self, db: Session, qr_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém o conteúdo vinculado a um QR code (objeto, pista, etc).
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            
        Returns:
            Dicionário com o conteúdo vinculado
        """
        qr_code = self.get_by_id(db, qr_id)
        if not qr_code:
            return None
            
        content = {"type": qr_code.type}
        
        if qr_code.type == "object":
            obj = db.query(GameObject).filter(GameObject.object_id == qr_code.linked_id).first()
            if obj:
                content["object"] = obj
                
        elif qr_code.type == "clue":
            clue = db.query(Clue).filter(Clue.clue_id == qr_code.linked_id).first()
            if clue:
                content["clue"] = clue
                
        return content
    
    def create_qrcode(self, db: Session, qr_data: Dict[str, Any]) -> QRCode:
        """
        Cria um novo QR code no jogo.
        
        Args:
            db: Sessão do banco de dados
            qr_data: Dados do novo QR code
            
        Returns:
            QR code criado
        """
        qr_code = QRCode(
            story_id=qr_data.get("story_id"),
            uuid=qr_data.get("uuid"),
            type=qr_data.get("type"),
            linked_id=qr_data.get("linked_id"),
            location_id=qr_data.get("location_id"),
            area_id=qr_data.get("area_id"),
            description=qr_data.get("description"),
            scan_requirements=qr_data.get("scan_requirements", {}),
            scan_effects=qr_data.get("scan_effects", {})
        )
        
        db.add(qr_code)
        db.commit()
        db.refresh(qr_code)
        
        return qr_code
    
    def check_scan_requirements(self, db: Session, qr_id: int, player_data: Dict[str, Any]) -> bool:
        """
        Verifica se um jogador atende aos requisitos para escanear um QR code.
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            player_data: Dados do jogador para verificação
            
        Returns:
            True se os requisitos foram atendidos, False caso contrário
        """
        qr_code = self.get_by_id(db, qr_id)
        if not qr_code or not qr_code.scan_requirements:
            return True
            
        requirements = qr_code.scan_requirements
        
        # Verifica nível de especialização necessário
        if "specialization_required" in requirements:
            spec_req = requirements["specialization_required"]
            player_spec = player_data.get("specializations", {})
            
            if player_spec.get(spec_req["category"], 0) < spec_req["level"]:
                return False
        
        # Verifica objetos necessários no inventário
        if "required_objects" in requirements:
            player_inventory = player_data.get("inventory", set())
            if not all(obj_id in player_inventory for obj_id in requirements["required_objects"]):
                return False
        
        # Verifica pistas necessárias
        if "required_clues" in requirements:
            discovered_clues = player_data.get("discovered_clues", set())
            if not all(clue_id in discovered_clues for clue_id in requirements["required_clues"]):
                return False
        
        return True
    
    def get_location_data(self, db: Session, qr_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém dados da localização de um QR code.
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            
        Returns:
            Dicionário com dados da localização
        """
        qr_code = self.get_by_id(db, qr_id)
        if not qr_code:
            return None
            
        location_data = {}
        
        if qr_code.location_id:
            location = db.query(Location).filter(Location.location_id == qr_code.location_id).first()
            if location:
                location_data["location"] = location
                
        if qr_code.area_id:
            area = db.query(Area).filter(Area.area_id == qr_code.area_id).first()
            if area:
                location_data["area"] = area
                
        return location_data