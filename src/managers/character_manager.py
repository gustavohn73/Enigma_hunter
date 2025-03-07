# src/managers/character_manager.py

import json
import logging
from typing import Dict, List, Any, Optional

import requests
from sqlalchemy.orm import Session

from src.repositories.character_repository import CharacterRepository
from src.repositories.dialogue_repository import DialogueRepository
from src.models.db_models import PlayerCharacterLevel, Character, CharacterLevel, EvolutionTrigger

logger = logging.getLogger(__name__)

class CharacterManager:
    """
    Gerenciador de personagens para o sistema Enigma Hunter.
    
    Responsável por:
    - Gerenciar diálogos com os personagens usando IA
    - Controlar a evolução dos personagens com base nas interações
    - Processar gatilhos para revelação de informações
    - Persistir o histórico de diálogos e estado dos personagens
    """
    
    def __init__(
        self,
        character_repository: CharacterRepository,
        dialogue_repository: DialogueRepository,
        ai_model: str = "llama3",
        api_url: str = "http://localhost:11434/api/generate"
    ):
        """
        Inicializa o gerenciador de personagens.
        
        Args:
            character_repository: Repositório para acesso aos dados de personagens
            dialogue_repository: Repositório para acesso aos diálogos
            ai_model: Modelo de IA a ser utilizado (padrão: llama3)
            api_url: URL da API do modelo de IA
        """
        self.character_repository = character_repository
        self.dialogue_repository = dialogue_repository
        self.ai_model = ai_model
        self.api_url = api_url
        self.logger = logger
        
        # Configuração do logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def get_character(self, db: Session, character_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém os dados de um personagem.
        
        Args:
            db: Sessão do banco de dados
            character_id: ID do personagem
            
        Returns:
            Dados do personagem ou None se não encontrado
        """
        return self.character_repository.get_character_with_levels(db, character_id)
    
    def get_character_level(self, db: Session, session_id: str, character_id: int) -> int:
        """
        Obtém o nível atual de interação entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            
        Returns:
            Nível atual do personagem para esta sessão
        """
        try:
            # Busca o progresso do personagem para esta sessão
            character_level = db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id,
                PlayerCharacterLevel.character_id == character_id
            ).first()
            
            # Se não há registro, o nível é 0 (inicial)
            if not character_level:
                return 0
            
            return character_level.current_level
        except Exception as e:
            self.logger.error(f"Erro ao obter nível do personagem: {str(e)}")
            return 0
    
    def update_character_level(self, db: Session, session_id: str, character_id: int, new_level: int) -> bool:
        """
        Atualiza o nível de interação entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            new_level: Novo nível
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            # Busca o progresso com este personagem
            character_level = db.query(PlayerCharacterLevel).filter(
                PlayerCharacterLevel.session_id == session_id,
                PlayerCharacterLevel.character_id == character_id
            ).first()
            
            # Se não existe, cria um novo registro
            if not character_level:
                character_level = PlayerCharacterLevel(
                    session_id=session_id,
                    character_id=character_id,
                    current_level=new_level
                )
                db.add(character_level)
            else:
                # Só atualiza se o novo nível for maior que o atual
                if new_level > character_level.current_level:
                    character_level.current_level = new_level
            
            db.commit()
            self.logger.info(f"Nível do personagem {character_id} para a sessão {session_id} atualizado para {new_level}")
            return True
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível: {e}")
            return False
    
    def start_conversation(self, db: Session, session_id: str, character_id: int) -> Dict[str, Any]:
        """
        Inicia uma conversa com um personagem.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            
        Returns:
            Dicionário com a mensagem inicial e metadata
        """
        try:
            # Obtém os dados do personagem
            character_data = self.get_character(db, character_id)
            if not character_data:
                return {
                    "success": False,
                    "message": "Personagem não encontrado"
                }
            
            # Obtém o nível atual para esta sessão
            current_level = self.get_character_level(db, session_id, character_id)
            
            # Obtém os dados do nível atual
            if current_level >= len(character_data["levels"]):
                current_level = len(character_data["levels"]) - 1
            
            level_data = character_data["levels"][current_level]
            
            # Gera uma mensagem inicial com base no nível
            initial_message = self._generate_initial_message(character_data, level_data)
            
            # Registra esta mensagem inicial no histórico
            self.dialogue_repository.add_dialogue_entry(
                db=db,
                session_id=session_id,
                character_id=character_id,
                player_statement="",  # Não há mensagem do jogador inicialmente
                character_response=initial_message,
                character_level=current_level
            )
            
            return {
                "success": True,
                "message": initial_message,
                "character_name": character_data["name"],
                "character_level": current_level
            }
        except Exception as e:
            self.logger.error(f"Erro ao iniciar conversa: {str(e)}")
            return {
                "success": False,
                "message": f"Erro ao iniciar conversa: {str(e)}"
            }
    
    def _generate_initial_message(self, character_data: Dict[str, Any], level_data: Dict[str, Any]) -> str:
        """
        Gera uma mensagem inicial para um personagem com base no seu nível.
        
        Args:
            character_data: Dados do personagem
            level_data: Dados do nível atual
            
        Returns:
            Mensagem inicial do personagem
        """
        character_name = character_data["name"]
        
        if level_data.get("is_defensive", False):
            return f"Olá. Sou {character_name}. O que você quer?"
        else:
            return f"Olá! Eu sou {character_name}. Como posso ajudá-lo?"
    
    def send_message(self, db: Session, session_id: str, character_id: int, message: str) -> Dict[str, Any]:
        """
        Envia uma mensagem a um personagem e processa sua resposta.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            message: Mensagem do jogador
            
        Returns:
            Dicionário com a resposta e metadados
        """
        try:
            # Obtém os dados do personagem
            character_data = self.get_character(db, character_id)
            if not character_data:
                return {
                    "success": False,
                    "message": "Personagem não encontrado"
                }
            
            # Obtém o nível atual para esta sessão
            current_level = self.get_character_level(db, session_id, character_id)
            
            # Obtém os dados do nível atual
            if current_level >= len(character_data["levels"]):
                current_level = len(character_data["levels"]) - 1
            
            level_data = character_data["levels"][current_level]
            
            # Obtém o histórico de diálogo recente
            dialogue_history = self.dialogue_repository.get_dialogue_history(db, session_id, character_id)
            
            # Verifica se a mensagem ativa algum gatilho
            trigger_result = self._check_triggers(db, session_id, character_id, message)
            
            if trigger_result["triggered"]:
                # Processa a resposta de desafio
                defensive_response = trigger_result["defensive_response"]
                
                # Registra no histórico
                self.dialogue_repository.add_dialogue_entry(
                    db=db,
                    session_id=session_id,
                    character_id=character_id,
                    player_statement=message,
                    character_response=defensive_response,
                    detected_keywords=[trigger_result["keyword"]],
                    character_level=current_level
                )
                
                # Retorna a resposta com informações sobre o desafio
                return {
                    "success": True,
                    "message": defensive_response,
                    "challenge_activated": True,
                    "trigger_id": trigger_result["trigger_id"],
                    "challenge_question": trigger_result.get("challenge_question", "")
                }
            
            # Processamento normal da mensagem
            prompt = self._create_prompt(character_data, level_data, dialogue_history, message)
            
            # Envia o prompt para a IA
            ai_response = self._query_ai(prompt)
            
            # Limpa a resposta
            cleaned_response = self._clean_response(ai_response)
            
            # Registra a conversa no histórico
            self.dialogue_repository.add_dialogue_entry(
                db=db,
                session_id=session_id,
                character_id=character_id,
                player_statement=message,
                character_response=cleaned_response,
                character_level=current_level
            )
            
            return {
                "success": True,
                "message": cleaned_response,
                "evolution": False
            }
        except Exception as e:
            self.logger.error(f"Erro ao processar mensagem: {str(e)}")
            return {
                "success": False,
                "message": f"Erro ao processar mensagem: {str(e)}"
            }
    
    def process_challenge_response(self, db: Session, session_id: str, character_id: int, 
                                 trigger_id: int, response: str, 
                                 evidence_ids: List[int] = None) -> Dict[str, Any]:
        """
        Processa a resposta do jogador a um desafio de gatilho.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            trigger_id: ID do gatilho/desafio
            response: Resposta do jogador
            evidence_ids: IDs de evidências apresentadas
            
        Returns:
            Resultado do processamento do desafio
        """
        try:
            # Verifica os requisitos do gatilho
            requirements_check = self.dialogue_repository.check_evolution_requirements(
                db=db,
                player_id=session_id,  # Usando session_id aqui
                trigger_id=trigger_id
            )
            
            current_level = self.get_character_level(db, session_id, character_id)
            
            if requirements_check["met"]:
                # Requisitos atendidos, personagem evolui
                new_level = current_level + 1
                
                # Obtém dados do gatilho para resposta de sucesso
                trigger = db.query(EvolutionTrigger).filter(
                    EvolutionTrigger.trigger_id == trigger_id
                ).first()
                
                if not trigger:
                    return {
                        "success": False,
                        "message": "Gatilho não encontrado"
                    }
                
                # Atualiza o nível do personagem
                self.update_character_level(db, session_id, character_id, new_level)
                
                # Registra a evolução
                self.dialogue_repository.register_evolution(
                    db=db,
                    player_id=session_id,  # Usando session_id aqui
                    character_id=character_id,
                    trigger_id=trigger_id,
                    old_level=current_level,
                    new_level=new_level
                )
                
                # Registra a resposta ao desafio
                self.dialogue_repository.add_dialogue_entry(
                    db=db,
                    session_id=session_id,
                    character_id=character_id,
                    player_statement=response,
                    character_response=trigger.success_response,
                    character_level=current_level
                )
                
                return {
                    "success": True,
                    "message": trigger.success_response,
                    "evolution": True,
                    "new_level": new_level
                }
            else:
                # Requisitos não atendidos
                trigger = db.query(EvolutionTrigger).filter(
                    EvolutionTrigger.trigger_id == trigger_id
                ).first()
                
                if not trigger:
                    return {
                        "success": False,
                        "message": "Gatilho não encontrado"
                    }
                
                # Registra a resposta ao desafio
                self.dialogue_repository.add_dialogue_entry(
                    db=db,
                    session_id=session_id,
                    character_id=character_id,
                    player_statement=response,
                    character_response=trigger.fail_response,
                    character_level=current_level
                )
                
                return {
                    "success": False,
                    "message": trigger.fail_response,
                    "evolution": False,
                    "missing_requirements": requirements_check["missing"]
                }
        except Exception as e:
            self.logger.error(f"Erro ao processar resposta ao desafio: {str(e)}")
            return {
                "success": False,
                "message": f"Erro ao processar resposta: {str(e)}",
                "evolution": False
            }
    
    def _check_triggers(self, db: Session, session_id: str, character_id: int, 
                      message: str) -> Dict[str, Any]:
        """
        Verifica se uma mensagem ativa algum gatilho.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            message: Mensagem do jogador
            
        Returns:
            Dicionário com informações sobre o gatilho ativado (se houver)
        """
        try:
            # Verifica os gatilhos através do DialogueRepository
            triggers = self.dialogue_repository.check_triggers(db, session_id, character_id, message)
            
            if not triggers:
                return {
                    "triggered": False,
                    "defensive_response": "",
                    "keyword": "",
                    "trigger_id": None
                }
            
            # Obtém o primeiro gatilho ativado
            trigger = triggers[0]
            
            return {
                "triggered": True,
                "defensive_response": trigger.get("defensive_response", "Interessante... Por que você pergunta isso?"),
                "keyword": trigger.get("keyword", ""),
                "trigger_id": trigger.get("trigger_id"),
                "challenge_question": trigger.get("challenge_question", "")
            }
        except Exception as e:
            self.logger.error(f"Erro ao verificar gatilhos: {str(e)}")
            return {
                "triggered": False,
                "defensive_response": "",
                "keyword": "",
                "trigger_id": None
            }
    
    def _create_prompt(self, character_data: Dict[str, Any], level_data: Dict[str, Any], 
                     dialogue_history: List[Dict[str, str]], user_message: str) -> str:
        """
        Cria o prompt para o modelo de IA.
        
        Args:
            character_data: Dados do personagem
            level_data: Dados do nível atual
            dialogue_history: Histórico de diálogo
            user_message: Mensagem do jogador
            
        Returns:
            Prompt formatado
        """
        # Obtém dados do personagem
        character_name = character_data["name"]
        character_description = character_data["base_description"]
        personality = character_data.get("personality", "")
        
        # Obtém dados específicos do nível
        knowledge_scope = level_data.get("knowledge_scope", "")
        narrative_stance = level_data.get("narrative_stance", "")
        is_defensive = level_data.get("is_defensive", False)
        level_number = level_data.get("level_number", 0)
        
        # Constrói o prompt
        prompt = f"""Você é {character_name}, {character_description}. Responda como ele.

CONTEXTO DO PERSONAGEM (NÍVEL {level_number}):
{knowledge_scope}

PERSONALIDADE:
{personality}

COMO SE COMPORTAR:
{narrative_stance}
"""
        
        if is_defensive:
            prompt += "Você deve ser defensivo e evasivo quando questionado diretamente.\n"
        else:
            prompt += "Você pode ser mais aberto e comunicativo.\n"
        
        prompt += f"""
INSTRUÇÕES ESPECIAIS:
1. Mantenha-se fiel ao personagem e seu estágio atual de conhecimento.
2. Não revele informações além do que o personagem sabe no estágio atual.
3. Responda de forma natural e conversacional, mantendo o estilo de fala do personagem.
4. Suas respostas devem ter no máximo 3 parágrafos.
5. Não use expressões entre parênteses como (sorrindo) ou (pausa) ou [ação].
6. Não repita a mesma resposta que você já deu anteriormente.

"""
        
        prompt += "\nHISTÓRICO DA CONVERSA:\n"
        
        # Adiciona o histórico ao prompt
        for msg in dialogue_history:
            if msg["role"] == "user":
                prompt += f"\nJogador: {msg['content']}"
            else:
                prompt += f"\n{character_name}: {msg['content']}"
        
        # Adiciona a mensagem atual
        prompt += f"\nJogador: {user_message}\n\n{character_name}:"
        
        return prompt
    
    def _query_ai(self, prompt: str) -> str:
        """
        Envia o prompt para a API de IA e obtém a resposta.
        
        Args:
            prompt: Prompt formatado
            
        Returns:
            Resposta da IA
        """
        try:
            payload = {
                "model": self.ai_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }
            
            response = requests.post(self.api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Não consegui processar sua pergunta.")
            else:
                self.logger.error(f"Erro na API da IA: {response.status_code} - {response.text}")
                return "Desculpe, ocorreu um erro na comunicação."
                
        except requests.RequestException as e:
            self.logger.error(f"Erro ao consultar IA: {e}")
            return "Desculpe, ocorreu um erro de conexão com o sistema de IA."
        except Exception as e:
            self.logger.error(f"Erro inesperado ao consultar IA: {e}")
            return "Ocorreu um erro inesperado no processamento da sua pergunta."
    
    def _clean_response(self, response: str) -> str:
        """
        Limpa a resposta da IA, removendo artefatos indesejados.
        
        Args:
            response: Resposta original
            
        Returns:
            Resposta limpa
        """
        # Lista de padrões a serem removidos
        patterns_to_remove = [
            "(Evita a resposta directa e muda o assunto)",
            "(sorrindo)",
            "(rindo)",
            "(pausa)",
            "(olha fixo em frente)",
            "[Seu rosto endurece momentaneamente]",
            "[Seu sorriso falha brevemente]",
            "[Após um longo silêncio, seu rosto assume uma expressão fria e calculista]",
            "[Com amargura crescente]",
            "[Recuperando parte de sua compostura]"
        ]
        
        cleaned_response = response
        for pattern in patterns_to_remove:
            cleaned_response = cleaned_response.replace(pattern, "")
        
        # Remove linhas vazias extras e espaços duplicados
        cleaned_response = " ".join(cleaned_response.split())
        
        return cleaned_response