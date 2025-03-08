# src/repositories/qrcode_repository.py
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json
import logging
import uuid

from src.models.db_models import QRCode
from src.repositories.base_repository import BaseRepository

class QRCodeRepository(BaseRepository[QRCode]):
    """
    Repositório para operações de banco de dados relacionadas a QR codes.
    Responsável por gerenciar a persistência e recuperação de QR codes.
    """
    
    def __init__(self):
        super().__init__(QRCode)
        self.logger = logging.getLogger(__name__)
    
    def get_by_uuid(self, db: Session, uuid: str) -> Optional[QRCode]:
        """
        Busca um QR code pelo UUID.
        
        Args:
            db: Sessão do banco de dados
            uuid: UUID do QR code
            
        Returns:
            QR code encontrado ou None se não existir
        """
        try:
            return db.query(QRCode).filter(QRCode.uuid == uuid).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar QR code por UUID {uuid}: {str(e)}")
            raise
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[QRCode]:
        """
        Busca todos os QR codes associados a uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de QR codes da história
        """
        try:
            # Assumindo que QRCode tenha um relacionamento com Story ou um campo story_id
            return db.query(QRCode).filter(QRCode.story_id == story_id).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar QR codes da história {story_id}: {str(e)}")
            raise
    
    def get_by_target(self, db: Session, target_type: str, target_id: int) -> List[QRCode]:
        """
        Busca QR codes por tipo e ID de alvo.
        
        Args:
            db: Sessão do banco de dados
            target_type: Tipo do alvo (location, area, character, object, clue)
            target_id: ID do alvo
            
        Returns:
            Lista de QR codes para o alvo
        """
        try:
            return db.query(QRCode).filter(
                QRCode.target_type == target_type,
                QRCode.target_id == target_id
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar QR codes por alvo {target_type}:{target_id}: {str(e)}")
            raise
    
    def create_qrcode(self, db: Session, qrcode_data: Dict[str, Any]) -> Optional[QRCode]:
        """
        Cria um novo QR code no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            qrcode_data: Dados do QR code
            
        Returns:
            QR code criado ou None em caso de erro
        """
        try:
            # Gera UUID se não fornecido
            if 'uuid' not in qrcode_data or not qrcode_data['uuid']:
                qrcode_data['uuid'] = str(uuid.uuid4())
            
            # Verificar se já existe um QR code com este UUID
            existing = self.get_by_uuid(db, qrcode_data['uuid'])
            if existing:
                return existing
            
            # Serializa campos JSON
            parameters = qrcode_data.get("parameters", {})
            access_requirements = qrcode_data.get("access_requirements", {})
            location_requirement = qrcode_data.get("location_requirement", {})
            
            # Cria o QR code
            qrcode = QRCode(
                uuid=qrcode_data['uuid'],
                target_type=qrcode_data.get("target_type", ""),
                target_id=qrcode_data.get("target_id"),
                action=qrcode_data.get("action", ""),
                parameters=self._ensure_json(parameters),
                access_requirements=self._ensure_json(access_requirements),
                location_requirement=self._ensure_json(location_requirement),
                story_id=qrcode_data.get("story_id")
            )
            
            db.add(qrcode)
            db.commit()
            db.refresh(qrcode)
            
            return qrcode
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar QR code: {str(e)}")
            raise
    
    def update_qrcode(self, db: Session, qr_id: int, qrcode_data: Dict[str, Any]) -> Optional[QRCode]:
        """
        Atualiza um QR code existente.
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            qrcode_data: Dados atualizados
            
        Returns:
            QR code atualizado ou None em caso de erro
        """
        try:
            qrcode = self.get_by_id(db, qr_id)
            if not qrcode:
                return None
            
            # Atualiza campos existentes
            if "target_type" in qrcode_data:
                qrcode.target_type = qrcode_data["target_type"]
            if "target_id" in qrcode_data:
                qrcode.target_id = qrcode_data["target_id"]
            if "action" in qrcode_data:
                qrcode.action = qrcode_data["action"]
            
            # Atualiza campos JSON
            if "parameters" in qrcode_data:
                qrcode.parameters = self._ensure_json(qrcode_data["parameters"])
            if "access_requirements" in qrcode_data:
                qrcode.access_requirements = self._ensure_json(qrcode_data["access_requirements"])
            if "location_requirement" in qrcode_data:
                qrcode.location_requirement = self._ensure_json(qrcode_data["location_requirement"])
            if "story_id" in qrcode_data:
                qrcode.story_id = qrcode_data["story_id"]
            
            db.commit()
            db.refresh(qrcode)
            
            return qrcode
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar QR code {qr_id}: {str(e)}")
            raise
    
    def delete_qrcode(self, db: Session, qr_id: int) -> bool:
        """
        Remove um QR code do banco de dados.
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            
        Returns:
            True se removido com sucesso
        """
        try:
            qrcode = self.get_by_id(db, qr_id)
            if not qrcode:
                return False
            
            db.delete(qrcode)
            db.commit()
            
            return True
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao excluir QR code {qr_id}: {str(e)}")
            raise
    
    def bulk_create_qrcodes(self, db: Session, qrcodes_data: List[Dict[str, Any]]) -> List[QRCode]:
        """
        Cria vários QR codes de uma vez.
        
        Args:
            db: Sessão do banco de dados
            qrcodes_data: Lista de dados de QR codes
            
        Returns:
            Lista de QR codes criados
        """
        try:
            qrcodes = []
            for qrcode_data in qrcodes_data:
                qrcode = self.create_qrcode(db, qrcode_data)
                if qrcode:
                    qrcodes.append(qrcode)
            
            return qrcodes
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar QR codes em lote: {str(e)}")
            raise
    
    def _ensure_json(self, value: Union[Dict, List, str, None]) -> str:
        """
        Garante que o valor seja uma string JSON.
        
        Args:
            value: Valor que pode ser um dicionário, uma lista, uma string ou None
            
        Returns:
            String JSON
        """
        if value is None:
            return "{}"
        
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        
        if isinstance(value, str):
            try:
                # Verifica se é uma string JSON válida
                json.loads(value)
                return value
            except json.JSONDecodeError:
                # Se não for JSON válido, retorna como string em formato JSON
                return json.dumps(value)
        
        # Para outros tipos, converte para string e depois para JSON
        return json.dumps(str(value))
    
    def _parse_json(self, value: Optional[str]) -> Union[Dict, List, None]:
        """
        Converte uma string JSON para um objeto Python.
        
        Args:
            value: String JSON ou None
            
        Returns:
            Objeto Python (dicionário ou lista) ou None
        """
        if not value:
            return {}
        
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        
        return value