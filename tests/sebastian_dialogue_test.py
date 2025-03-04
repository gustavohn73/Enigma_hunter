import json
import requests
import time
from typing import Dict, List, Any, Optional, Set

class PlayerInventory:
    """Classe simples para simular o inventário do jogador"""
    
    def __init__(self):
        self.collected_items = set()
        self.npc_interactions = {}  # NPC_id -> nível de interação
        self.knowledge = set()  # Conhecimentos específicos adquiridos
    
    def add_item(self, item_id: int, item_name: str) -> None:
        """Adiciona um item ao inventário"""
        self.collected_items.add(item_id)
        print(f"Item adicionado ao inventário: {item_name} (ID: {item_id})")
    
    def has_item(self, item_id: int) -> bool:
        """Verifica se o jogador possui um item específico"""
        return item_id in self.collected_items
    
    def add_knowledge(self, knowledge_id: str) -> None:
        """Adiciona um conhecimento específico"""
        self.knowledge.add(knowledge_id)
        print(f"Novo conhecimento adquirido: {knowledge_id}")
    
    def has_knowledge(self, knowledge_id: str) -> bool:
        """Verifica se o jogador possui um conhecimento específico"""
        return knowledge_id in self.knowledge
    
    def record_npc_interaction(self, npc_id: int, level: int) -> None:
        """Registra interação com um NPC"""
        self.npc_interactions[npc_id] = max(level, self.npc_interactions.get(npc_id, 0))
    
    def get_npc_level(self, npc_id: int) -> int:
        """Obtém o nível de interação com um NPC"""
        return self.npc_interactions.get(npc_id, 0)


