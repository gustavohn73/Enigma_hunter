# src/managers/qrcode_manager.py
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging
import json
import uuid

from src.repositories.qrcode_repository import QRCodeRepository
from src.repositories.player_progress_repository import PlayerProgressRepository

class QRCodeManager:
    """
    Gerenciador para operações de negócio relacionadas a QR codes.
    Responsável pela lógica de processamento de QR codes e controle de acesso.
    """
    
    def __init__(
        self,
        qrcode_repository: QRCodeRepository,
        player_progress_repository: PlayerProgressRepository
    ):
        """
        Inicializa o gerenciador de QR codes.
        
        Args:
            qrcode_repository: Repositório de QR codes
            player_progress_repository: Repositório de progresso do jogador
        """
        self.qrcode_repository = qrcode_repository
        self.player_progress_repository = player_progress_repository
        self.logger = logging.getLogger(__name__)
    
    def check_scan_requirements(self, db: Session, qr_uuid: str, session_id: str) -> Dict[str, Any]:
        """
        Verifica se um jogador atende aos requisitos para escanear um QR code.
        
        Args:
            db: Sessão do banco de dados
            qr_uuid: UUID do QR code
            session_id: ID da sessão do jogador
            
        Returns:
            Resultado da verificação
        """
        try:
            # Obter o QR code
            qr_code = self.qrcode_repository.get_by_uuid(db, qr_uuid)
            if not qr_code:
                return {"access_granted": False, "reason": "QR Code não encontrado"}
            
            # Obter o progresso do jogador
            player_progress = self.player_progress_repository.get_by_session_id(db, session_id)
            if not player_progress:
                return {"access_granted": False, "reason": "Sessão não encontrada"}
            
            # Extrair requisitos de acesso
            access_requirements = self._parse_json(qr_code.access_requirements)
            
            # Se não há requisitos, o acesso é permitido
            if not access_requirements:
                return {"access_granted": True}
            
            # Verificar requisitos de localização
            if 'current_location_id' in access_requirements:
                required_location = access_requirements['current_location_id']
                current_location = player_progress.current_location_id
                
                if current_location != required_location:
                    return {
                        "access_granted": False, 
                        "reason": "Você precisa estar em outra localização para escanear este QR code"
                    }
            
            # Verificar requisitos de inventário
            if 'required_objects' in access_requirements:
                required_objects = access_requirements['required_objects']
                inventory = self._ensure_list(player_progress.inventory)
                
                missing_objects = [obj for obj in required_objects if obj not in inventory]
                if missing_objects:
                    return {
                        "access_granted": False,
                        "reason": "Você precisa de certos objetos para escanear este QR code"
                    }
            
            # Verificar requisitos de especialização
            if 'specialization_required' in access_requirements:
                spec_req = access_requirements['specialization_required']
                specializations = player_progress.specialization_levels
                
                for category, required_level in spec_req.items():
                    current_level = specializations.get(category, 0)
                    if current_level < required_level:
                        return {
                            "access_granted": False,
                            "reason": "Você precisa de mais experiência para escanear este QR code"
                        }
            
            # Todos os requisitos foram atendidos
            return {"access_granted": True}
        except Exception as e:
            self.logger.error(f"Erro ao verificar requisitos de QR code: {str(e)}")
            return {"access_granted": False, "reason": f"Erro ao verificar requisitos: {str(e)}"}
    
    def register_scan(self, db: Session, qr_uuid: str, session_id: str, scan_result: Dict[str, Any]) -> bool:
        """
        Registra um escaneamento de QR code pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            qr_uuid: UUID do QR code
            session_id: ID da sessão do jogador
            scan_result: Resultado do escaneamento
            
        Returns:
            True se registrado com sucesso
        """
        try:
            # Obter o progresso do jogador
            progress = self.player_progress_repository.get_by_session_id(db, session_id)
            if not progress:
                return False
            
            # Adicionar o QR code à lista de escaneados
            scanned_qr_codes = self._ensure_list(progress.scanned_qr_codes)
            
            if qr_uuid not in scanned_qr_codes:
                scanned_qr_codes.append(qr_uuid)
                progress.scanned_qr_codes = scanned_qr_codes
                progress.last_activity = self._get_current_datetime()
                
                # Registrar a ação no histórico
                self._add_scan_to_history(db, progress, qr_uuid, scan_result)
                
                db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao registrar escaneamento de QR code: {str(e)}")
            return False
    
    def generate_qrcode(self, db: Session, target_type: str, target_id: int, 
                      action: str, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Gera um novo QR code para um alvo específico.
        
        Args:
            db: Sessão do banco de dados
            target_type: Tipo do alvo (location, area, character, object, clue)
            target_id: ID do alvo
            action: Ação a ser executada (enter, explore, talk, collect, examine)
            requirements: Requisitos para acessar o QR code (opcional)
            
        Returns:
            Dados do QR code gerado
        """
        try:
            # Preparar dados do QR code
            qrcode_data = {
                "uuid": str(uuid.uuid4()),
                "target_type": target_type,
                "target_id": target_id,
                "action": action,
                "access_requirements": requirements or {}
            }
            
            # Criar o QR code
            qrcode = self.qrcode_repository.create_qrcode(db, qrcode_data)
            
            if not qrcode:
                return {"success": False, "message": "Erro ao criar QR code"}
            
            return {
                "success": True,
                "qrcode": {
                    "uuid": qrcode.uuid,
                    "target_type": qrcode.target_type,
                    "target_id": qrcode.target_id,
                    "action": qrcode.action
                }
            }
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao gerar QR code: {str(e)}")
            return {"success": False, "message": f"Erro ao gerar QR code: {str(e)}"}
    
    def get_qrcode_info(self, db: Session, qr_uuid: str) -> Dict[str, Any]:
        """
        Obtém informações detalhadas sobre um QR code.
        
        Args:
            db: Sessão do banco de dados
            qr_uuid: UUID do QR code
            
        Returns:
            Informações detalhadas do QR code
        """
        try:
            qrcode = self.qrcode_repository.get_by_uuid(db, qr_uuid)
            
            if not qrcode:
                return {"success": False, "message": "QR Code não encontrado"}
            
            return {
                "success": True,
                "qrcode": {
                    "uuid": qrcode.uuid,
                    "target_type": qrcode.target_type,
                    "target_id": qrcode.target_id,
                    "action": qrcode.action,
                    "parameters": self._parse_json(qrcode.parameters),
                    "access_requirements": self._parse_json(qrcode.access_requirements),
                    "location_requirement": self._parse_json(qrcode.location_requirement)
                }
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter informações do QR code: {str(e)}")
            return {"success": False, "message": f"Erro ao obter informações: {str(e)}"}
    
    # Métodos auxiliares
    
    def _parse_json(self, value) -> Dict[str, Any]:
        """
        Converte um valor para um dicionário Python.
        
        Args:
            value: Valor que pode ser um dicionário ou uma string JSON
            
        Returns:
            Dicionário Python
        """
        if not value:
            return {}
        
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            try:
                result = json.loads(value)
                if isinstance(result, dict):
                    return result
                return {}
            except json.JSONDecodeError:
                return {}
        
        return {}
    
    def _ensure_list(self, value) -> list:
        """
        Garante que o valor seja uma lista Python.
        
        Args:
            value: Valor que pode ser uma lista ou uma string JSON
            
        Returns:
            Lista Python
        """
        if value is None:
            return []
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, str):
            try:
                result = json.loads(value)
                if isinstance(result, list):
                    return result
                return []
            except json.JSONDecodeError:
                return []
        
        return []
    
    def _get_current_datetime(self):
        """
        Obtém a data e hora atual.
        
        Returns:
            Data e hora atual
        """
        from datetime import datetime
        return datetime.now()
    
    def _add_scan_to_history(self, db: Session, progress, qr_uuid: str, scan_result: Dict[str, Any]) -> None:
        """
        Adiciona um registro de escaneamento ao histórico de ações do jogador.
        
        Args:
            db: Sessão do banco de dados
            progress: Objeto PlayerProgress
            qr_uuid: UUID do QR code
            scan_result: Resultado do escaneamento
        """
        # Obter histórico atual
        action_history = self._ensure_list(progress.action_history)
        
        # Criar registro de ação
        action = {
            "timestamp": self._get_current_datetime().isoformat(),
            "action_type": "scan_qr",
            "details": {
                "qr_uuid": qr_uuid,
                "access_granted": scan_result.get("access_granted", False),
                "reason": scan_result.get("reason", "")
            }
        }
        
        # Adicionar nova ação
        action_history.append(action)
        
        # Atualizar histórico no progresso
        progress.action_history = action_history