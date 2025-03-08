# src/qr_code_processor.py
import json
import logging
from typing import Dict, Any, Optional, List, Protocol
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

class QRCodeCommand(ABC):
    """
    Classe base abstrata para comandos de QR Code seguindo o padrão Command.
    Cada tipo de ação será implementado como uma subclasse concreta.
    """
    
    @abstractmethod
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executa a ação associada ao comando.
        
        Args:
            session_id: ID da sessão do jogador
            target_id: ID do alvo (localização, área, personagem, objeto, etc.)
            parameters: Parâmetros adicionais específicos da ação
            
        Returns:
            Resultado da ação
        """
        pass


class EnterLocationCommand(QRCodeCommand):
    """Comando para entrar em uma localização"""
    
    def __init__(self, db: Session, player_progress_repository, location_repository):
        self.db = db
        self.player_progress_repository = player_progress_repository
        self.location_repository = location_repository
        self.logger = logging.getLogger(__name__)
    
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
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


class ExploreAreaCommand(QRCodeCommand):
    """Comando para explorar uma área"""
    
    def __init__(self, db: Session, player_progress_repository, location_repository):
        self.db = db
        self.player_progress_repository = player_progress_repository
        self.location_repository = location_repository
        self.logger = logging.getLogger(__name__)
    
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
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


class TalkToCharacterCommand(QRCodeCommand):
    """Comando para iniciar diálogo com personagem"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            # Em uma implementação real, este método interagiria com o
            # CharacterManager para iniciar o diálogo. Para fins de simplicidade
            # apenas retornamos as informações necessárias para iniciar o diálogo.
            
            return {
                "success": True,
                "message": "Preparando diálogo",
                "character_id": target_id,
                "action_type": "start_dialogue"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar início de diálogo: {str(e)}")
            return {"success": False, "message": f"Erro ao iniciar diálogo: {str(e)}"}


class CollectObjectCommand(QRCodeCommand):
    """Comando para coletar um objeto"""
    
    def __init__(self, db: Session, player_progress_repository, object_repository):
        self.db = db
        self.player_progress_repository = player_progress_repository
        self.object_repository = object_repository
        self.logger = logging.getLogger(__name__)
    
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            # Tenta adicionar ao inventário
            result = self.player_progress_repository.add_to_inventory(
                self.db, 
                session_id=session_id, 
                object_id=target_id, 
                acquisition_method="qrcode"
            )
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": result.get("message", "Erro ao coletar objeto")
                }
            
            # Obtém detalhes do objeto
            game_object = self.object_repository.get_by_id(self.db, target_id)
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
                    interaction_id=str(target_id)
                )
            
            return {
                "success": True,
                "message": message,
                "object_id": target_id,
                "object_name": object_name,
                "is_new": is_new,
                "action_type": "collect_object"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar coleta de objeto: {str(e)}")
            return {"success": False, "message": f"Erro ao coletar objeto: {str(e)}"}


class ExamineObjectCommand(QRCodeCommand):
    """Comando para examinar um objeto"""
    
    def __init__(self, db: Session, player_progress_repository, object_repository):
        self.db = db
        self.player_progress_repository = player_progress_repository
        self.object_repository = object_repository
        self.logger = logging.getLogger(__name__)
    
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
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
        except Exception as e:
            self.logger.error(f"Erro ao processar exame de objeto: {str(e)}")
            return {"success": False, "message": f"Erro ao examinar objeto: {str(e)}"}


class ExamineAreaCommand(QRCodeCommand):
    """Comando para examinar uma área"""
    
    def __init__(self, db: Session, player_progress_repository, location_repository):
        self.db = db
        self.player_progress_repository = player_progress_repository
        self.location_repository = location_repository
        self.logger = logging.getLogger(__name__)
    
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
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
        except Exception as e:
            self.logger.error(f"Erro ao processar exame de área: {str(e)}")
            return {"success": False, "message": f"Erro ao examinar área: {str(e)}"}


class DiscoverClueCommand(QRCodeCommand):
    """Comando para descobrir uma pista"""
    
    def __init__(self, db: Session, player_progress_repository, clue_repository):
        self.db = db
        self.player_progress_repository = player_progress_repository
        self.clue_repository = clue_repository
        self.logger = logging.getLogger(__name__)
    
    def execute(self, session_id: str, target_id: int, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            # Registra a descoberta da pista
            result = self.player_progress_repository.discover_clue(
                self.db,
                session_id=session_id,
                clue_id=target_id
            )
            
            if not result.get("success", False):
                return {
                    "success": False,
                    "message": result.get("message", "Erro ao descobrir pista")
                }
            
            # Obtém detalhes da pista
            clue = self.clue_repository.get_by_id(self.db, target_id)
            clue_name = clue.name if clue else "Pista desconhecida"
            
            # Determina se é uma nova pista
            is_new = result.get("is_new_discovery", True)
            
            message = f"Você descobriu: {clue_name}" if is_new else f"Você já descobriu esta pista: {clue_name}"
            
            return {
                "success": True,
                "message": message,
                "clue_id": target_id,
                "clue_name": clue_name,
                "is_new": is_new,
                "action_type": "discover_clue"
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar descoberta de pista: {str(e)}")
            return {"success": False, "message": f"Erro ao descobrir pista: {str(e)}"}


class QRCodeProcessor:
    """
    Processador de QR Codes para o sistema Enigma Hunter.
    Implementa o padrão Command para delegar ações específicas.
    """
    
    def __init__(
        self,
        db: Session,
        qrcode_repository,
        player_progress_repository,
        location_repository,
        object_repository,
        clue_repository
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
        
        # Inicializa o mapeamento de comandos
        self._init_commands()
    
    def _init_commands(self):
        """Inicializa os comandos para cada tipo de ação."""
        self.commands = {
            "enter": EnterLocationCommand(self.db, self.player_progress_repository, self.location_repository),
            "explore": ExploreAreaCommand(self.db, self.player_progress_repository, self.location_repository),
            "talk": TalkToCharacterCommand(self.db),
            "collect": CollectObjectCommand(self.db, self.player_progress_repository, self.object_repository),
            "examine_object": ExamineObjectCommand(self.db, self.player_progress_repository, self.object_repository),
            "examine_area": ExamineAreaCommand(self.db, self.player_progress_repository, self.location_repository),
            "discover_clue": DiscoverClueCommand(self.db, self.player_progress_repository, self.clue_repository)
        }
    
    def processar_qr_code(self, session_id: str, uuid: str) -> Dict[str, Any]:
        """
        Processa um QR Code escaneado por um jogador.
        
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
            target_id = qr_code.target_id
            target_type = qr_code.target_type
            parameters = self._parse_parameters(qr_code.parameters)
            
            # Seleciona o comando apropriado com base na ação e no tipo de alvo
            command_key = action
            if action == "examine":
                # Para a ação "examine", o comando depende do tipo de alvo
                command_key = f"examine_{target_type}"
            
            if command_key in self.commands:
                resultado = self.commands[command_key].execute(session_id, target_id, parameters)
            else:
                resultado = {"success": False, "message": f"Ação não suportada: {action}"}
            
            # Adiciona os parâmetros ao resultado
            if "parameters" not in resultado:
                resultado["parameters"] = parameters
            
            # Verificar se há gatilhos de evolução
            self._verificar_gatilhos_evolucao(session_id, qr_code)
            
            return resultado
        except Exception as e:
            self.logger.error(f"Erro ao processar QR code: {str(e)}")
            self.db.rollback()
            return {"success": False, "message": f"Erro ao processar QR code: {str(e)}"}
    
    def _parse_parameters(self, parameters) -> Dict[str, Any]:
        """
        Converte os parâmetros do QR code para um dicionário.
        
        Args:
            parameters: Parâmetros do QR code (string JSON ou dicionário)
            
        Returns:
            Dicionário de parâmetros
        """
        if not parameters:
            return {}
            
        if isinstance(parameters, str):
            try:
                return json.loads(parameters)
            except json.JSONDecodeError:
                return {}
        elif isinstance(parameters, dict):
            return parameters
        else:
            return {}
    
    def _verificar_gatilhos_evolucao(self, session_id: str, qr_code) -> None:
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