class SimpleCharacterManager:
    """
    Versão simplificada do GerenciadorPersonagens para testar diálogos
    com personagens do Enigma Hunter.
    """
    
    def __init__(self, model: str = "llama3", api_url: str = "http://localhost:11434/api/generate"):
        """
        Inicializa o gerenciador simplificado.
        
        Args:
            model: O modelo de IA a ser utilizado (padrão: llama3)
            api_url: URL da API do Ollama
        """
        self.model = model
        self.api_url = api_url
        self.conversation_history = []
        self.character_data = None
        self.current_level = 0
        self.last_response = ""
        self.inventory = PlayerInventory()
        self.challenge_mode = False
        self.current_challenge = None
        
    def load_character(self, character_data_file: str) -> bool:
        """
        Carrega os dados de um personagem a partir de um arquivo JSON.
        
        Args:
            character_data_file: Caminho para o arquivo com dados do personagem
            
        Returns:
            True se o carregamento foi bem-sucedido, False caso contrário
        """
        try:
            with open(character_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Assumimos que o arquivo contém uma lista de personagens
                # e queremos o primeiro
                if isinstance(data, list) and len(data) > 0:
                    self.character_data = data[0]
                else:
                    self.character_data = data
                
                print(f"Personagem carregado: {self.character_data.get('name')}")
                return True
        except Exception as e:
            print(f"Erro ao carregar dados do personagem: {e}")
            return False
    
    def get_character_level(self) -> int:
        """Retorna o nível atual do personagem."""
        return self.current_level
    
    def set_character_level(self, level: int) -> None:
        """Define o nível do personagem para testes."""
        if level >= 0 and level < len(self.character_data.get('levels', [])):
            self.current_level = level
            print(f"Nível do personagem definido para: {level}")
        else:
            print(f"Nível inválido. O personagem tem {len(self.character_data.get('levels', []))} níveis (0-{len(self.character_data.get('levels', [])) - 1})")
    
    def start_conversation(self) -> str:
        """
        Inicia uma nova conversa com o personagem.
        
        Returns:
            Mensagem inicial do personagem
        """
        self.conversation_history = []
        
        # Gerar uma mensagem inicial baseada no nível atual
        greeting = f"Olá, eu sou {self.character_data.get('name')}. Como posso ajudá-lo?"
        
        # Adicionar a mensagem ao histórico
        self.conversation_history.append({"role": "assistant", "content": greeting})
        self.last_response = greeting
        
        return greeting
    
    def send_message(self, message: str) -> Dict[str, Any]:
        """
        Envia uma mensagem ao personagem e recebe sua resposta.
        
        Args:
            message: A mensagem do jogador
            
        Returns:
            Dicionário contendo a resposta e informações sobre evolução
        """
        if not self.character_data:
            return {"response": "Erro: Personagem não carregado", "evolution": False}
        
        # Adicionar mensagem do jogador ao histórico
        self.conversation_history.append({"role": "user", "content": message})
        
        # Verificar se estamos em modo de desafio
        if self.challenge_mode and self.current_challenge:
            # Verificar se a resposta do jogador satisfaz o desafio
            challenge_result = self._evaluate_challenge_response(message)
            
            if challenge_result["success"]:
                # Desafio superado, evoluir personagem
                new_level = self.current_level + 1
                self.current_level = new_level
                
                # Resetar modo de desafio
                self.challenge_mode = False
                self.current_challenge = None
                
                # Criar resposta de sucesso específica do gatilho
                trigger_response = challenge_result["trigger_response"]
                
                # Adicionar resposta ao histórico
                self.conversation_history.append({"role": "assistant", "content": trigger_response})
                self.last_response = trigger_response
                
                return {
                    "response": trigger_response,
                    "evolution": True,
                    "new_level": new_level
                }
            else:
                # Desafio falhou, criar resposta de falha
                fail_response = challenge_result["fail_response"]
                
                # Adicionar resposta ao histórico
                self.conversation_history.append({"role": "assistant", "content": fail_response})
                self.last_response = fail_response
                
                return {
                    "response": fail_response,
                    "evolution": False,
                    "new_level": self.current_level
                }
        
        # Processamento normal da mensagem
        # Obter os dados do nível atual
        level_data = self.character_data.get('levels', [])[self.current_level]
        
        # Verificar se a mensagem ativa algum gatilho
        trigger_check = self._check_triggers(message)
        
        if trigger_check["triggered"]:
            # Se um gatilho foi ativado, entrar em modo de desafio
            self.challenge_mode = True
            self.current_challenge = trigger_check["challenge"]
            
            # Criar resposta de desafio
            challenge_response = trigger_check["defensive_response"]
            
            # Adicionar resposta ao histórico
            self.conversation_history.append({"role": "assistant", "content": challenge_response})
            self.last_response = challenge_response
            
            return {
                "response": challenge_response,
                "evolution": False,
                "new_level": self.current_level,
                "challenge_activated": True
            }
        
        # Se nenhum gatilho foi ativado, processamento normal
        # Criar o prompt para a IA
        prompt = self._create_prompt(message, level_data)
        
        # Obter resposta da IA
        ai_response = self._query_ai(prompt)
        
        # Remover possíveis instruções que vazaram
        ai_response = self._clean_response(ai_response)
        
        # Adicionar resposta ao histórico
        self.conversation_history.append({"role": "assistant", "content": ai_response})
        self.last_response = ai_response
        
        # Limitar o tamanho do histórico
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return {
            "response": ai_response,
            "evolution": False,
            "new_level": self.current_level
        }
    
    def _clean_response(self, response: str) -> str:
        """
        Limpa a resposta de possíveis instruções que vazaram.
        
        Args:
            response: Resposta original da IA
            
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
        
        # Remover linhas vazias extras e espaços duplicados
        cleaned_response = " ".join(cleaned_response.split())
        
        return cleaned_response
    
    def _create_prompt(self, user_message: str, level_data: Dict[str, Any], for_evolution: bool = False) -> str:
        """
        Cria o prompt para enviar ao modelo de IA.
        
        Args:
            user_message: Mensagem do usuário
            level_data: Dados do nível atual do personagem
            for_evolution: Se o prompt é para resposta após evolução
            
        Returns:
            Prompt formatado
        """
        # Informações do personagem no nível atual
        character_name = self.character_data.get('name', 'Personagem')
        character_description = self.character_data.get('base_description', '')
        personality = self.character_data.get('personality', '')
        knowledge_scope = level_data.get('knowledge_scope', '')
        narrative_stance = level_data.get('narrative_stance', '')
        is_defensive = level_data.get('is_defensive', False)
        
        # Construir o prompt
        prompt = f"""Você é {character_name}, {character_description}. Responda como ele.

CONTEXTO DO PERSONAGEM (NÍVEL {self.current_level}):
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
        
        if for_evolution:
            prompt += """
IMPORTANTE: Você acabou de evoluir para um novo nível. Sua resposta deve refletir seu novo conhecimento e postura.
Responda de maneira diferente do que você responderia no nível anterior.
"""
        
        prompt += "\nHISTÓRICO DA CONVERSA:\n"
        
        # Adicionar o histórico recente da conversa
        for idx, msg in enumerate(self.conversation_history[-10:]):
            if msg["role"] == "user":
                prompt += f"\nJogador: {msg['content']}"
            else:
                prompt += f"\n{character_name}: {msg['content']}"
        
        # Adicionar a nova mensagem do usuário
        prompt += f"\nJogador: {user_message}\n\n{character_name}:"
        
        return prompt
    
    def _query_ai(self, prompt: str) -> str:
        """
        Envia o prompt para a API do Ollama e retorna a resposta.
        
        Args:
            prompt: Prompt formatado
            
        Returns:
            Resposta gerada pela IA
        """
        try:
            # Para testes, você pode comentar este bloco e usar respostas simuladas
            # se não tiver acesso ao Ollama/llama3
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }
            
            response = requests.post(self.api_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Não consegui processar sua pergunta.")
            else:
                print(f"Erro na API do Ollama: {response.status_code} - {response.text}")
                return "Desculpe, ocorreu um erro na comunicação."
                
        except requests.RequestException as e:
            print(f"Erro ao consultar IA: {e}")
            
            # Resposta simulada para teste quando a API não está disponível
            return self._simulate_response(prompt)
    
    def _simulate_response(self, prompt: str) -> str:
        """
        Simula uma resposta para quando a API não está disponível.
        Isso é útil para testes sem depender da API do Ollama.
        
        Args:
            prompt: Prompt enviado
            
        Returns:
            Resposta simulada
        """
        # Determinar qual nível estamos simulando
        responses = [
            # Nível 0
            "É um prazer conhecê-lo. Sou apenas um contador que frequenta a estalagem regularmente. Não tenho conhecimento específico sobre o que aconteceu com Thaddeus, além do que todos já sabem. Foi uma pena, ele parecia um homem de negócios respeitável.",
            
            # Nível 1
            "Conheço um pouco sobre botânica, sim, é um hobby que cultivo há algum tempo. O senhor Thaddeus e eu tínhamos alguns interesses em comum, principalmente relacionados a documentos históricos da região. É uma área fascinante, não concorda?",
            
            # Nível 2
            "Acho que está fazendo perguntas bastante específicas. Sim, estive na biblioteca pesquisando documentos antigos, mas isso não é nenhum crime, é? Tenho interesse legítimo na história local. Agora, se me dá licença, tenho assuntos a resolver.",
            
            # Nível 3
            "Muito bem, você descobriu. Sou o último descendente da família Reed e aquela escritura é legitimamente minha. Os Ironwood roubaram nossas terras através de manipulações legais. Thaddeus descobriu a verdade e ia destruir a evidência. Eu apenas fiz justiça."
        ]
        
        # Adicionar um atraso simulado para imitar o tempo de resposta da IA
        time.sleep(1.5)
        
        # Retornar resposta apropriada ao nível
        if self.current_level < len(responses):
            return responses[self.current_level]
        return "Não sei como responder a isso."
    
    def _check_triggers(self, user_message: str) -> Dict[str, Any]:
        """
        Verifica se a mensagem ativa algum gatilho de desafio.
        
        Args:
            user_message: Mensagem do usuário
            
        Returns:
            Dicionário com informações sobre o gatilho ativado
        """
        # Obtém os gatilhos do nível atual
        level_data = self.character_data.get('levels', [])[self.current_level]
        triggers = level_data.get('triggers', [])
        
        result = {
            "triggered": False,
            "challenge": None,
            "defensive_response": ""
        }
        
        if not triggers:
            return result
        
        user_message_lower = user_message.lower()
        
        # Verificar cada gatilho
        for trigger in triggers:
            keyword = trigger.get('trigger_keyword', '').lower()
            
            # Verificar se a palavra-chave está presente na mensagem
            if keyword and keyword in user_message_lower:
                # Palavra-chave detectada, verificar o contexto
                context_condition = trigger.get('contextual_condition', '')
                print(f"Gatilho potencial detectado: '{keyword}'")
                print(f"Condição contextual: {context_condition}")
                
                # Em um sistema real, verificaríamos aqui se o contexto 
                # da mensagem corresponde à condição contextual.
                # Para este teste simplificado, vamos apenas ativar o desafio.
                
                result["triggered"] = True
                result["challenge"] = trigger
                result["defensive_response"] = trigger.get('defensive_response', 
                    "Isso é um assunto delicado. Por que você quer saber sobre isso?")
                
                return result
        
        return result
    
    def _evaluate_challenge_response(self, user_message: str) -> Dict[str, Any]:
        """
        Avalia a resposta do jogador ao desafio.
        
        Args:
            user_message: Mensagem de resposta do jogador ao desafio
            
        Returns:
            Dicionário com resultado da avaliação
        """
        if not self.current_challenge:
            return {
                "success": False,
                "fail_response": "Não há desafio ativo."
            }
        
        # Em um sistema real, aqui verificaríamos os requisitos específicos.
        # No nosso teste simplificado, vamos apresentar um mini-inventário virtual
        requirements = self.current_challenge.get('requirements', [])
        
        # Verificar cada requisito
        for req in requirements:
            req_type = req.get('requirement_type', '')
            
            # Verificar tipo de requisito
            if req_type == 'knowledge':
                # Verificar se o jogador menciona conhecimento específico
                knowledge_text = user_message.lower()
                req_object_id = req.get('required_object_id')
                
                # Para teste, verificar se a resposta menciona alguma palavra-chave
                # relacionada ao "Suspiro da Viúva"
                knowledge_keywords = ['suspiro', 'viúva', 'planta', 'veneno', 'tóxico']
                
                # Verificar se alguma palavra-chave está presente
                has_knowledge = any(kw in knowledge_text for kw in knowledge_keywords)
                
                # Aqui, em um sistema real, verificaríamos se o jogador tem 
                # o conhecimento no seu inventário. Para o teste, verificamos
                # apenas se ele mencionou as palavras-chave.
                
                if has_knowledge:
                    print(f"Conhecimento verificado com sucesso: {req_object_id}")
                    return {
                        "success": True,
                        "trigger_response": self.current_challenge.get('success_response', 
                            "Você está certo. Tenho conhecimento botânico, sim...")
                    }
                
            elif req_type == 'document' or req_type == 'object':
                # Verificar se o jogador tem documento/objeto específico
                # No teste atual, isso será simulado pelo "inventário virtual"
                
                # Verificar menção a documentos/mapa/escritura
                object_keywords = ['mapa', 'documento', 'escritura', 'registro', 'prova']
                has_object = any(kw in user_message.lower() for kw in object_keywords)
                
                if has_object:
                    # Para o teste, aceitamos qualquer menção aos objetos
                    print(f"Objeto verificado com sucesso: {req.get('required_object_id')}")
                    return {
                        "success": True,
                        "trigger_response": self.current_challenge.get('success_response', 
                            "Você encontrou evidências importantes...")
                    }
            
            # Outros tipos de requisitos podem ser adicionados aqui
        
        # Se chegamos aqui, nenhum requisito foi atendido
        return {
            "success": False,
            "fail_response": self.current_challenge.get('fail_response', 
                "Não vejo como isso é relevante para nossa conversa.")
        }
    
    def add_to_inventory(self, item_id: int, name: str) -> None:
        """Adiciona um item ao inventário do jogador"""
        self.inventory.add_item(item_id, name)
    
    def add_knowledge(self, knowledge_id: str) -> None:
        """Adiciona um conhecimento ao inventário do jogador"""
        self.inventory.add_knowledge(knowledge_id)


def run_dialogue_test():
    """Função principal para testar o diálogo com Sebastian Reed."""
    
    print("=== TESTE DE DIÁLOGO COM SEBASTIAN REED ===")
    
    # Inicializar o gerenciador
    manager = SimpleCharacterManager()
    
    # Carregar os dados do personagem
    if not manager.load_character('Personagem_2.json'):
        print("Erro ao carregar dados do personagem. Verifique se o arquivo existe.")
        return
    
    # Iniciar conversa
    greeting = manager.start_conversation()
    print(f"Sebastian: {greeting}")
    
    # Adicionar alguns itens virtuais ao inventário para teste
    # Isto seria feito pelo jogador ao explorar o ambiente
    manager.add_to_inventory(3, "Frasco de Veneno 'Suspiro da Viúva'")
    manager.add_to_inventory(6, "Mapa Antigo de Ravenshire")
    manager.add_knowledge("suspiro_da_viuva")
    
    print("\nVocê está conversando com Sebastian Reed (Nível 0)")
    print("Digite 'sair' para encerrar, 'ajuda' para ver comandos adicionais.")
    
    # Loop de conversação
    while True:
        user_input = input("\nVocê: ")
        
        # Comandos especiais
        if user_input.lower() == 'sair':
            print("Encerrando conversa.")
            break
        elif user_input.lower() == 'ajuda':
            print("\nComandos disponíveis:")
            print("  sair - Encerra a conversa")
            print("  ajuda - Mostra esta mensagem")
            print("  nivel X - Define o nível do personagem (0-3)")
            print("  info - Mostra informações do nível atual")
            print("  historia - Mostra o histórico da conversa")
            print("  limpar - Limpa o histórico da conversa")
            print("  gatilhos - Mostra os gatilhos do nível atual")
            print("  inv - Mostra inventário virtual")
            continue
        elif user_input.lower().startswith('nivel '):
            try:
                level = int(user_input.split()[1])
                manager.set_character_level(level)
                print(f"Sebastian agora está no nível {level}")
            except (IndexError, ValueError):
                print("Formato inválido. Use 'nivel X' onde X é um número (0-3).")
            continue
        elif user_input.lower() == 'info':
            level = manager.get_character_level()
            level_data = manager.character_data.get('levels', [])[level]
            print(f"\nNível atual: {level}")
            print(f"Conhecimento: {level_data.get('knowledge_scope', '')[:100]}...")
            print(f"Postura: {level_data.get('narrative_stance', '')[:100]}...")
            print(f"Defensivo: {'Sim' if level_data.get('is_defensive', False) else 'Não'}")
            continue
        elif user_input.lower() == 'historia':
            print("\nHistórico da conversa:")
            for idx, msg in enumerate(manager.conversation_history):
                role = "Sebastian" if msg["role"] == "assistant" else "Você"
                print(f"{idx+1}. {role}: {msg['content']}")
            continue
        elif user_input.lower() == 'limpar':
            greeting = manager.start_conversation()
            print(f"Histórico limpo. Sebastian: {greeting}")
            continue
        elif user_input.lower() == 'gatilhos':
            level = manager.get_character_level()
            level_data = manager.character_data.get('levels', [])[level]
            triggers = level_data.get('triggers', [])
            if triggers:
                print(f"\nGatilhos do nível {level}:")
                for i, trigger in enumerate(triggers):
                    print(f"  {i+1}. Palavra-chave: '{trigger.get('trigger_keyword', '')}'")
                    print(f"     Condição: {trigger.get('contextual_condition', '')}")
                    
                    # Mostrar requisitos
                    requirements = trigger.get('requirements', [])
                    if requirements:
                        print("     Requisitos:")
                        for req in requirements:
                            req_type = req.get('requirement_type', '')
                            req_obj = req.get('required_object_id', 'N/A')
                            print(f"       - Tipo: {req_type}, Objeto: {req_obj}")
            else:
                print(f"\nNão há gatilhos definidos para o nível {level}")
            continue
        elif user_input.lower() == 'inv':
            print("\nInventário Virtual (para testes):")
            for item_id in manager.inventory.collected_items:
                print(f"  - Item ID {item_id}")
            print("\nConhecimentos:")
            for k in manager.inventory.knowledge:
                print(f"  - {k}")
            continue
        
        # Processar mensagem normal
        result = manager.send_message(user_input)
        
        print(f"\nSebastian: {result['response']}")
        
        if result.get("challenge_activated", False):
            print("\n[DESAFIO ATIVADO! Sebastian está testando seu conhecimento]")
            print("Responda de forma a demonstrar que você tem a evidência ou conhecimento necessário.")
        
        if result.get("evolution", False):
            print(f"\n[EVOLUÇÃO DETECTADA! Sebastian avançou para o nível {result['new_level']}]")
            print(f"Seu conhecimento e comportamento mudaram. Ele agora pode revelar mais informações.")


if __name__ == "__main__":
    run_dialogue_test()