# src/managers/character_manager.py

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import traceback
import time

import requests
from sqlalchemy.orm import Session

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
        character_repository,
        dialogue_repository,
        ai_model: str = "llama3",
        api_url: str = "http://localhost:11434/api/generate",
        max_retries: int = 3,
        retry_delay: int = 2,
        timeout: int = 30
    ):
        """
        Inicializa o gerenciador de personagens.
        
        Args:
            character_repository: Repositório para acesso aos dados de personagens
            dialogue_repository: Repositório para acesso aos diálogos
            ai_model: Modelo de IA a ser utilizado (padrão: llama3)
            api_url: URL da API do modelo de IA
            max_retries: Número máximo de tentativas para conexão com a IA
            retry_delay: Tempo de espera entre tentativas em segundos
            timeout: Tempo limite para respostas da IA em segundos
        """
        self.character_repository = character_repository
        self.dialogue_repository = dialogue_repository
        self.ai_model = ai_model
        self.api_url = api_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        self.logger = logging.getLogger(__name__)
        self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Configura o logger com formato padrão se ainda não configurado."""
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
        try:
            return self.character_repository.get_character_with_levels(db, character_id)
        except Exception as e:
            self.logger.error(f"Erro ao obter dados do personagem {character_id}: {str(e)}")
            return None
    
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
            return self.character_repository.get_player_character_level(db, session_id, character_id)
        except Exception as e:
            self.logger.error(f"Erro ao obter nível do personagem {character_id}: {str(e)}")
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
            # Usar o repositório para atualizar o nível
            result = self.character_repository.update_player_character_level(
                db, session_id, character_id, new_level
            )
            
            if result:
                self.logger.info(f"Nível do personagem {character_id} atualizado para {new_level} (sessão {session_id})")
            
            return result
        except Exception as e:
            self.logger.error(f"Erro ao atualizar nível de personagem: {str(e)}")
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
            self.logger.error(f"Erro ao iniciar conversa: {str(e)}\n{traceback.format_exc()}")
            return {
                "success": False,
                "message": "Erro ao iniciar conversa. Por favor, tente novamente."
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
        
        # Verificar se há instruções específicas para o nível
        ia_instructions = level_data.get("ia_instruction_set", {})
        greeting = ia_instructions.get("greeting", "")
        
        if greeting:
            return greeting
            
        # Mensagem padrão baseada no comportamento defensivo
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
            trigger_result = self.dialogue_repository.check_trigger_activation(
                db, session_id, character_id, current_level, message
            )
            
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
                    character_level=current_level,
                    is_key_interaction=True
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
            ai_response = self._query_ai_with_retry(prompt)
            
            # Limpa a resposta
            cleaned_response = self._clean_response(ai_response)
            
            # Analisa o sentimento da resposta (opcional para implementação futura)
            # sentiment = self._analyze_sentiment(cleaned_response)
            
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
            self.logger.error(f"Erro ao processar mensagem: {str(e)}\n{traceback.format_exc()}")
            return {
                "success": False,
                "message": "Desculpe, tive um problema ao processar sua mensagem. Por favor, tente novamente."
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
            verification_result = self.dialogue_repository.verify_trigger_requirements(
                db=db,
                session_id=session_id,
                trigger_id=trigger_id,
                response=response,
                evidence_ids=evidence_ids or []
            )
            
            current_level = self.get_character_level(db, session_id, character_id)
            
            # Obtém o gatilho para respostas
            trigger = self.character_repository.get_trigger_by_id(db, trigger_id)
            
            if not trigger:
                return {
                    "success": False,
                    "message": "Gatilho não encontrado"
                }
            
            if verification_result["requirements_met"]:
                # Requisitos atendidos, personagem evolui
                new_level = current_level + 1
                
                # Atualiza o nível do personagem
                self.update_character_level(db, session_id, character_id, new_level)
                
                # Registra a evolução
                self.dialogue_repository.register_evolution(
                    db=db,
                    session_id=session_id,
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
                    character_level=current_level,
                    is_key_interaction=True
                )
                
                return {
                    "success": True,
                    "message": trigger.success_response,
                    "evolution": True,
                    "new_level": new_level
                }
            else:
                # Requisitos não atendidos                
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
                    "missing_requirements": verification_result["missing_requirements"]
                }
        except Exception as e:
            self.logger.error(f"Erro ao processar resposta ao desafio: {str(e)}\n{traceback.format_exc()}")
            return {
                "success": False,
                "message": "Houve um problema ao processar sua resposta. Por favor, tente novamente.",
                "evolution": False
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
        
        # Obtém instruções específicas para a IA neste nível
        ia_instructions = level_data.get("ia_instruction_set", {})
        instruction_details = ia_instructions.get("instructions", "")
        
        # Constrói o prompt
        prompt = f"""Você é {character_name}, {character_description}. Responda como ele.

CONTEXTO DO PERSONAGEM (NÍVEL {level_number}):
{knowledge_scope}

PERSONALIDADE:
{personality}

COMO SE COMPORTAR:
{narrative_stance}
"""
        
        if instruction_details:
            prompt += f"\nINSTRUÇÕES ESPECÍFICAS:\n{instruction_details}\n"
        
        if is_defensive:
            prompt += "Você deve ser defensivo e evasivo quando questionado diretamente.\n"
        else:
            prompt += "Você pode ser mais aberto e comunicativo.\n"
        
        prompt += f"""
INSTRUÇÕES GERAIS:
1. Mantenha-se fiel ao personagem e seu estágio atual de conhecimento.
2. Não revele informações além do que o personagem sabe no estágio atual.
3. Responda de forma natural e conversacional, mantendo o estilo de fala do personagem.
4. Suas respostas devem ter no máximo 3 parágrafos.
5. Não use expressões entre parênteses como (sorrindo) ou (pausa).
6. Não use marcações de ação como [ação] ou *ação*.
7. Não repita a mesma resposta que você já deu anteriormente.
8. Mantenha suas respostas concisas e diretas.

