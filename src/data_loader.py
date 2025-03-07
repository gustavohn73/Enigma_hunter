# src/data_loader.py
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.repositories.story_repository import StoryRepository
from src.repositories.character_repository import CharacterRepository
from src.repositories.location_repository import LocationRepository
from src.repositories.object_repository import ObjectRepository
from src.repositories.clue_repository import ClueRepository
from src.repositories.qrcode_repository import QRCodeRepository


class DataLoader:
    """
    Classe responsável por carregar dados iniciais dos arquivos JSON para o banco de dados.
    Esta classe não mantém estado em memória e serve apenas para inicializar o banco de dados.
    """
    
    def __init__(self, 
                story_repository: StoryRepository,
                character_repository: CharacterRepository,
                location_repository: LocationRepository,
                object_repository: ObjectRepository,
                clue_repository: ClueRepository,
                qrcode_repository: QRCodeRepository):
        """
        Inicializa o carregador de dados com os repositórios necessários.
        
        Args:
            story_repository: Repositório para histórias
            character_repository: Repositório para personagens
            location_repository: Repositório para localizações
            object_repository: Repositório para objetos
            clue_repository: Repositório para pistas
            qrcode_repository: Repositório para QR codes
        """
        self.story_repository = story_repository
        self.character_repository = character_repository
        self.location_repository = location_repository
        self.object_repository = object_repository
        self.clue_repository = clue_repository
        self.qrcode_repository = qrcode_repository
        
        self.logger = logging.getLogger(__name__)
    
    def load_all_data(self, db: Session, base_path: str = "") -> Dict[str, Any]:
        """
        Carrega todos os dados das histórias para o banco de dados.
        
        Args:
            db: Sessão do banco de dados
            base_path: Caminho base para os arquivos de dados
            
        Returns:
            Dicionário com estatísticas de carregamento
        """
        self.logger.info("Iniciando carregamento de todos os dados")
        
        base_dir = Path(base_path) if base_path else Path.cwd()
        historias_dir = base_dir / "historias"
        
        if not historias_dir.exists():
            self.logger.error(f"Diretório de histórias não encontrado: {historias_dir}")
            return {"success": False, "error": "Diretório de histórias não encontrado"}
        
        stats = {
            "historias_processadas": 0,
            "personagens_carregados": 0,
            "ambientes_carregados": 0,
            "objetos_carregados": 0,
            "pistas_carregadas": 0,
            "qrcodes_carregados": 0
        }
        
        # Processa cada diretório de história
        for historia_dir in historias_dir.iterdir():
            if historia_dir.is_dir():
                try:
                    self.logger.info(f"Processando história: {historia_dir.name}")
                    result = self.load_story(db, str(historia_dir))
                    
                    if result["success"]:
                        stats["historias_processadas"] += 1
                        stats["personagens_carregados"] += result.get("personagens_carregados", 0)
                        stats["ambientes_carregados"] += result.get("ambientes_carregados", 0)
                        stats["objetos_carregados"] += result.get("objetos_carregados", 0)
                        stats["pistas_carregadas"] += result.get("pistas_carregadas", 0)
                        stats["qrcodes_carregados"] += result.get("qrcodes_carregados", 0)
                    else:
                        self.logger.error(f"Erro ao processar história {historia_dir.name}: {result.get('error')}")
                except Exception as e:
                    self.logger.exception(f"Erro não tratado ao processar história {historia_dir.name}: {str(e)}")
        
        stats["success"] = True
        self.logger.info(f"Carregamento concluído. Estatísticas: {stats}")
        return stats
    
    def load_story(self, db: Session, story_path: str) -> Dict[str, Any]:
        """
        Carrega uma história específica e todos os seus componentes.
        
        Args:
            db: Sessão do banco de dados
            story_path: Caminho para o diretório da história
            
        Returns:
            Dicionário com resultado da operação e estatísticas
        """
        story_dir = Path(story_path)
        
        # Verifica se o diretório existe
        if not story_dir.exists() or not story_dir.is_dir():
            self.logger.error(f"Diretório de história não encontrado: {story_dir}")
            return {"success": False, "error": "Diretório de história não encontrado"}
        
        # Verifica se existe o arquivo história base
        historia_base_path = story_dir / "historia_base.json"
        if not historia_base_path.exists():
            self.logger.error(f"Arquivo historia_base.json não encontrado em: {story_dir}")
            return {"success": False, "error": "Arquivo historia_base.json não encontrado"}
        
        try:
            # Carrega dados básicos da história
            historia_data = self._load_json_file(historia_base_path)
            if not historia_data:
                return {"success": False, "error": "Erro ao carregar arquivo historia_base.json"}
            
            # Carrega a configuração de especialização
            especializacao_config = self._load_specialization_config(story_dir)
            
            # Cria a história no banco de dados
            with db.begin_nested():  # Cria um savepoint
                story = self.story_repository.create(db, {
                    "title": historia_data.get("title", "História sem título"),
                    "description": historia_data.get("description", ""),
                    "introduction": historia_data.get("introduction", ""),
                    "conclusion": historia_data.get("conclusion", ""),
                    "difficulty_level": historia_data.get("difficulty_level", 1),
                    "solution_criteria": historia_data.get("solution_criteria", {}),
                    "specialization_config": especializacao_config,
                    "is_active": True
                })
                
                if not story:
                    return {"success": False, "error": "Erro ao criar história no banco de dados"}
                
                story_id = story.story_id
            
            # Carrega os componentes da história
            stats = {
                "success": True,
                "story_id": story_id,
                "title": historia_data.get("title", "História sem título"),
                "personagens_carregados": 0,
                "ambientes_carregados": 0,
                "objetos_carregados": 0,
                "pistas_carregadas": 0,
                "qrcodes_carregados": 0
            }
            
            # Carrega ambientes
            ambiente_stats = self._load_environments(db, story_id, story_dir)
            stats["ambientes_carregados"] = ambiente_stats.get("ambientes_carregados", 0)
            
            # Carrega personagens
            personagem_stats = self._load_characters(db, story_id, story_dir)
            stats["personagens_carregados"] = personagem_stats.get("personagens_carregados", 0)
            
            # Carrega objetos e pistas
            obj_clue_stats = self._load_objects_and_clues(db, story_id, story_dir)
            stats["objetos_carregados"] = obj_clue_stats.get("objetos_carregados", 0)
            stats["pistas_carregadas"] = obj_clue_stats.get("pistas_carregadas", 0)
            
            # Carrega QR codes
            qrcode_stats = self._load_qrcodes(db, story_id, story_dir)
            stats["qrcodes_carregados"] = qrcode_stats.get("qrcodes_carregados", 0)
            
            self.logger.info(f"História {historia_data.get('title')} carregada com sucesso")
            return stats
            
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.exception(f"Erro de banco de dados ao carregar história: {str(e)}")
            return {"success": False, "error": f"Erro de banco de dados: {str(e)}"}
        
        except Exception as e:
            self.logger.exception(f"Erro ao carregar história: {str(e)}")
            return {"success": False, "error": f"Erro não tratado: {str(e)}"}
    
    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Carrega um arquivo JSON com tratamento de erros.
        
        Args:
            file_path: Caminho para o arquivo JSON
            
        Returns:
            Dicionário com dados do JSON ou None em caso de erro
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except json.JSONDecodeError as e:
            self.logger.error(f"Erro ao decodificar JSON do arquivo {file_path}: {str(e)}")
            return None
        except FileNotFoundError:
            self.logger.error(f"Arquivo não encontrado: {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao ler arquivo {file_path}: {str(e)}")
            return None
    
    def _load_specialization_config(self, story_dir: Path) -> Dict[str, Any]:
        """
        Carrega a configuração do sistema de especialização.
        
        Args:
            story_dir: Diretório da história
            
        Returns:
            Dicionário com a configuração de especialização ou dicionário vazio
        """
        try:
            config_path = story_dir / "data" / "sistema-especializacao.json"
            if not config_path.exists():
                self.logger.warning(f"Arquivo de configuração de especialização não encontrado: {config_path}")
                return {}
            
            config_data = self._load_json_file(config_path)
            if not config_data:
                return {}
            
            return config_data
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração de especialização: {str(e)}")
            return {}
    
    def _load_environments(self, db: Session, story_id: int, story_dir: Path) -> Dict[str, Any]:
        """
        Carrega os ambientes de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            story_dir: Diretório da história
            
        Returns:
            Dicionário com estatísticas de carregamento
        """
        ambientes_dir = story_dir / "ambientes"
        if not ambientes_dir.exists():
            self.logger.warning(f"Diretório de ambientes não encontrado: {ambientes_dir}")
            return {"ambientes_carregados": 0}
        
        ambientes_carregados = 0
        
        try:
            for arquivo in ambientes_dir.glob("Ambiente_*.json"):
                ambiente_data = self._load_json_file(arquivo)
                if not ambiente_data:
                    continue
                
                # Processa cada ambiente (pode ser lista ou dicionário único)
                if isinstance(ambiente_data, list):
                    for amb in ambiente_data:
                        location = self._process_environment(db, story_id, amb)
                        if location:
                            ambientes_carregados += 1
                else:
                    location = self._process_environment(db, story_id, ambiente_data)
                    if location:
                        ambientes_carregados += 1
            
            return {"ambientes_carregados": ambientes_carregados}
        except Exception as e:
            self.logger.exception(f"Erro ao carregar ambientes: {str(e)}")
            return {"ambientes_carregados": ambientes_carregados}
    
    def _process_environment(self, db: Session, story_id: int, ambiente_data: Dict[str, Any]) -> Any:
        """
        Processa e insere um ambiente no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            ambiente_data: Dados do ambiente
            
        Returns:
            Objeto Location ou None em caso de erro
        """
        try:
            # Cria a localização
            location = self.location_repository.create(db, {
                "story_id": story_id,
                "location_id": ambiente_data.get("location_id"),
                "name": ambiente_data.get("name", "Ambiente sem nome"),
                "description": ambiente_data.get("description", ""),
                "is_locked": ambiente_data.get("is_locked", False),
                "unlock_condition": ambiente_data.get("unlock_condition", ""),
                "navigation_map": ambiente_data.get("navigation_map", {}),
                "is_starting_location": ambiente_data.get("is_starting_location", False)
            })
            
            if not location:
                return None
            
            # Processa áreas da localização
            areas = ambiente_data.get("areas", [])
            for area_data in areas:
                area = self.location_repository.add_area(db, location.location_id, {
                    "area_id": area_data.get("area_id"),
                    "name": area_data.get("name", "Área sem nome"),
                    "description": area_data.get("description", ""),
                    "initially_visible": area_data.get("initially_visible", True),
                    "connected_areas": area_data.get("connected_areas", []),
                    "discovery_level_required": area_data.get("discovery_level_required", 0)
                })
                
                if area:
                    # Processa detalhes da área
                    details = area_data.get("details", [])
                    for detail_data in details:
                        self.location_repository.add_detail(db, area.area_id, {
                            "detail_id": detail_data.get("detail_id"),
                            "name": detail_data.get("name", "Detalhe sem nome"),
                            "description": detail_data.get("description", ""),
                            "discovery_level_required": detail_data.get("discovery_level_required", 0),
                            "has_clue": detail_data.get("has_clue", False),
                            "clue_id": detail_data.get("clue_id")
                        })
            
            return location
        except Exception as e:
            self.logger.error(f"Erro ao processar ambiente: {str(e)}")
            return None
    
    def _load_characters(self, db: Session, story_id: int, story_dir: Path) -> Dict[str, Any]:
        """
        Carrega os personagens de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            story_dir: Diretório da história
            
        Returns:
            Dicionário com estatísticas de carregamento
        """
        personagens_dir = story_dir / "personagens"
        if not personagens_dir.exists():
            self.logger.warning(f"Diretório de personagens não encontrado: {personagens_dir}")
            return {"personagens_carregados": 0}
        
        personagens_carregados = 0
        
        try:
            for arquivo in personagens_dir.glob("Personagem_*.json"):
                personagem_data = self._load_json_file(arquivo)
                if not personagem_data:
                    continue
                
                # Processa cada personagem (pode ser lista ou dicionário único)
                if isinstance(personagem_data, list):
                    for pers in personagem_data:
                        character = self._process_character(db, story_id, pers)
                        if character:
                            personagens_carregados += 1
                else:
                    character = self._process_character(db, story_id, personagem_data)
                    if character:
                        personagens_carregados += 1
            
            return {"personagens_carregados": personagens_carregados}
        except Exception as e:
            self.logger.exception(f"Erro ao carregar personagens: {str(e)}")
            return {"personagens_carregados": personagens_carregados}
    
    def _process_character(self, db: Session, story_id: int, character_data: Dict[str, Any]) -> Any:
        """
        Processa e insere um personagem no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            character_data: Dados do personagem
            
        Returns:
            Objeto Character ou None em caso de erro
        """
        try:
            # Cria o personagem
            character = self.character_repository.create(db, {
                "story_id": story_id,
                "character_id": character_data.get("character_id"),
                "name": character_data.get("name", "Personagem sem nome"),
                "base_description": character_data.get("base_description", ""),
                "personality": character_data.get("personality", ""),
                "appearance": character_data.get("appearance", ""),
                "is_culprit": character_data.get("is_culprit", False),
                "motive": character_data.get("motive", ""),
                "location_schedule": character_data.get("location_schedule", {})
            })
            
            if not character:
                return None
            
            # Processa níveis do personagem
            levels = character_data.get("levels", [])
            for level_data in levels:
                level = self.character_repository.add_level(db, character.character_id, {
                    "level_number": level_data.get("level_number", 0),
                    "knowledge_scope": level_data.get("knowledge_scope", ""),
                    "narrative_stance": level_data.get("narrative_stance", ""),
                    "is_defensive": level_data.get("is_defensive", False),
                    "dialogue_parameters": level_data.get("dialogue_parameters", ""),
                    "ia_instruction_set": level_data.get("ia_instruction_set", {})
                })
                
                if level:
                    # Processa gatilhos do nível
                    triggers = level_data.get("triggers", [])
                    for trigger_data in triggers:
                        trigger = self.character_repository.add_trigger(db, level.level_id, {
                            "trigger_keyword": trigger_data.get("trigger_keyword", ""),
                            "contextual_condition": trigger_data.get("contextual_condition", ""),
                            "defensive_response": trigger_data.get("defensive_response", ""),
                            "challenge_question": trigger_data.get("challenge_question", ""),
                            "success_response": trigger_data.get("success_response", ""),
                            "fail_response": trigger_data.get("fail_response", ""),
                            "multi_step_verification": trigger_data.get("multi_step_verification", False)
                        })
                        
                        if trigger:
                            # Processa requisitos do gatilho
                            requirements = trigger_data.get("requirements", [])
                            for req_data in requirements:
                                self.character_repository.add_requirement(db, trigger.trigger_id, {
                                    "requirement_type": req_data.get("requirement_type", ""),
                                    "required_object_id": req_data.get("required_object_id"),
                                    "required_knowledge": req_data.get("required_knowledge", {}),
                                    "verification_method": req_data.get("verification_method", ""),
                                    "hint_if_incorrect": req_data.get("hint_if_incorrect", ""),
                                    "minimum_presentation_level": req_data.get("minimum_presentation_level", 0)
                                })
            
            return character
        except Exception as e:
            self.logger.error(f"Erro ao processar personagem: {str(e)}")
            return None
    
    def _load_objects_and_clues(self, db: Session, story_id: int, story_dir: Path) -> Dict[str, Any]:
        """
        Carrega os objetos e pistas de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            story_dir: Diretório da história
            
        Returns:
            Dicionário com estatísticas de carregamento
        """
        data_dir = story_dir / "data"
        if not data_dir.exists():
            self.logger.warning(f"Diretório de dados não encontrado: {data_dir}")
            return {"objetos_carregados": 0, "pistas_carregadas": 0}
        
        objetos_carregados = 0
        pistas_carregadas = 0
        
        try:
            # Carrega objetos
            objetos_path = data_dir / "objetos.json"
            if objetos_path.exists():
                objetos_data = self._load_json_file(objetos_path)
                if objetos_data:
                    for objeto_data in objetos_data:
                        objeto = self._process_object(db, story_id, objeto_data)
                        if objeto:
                            objetos_carregados += 1
            
            # Carrega pistas
            pistas_path = data_dir / "pistas.json"
            if pistas_path.exists():
                pistas_data = self._load_json_file(pistas_path)
                if pistas_data:
                    for pista_data in pistas_data:
                        pista = self._process_clue(db, story_id, pista_data)
                        if pista:
                            pistas_carregadas += 1
            
            return {
                "objetos_carregados": objetos_carregados,
                "pistas_carregadas": pistas_carregadas
            }
        except Exception as e:
            self.logger.exception(f"Erro ao carregar objetos e pistas: {str(e)}")
            return {
                "objetos_carregados": objetos_carregados,
                "pistas_carregadas": pistas_carregadas
            }
    
    def _process_object(self, db: Session, story_id: int, object_data: Dict[str, Any]) -> Any:
        """
        Processa e insere um objeto no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            object_data: Dados do objeto
            
        Returns:
            Objeto GameObject ou None em caso de erro
        """
        try:
            # Cria o objeto
            game_object = self.object_repository.create_object(db, {
                "story_id": story_id,
                "object_id": object_data.get("object_id"),
                "name": object_data.get("name", "Objeto sem nome"),
                "base_description": object_data.get("base_description", ""),
                "is_collectible": object_data.get("is_collectible", True),
                "initial_location_id": object_data.get("initial_location_id"),
                "initial_area_id": object_data.get("initial_area_id"),
                "discovery_condition": object_data.get("discovery_condition", "")
            })
            
            if not game_object:
                return None
            
            # Processa níveis do objeto
            levels = object_data.get("levels", [])
            for level_data in levels:
                self.object_repository.add_object_level(db, game_object.object_id, {
                    "level_number": level_data.get("level_number", 0),
                    "level_description": level_data.get("level_description", ""),
                    "level_attributes": level_data.get("level_attributes", {}),
                    "evolution_trigger": level_data.get("evolution_trigger", ""),
                    "related_clue_id": level_data.get("related_clue_id")
                })
            
            return game_object
        except Exception as e:
            self.logger.error(f"Erro ao processar objeto: {str(e)}")
            return None
    
    def _process_clue(self, db: Session, story_id: int, clue_data: Dict[str, Any]) -> Any:
        """
        Processa e insere uma pista no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            clue_data: Dados da pista
            
        Returns:
            Objeto Clue ou None em caso de erro
        """
        try:
            # Cria a pista
            clue = self.clue_repository.create_clue(db, {
                "story_id": story_id,
                "clue_id": clue_data.get("clue_id"),
                "name": clue_data.get("name", "Pista sem nome"),
                "description": clue_data.get("description", ""),
                "type": clue_data.get("type", ""),
                "relevance": clue_data.get("relevance", 1),
                "is_key_evidence": clue_data.get("is_key_evidence", False),
                "related_aspect": clue_data.get("related_aspect", ""),
                "discovery_conditions": clue_data.get("discovery_conditions", {})
            })
            
            return clue
        except Exception as e:
            self.logger.error(f"Erro ao processar pista: {str(e)}")
            return None
    
    def _load_qrcodes(self, db: Session, story_id: int, story_dir: Path) -> Dict[str, Any]:
        """
        Carrega os QR codes de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            story_dir: Diretório da história
            
        Returns:
            Dicionário com estatísticas de carregamento
        """
        data_dir = story_dir / "data"
        if not data_dir.exists():
            self.logger.warning(f"Diretório de dados não encontrado: {data_dir}")
            return {"qrcodes_carregados": 0}
        
        qrcodes_carregados = 0
        
        try:
            # Carrega QR codes
            qrcodes_path = data_dir / "qrcodes.json"
            if qrcodes_path.exists():
                qrcodes_data = self._load_json_file(qrcodes_path)
                if qrcodes_data:
                    for qrcode_data in qrcodes_data:
                        qrcode = self._process_qrcode(db, qrcode_data)
                        if qrcode:
                            qrcodes_carregados += 1
            
            return {"qrcodes_carregados": qrcodes_carregados}
        except Exception as e:
            self.logger.exception(f"Erro ao carregar QR codes: {str(e)}")
            return {"qrcodes_carregados": qrcodes_carregados}
    
    def _process_qrcode(self, db: Session, qrcode_data: Dict[str, Any]) -> Any:
        """
        Processa e insere um QR code no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            qrcode_data: Dados do QR code
            
        Returns:
            Objeto QRCode ou None em caso de erro
        """
        try:
            # Cria o QR code
            qrcode = self.qrcode_repository.create_qrcode(db, {
                "uuid": qrcode_data.get("uuid"),
                "target_type": qrcode_data.get("target_type", ""),
                "target_id": qrcode_data.get("target_id"),
                "action": qrcode_data.get("action", ""),
                "parameters": qrcode_data.get("parameters", {}),
                "access_requirements": qrcode_data.get("access_requirements", {}),
                "location_requirement": qrcode_data.get("location_requirement", {})
            })
            
            return qrcode
        except Exception as e:
            self.logger.error(f"Erro ao processar QR code: {str(e)}")
            return None