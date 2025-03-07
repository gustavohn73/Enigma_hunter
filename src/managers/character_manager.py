# src/managers/character_manager.py

import json
import logging
from typing import Dict, List, Any, Optional

import requests
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.db_models import DialogueHistory, PlayerCharacterLevel, PlayerSession
from src.repositories.character_repository import CharacterRepository

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
        ai_model: str = "llama3",
        api_url: str = "http://localhost:11434/api/generate"
    ):
        """
        Inicializa o gerenciador de personagens.
        
        Args:
            character_repository: Repositório para acesso aos dados de personagens
            ai_model: Modelo de IA a ser utilizado (padrão: llama3)
            api_url: URL da API do modelo de IA
        """
        self.character_repository = character_repository
        self.ai_model = ai_model
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        
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
    
    def get_player_character_level(self, db: Session, player_id: int, character_id: int) -> int:
        """
        Obtém o nível atual de interação entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            
        Returns:
            Nível atual do personagem para este jogador
        """
        # Busca o progresso do jogador com este personagem
        character_progress = db.query(PlayerCharacterLevel).filter_by(
            player_id=player_id,
            character_id=character_id
        ).first()
        
        # Se não há registro, o nível é 0 (inicial)
        if not character_progress:
            return 0
        
        return character_progress.current_level
    
    def update_character_level(self, db: Session, player_id: int, character_id: int, new_level: int) -> bool:
        """
        Atualiza o nível de interação entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            new_level: Novo nível
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            # Busca o progresso do jogador com este personagem
            character_progress = db.query(PlayerCharacterLevel).filter_by(
                player_id=player_id,
                character_id=character_id
            ).first()
            
            # Se não existe, cria um novo registro
            if not character_progress:
                character_progress = PlayerCharacterLevel(
                    player_id=player_id,
                    character_id=character_id,
                    current_level=new_level
                )
                db.add(character_progress)
            else:
                # Só atualiza se o novo nível for maior que o atual
                if new_level > character_progress.current_level:
                    character_progress.current_level = new_level
                    character_progress.last_interaction = func.now()
            
            db.commit()
            self.logger.info(f"Nível do personagem {character_id} para o jogador {player_id} atualizado para {new_level}")
            return True
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível: {e}")
            return False
    
    def get_dialogue_history(self, db: Session, player_id: int, character_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de diálogo entre um jogador e um personagem.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            limit: Número máximo de mensagens a retornar
            
        Returns:
            Lista de mensagens do histórico
        """
        # Obtém a sessão do jogador ativa
        player_session = db.query(PlayerSession).filter_by(
            player_id=player_id,
            game_status='active'
        ).order_by(PlayerSession.start_time.desc()).first()
        
        if not player_session:
            self.logger.warning(f"Sessão ativa não encontrada para o jogador {player_id}")
            return []
        
        # Busca o histórico de diálogo
        dialogue_history = db.query(DialogueHistory).filter_by(
            session_id=player_session.session_id,
            character_id=character_id
        ).order_by(DialogueHistory.timestamp.desc()).limit(limit).all()
        
        # Converte para o formato desejado
        history = []
        for entry in reversed(dialogue_history):  # Reverte para ordem cronológica
            if entry.player_statement:
                history.append({
                    "role": "user",
                    "content": entry.player_statement
                })
            if entry.character_response:
                history.append({
                    "role": "assistant",
                    "content": entry.character_response
                })
        
        return history
    
    def add_dialogue_entry(self, db: Session, player_id: int, character_id: int, player_statement: str, 
                          character_response: str, detected_keywords: List[str] = None) -> bool:
        """
        Adiciona uma entrada ao histórico de diálogo.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            player_statement: Mensagem do jogador
            character_response: Resposta do personagem
            detected_keywords: Palavras-chave detectadas na interação
            
        Returns:
            True se adicionado com sucesso, False caso contrário
        """
        try:
            # Obtém a sessão do jogador ativa
            player_session = db.query(PlayerSession).filter_by(
                player_id=player_id,
                game_status='active'
            ).order_by(PlayerSession.start_time.desc()).first()
            
            if not player_session:
                self.logger.warning(f"Sessão ativa não encontrada para o jogador {player_id}")
                return False
            
            # Obtém o nível atual do personagem para este jogador
            current_level = self.get_player_character_level(db, player_id, character_id)
            
            # Cria uma nova entrada no histórico
            dialogue_entry = DialogueHistory(
                session_id=player_session.session_id,
                character_id=character_id,
                player_statement=player_statement,
                character_response=character_response,
                detected_keywords=json.dumps(detected_keywords or []),
                character_level=current_level
            )
            
            db.add(dialogue_entry)
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar diálogo: {e}")
            return False
    
    def start_conversation(self, db: Session, player_id: int, character_id: int) -> Dict[str, Any]:
        """
        Inicia uma conversa com um personagem.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            
        Returns:
            Dicionário com a mensagem inicial e metadata
        """
        # Obtém os dados do personagem
        character_data = self.get_character(db, character_id)
        if not character_data:
            return {
                "success": False,
                "message": "Personagem não encontrado"
            }
        
        # Obtém o nível atual para este jogador
        current_level = self.get_player_character_level(db, player_id, character_id)
        
        # Obtém os dados do nível atual
        if current_level >= len(character_data["levels"]):
            current_level = len(character_data["levels"]) - 1
        
        level_data = character_data["levels"][current_level]
        
        # Gera uma mensagem inicial com base no nível
        initial_message = self._generate_initial_message(character_data, level_data)
        
        # Registra esta mensagem inicial no histórico
        self.add_dialogue_entry(
            db=db,
            player_id=player_id,
            character_id=character_id,
            player_statement="",  # Não há mensagem do jogador inicialmente
            character_response=initial_message
        )
        
        return {
            "success": True,
            "message": initial_message,
            "character_name": character_data["name"],
            "character_level": current_level
        }
    
    # Métodos privados para lógica interna
    
    def _generate_initial_message(self, character_data: Dict[str, Any], level_data: Dict[str, Any]) -> str:
        """
        Gera uma mensagem inicial para um personagem com base no seu nível.
        
        Args:
            character_data: Dados do personagem
            level_data: Dados do nível atual
            
        Returns:
            Mensagem inicial do personagem
        """
        # Em uma implementação completa, poderíamos ter mensagens iniciais específicas para cada nível
        # armazenadas no banco de dados. Por enquanto, usamos uma abordagem simples.
        
        character_name = character_data["name"]
        
        if level_data["is_defensive"]:
            return f"Olá. Sou {character_name}. O que você quer?"
        else:
            return f"Olá! Eu sou {character_name}. Como posso ajudá-lo?"
    
    def send_message(self, db: Session, player_id: int, character_id: int, message: str) -> Dict[str, Any]:
        """
        Envia uma mensagem a um personagem e processa sua resposta.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            message: Mensagem do jogador
            
        Returns:
            Dicionário com a resposta e metadados
        """
        # Obtém os dados do personagem
        character_data = self.get_character(db, character_id)
        if not character_data:
            return {
                "success": False,
                "message": "Personagem não encontrado"
            }
        
        # Obtém o nível atual para este jogador
        current_level = self.get_player_character_level(db, player_id, character_id)
        
        # Obtém os dados do nível atual
        if current_level >= len(character_data["levels"]):
            current_level = len(character_data["levels"]) - 1
        
        level_data = character_data["levels"][current_level]
        
        # Obtém o histórico de diálogo recente
        dialogue_history = self.get_dialogue_history(db, player_id, character_id)
        
        # Verifica se a mensagem ativa algum gatilho
        trigger_result = self._check_triggers(character_data, level_data, message)
        
        if trigger_result["triggered"]:
            # Processa a resposta de desafio
            defensive_response = trigger_result["defensive_response"]
            
            # Registra no histórico
            self.add_dialogue_entry(
                db=db,
                player_id=player_id,
                character_id=character_id,
                player_statement=message,
                character_response=defensive_response,
                detected_keywords=[trigger_result["keyword"]]
            )
            
            # Retorna a resposta com informações sobre o desafio
            return {
                "success": True,
                "message": defensive_response,
                "challenge_activated": True,
                "trigger_data": trigger_result["trigger_data"]
            }
        
        # Processamento normal da mensagem
        prompt = self._create_prompt(character_data, level_data, dialogue_history, message)
        
        # Envia o prompt para a IA
        ai_response = self._query_ai(prompt)
        
        # Limpa a resposta
        cleaned_response = self._clean_response(ai_response)
        
        # Registra a conversa no histórico
        self.add_dialogue_entry(
            db=db,
            player_id=player_id,
            character_id=character_id,
            player_statement=message,
            character_response=cleaned_response
        )
        
        # Extrai possíveis pistas reveladas
        revealed_clues = self._extract_clues(character_data, level_data, message, cleaned_response)
        
        result = {
            "success": True,
            "message": cleaned_response,
            "evolution": False
        }
        
        if revealed_clues:
            result["revealed_clues"] = revealed_clues
        
        return result
    
    def process_challenge_response(self, db: Session, player_id: int, character_id: int, challenge_id: int, 
                                  response: str, evidence_ids: List[int] = None) -> Dict[str, Any]:
        """
        Processa a resposta do jogador a um desafio de gatilho.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            character_id: ID do personagem
            challenge_id: ID do desafio/gatilho
            response: Resposta do jogador
            evidence_ids: IDs de evidências apresentadas
            
        Returns:
            Resultado do processamento do desafio
        """
        # Obtém o gatilho específico
        trigger = self.character_repository.get_trigger_by_id(db, challenge_id)
        
        if not trigger:
            return {
                "success": False,
                "message": "Desafio não encontrado"
            }
        
        # Obtém os requisitos para este gatilho
        requirements = self.character_repository.get_trigger_requirements(db, challenge_id)
        
        # Verifica se os requisitos foram atendidos
        requirements_met = True
        failed_requirement = None
        
        for req in requirements:
            # Verifica o tipo de requisito
            if req.requirement_type == "object" and evidence_ids:
                # Verifica se o objeto necessário foi apresentado
                required_object_id = json.loads(req.required_object_id) if isinstance(req.required_object_id, str) else req.required_object_id
                if required_object_id not in evidence_ids:
                    requirements_met = False
                    failed_requirement = req
                    break
            
            # Implementar outras verificações conforme necessário
            # (conhecimento, localização, etc.)
        
        # Determina o resultado
        if requirements_met:
            # Atualiza o nível do personagem
            current_level = self.get_player_character_level(db, player_id, character_id)
            new_level = current_level + 1
            self.update_character_level(db, player_id, character_id, new_level)
            
            # Registra o sucesso no histórico
            self.add_dialogue_entry(
                db=db,
                player_id=player_id,
                character_id=character_id,
                player_statement=response,
                character_response=trigger.success_response
            )
            
            return {
                "success": True,
                "message": trigger.success_response,
                "evolution": True,
                "new_level": new_level
            }
        else:
            # Registra a falha no histórico
            self.add_dialogue_entry(
                db=db,
                player_id=player_id,
                character_id=character_id,
                player_statement=response,
                character_response=trigger.fail_response
            )
            
            # Adiciona dica se disponível
            hint = failed_requirement.hint_if_incorrect if failed_requirement else None
            
            return {
                "success": False,
                "message": trigger.fail_response,
                "evolution": False,
                "hint": hint
            }
    
    # Resto dos métodos para verificação de gatilhos, criação de prompts, etc.
    # (Os métodos internos podem permanecer basicamente os mesmos)
    
    def _check_triggers(self, character_data: Dict[str, Any], level_data: Dict[str, Any], 
                      message: str) -> Dict[str, Any]:
        """
        Verifica se uma mensagem ativa algum gatilho.
        
        Args:
            character_data: Dados do personagem
            level_data: Dados do nível atual
            message: Mensagem do jogador
            
        Returns:
            Dicionário com informações sobre o gatilho ativado (se houver)
        """
        # Resultado padrão
        result = {
            "triggered": False,
            "defensive_response": "",
            "keyword": "",
            "trigger_data": None
        }
        
        # Obtém os gatilhos para este nível
        triggers = level_data.get("triggers", [])
        
        if not triggers:
            return result
        
        # Converte a mensagem para minúsculas para comparação
        message_lower = message.lower()
        
        # Verifica cada gatilho
        for trigger in triggers:
            keyword = trigger.get("trigger_keyword", "").lower()
            
            if keyword and keyword in message_lower:
                self.logger.info(f"Gatilho '{keyword}' detectado")
                
                # Em uma implementação completa, verificaríamos condições contextuais aqui
                
                result = {
                    "triggered": True,
                    "defensive_response": trigger.get("defensive_response", 
                        "Isso é um assunto delicado. Por que você quer saber sobre isso?"),
                    "keyword": keyword,
                    "trigger_data": trigger
                }
                
                return result
        
        return result
    
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
        personality = character_data["personality"]
        
        # Obtém dados específicos do nível
        knowledge_scope = level_data["knowledge_scope"]
        narrative_stance = level_data["narrative_stance"]
        is_defensive = level_data["is_defensive"]
        level_number = level_data["level_number"]
        
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
    
    def _extract_clues(self, character_data: Dict[str, Any], level_data: Dict[str, Any], 
                     user_message: str, ai_response: str) -> List[Dict[str, Any]]:
        """
        Extrai pistas da interação com o personagem.
        
        Args:
            character_data: Dados do personagem
            level_data: Dados do nível atual
            user_message: Mensagem do jogador
            ai_response: Resposta da IA
            
        Returns:
            Lista de pistas reveladas
        """
        # Em uma implementação completa, consultaríamos o banco de dados
        # para verificar pistas associadas a este personagem e nível
        # e usaríamos detecção de palavras-chave para determinar quais foram reveladas
        
        # Por enquanto, retornamos uma lista vazia
        return []