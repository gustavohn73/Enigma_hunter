# src/qr_code_processor.py
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from src.repositories.qrcode_repository import QRCodeRepository
from src.repositories.player_progress_repository import PlayerProgressRepository
from src.repositories.location_repository import LocationRepository
from src.repositories.object_repository import ObjectRepository
from src.repositories.clue_repository import ClueRepository
from src.models.db_models import QRCode, PlayerProgress, PlayerInventory, PlayerDiscoveredClues

logger = logging.getLogger(__name__)

class QRCodeProcessor:
    """
    Processador de QR Codes para o sistema Enigma Hunter
    Suporta múltiplas ações e gatilhos de evolução
    """
    
    # Mapeamento de ações possíveis
    ACOES_SUPORTADAS = {
        'enter': 'processar_entrada',
        'explore': 'processar_exploracao',
        'talk': 'processar_dialogo',
        'collect': 'processar_coleta',
        'examine': 'processar_exame'
    }
    
    def __init__(
        self,
        db: Session,
        qrcode_repository: QRCodeRepository,
        player_progress_repository: PlayerProgressRepository,
        location_repository: LocationRepository,
        object_repository: ObjectRepository,
        clue_repository: ClueRepository
    ):
        """
        Inicializa o processador de QR Codes.
        
        Args:
            db: Sessão do banco de dados
            qrcode_repository: Repositório para QR Codes
            player_progress_repository: Repositório para progresso do jogador
            location_repository: Repositório para localizações
            object_repository: Repositório para objetos
            clue_repository: Repositório para pistas
        """
        self.db = db
        self.qrcode_repository = qrcode_repository
        self.player_progress_repository = player_progress_repository
        self.location_repository = location_repository
        self.object_repository = object_repository
        self.clue_repository = clue_repository
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def processar_qr_code(self, session_id: str, uuid: str) -> Dict[str, Any]:
        """
        Processa um QR Code com verificações avançadas e múltiplas ações
        
        Args:
            session_id: ID da sessão do jogador
            uuid: UUID do QR code
            
        Returns:
            Resultado do processamento
        """
        try:
            # Verifica se a sessão existe
            progress = self.player_progress_repository.get_by_session_id(self.db, session_id)
            if not progress:
                return {"success": False, "message": "Sessão não encontrada"}
            
            # Obtém os dados do QR code
            qr_code = self.qrcode_repository.get_by_uuid(self.db, uuid)
            if not qr_code:
                return {"success": False, "message": "QR Code inválido"}
            
            # Verificação de requisitos de acesso
            resultado_acesso = self.qrcode_repository.check_scan_requirements(self.db, uuid, session_id)
            if not resultado_acesso.get("access_granted", False):
                return {
                    "success": False, 
                    "message": resultado_acesso.get("reason", "Acesso negado")
                }
            
            # Marca QR Code como escaneado
            self.qrcode_repository.register_scan(self.db, uuid, session_id, resultado_acesso)
            
            # Processa ação específica
            action = qr_code.action
            if action in self.ACOES_SUPORTADAS:
                metodo_acao = getattr(self, self.ACOES_SUPORTADAS[action])
                resultado = metodo_acao(session_id, qr_code)
            else:
                resultado = {"success": False, "message": "Ação não suportada"}
            
            # Verificar se há gatilhos de evolução
            self._verificar_gatilhos_evolucao(session_id, qr_code)
            
            return resultado
        except Exception as e:
            self.logger.error(f"Erro ao processar QR code: {str(e)}")
            self.db.rollback()
            return {"success": False, "message": f"Erro ao processar QR code: {str(e)}"}
    
    def processar_entrada(self, session_id: str, qr_code: QRCode) -> Dict[str, Any]:
        """
        Processa entrada em localização
        
        Args:
            session_id: ID da sessão do jogador
            qr_code: Objeto QR code
            
        Returns:
            Resultado da ação
        """
        try:
            target_id = qr_code.target_id
            
            # Atualiza a localização atual do jogador
            result = self.player_progress_repository.discover_location(self.db, session_id, target_id)
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": result.get("message", "Erro ao entrar na localização")
                }
                
            # Obtém detalhes da localização
            location = self.location_repository.get_by_id(self.db, target_id)
            location_name = location.name if location else "Localização desconhecida"
            
            return {
                "success": True,
                "message": f"Você entrou em: {location_name}",
                "location_id": target_id,
                "location_name": location_name,
                "action_type": "enter_location"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar entrada em localização: {str(e)}")
            return {"success": False, "message": f"Erro ao entrar na localização: {str(e)}"}
    
    def processar_exploracao(self, session_id: str, qr_code: QRCode) -> Dict[str, Any]:
        """
        Processa exploração de área
        
        Args:
            session_id: ID da sessão do jogador
            qr_code: Objeto QR code
            
        Returns:
            Resultado da ação
        """
        try:
            target_id = qr_code.target_id
            
            # Atualiza a área atual do jogador
            result = self.player_progress_repository.discover_area(self.db, session_id, target_id)
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": result.get("message", "Erro ao explorar área")
                }
                
            # Obtém detalhes da área
            area = self.location_repository.get_area_by_id(self.db, target_id)
            area_name = area.name if area else "Área desconhecida"
            
            # Atualizando especialização para exploração
            self.player_progress_repository.update_specialization(
                self.db,
                session_id=session_id,
                category_id="exploracao",
                points=5,
                interaction_type="areas",
                interaction_id=str(target_id)
            )
            
            return {
                "success": True,
                "message": f"Você explorou: {area_name}",
                "area_id": target_id,
                "area_name": area_name,
                "action_type": "explore_area"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar exploração de área: {str(e)}")
            return {"success": False, "message": f"Erro ao explorar área: {str(e)}"}
    
    def processar_dialogo(self, session_id: str, qr_code: QRCode) -> Dict[str, Any]:
        """
        Processa início de diálogo com personagem
        
        Args:
            session_id: ID da sessão do jogador
            qr_code: Objeto QR code
            
        Returns:
            Resultado da ação
        """
        try:
            character_id = qr_code.target_id
            
            # Em uma implementação real, este método interagiria com o
            # CharacterManager para iniciar o diálogo. Para fins de simplicidade
            # apenas retornamos as informações necessárias para iniciar o diálogo.
            
            return {
                "success": True,
                "message": "Preparando diálogo",
                "character_id": character_id,
                "action_type": "start_dialogue"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar início de diálogo: {str(e)}")
            return {"success": False, "message": f"Erro ao iniciar diálogo: {str(e)}"}
    
    def processar_coleta(self, session_id: str, qr_code: QRCode) -> Dict[str, Any]:
        """
        Processa coleta de objeto
        
        Args:
            session_id: ID da sessão do jogador
            qr_code: Objeto QR code
            
        Returns:
            Resultado da ação
        """
        try:
            object_id = qr_code.target_id
            
            # Tenta adicionar ao inventário
            result = self.player_progress_repository.add_to_inventory(
                self.db, 
                session_id=session_id, 
                object_id=object_id, 
                acquisition_method="qrcode"
            )
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": result.get("message", "Erro ao coletar objeto")
                }
            
            # Obtém detalhes do objeto
            game_object = self.object_repository.get_by_id(self.db, object_id)
            object_name = game_object.name if game_object else "Objeto desconhecido"
            
            # Determina se é um novo objeto ou já estava no inventário
            is_new = result.get("is_new", True)
            
            message = f"Você coletou: {object_name}" if is_new else f"Você já possui: {object_name}"
            
            # Adiciona pontos de especialização se for um novo objeto
            if is_new:
                self.player_progress_repository.update_specialization(
                    self.db,
                    session_id=session_id,
                    category_id="coleta",
                    points=10,
                    interaction_type="objetos",
                    interaction_id=str(object_id)
                )
            
            return {
                "success": True,
                "message": message,
                "object_id": object_id,
                "object_name": object_name,
                "is_new": is_new,
                "action_type": "collect_object"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar coleta de objeto: {str(e)}")
            return {"success": False, "message": f"Erro ao coletar objeto: {str(e)}"}
    
    def processar_exame(self, session_id: str, qr_code: QRCode) -> Dict[str, Any]:
        """
        Processa exame detalhado de objeto/área
        
        Args:
            session_id: ID da sessão do jogador
            qr_code: Objeto QR code
            
        Returns:
            Resultado da ação
        """
        try:
            target_id = qr_code.target_id
            target_type = qr_code.target_type
            
            # Diferentes tipos de exame
            if target_type == "object":
                # Examinar objeto
                game_object = self.object_repository.get_by_id(self.db, target_id)
                
                if not game_object:
                    return {
                        "success": False,
                        "message": "Objeto não encontrado"
                    }
                
                # Atualiza o nível de conhecimento sobre o objeto
                self.player_progress_repository.update_object_progress(
                    self.db,
                    session_id=session_id,
                    object_id=target_id,
                    level=1  # Nível básico de conhecimento
                )
                
                # Adiciona pontos de especialização
                self.player_progress_repository.update_specialization(
                    self.db,
                    session_id=session_id,
                    category_id="analise",
                    points=5,
                    interaction_type="exame_objeto",
                    interaction_id=str(target_id)
                )
                
                return {
                    "success": True,
                    "message": f"Você examinou: {game_object.name}",
                    "object_id": target_id,
                    "object_name": game_object.name,
                    "description": game_object.base_description,
                    "action_type": "examine_object"
                }
                
            elif target_type == "area":
                # Examinar área
                area = self.location_repository.get_area_by_id(self.db, target_id)
                
                if not area:
                    return {
                        "success": False,
                        "message": "Área não encontrada"
                    }
                
                # Atualiza o nível de exploração da área
                self.player_progress_repository.update_environment_progress(
                    self.db,
                    session_id=session_id,
                    location_id=area.location_id,
                    level=1  # Nível básico de exploração
                )
                
                # Adiciona pontos de especialização
                self.player_progress_repository.update_specialization(
                    self.db,
                    session_id=session_id,
                    category_id="exploracao",
                    points=5,
                    interaction_type="exame_area",
                    interaction_id=str(target_id)
                )
                
                return {
                    "success": True,
                    "message": f"Você examinou: {area.name}",
                    "area_id": target_id,
                    "area_name": area.name,
                    "description": area.description,
                    "action_type": "examine_area"
                }
                
            elif target_type == "clue":
                # Descobrir pista
                return self._processar_descoberta_pista(session_id, target_id)
                
            else:
                return {
                    "success": False,
                    "message": f"Tipo de exame não suportado: {target_type}"
                }
                
        except Exception as e:
            self.logger.error(f"Erro ao processar exame: {str(e)}")
            return {"success": False, "message": f"Erro ao examinar: {str(e)}"}
    
    def _processar_descoberta_pista(self, session_id: str, clue_id: int) -> Dict[str, Any]:
        """
        Processa descoberta de pista
        
        Args:
            session_id: ID da sessão do jogador
            clue_id: ID da pista
            
        Returns:
            Resultado da ação
        """
        try:
            # Registra a descoberta da pista
            result = self.player_progress_repository.discover_clue(
                self.db,
                session_id=session_id,
                clue_id=clue_id
            )
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": result.get("message", "Erro ao descobrir pista")
                }
            
            # Obtém detalhes da pista
            clue = self.clue_repository.get_by_id(self.db, clue_id)
            clue_name = clue.name if clue else "Pista desconhecida"
            
            # Determina se é uma nova pista
            is_new = result.get("is_new_discovery", True)
            
            message = f"Você descobriu: {clue_name}" if is_new else f"Você já descobriu esta pista: {clue_name}"
            
            # Adiciona pontos de especialização específicos para a pista, 
            # se for uma nova descoberta
            if is_new and clue:
                # Na implementação real, o clue repository já tem esta lógica
                # incorporada no método discover_clue
                pass
            
            return {
                "success": True,
                "message": message,
                "clue_id": clue_id,
                "clue_name": clue_name,
                "is_new": is_new,
                "action_type": "discover_clue"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar descoberta de pista: {str(e)}")
            return {"success": False, "message": f"Erro ao descobrir pista: {str(e)}"}
    
    def _verificar_gatilhos_evolucao(self, session_id: str, qr_code: QRCode) -> None:
        """
        Verifica e processa gatilhos de evolução para personagens, objetos, etc.
        
        Args:
            session_id: ID da sessão do jogador
            qr_code: Objeto QR code
        """
        try:
            target_type = qr_code.target_type
            target_id = qr_code.target_id
            
            # Evolução de personagem
            if target_type == "character":
                # Esta lógica seria delegada ao CharacterManager em uma implementação completa
                # Apenas um placeholder vazio para a estrutura
                pass
            
            # Evolução de objeto
            if target_type == "object":
                # Verifica se o objeto pode evoluir baseado em requisitos
                # Esta lógica seria implementada pelo ObjectManager ou ObjectRepository
                pass
                
            # Outros tipos de evolução podem ser implementados aqui
        except Exception as e:
            self.logger.error(f"Erro ao verificar gatilhos de evolução: {str(e)}")