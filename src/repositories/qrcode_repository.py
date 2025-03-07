# src/repositories/qrcode_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import logging

from src.models.db_models import (
    QRCode, 
    Location, 
    LocationArea, 
    GameObject, 
    Clue,
    PlayerSession,
    PlayerInventory,
    PlayerProgress,
    PlayerDiscoveredClues,
    PlayerSpecialization
)
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class QRCodeRepository(BaseRepository[QRCode]):
    """
    Repositório para operações de banco de dados relacionadas a QR codes.
    Gerencia QR codes, suas localizações e relacionamentos com objetos, pistas e áreas.
    """
    
    def __init__(self):
        super().__init__(QRCode)
        self.logger = logger
    
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
    
    def get_active_session(self, db: Session, session_id: str) -> Optional[PlayerSession]:
        """
        Obtém uma sessão ativa pelo ID.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            
        Returns:
            Sessão ativa ou None
        """
        return db.query(PlayerSession).filter(
            PlayerSession.session_id == session_id,
            PlayerSession.game_status == 'active'
        ).first()
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[QRCode]:
        """
        Busca todos os QR codes de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de QR codes da história
        """
        try:
            # Assumindo que a tabela QRCode tem uma coluna story_id
            return db.query(QRCode).filter(QRCode.story_id == story_id).all()
        except Exception as e:
            self.logger.error(f"Erro ao buscar QR codes por história: {str(e)}")
            return []
    
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
        except Exception as e:
            self.logger.error(f"Erro ao buscar QR codes por alvo: {str(e)}")
            return []
    
    def get_by_location(self, db: Session, location_id: int) -> List[QRCode]:
        """
        Busca QR codes em uma localização específica.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            
        Returns:
            Lista de QR codes na localização
        """
        try:
            # Busca QR codes com target_type 'location' e target_id correspondente
            return self.get_by_target(db, 'location', location_id)
        except Exception as e:
            self.logger.error(f"Erro ao buscar QR codes por localização: {str(e)}")
            return []
    
    def get_by_area(self, db: Session, area_id: int) -> List[QRCode]:
        """
        Busca QR codes em uma área específica.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de QR codes na área
        """
        try:
            # Busca QR codes com target_type 'area' e target_id correspondente
            return self.get_by_target(db, 'area', area_id)
        except Exception as e:
            self.logger.error(f"Erro ao buscar QR codes por área: {str(e)}")
            return []
    
    def get_linked_content(self, db: Session, qr_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém o conteúdo vinculado a um QR code (objeto, pista, etc).
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            
        Returns:
            Dicionário com o conteúdo vinculado
        """
        try:
            qr_code = self.get_by_id(db, qr_id)
            if not qr_code:
                return None
                
            content = {"type": qr_code.target_type, "action": qr_code.action}
            
            if qr_code.target_type == "object":
                obj = db.query(GameObject).filter(GameObject.object_id == qr_code.target_id).first()
                if obj:
                    content["content"] = obj
                    
            elif qr_code.target_type == "clue":
                clue = db.query(Clue).filter(Clue.clue_id == qr_code.target_id).first()
                if clue:
                    content["content"] = clue
                    
            elif qr_code.target_type == "location":
                location = db.query(Location).filter(Location.location_id == qr_code.target_id).first()
                if location:
                    content["content"] = location
                    
            elif qr_code.target_type == "area":
                area = db.query(LocationArea).filter(LocationArea.area_id == qr_code.target_id).first()
                if area:
                    content["content"] = area
                    
            return content
        except Exception as e:
            self.logger.error(f"Erro ao obter conteúdo vinculado: {str(e)}")
            return None
    
    def create_qrcode(self, db: Session, qr_data: Dict[str, Any]) -> Optional[QRCode]:
        """
        Cria um novo QR code no jogo.
        
        Args:
            db: Sessão do banco de dados
            qr_data: Dados do novo QR code
            
        Returns:
            QR code criado
        """
        try:
            # Verificar se já existe um QR code com este UUID
            existing = None
            if 'uuid' in qr_data:
                existing = self.get_by_uuid(db, qr_data['uuid'])
            
            if existing:
                return existing
                
            qr_code = QRCode(
                uuid=qr_data.get("uuid"),
                target_type=qr_data.get("target_type"),
                target_id=qr_data.get("target_id"),
                action=qr_data.get("action"),
                parameters=json.dumps(qr_data.get("parameters", {})) if isinstance(qr_data.get("parameters"), dict) else qr_data.get("parameters"),
                access_requirements=json.dumps(qr_data.get("access_requirements", {})) if isinstance(qr_data.get("access_requirements"), dict) else qr_data.get("access_requirements"),
                location_requirement=json.dumps(qr_data.get("location_requirement", {})) if isinstance(qr_data.get("location_requirement"), dict) else qr_data.get("location_requirement")
            )
            
            db.add(qr_code)
            db.commit()
            db.refresh(qr_code)
            
            return qr_code
        except Exception as e:
            self.logger.error(f"Erro ao criar QR code: {str(e)}")
            db.rollback()
            return None
    
    def update_qrcode(self, db: Session, qr_id: int, qr_data: Dict[str, Any]) -> Optional[QRCode]:
        """
        Atualiza um QR code existente.
        
        Args:
            db: Sessão do banco de dados
            qr_id: ID do QR code
            qr_data: Dados atualizados
            
        Returns:
            QR code atualizado ou None
        """
        try:
            qr_code = self.get_by_id(db, qr_id)
            if not qr_code:
                return None
                
            # Atualiza os campos especificados
            for key, value in qr_data.items():
                if hasattr(qr_code, key):
                    # Se for um dicionário, converte para JSON
                    if key in ['parameters', 'access_requirements', 'location_requirement'] and isinstance(value, dict):
                        value = json.dumps(value)
                    setattr(qr_code, key, value)
            
            db.commit()
            db.refresh(qr_code)
            
            return qr_code
        except Exception as e:
            self.logger.error(f"Erro ao atualizar QR code: {str(e)}")
            db.rollback()
            return None
    
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
            qr_code = self.get_by_uuid(db, qr_uuid)
            if not qr_code:
                return {"access_granted": False, "reason": "QR Code não encontrado"}
                
            # Obtém a sessão do jogador
            session = self.get_active_session(db, session_id)
            if not session:
                return {"access_granted": False, "reason": "Sessão não encontrada ou inativa"}
            
            # Obtém os requisitos de acesso
            access_requirements = {}
            if qr_code.access_requirements:
                if isinstance(qr_code.access_requirements, str):
                    try:
                        access_requirements = json.loads(qr_code.access_requirements)
                    except json.JSONDecodeError:
                        pass
                elif isinstance(qr_code.access_requirements, dict):
                    access_requirements = qr_code.access_requirements
            
            # Se não há requisitos, o acesso é permitido
            if not access_requirements:
                return {"access_granted": True}
            
            # Verificação de requisitos de localização
            if 'current_location_id' in access_requirements:
                player_location = self._get_player_location(db, session_id)
                if player_location != access_requirements['current_location_id']:
                    return {
                        "access_granted": False, 
                        "reason": "Você precisa estar em outra localização para escanear este QR code"
                    }
            
            # Verificação de requisitos de especialização
            if 'specialization_required' in access_requirements:
                spec_req = access_requirements['specialization_required']
                if not self._check_specialization_requirement(db, session_id, spec_req):
                    return {
                        "access_granted": False,
                        "reason": "Você precisa ter mais experiência para escanear este QR code"
                    }
            
            # Verificação de requisitos de inventário
            if 'required_objects' in access_requirements:
                if not self._check_inventory_requirement(db, session_id, access_requirements['required_objects']):
                    return {
                        "access_granted": False,
                        "reason": "Você precisa de certos objetos para escanear este QR code"
                    }
            
            # Todos os requisitos foram atendidos
            return {"access_granted": True}
        except Exception as e:
            self.logger.error(f"Erro ao verificar requisitos de QR code: {str(e)}")
            return {"access_granted": False, "reason": "Erro interno ao verificar requisitos"}
    
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
            # Obtém o QR code
            qr_code = self.get_by_uuid(db, qr_uuid)
            if not qr_code:
                return False
                
            # Obtém a sessão do jogador
            session = self.get_active_session(db, session_id)
            if not session:
                return False
                
            # Cria um registro de escaneamento (adaptar conforme seu modelo de dados)
            # Aqui você precisaria criar a instância do modelo QRCodeScan e adicioná-la ao banco
            # Exemplo:
            # scan = QRCodeScan(
            #     session_id=session_id,
            #     qr_uuid=qr_uuid,
            #     scan_time=datetime.utcnow(),
            #     access_granted=scan_result.get("access_granted", False),
            #     denial_reason=scan_result.get("reason"),
            #     returned_content=json.dumps(scan_result.get("content", {}))
            # )
            # db.add(scan)
            # db.commit()
            
            # Como alternativa, pode-se registrar no progresso do jogador
            progress = db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if progress:
                # Adiciona o UUID do QR code à lista de QR codes escaneados
                scanned_qr_codes = progress.scanned_qr_codes
                if isinstance(scanned_qr_codes, str):
                    try:
                        scanned_list = json.loads(scanned_qr_codes)
                        if qr_uuid not in scanned_list:
                            scanned_list.append(qr_uuid)
                        progress.scanned_qr_codes = json.dumps(scanned_list)
                    except json.JSONDecodeError:
                        progress.scanned_qr_codes = json.dumps([qr_uuid])
                elif isinstance(scanned_qr_codes, list):
                    if qr_uuid not in scanned_qr_codes:
                        scanned_qr_codes.append(qr_uuid)
                    progress.scanned_qr_codes = scanned_qr_codes
                else:
                    progress.scanned_qr_codes = [qr_uuid]
                
                db.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao registrar escaneamento de QR code: {str(e)}")
            db.rollback()
            return False
    
    def process_qr_action(self, db: Session, qr_uuid: str, session_id: str) -> Dict[str, Any]:
        """
        Processa a ação de um QR code escaneado por um jogador.
        
        Args:
            db: Sessão do banco de dados
            qr_uuid: UUID do QR code
            session_id: ID da sessão do jogador
            
        Returns:
            Resultado do processamento
        """
        try:
            # Primeiro verifica se o jogador pode escanear este QR code
            check_result = self.check_scan_requirements(db, qr_uuid, session_id)
            if not check_result.get("access_granted", False):
                return check_result
                
            # Obtém o QR code
            qr_code = self.get_by_uuid(db, qr_uuid)
            if not qr_code:
                return {"success": False, "message": "QR Code não encontrado"}
                
            # Registra o escaneamento
            self.register_scan(db, qr_uuid, session_id, check_result)
            
            # Processa a ação específica do QR code
            action = qr_code.action
            target_type = qr_code.target_type
            target_id = qr_code.target_id
            parameters = {}
            
            if qr_code.parameters:
                if isinstance(qr_code.parameters, str):
                    try:
                        parameters = json.loads(qr_code.parameters)
                    except json.JSONDecodeError:
                        pass
                elif isinstance(qr_code.parameters, dict):
                    parameters = qr_code.parameters
            
            result = {"success": True, "message": "QR Code processado com sucesso"}
            
            # Ação: Entrar em uma localização
            if action == "enter" and target_type == "location":
                self._handle_enter_location(db, session_id, target_id)
                result["action_type"] = "enter_location"
                result["location_id"] = target_id
            
            # Ação: Explorar uma área
            elif action == "explore" and target_type == "area":
                self._handle_explore_area(db, session_id, target_id)
                result["action_type"] = "explore_area"
                result["area_id"] = target_id
            
            # Ação: Iniciar diálogo com personagem
            elif action == "talk" and target_type == "character":
                # Neste caso apenas indicamos que um diálogo deve ser iniciado,
                # a lógica completa do diálogo seria tratada por outro componente
                result["action_type"] = "talk_character"
                result["character_id"] = target_id
            
            # Ação: Coletar um objeto
            elif action == "collect" and target_type == "object":
                self._handle_collect_object(db, session_id, target_id)
                result["action_type"] = "collect_object"
                result["object_id"] = target_id
            
            # Ação: Examinar objeto ou detalhe
            elif action == "examine":
                if target_type == "object":
                    self._handle_examine_object(db, session_id, target_id)
                    result["action_type"] = "examine_object"
                    result["object_id"] = target_id
                elif target_type == "area":
                    self._handle_examine_area(db, session_id, target_id)
                    result["action_type"] = "examine_area"
                    result["area_id"] = target_id
                elif target_type == "clue":
                    self._handle_discover_clue(db, session_id, target_id)
                    result["action_type"] = "discover_clue"
                    result["clue_id"] = target_id
            
            # Adiciona os parâmetros ao resultado
            result["parameters"] = parameters
            
            return result
        except Exception as e:
            self.logger.error(f"Erro ao processar ação de QR code: {str(e)}")
            return {"success": False, "message": f"Erro ao processar QR code: {str(e)}"}
    
    # Métodos auxiliares
    
    def _get_player_location(self, db: Session, session_id: str) -> Optional[int]:
        """
        Obtém a localização atual do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            
        Returns:
            ID da localização atual ou None
        """
        try:
            # Busca a localização atual no progresso do jogador
            progress = db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if progress and hasattr(progress, 'current_location_id'):
                return progress.current_location_id
                
            return None
        except Exception as e:
            self.logger.error(f"Erro ao obter localização do jogador: {str(e)}")
            return None
    
    def _check_specialization_requirement(self, db: Session, session_id: str, requirement: Dict[str, Any]) -> bool:
        """
        Verifica se o jogador atende a um requisito de especialização.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            requirement: Requisito a verificar
            
        Returns:
            True se atendido, False caso contrário
        """
        try:
            if not requirement:
                return True
                
            category = requirement.get('category')
            level = requirement.get('level', 1)
            
            if not category:
                return True
                
            # Busca o nível de especialização do jogador
            specialization = db.query(PlayerSpecialization).filter(
                PlayerSpecialization.session_id == session_id,
                PlayerSpecialization.category_id == category
            ).first()
            
            if not specialization:
                return level <= 0
                
            return specialization.level >= level
        except Exception as e:
            self.logger.error(f"Erro ao verificar requisito de especialização: {str(e)}")
            return False
    
    def _check_inventory_requirement(self, db: Session, session_id: str, required_objects: List[int]) -> bool:
        """
        Verifica se o jogador tem os objetos necessários no inventário.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            required_objects: Lista de IDs de objetos necessários
            
        Returns:
            True se todos os objetos estiverem no inventário
        """
        try:
            if not required_objects:
                return True
                
            # Busca objetos no inventário do jogador
            for obj_id in required_objects:
                inventory_item = db.query(PlayerInventory).filter(
                    PlayerInventory.session_id == session_id,
                    PlayerInventory.object_id == obj_id
                ).first()
                
                if not inventory_item:
                    return False
                    
            return True
        except Exception as e:
            self.logger.error(f"Erro ao verificar requisito de inventário: {str(e)}")
            return False
    
    # Métodos de manipulação de ações
    
    def _handle_enter_location(self, db: Session, session_id: str, location_id: int) -> None:
        """
        Manipula a ação de entrar em uma localização.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            location_id: ID da localização
        """
        try:
            # Atualiza a localização atual do jogador
            progress = db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if progress:
                progress.current_location_id = location_id
                progress.current_area_id = None  # Reset da área atual
                
                # Adiciona à lista de localizações descobertas se necessário
                discovered_locations = progress.discovered_locations
                if isinstance(discovered_locations, str):
                    try:
                        locations_list = json.loads(discovered_locations)
                        if location_id not in locations_list:
                            locations_list.append(location_id)
                        progress.discovered_locations = json.dumps(locations_list)
                    except json.JSONDecodeError:
                        progress.discovered_locations = json.dumps([location_id])
                elif isinstance(discovered_locations, list):
                    if location_id not in discovered_locations:
                        discovered_locations.append(location_id)
                    progress.discovered_locations = discovered_locations
                else:
                    progress.discovered_locations = [location_id]
                
                db.commit()
        except Exception as e:
            self.logger.error(f"Erro ao processar entrada em localização: {str(e)}")
            db.rollback()
    
    def _handle_explore_area(self, db: Session, session_id: str, area_id: int) -> None:
        """
        Manipula a ação de explorar uma área.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            area_id: ID da área
        """
        try:
            # Atualiza a área atual do jogador
            progress = db.query(PlayerProgress).filter(
                PlayerProgress.session_id == session_id
            ).first()
            
            if progress:
                progress.current_area_id = area_id
                
                # Adiciona à lista de áreas descobertas
                discovered_areas = progress.discovered_areas
                current_location = progress.current_location_id
                
                if isinstance(discovered_areas, str):
                    try:
                        areas_dict = json.loads(discovered_areas)
                        loc_key = str(current_location)
                        if loc_key not in areas_dict:
                            areas_dict[loc_key] = []
                        if area_id not in areas_dict[loc_key]:
                            areas_dict[loc_key].append(area_id)
                        progress.discovered_areas = json.dumps(areas_dict)
                    except json.JSONDecodeError:
                        areas_dict = {str(current_location): [area_id]}
                        progress.discovered_areas = json.dumps(areas_dict)
                elif isinstance(discovered_areas, dict):
                    loc_key = str(current_location)
                    if loc_key not in discovered_areas:
                        discovered_areas[loc_key] = []
                    if area_id not in discovered_areas[loc_key]:
                        discovered_areas[loc_key].append(area_id)
                    progress.discovered_areas = discovered_areas
                else:
                    progress.discovered_areas = {str(current_location): [area_id]}
                
                db.commit()
        except Exception as e:
            self.logger.error(f"Erro ao processar exploração de área: {str(e)}")
            db.rollback()
    
    def _handle_collect_object(self, db: Session, session_id: str, object_id: int) -> None:
        """
        Manipula a ação de coletar um objeto.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_id: ID do objeto
        """
        try:
            # Verifica se o objeto já está no inventário
            existing_item = db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id,
                PlayerInventory.object_id == object_id
            ).first()
            
            if not existing_item:
                # Adiciona o objeto ao inventário
                inventory_item = PlayerInventory(
                    session_id=session_id,
                    object_id=object_id,
                    acquisition_method='qrcode',
                    acquired_time=func.now()
                )
                db.add(inventory_item)
                db.commit()
        except Exception as e:
            self.logger.error(f"Erro ao processar coleta de objeto: {str(e)}")
            db.rollback()
    
    def _handle_examine_object(self, db: Session, session_id: str, object_id: int) -> None:
        """
        Manipula a ação de examinar um objeto.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_id: ID do objeto
        """
        # Implementar lógica para examinar objeto
        # Pode atualizar níveis de objeto, especialização, etc.
        pass
    
    def _handle_examine_area(self, db: Session, session_id: str, area_id: int) -> None:
        """
        Manipula a ação de examinar uma área.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            area_id: ID da área
        """
        # Implementar lógica para examinar área
        # Pode atualizar níveis de exploração, especialização, etc.
        pass
    
def _handle_discover_clue(self, db: Session, session_id: str, clue_id: int) -> None:
        """
        Manipula a ação de descobrir uma pista.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            clue_id: ID da pista
        """
        try:
            # Verifica se a pista já foi descoberta
            existing_clue = db.query(PlayerDiscoveredClues).filter(
                PlayerDiscoveredClues.session_id == session_id,
                PlayerDiscoveredClues.clue_id == clue_id
            ).first()
            
            if not existing_clue:
                # Adiciona a pista às descobertas do jogador
                # Aqui estamos assumindo que existe um modelo PlayerDiscoveredClues
                # Se não existir, você precisará adaptar para o modelo real
                clue_discovery = PlayerDiscoveredClues(
                    session_id=session_id,
                    clue_id=clue_id,
                    discovery_time=func.now(),
                    discovery_method='qrcode'
                )
                db.add(clue_discovery)
                
                # Alternativamente, pode-se armazenar na lista de pistas descobertas no progresso
                progress = db.query(PlayerProgress).filter(
                    PlayerProgress.session_id == session_id
                ).first()
                
                if progress:
                    discovered_clues = progress.discovered_clues
                    if isinstance(discovered_clues, str):
                        try:
                            clues_list = json.loads(discovered_clues)
                            if clue_id not in clues_list:
                                clues_list.append(clue_id)
                            progress.discovered_clues = json.dumps(clues_list)
                        except json.JSONDecodeError:
                            progress.discovered_clues = json.dumps([clue_id])
                    elif isinstance(discovered_clues, list):
                        if clue_id not in discovered_clues:
                            discovered_clues.append(clue_id)
                        progress.discovered_clues = discovered_clues
                    else:
                        progress.discovered_clues = [clue_id]
                
                db.commit()
        except Exception as e:
            self.logger.error(f"Erro ao processar descoberta de pista: {str(e)}")
            db.rollback()