"""
        
        prompt += "\nHISTÓRICO DA CONVERSA:\n"
        
        # Adiciona o histórico ao prompt (limitado para evitar tokens excessivos)
        recent_history = dialogue_history[-10:] if len(dialogue_history) > 10 else dialogue_history
        for msg in recent_history:
            if msg["role"] == "user":
                prompt += f"\nJogador: {msg['content']}"
            else:
                prompt += f"\n{character_name}: {msg['content']}"
        
        # Adiciona a mensagem atual
        prompt += f"\nJogador: {user_message}\n\n{character_name}:"
        
        return prompt
    
    def _query_ai_with_retry(self, prompt: str) -> str:
        """
        Envia o prompt para a API de IA com sistema de retry.
        
        Args:
            prompt: Prompt formatado
            
        Returns:
            Resposta da IA ou mensagem de fallback em caso de falha
        """
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                return self._query_ai(prompt)
            except requests.RequestException as e:
                last_error = e
                retries += 1
                self.logger.warning(f"Tentativa {retries}/{self.max_retries} falhou: {str(e)}")
                
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)
            except Exception as e:
                self.logger.error(f"Erro inesperado ao consultar IA: {str(e)}")
                return self._get_fallback_response()
        
        self.logger.error(f"Todas as {self.max_retries} tentativas falharam. Último erro: {str(last_error)}")
        return self._get_fallback_response()
    
    def _query_ai(self, prompt: str) -> str:
        """
        Envia o prompt para a API de IA e obtém a resposta.
        
        Args:
            prompt: Prompt formatado
            
        Returns:
            Resposta da IA
        
        Raises:
            requests.RequestException: Erro na comunicação com a API
        """
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
        
        response = requests.post(self.api_url, json=payload, timeout=self.timeout)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            error_message = f"Erro na API da IA: {response.status_code} - {response.text}"
            self.logger.error(error_message)
            raise requests.RequestException(error_message)
    
    def _get_fallback_response(self) -> str:
        """
        Fornece uma resposta de fallback quando a IA falha.
        
        Returns:
            Mensagem de fallback
        """
        fallback_responses = [
            "Desculpe, preciso de um momento para organizar meus pensamentos...",
            "Hmm, deixe-me pensar sobre isso por um instante.",
            "Parece que tenho dificuldade em responder agora.",
            "Poderia reformular sua pergunta? Não entendi completamente."
        ]
        
        from random import choice
        return choice(fallback_responses)
    
    def _clean_response(self, response: str) -> str:
        """
        Limpa a resposta da IA, removendo artefatos indesejados.
        
        Args:
            response: Resposta original
            
        Returns:
            Resposta limpa
        """
        if not response:
            return ""
            
        # Lista de padrões a serem removidos
        patterns_to_remove = [
            r"\(.*?\)",  # Expressões entre parênteses: (sorrindo), (pausa)
            r"\[.*?\]",  # Expressões entre colchetes: [pensativo], [irritado]
            r"\*.*?\*",  # Expressões entre asteriscos: *sorri*, *suspira*
        ]
        
        cleaned_response = response
        
        # Remove padrões usando expressões regulares
        import re
        for pattern in patterns_to_remove:
            cleaned_response = re.sub(pattern, "", cleaned_response)
        
        # Remove linhas vazias extras
        cleaned_response = re.sub(r"\n\s*\n", "\n", cleaned_response)
        
        # Remove espaços duplicados
        cleaned_response = re.sub(r" +", " ", cleaned_response)
        
        # Remove espaços no início e fim
        cleaned_response = cleaned_response.strip()
        
        return cleaned_response
    
    def _analyze_content(self, response: str) -> Dict[str, Any]:
        """
        Analisa o conteúdo da resposta para detecção de elementos importantes.
        
        Args:
            response: Resposta do personagem
            
        Returns:
            Dicionário com análise do conteúdo
        """
        # Esta função poderia implementar análise mais avançada no futuro
        # como detecção de sentimento, palavras-chave, etc.
        return {
            "length": len(response),
            "words": len(response.split()),
            "contains_question": "?" in response
        }
    
    def get_character_context(self, db: Session, session_id: str, character_id: int) -> Dict[str, Any]:
        """
        Obtém o contexto completo de um personagem para o jogador, incluindo histórico e nível.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão
            character_id: ID do personagem
            
        Returns:
            Dicionário com o contexto completo
        """
        try:
            # Obtém dados do personagem
            character_data = self.get_character(db, character_id)
            if not character_data:
                return {"success": False, "message": "Personagem não encontrado"}
            
            # Obtém nível atual
            current_level = self.get_character_level(db, session_id, character_id)
            
            # Obtém histórico de diálogo
            dialogue_history = self.dialogue_repository.get_dialogue_history(db, session_id, character_id)
            
            # Obtém interações importantes
            key_interactions = self.dialogue_repository.get_key_interactions(db, session_id, character_id)
            
            return {
                "success": True,
                "character": {
                    "id": character_id,
                    "name": character_data["name"],
                    "description": character_data["base_description"],
                    "current_level": current_level
                },
                "dialogue_history": dialogue_history,
                "key_interactions": [
                    {
                        "timestamp": interaction.timestamp,
                        "player_statement": interaction.player_statement,
                        "character_response": interaction.character_response
                    } for interaction in key_interactions
                ],
                "total_interactions": len(dialogue_history)
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter contexto do personagem: {str(e)}")
            return {"success": False, "message": "Erro ao obter contexto do personagem"}