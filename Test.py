import os
import json
import sys
from pathlib import Path
import re
import requests
from time import sleep
import datetime
import uuid

class GameEngine:
    def __init__(self, historia_path):
        self.historia_path = Path(historia_path)
        self.data = {}
        self.current_location = None
        self.current_area = None
        self.player_id = None
        self.player_data = {
            "inventory": [],
            "discovered_clues": [],
            "character_levels": {},
            "location_levels": {},
            "object_levels": {},
            "last_seen_details": {},
            "skills": {
                "analise_evidencias": 0,
                "conhecimento_historico": 0,
                "interpretacao_comportamento": 0,
                "descoberta_ambiental": 0,
                "conexao_informacoes": 0
            }
        }
        self.ollama_model = "llama3"
        self.dynamic_details_cache = {}  # Guarda detalhes gerados pela IA para consistência
        self.save_file = None  # Será definido após a escolha do ID do jogador
        
    def set_player_id(self, player_id):
        """Define o ID do jogador e configura o arquivo de salvamento"""
        self.player_id = player_id
        self.save_file = f"save_{player_id}.json"
        
    def load_game_data(self):
        """Carrega todos os dados do jogo dos arquivos JSON"""
        # Carregar história base
        with open(self.historia_path / "historia_base.json", "r", encoding="utf-8") as f:
            self.data["historia_base"] = json.load(f)
        
        # Carregar ambientes
        self.data["ambientes"] = {}
        for arquivo in (self.historia_path / "ambientes").glob("*.json"):
            with open(arquivo, "r", encoding="utf-8") as f:
                ambiente = json.load(f)
                for location in ambiente:
                    self.data["ambientes"][location["location_id"]] = location
        
        # Carregar personagens
        self.data["personagens"] = {}
        for arquivo in (self.historia_path / "personagens").glob("*.json"):
            with open(arquivo, "r", encoding="utf-8") as f:
                personagem = json.load(f)
                for character in personagem:
                    self.data["personagens"][character["character_id"]] = character
        
        # Carregar dados adicionais
        data_dir = self.historia_path / "data"
        with open(data_dir / "objetos.json", "r", encoding="utf-8") as f:
            self.data["objetos"] = json.load(f)
        
        with open(data_dir / "pistas.json", "r", encoding="utf-8") as f:
            self.data["pistas"] = json.load(f)
        
        with open(data_dir / "qrcodes.json", "r", encoding="utf-8") as f:
            self.data["qrcodes"] = json.load(f)
        
        with open(data_dir / "sistema-especializacao.json", "r", encoding="utf-8") as f:
            self.data["sistema_especializacao"] = json.load(f)
        
        # Definir localização inicial
        for loc_id, location in self.data["ambientes"].items():
            if location.get("is_starting_location", False):
                self.current_location = loc_id
                # Definir área inicial (primeira área do local inicial)
                if location.get("areas"):
                    self.current_area = location["areas"][0]["area_id"]
                break
    
    def start_game(self):
        """Inicia o jogo mostrando a introdução e o local inicial"""
        clear_screen()
        print_title(self.data["historia_base"]["title"])
        print("\n" + self.data["historia_base"]["description"] + "\n")
        
        # Verifica sem mostrar informações se o Ollama está disponível
        self.check_ollama_availability(silent=True)
        
        input("Pressione Enter para começar...")
        
        # Mostrar a introdução usando o Ollama para enriquecê-la
        clear_screen()
        intro_text = self.data["historia_base"]["introduction"]
        enhanced_intro = self.enhance_text_with_ollama(
            "Introdução do jogo", 
            intro_text, 
            "Mantenha o mesmo sentido mas torne mais vívido e detalhado, adicione detalhes sensoriais."
        )
        print_colored(enhanced_intro or intro_text, "cyan")
        input("\nPressione Enter para continuar...")
        
        # Iniciar o loop principal do jogo
        self.game_loop()
    
    def check_ollama_availability(self, silent=False):
        """Verifica se o Ollama está disponível"""
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                # Lista os modelos disponíveis
                models = response.json().get("models", [])
                if models:
                    available_models = [model["name"] for model in models]
                    
                    # Verificar se o modelo padrão está disponível, senão usa o primeiro da lista
                    if self.ollama_model not in available_models and available_models:
                        self.ollama_model = available_models[0]
                        if not silent:
                            print(f"Usando modelo: {self.ollama_model}")
                return True
            return False
        except:
            return False
    
    def enhance_text_with_ollama(self, context, text, instruction=""):
        """Usa o Ollama para melhorar textos ou gerar respostas de NPCs"""
        if not self.check_ollama_availability(silent=True):
            return None
            
        try:
            system_prompt = """
            Você é um assistente de narração para um jogo de mistério ambientado em uma estalagem antiga.
            Seu trabalho é:
            1. Enriquecer descrições com detalhes vívidos e sensoriais
            2. Falar como os personagens de forma coerente com suas personalidades
            3. Criar pequenos elementos narrativos que se encaixem no tema do jogo
            
            Importante:
            - Mantenha o tom de mistério e investigação
            - Seja conciso mas detalhado
            - Não mude fatos essenciais da história
            - Não use marcações como asteriscos ou aspas, apenas texto puro
            - Sempre responda em português brasileiro
            - Nunca use palavras em inglês
            """
            
            prompt = f"""
            Contexto: {context}
            
            Texto original: {text}
            
            Instrução: {instruction}
            
            Responda apenas com o texto melhorado, em português brasileiro, sem comentários adicionais.
            """
            
            response = requests.post("http://localhost:11434/api/generate", 
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 1024,
                    }
                }
            )
            
            if response.status_code == 200:
                return response.json().get("response", text)
            return text
        except Exception as e:
            return text
    
    def generate_npc_dialogue(self, character, player_question):
        """Gera diálogo de NPC baseado na pergunta aberta do jogador"""
        if not self.check_ollama_availability(silent=True):
            return "Não consigo responder a isso no momento."
            
        char_personality = character.get("personality", "")
        char_name = character.get("name", "")
        char_id = character.get("character_id", 0)
        char_level = self.get_character_level(char_id)
        
        # Obter conhecimento disponível para o personagem baseado no nível atual
        knowledge = ""
        for level in character.get("levels", []):
            if level["level_number"] <= char_level:
                knowledge += level.get("knowledge_scope", "") + " "
                
        # Analisar se a pergunta aciona algum trigger
        triggered_response = self.check_for_trigger(character, player_question)
        if triggered_response:
            return triggered_response
        
        try:
            system_prompt = f"""
            Você é {char_name}, um personagem em um jogo de mistério.
            
            Sua personalidade: {char_personality}
            
            O que você sabe (baseado no nível atual do jogador): {knowledge}
            
            Regras importantes:
            1. Responda sempre em primeira pessoa como {char_name}
            2. Seja fiel à sua personalidade
            3. Só compartilhe informações que você conhece no nível atual
            4. Mantenha respostas concisas (1-4 frases)
            5. Use pulsação narrativa para incluir detalhe de linguagem corporal ou expressão.
            6. Se a pergunta busca informações que você não deveria saber, demonstre confusão ou negue conhecimento
            7. Sempre responda em português brasileiro
            8. Nunca use palavras em inglês
            """
            
            prompt = f"""
            Um jogador perguntou: "{player_question}"
            
            Como {char_name}, responda de acordo com seu conhecimento atual e personalidade.
            Se a pergunta for sobre algo que você não deveria saber, demonstre confusão ou negue conhecimento de maneira natural.
            """
            
            response = requests.post("http://localhost:11434/api/generate", 
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,
                        "top_p": 0.9,
                        "max_tokens": 512,
                    }
                }
            )
            
            if response.status_code == 200:
                return response.json().get("response", "Não sei o que dizer sobre isso.")
            return "Não sei o que dizer sobre isso."
        except:
            return "Não sei o que dizer sobre isso."
    
    def check_for_trigger(self, character, player_question):
        """Verifica se a pergunta do jogador aciona algum trigger de diálogo"""
        char_id = character.get("character_id", 0)
        char_level = self.get_character_level(char_id)
        
        # Normalizar a pergunta para busca de palavras-chave
        question_lower = player_question.lower()
        
        # Verificar todos os triggers disponíveis para o nível atual do personagem
        for level in character.get("levels", []):
            if level["level_number"] <= char_level and "triggers" in level:
                for trigger in level["triggers"]:
                    keyword = trigger.get("trigger_keyword", "").lower()
                    # Se a palavra-chave estiver presente na pergunta
                    if keyword in question_lower:
                        # Verificar se o personagem está na defensiva
                        if level.get("is_defensive", False):
                            # Gerar resposta defensiva
                            defensive_response = self.enhance_text_with_ollama(
                                f"Resposta defensiva de {character['name']}",
                                trigger.get("defensive_response", ""),
                                "Torne esta resposta mais natural, mantendo o tom defensivo. Adicione detalhes de linguagem corporal ou expressão."
                            )
                            
                            # Verificar requisitos para superar a defesa
                            has_requirements = self.check_dialogue_requirements(trigger)
                            
                            if has_requirements:
                                # Jogador tem os requisitos, retornar a resposta de sucesso
                                success_response = self.enhance_text_with_ollama(
                                    f"Resposta bem-sucedida de {character['name']}",
                                    trigger.get("success_response", ""),
                                    "Torne esta resposta mais natural. Adicione detalhes de linguagem corporal ou expressão."
                                )
                                
                                # Aumentar nível do personagem
                                if char_level < len(character["levels"]) - 1:
                                    self.player_data["character_levels"][char_id] = char_level + 1
                                    
                                    # Descobrir pistas relacionadas
                                    self.discover_clues_by_character(char_id)
                                    
                                    # Salvar o jogo automaticamente
                                    self.save_game()
                                    
                                return success_response or trigger.get("success_response", "")
                            else:
                                # Jogador não tem os requisitos, retornar a resposta de falha
                                fail_response = self.enhance_text_with_ollama(
                                    f"Resposta de falha de {character['name']}",
                                    trigger.get("fail_response", ""),
                                    "Torne esta resposta mais natural, mantendo o tom de recusa. Adicione detalhes de linguagem corporal ou expressão."
                                )
                                return fail_response or trigger.get("fail_response", "")
                        else:
                            # Se não for defensivo, retornar resposta normal ou de sucesso
                            if "success_response" in trigger:
                                success_response = self.enhance_text_with_ollama(
                                    f"Resposta de {character['name']}",
                                    trigger.get("success_response", ""),
                                    "Torne esta resposta mais natural. Adicione detalhes de linguagem corporal ou expressão."
                                )
                                return success_response or trigger.get("success_response", "")
        
        # Nenhum trigger encontrado
        return None
    
    def generate_dynamic_description(self, location, area):
        """Gera uma descrição dinâmica para uma área usando Ollama"""
        # Verificar se já existe no cache para manter consistência
        cache_key = f"{location.get('location_id')}_{area.get('area_id')}"
        if cache_key in self.dynamic_details_cache.get("descriptions", {}):
            return self.dynamic_details_cache["descriptions"][cache_key]
        
        if not self.check_ollama_availability(silent=True):
            return None
            
        loc_name = location.get("name", "")
        area_name = area.get("name", "")
        base_desc = area.get("description", "")
        
        try:
            system_prompt = """
            Você é um narrador de um jogo de mistério ambientado em uma estalagem antiga.
            Seu trabalho é criar descrições vívidas e atmosféricas dos ambientes que o jogador visita.
            
            Importante:
            - Crie descrições imersivas com detalhes sensoriais (visão, sons, cheiros, etc.)
            - Mantenha o tom de mistério e suspense
            - Adicione pequenos detalhes que não mudem a essência do local
            - Não mencione personagens que não estejam explicitamente na descrição original
            - Sempre responda em português brasileiro
            - Nunca use palavras em inglês
            """
            
            prompt = f"""
            Local: {loc_name}
            Área: {area_name}
            
            Descrição original: "{base_desc}"
            
            Crie uma descrição mais vívida e atmosférica deste ambiente, mantendo todos os elementos-chave,
            mas adicionando detalhes sensoriais e elementos que aumentem a imersão.
            Limite-se a 3-4 frases detalhadas. Responda em português brasileiro.
            """
            
            response = requests.post("http://localhost:11434/api/generate", 
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 512,
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json().get("response", base_desc)
                # Salvar no cache
                if "descriptions" not in self.dynamic_details_cache:
                    self.dynamic_details_cache["descriptions"] = {}
                self.dynamic_details_cache["descriptions"][cache_key] = result
                return result
            return base_desc
        except:
            return base_desc

    def generate_additional_details(self, location, area):
        """Gera detalhes adicionais para uma área que não estão nos JSONs originais"""
        # Verificar cache para consistência
        cache_key = f"{location.get('location_id')}_{area.get('area_id')}"
        if cache_key in self.dynamic_details_cache.get("details", {}):
            return self.dynamic_details_cache["details"][cache_key]
        
        if not self.check_ollama_availability(silent=True):
            return []
            
        loc_name = location.get("name", "")
        area_name = area.get("name", "")
        base_desc = area.get("description", "")
        
        try:
            system_prompt = """
            Você é o assistente de um jogo de mistério e investigação em português brasileiro. O jogo segue uma estrutura definida,
            mas você pode enriquecer o ambiente com detalhes adicionais que se encaixem no contexto.
            
            Importante:
            - Crie apenas 1-2 elementos sutis que poderiam estar no ambiente
            - Esses elementos devem ser coerentes com o tema de um mistério em uma estalagem antiga
            - Não introduza novos personagens ou elementos que alterem a história principal
            - O formato deve ser um array JSON com 1-2 objetos, cada um com "name" e "description"
            - Use apenas nomes e descrições em português brasileiro
            - Nunca use palavras em inglês
            - Sempre responda apenas com o JSON válido, sem texto adicional
            """
            
            prompt = f"""
            Local: {loc_name}
            Área: {area_name}
            
            Descrição original: "{base_desc}"
            
            Crie 1-2 elementos ambientais adicionais em português brasileiro que poderiam estar neste local e que sejam
            coerentes com o cenário. Pode ser uma decoração, um objeto comum, um detalhe arquitetônico, etc.
            Estes elementos não devem alterar a narrativa principal, apenas tornar o ambiente mais rico.
            
            Responda APENAS com um array JSON válido no formato:
            [
                {{
                    "name": "Nome do elemento em português",
                    "description": "Descrição detalhada em português"
                }},
                ...
            ]
            """
            
            response = requests.post("http://localhost:11434/api/generate", 
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,
                        "top_p": 0.9,
                        "max_tokens": 512,
                    }
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "[]")
                try:
                    # Limpar a resposta para garantir que é apenas JSON
                    json_str = re.search(r'(\[.*\])', ai_response, re.DOTALL)
                    if json_str:
                        result = json.loads(json_str.group(1))
                    else:
                        result = json.loads(ai_response)
                    
                    # Salvar no cache
                    if "details" not in self.dynamic_details_cache:
                        self.dynamic_details_cache["details"] = {}
                    self.dynamic_details_cache["details"][cache_key] = result
                    
                    return result
                except:
                    return []
            return []
        except:
            return []
    
    def game_loop(self):
        """Loop principal do jogo"""
        while True:
            self.display_current_location()
            choice = input("\nEscolha uma opção: ").strip().upper()
            
            if choice == 'D':  # Sair do jogo
                if confirm("Tem certeza que deseja sair do jogo?"):
                    # Salvar antes de sair
                    self.save_game()
                    break
                continue
            
            # Processar escolha numérica
            if choice.isdigit():
                self.process_numeric_choice(int(choice))
            # Processar escolha alfabética
            elif choice == 'A':
                self.show_inventory()
            elif choice == 'B':
                self.show_clues()
            elif choice == 'C':
                self.show_skills()
            elif choice == 'E':
                self.save_game()
                print("Jogo salvo com sucesso!")
                input("Pressione Enter para continuar...")
            elif choice == 'F':
                self.make_accusation()
            else:
                print("Opção inválida.")
                input("Pressione Enter para continuar...")
    
    def process_numeric_choice(self, choice_num):
        """Processa escolhas numéricas do menu unificado"""
        current_loc = self.data["ambientes"][self.current_location]
        current_area = next((a for a in current_loc["areas"] if a["area_id"] == self.current_area), None)
        
        # Compilar lista de itens explorables
        explorables = []
        
        # Adicionar detalhes visíveis
        if "details" in current_area:
            visible_details = [d for d in current_area["details"] 
                              if d["discovery_level_required"] <= self.get_location_discovery_level(self.current_area)]
            for detail in visible_details:
                explorables.append(("detalhe", detail))
        
        # Adicionar detalhes dinâmicos
        dynamic_details = self.get_cached_dynamic_details(current_loc, current_area)
        for detail in dynamic_details:
            explorables.append(("dinamico", detail))
        
        # Adicionar objetos na área
        objects_in_area = self.get_objects_in_area(self.current_location, self.current_area)
        for obj in objects_in_area:
            explorables.append(("objeto", obj))
        
        # Adicionar áreas conectadas
        connected_areas = []
        for area_id in current_area.get("connected_areas", []):
            area = next((a for a in current_loc["areas"] if a["area_id"] == area_id), None)
            if area and area.get("initially_visible", True):
                connected_areas.append(area)
        
        # Adicionar personagens
        chars_in_area = self.get_characters_in_area(self.current_location, self.current_area)
        
        # Verificar qual opção foi selecionada
        total_explorables = len(explorables)
        total_connected = len(connected_areas)
        total_characters = len(chars_in_area)
        
        if choice_num <= total_explorables:
            # Explorar um item
            tipo, item = explorables[choice_num - 1]
            if tipo == "detalhe":
                self.explore_detail(item)
            elif tipo == "dinamico":
                self.explore_dynamic_detail(item)
            elif tipo == "objeto":
                self.explore_object(item)
        elif choice_num <= total_explorables + total_connected:
            # Mover para uma área
            target_area = connected_areas[choice_num - total_explorables - 1]
            self.move_to_area(target_area)
        elif choice_num <= total_explorables + total_connected + total_characters:
            # Falar com personagem
            character = chars_in_area[choice_num - total_explorables - total_connected - 1]
            self.start_conversation(character)
        else:
            print("Opção inválida.")
            input("Pressione Enter para continuar...")
    
    def get_cached_dynamic_details(self, location, area):
        """Retorna detalhes dinâmicos do cache ou gera novos"""
        cache_key = f"{location.get('location_id')}_{area.get('area_id')}"
        
        # Se não estiver no cache, gerar e salvar
        if "details" not in self.dynamic_details_cache or cache_key not in self.dynamic_details_cache.get("details", {}):
            details = self.generate_additional_details(location, area)
            if "details" not in self.dynamic_details_cache:
                self.dynamic_details_cache["details"] = {}
            self.dynamic_details_cache["details"][cache_key] = details
            return details
        
        # Retornar do cache
        return self.dynamic_details_cache["details"][cache_key]
    
    def display_current_location(self):
        """Mostra a descrição do local atual e opções disponíveis em um menu unificado"""
        clear_screen()
        current_loc = self.data["ambientes"][self.current_location]
        current_area = next((a for a in current_loc["areas"] if a["area_id"] == self.current_area), None)
        
        # Mostrar nome do local e área
        print_title(f"{current_loc['name']} - {current_area['name']}")
        
        # Gerar uma descrição mais rica com o Ollama
        enhanced_desc = self.generate_dynamic_description(current_loc, current_area)
        # Mostrar descrição
        print_colored(enhanced_desc or current_area["description"], "cyan")
        
        # Compilar opções
        option_counter = 1
        all_options = []
        
        # Mostrar detalhes visíveis
        visible_details = []
        if "details" in current_area:
            visible_details = [d for d in current_area["details"] 
                              if d["discovery_level_required"] <= self.get_location_discovery_level(self.current_area)]
        
        # Obter ou gerar detalhes dinâmicos consistentes
        dynamic_details = self.get_cached_dynamic_details(current_loc, current_area)
        
        # Obter objetos na área
        objects_in_area = self.get_objects_in_area(self.current_location, self.current_area)
        
        # Lembrar dos detalhes vistos
        area_id_str = str(self.current_area)
        if area_id_str not in self.player_data["last_seen_details"]:
            self.player_data["last_seen_details"][area_id_str] = []
        
        # Mostrar "Você nota:" apenas se houver algo para notar
        if visible_details or dynamic_details or objects_in_area:
            print("\nVocê nota:")
            
            # Adicionar detalhes do ambiente
            for detail in visible_details:
                print(f"{option_counter}. Explorar {detail['name']}")
                all_options.append(("detalhe", detail))
                option_counter += 1
                
                # Adicionar à lista de detalhes vistos
                if detail["detail_id"] not in self.player_data["last_seen_details"][area_id_str]:
                    self.player_data["last_seen_details"][area_id_str].append(detail["detail_id"])
            
            # Adicionar detalhes dinâmicos
            for detail in dynamic_details:
                print(f"{option_counter}. Explorar {detail['name']}")
                all_options.append(("dinamico", detail))
                option_counter += 1
                
            # Adicionar objetos
            for obj in objects_in_area:
                print(f"{option_counter}. Examinar {obj['name']}")
                all_options.append(("objeto", obj))
                option_counter += 1
        
        # Mostrar áreas conectadas
        connected_areas = []
        for area_id in current_area.get("connected_areas", []):
            area = next((a for a in current_loc["areas"] if a["area_id"] == area_id), None)
            if area and area.get("initially_visible", True):
                connected_areas.append(area)
        
        if connected_areas:
            print("\nÁreas conectadas:")
            for area in connected_areas:
                print(f"{option_counter}. Ir para {area['name']}")
                all_options.append(("area", area))
                option_counter += 1
        
        # Mostrar personagens presentes
        chars_in_area = self.get_characters_in_area(self.current_location, self.current_area)
        if chars_in_area:
            print("\nPersonagens presentes:")
            for char in chars_in_area:
                print(f"{option_counter}. Falar com {char['name']}")
                all_options.append(("personagem", char))
                option_counter += 1
        
        # Mostrar comandos gerais
        print("\nDemais comandos:")
        print("A. Ver inventário")
        print("B. Ver pistas descobertas")
        print("C. Ver habilidades")
        print("D. Sair do jogo")
        print("E. Salvar jogo")
        print("F. Fazer acusação")
        
        return all_options  # Retorna para uso em process_numeric_choice
    
    def explore_detail(self, detail):
        """Explora um detalhe do ambiente"""
        clear_screen()
        print_title(f"Explorando: {detail['name']}")
        
        # Enriquecer a descrição com o Ollama
        enhanced_desc = self.enhance_text_with_ollama(
            f"Explorando {detail['name']}", 
            detail["description"], 
            "Torne esta descrição mais vívida e detalhada, mantendo as informações importantes."
        )
        
        print_colored(enhanced_desc or detail["description"], "yellow")
        
        # Verificar se descobriu alguma pista
        if detail.get("has_clue", False):
            self.discover_clue_by_detail(self.current_location, self.current_area, detail["detail_id"])
            # Salvar automaticamente ao descobrir pista
            self.save_game()
        
        # Aumentar nível de descoberta da área
        self.increase_location_discovery(self.current_area)
        
        input("\nPressione Enter para continuar...")
    
    def explore_dynamic_detail(self, detail):
        """Explora um detalhe gerado dinamicamente"""
        clear_screen()
        print_title(f"Explorando: {detail['name']}")
        
        print_colored(detail["description"], "yellow")
        
        # Verificar se pode gerar uma pista ou conteúdo adicional
        if self.check_ollama_availability(silent=True):
            # Chance de descobrir algo interessante
            extra_content = self.enhance_text_with_ollama(
                f"Observação adicional sobre {detail['name']}", 
                "Ao examinar com mais atenção, você nota algo...", 
                "Gere uma observação adicional intrigante mas que não interfira na história principal."
            )
            
            if extra_content:
                print_colored(f"\nAo examinar mais cuidadosamente: {extra_content}", "green")
        
        input("\nPressione Enter para continuar...")
    
    def explore_object(self, obj):
        """Explora um objeto"""
        clear_screen()
        print_title(f"Examinando: {obj['name']}")
        
        # Obter nível de descoberta do objeto
        obj_id = obj["object_id"]
        obj_level = self.get_object_discovery_level(obj_id)
        level_info = obj["levels"][obj_level]
        
        # Enriquecer a descrição com o Ollama
        enhanced_desc = self.enhance_text_with_ollama(
            f"Examinando {obj['name']}", 
            level_info["level_description"], 
            "Torne esta descrição mais vívida e detalhada, adicione elementos sensoriais."
        )
        
        print_colored(enhanced_desc or level_info["level_description"], "yellow")
        
        # Se for um objeto coletável, oferecer opção de pegá-lo
        if obj.get("is_collectible", False) and obj_id not in self.player_data["inventory"]:
            if confirm("\nDeseja pegar este objeto?"):
                self.player_data["inventory"].append(obj_id)
                print_colored(f"Você pegou: {obj['name']}", "green")
                # Salvar automaticamente ao pegar um objeto
                self.save_game()
        
        # Verificar se pode evoluir o conhecimento sobre o objeto
        if obj_level < len(obj["levels"]) - 1:
            next_level = obj["levels"][obj_level + 1]
            if "evolution_trigger" in next_level:
                print(f"\nDica: {next_level['evolution_trigger']}")
        
        # Aumentar habilidades apropriadas
        self.increase_skill_by_object(obj["object_id"])
        
        input("\nPressione Enter para continuar...")
    
    def start_conversation(self, character):
        """Inicia uma conversa com um personagem usando entrada de texto livre"""
        char_id = character["character_id"]
        char_level = self.get_character_level(char_id)
        
        # Gerar uma saudação inicial
        greeting = self.enhance_text_with_ollama(
            f"Saudação de {character['name']} nível {char_level}",
            "Olá, em que posso ajudar?",
            f"Gere uma saudação inicial como o personagem {character['name']}, considerando sua personalidade e o nível de relacionamento {char_level}. Deve ser breve e em português brasileiro."
        )
        
        # Exibir descrição do personagem apenas uma vez
        clear_screen()
        print_title(f"Conversando com {character['name']}")
        
        # Gerar uma descrição melhorada do personagem
        if char_level == 0:
            enhanced_desc = self.enhance_text_with_ollama(
                f"Descrição de {character['name']}", 
                character["base_description"], 
                "Torne esta descrição mais vívida, enfatizando aspectos visuais e comportamentais."
            )
            print_colored(enhanced_desc or character["base_description"], "green")
        else:
            # Mostrar descrição mais detalhada para níveis mais altos
            level_info = character["levels"][char_level]
            enhanced_desc = self.enhance_text_with_ollama(
                f"Descrição de {character['name']} nível {char_level}", 
                character["base_description"] + "\n\n" + level_info["narrative_stance"], 
                "Combine estas informações em uma descrição coesa e vívida."
            )
            print_colored(enhanced_desc or character["base_description"], "green")
        
        # Iniciar conversa com saudação
        conversation_history = []
        if greeting:
            print_colored(f"\n{character['name']}: {greeting}", "cyan")
            conversation_history.append((character['name'], greeting))
        
        # Loop de conversa
        while True:
            # Interface de conversa
            print("\nO que você gostaria de perguntar? (digite 'sair' para encerrar a conversa)")
            player_input = input("> ").strip()
            
            if player_input.lower() in ['sair', 'voltar', 'encerrar']:
                break
            
            if not player_input:
                continue
            
            # Adicionar pergunta do jogador ao histórico
            conversation_history.append(("Você", player_input))
            
            # Gerar resposta do NPC
            response = self.generate_npc_dialogue(character, player_input)
            conversation_history.append((character['name'], response))
            
            # Limpar tela e mostrar todo o histórico novamente
            clear_screen()
            print_title(f"Conversando com {character['name']}")
            print_colored(enhanced_desc or character["base_description"], "green")
            
            # Mostrar histórico completo da conversa
            print("\nHistórico da conversa:")
            for speaker, text in conversation_history:
                if speaker == "Você":
                    print_colored(f"\nVocê: {text}", "white")
                else:
                    print_colored(f"\n{speaker}: {text}", "cyan")
            
            # Aumentar habilidade de interpretação de comportamento
            self.player_data["skills"]["interpretacao_comportamento"] += 5
        
    def move_to_area(self, target_area):
        """Move o jogador para outra área"""
        current_loc = self.data["ambientes"][self.current_location]
        current_area = next((a for a in current_loc["areas"] if a["area_id"] == self.current_area), None)
        
        # Verificar requisitos de descoberta
        if "discovery_level_required" in target_area and target_area["discovery_level_required"] > self.get_location_discovery_level(target_area["area_id"]):
            print("Esta área ainda não está acessível. Continue explorando para encontrar uma maneira de acessá-la.")
            input("Pressione Enter para continuar...")
            return
        
        # Mudar para a nova área
        self.current_area = target_area["area_id"]
        
        # Descrever a transição
        if self.check_ollama_availability(silent=True):
            transition = self.enhance_text_with_ollama(
                "Transição entre áreas",
                f"Você se move de {current_area['name']} para {target_area['name']}.",
                "Descreva esta transição de forma vívida, incluindo detalhes sensoriais e de movimento."
            )
            if transition:
                clear_screen()
                print_colored(transition, "cyan")
                input("\nPressione Enter para continuar...")
    
    def show_inventory(self):
        """Mostra os itens no inventário do jogador"""
        clear_screen()
        print_title("Inventário")
        
        if not self.player_data["inventory"]:
            print("Seu inventário está vazio.")
            input("\nPressione Enter para continuar...")
            return
        
        inventory_items = []
        for obj_id in self.player_data["inventory"]:
            obj = self.get_object_by_id(obj_id)
            if obj:
                inventory_items.append(obj)
        
        while True:
            clear_screen()
            print_title("Inventário")
            
            for i, obj in enumerate(inventory_items):
                obj_level = self.get_object_discovery_level(obj["object_id"])
                print(f"{i+1}. {obj['name']}")
            
            print(f"{len(inventory_items)+1}. Voltar")
            
            choice = input("\nSelecione um item para examinar ou voltar: ")
            
            try:
                choice_num = int(choice)
                if choice_num == len(inventory_items) + 1:
                    break
                elif 1 <= choice_num <= len(inventory_items):
                    self.explore_object(inventory_items[choice_num - 1])
                else:
                    print("Opção inválida.")
                    input("Pressione Enter para continuar...")
            except ValueError:
                print("Por favor, digite um número.")
                input("Pressione Enter para continuar...")
    
    def show_clues(self):
        """Mostra as pistas descobertas pelo jogador"""
        clear_screen()
        print_title("Pistas Descobertas")
        
        if not self.player_data["discovered_clues"]:
            print("Você ainda não descobriu nenhuma pista.")
            input("\nPressione Enter para continuar...")
            return
        
        discovered_clues = []
        for clue_id in self.player_data["discovered_clues"]:
            clue = self.get_clue_by_id(clue_id)
            if clue:
                discovered_clues.append(clue)
        
        # Ordenar pistas por relevância
        discovered_clues.sort(key=lambda c: c.get("relevance", 0), reverse=True)
        
        while True:
            clear_screen()
            print_title("Pistas Descobertas")
            
            for i, clue in enumerate(discovered_clues):
                relevance = "★" * clue.get("relevance", 0)
                print(f"{i+1}. {clue['name']} ({relevance})")
            
            print(f"{len(discovered_clues)+1}. Voltar")
            
            choice = input("\nSelecione uma pista para examinar com mais detalhes ou voltar: ")
            
            try:
                choice_num = int(choice)
                if choice_num == len(discovered_clues) + 1:
                    break
                elif 1 <= choice_num <= len(discovered_clues):
                    self.examine_clue(discovered_clues[choice_num - 1])
                else:
                    print("Opção inválida.")
                    input("Pressione Enter para continuar...")
            except ValueError:
                print("Por favor, digite um número.")
                input("Pressione Enter para continuar...")
    
    def examine_clue(self, clue):
        """Examina uma pista com mais detalhes"""
        clear_screen()
        print_title(f"Pista: {clue['name']}")
        
        # Melhorar a descrição da pista com o Ollama
        enhanced_desc = self.enhance_text_with_ollama(
            f"Descrição da pista {clue['name']}",
            clue["description"],
            "Torne esta descrição mais vívida e detalhada, mantendo todas as informações importantes."
        )
        
        print_colored(enhanced_desc or clue["description"], "cyan")
        print(f"\nTipo: {clue['type']}")
        print(f"Relevância: {'★' * clue['relevance']}")
        
        # Gerar insights sobre a pista usando o Ollama
        if self.check_ollama_availability(silent=True) and clue.get("is_key_evidence", False):
            insight = self.enhance_text_with_ollama(
                f"Insight sobre a pista {clue['name']}",
                "Ao refletir sobre esta pista...",
                "Gere uma reflexão perspicaz sobre esta pista e como ela pode se conectar ao caso. "
                "A reflexão deve ser intrigante mas não revelar diretamente o culpado. "
                "Comece com 'Ao refletir sobre esta pista...' e mantenha em 2-3 frases."
            )
            
            if insight:
                print_colored(f"\nInsight do Investigador: {insight}", "yellow")
        
        # Aumentar habilidade de conexão de informações
        self.player_data["skills"]["conexao_informacoes"] += 3
        
        input("\nPressione Enter para continuar...")
    
    def show_skills(self):
        """Mostra as habilidades do jogador"""
        clear_screen()
        print_title("Habilidades do Investigador")
        
        skill_names = {
            "analise_evidencias": "Análise de Evidências",
            "conhecimento_historico": "Conhecimento Histórico",
            "interpretacao_comportamento": "Interpretação de Comportamento",
            "descoberta_ambiental": "Descoberta Ambiental",
            "conexao_informacoes": "Conexão de Informações"
        }
        
        # Obter detalhes das categorias do sistema de especialização
        skill_categories = {}
        for category in self.data["sistema_especializacao"]["categorias"]:
            cat_id = category["nome_interno"]
            skill_categories[cat_id] = {
                "nome": category["nome_exibicao"],
                "descricao": category["descricao"],
                "niveis": category["niveis"]
            }
        
        for skill_id, level in self.player_data["skills"].items():
            skill_name = skill_names.get(skill_id, skill_id)
            skill_desc = skill_categories.get(skill_id, {}).get("descricao", "")
            
            # Determinar nível da habilidade
            skill_level = 0
            level_thresholds = skill_categories.get(skill_id, {}).get("niveis", {})
            for lvl, threshold in level_thresholds.items():
                if level >= threshold:
                    skill_level = int(lvl)
            
            # Mostrar barra de progresso
            progress = min(level / 100, 1.0)
            bar_width = 20
            bar = "■" * int(bar_width * progress) + "□" * (bar_width - int(bar_width * progress))
            
            print(f"{skill_name} (Nível {skill_level}): {bar} {level}/100")
            print(f"  {skill_desc}\n")
        
        # Gerar um conselho para melhorar as habilidades usando o Ollama
        if self.check_ollama_availability(silent=True):
            lowest_skill = min(self.player_data["skills"].items(), key=lambda x: x[1])
            lowest_skill_name = skill_names.get(lowest_skill[0], lowest_skill[0])
            
            advice = self.enhance_text_with_ollama(
                "Conselho sobre habilidades",
                f"Para melhorar sua habilidade de {lowest_skill_name}, você deveria focar em...",
                f"Gere um conselho útil sobre como o jogador pode melhorar sua habilidade de {lowest_skill_name}. "
                "Mantenha em 2-3 frases concisas e específicas."
            )
            
            if advice:
                print_colored(f"\nDica: {advice}", "yellow")
        
        input("\nPressione Enter para continuar...")
    
    def make_accusation(self):
        """Sistema para o jogador fazer uma acusação e resolver o mistério"""
        clear_screen()
        print_title("Fazer Acusação")
        
        # Verificar se o jogador descobriu pistas suficientes
        min_clues_needed = 5  # Ajuste conforme necessário
        key_evidence_count = 0
        
        for clue_id in self.player_data["discovered_clues"]:
            clue = self.get_clue_by_id(clue_id)
            if clue and clue.get("is_key_evidence", False):
                key_evidence_count += 1
        
        if key_evidence_count < min_clues_needed:
            print_colored(f"Você ainda não tem evidências suficientes para fazer uma acusação definitiva. Descubra mais pistas-chave primeiro. (Você tem {key_evidence_count}/{min_clues_needed} evidências-chave)", "red")
            input("\nPressione Enter para continuar...")
            return
        
        # Lista de possíveis culpados
        suspects = []
        for char_id, char in self.data["personagens"].items():
            suspects.append((char_id, char["name"]))
        
        # Apresentar suspeitos
        print("Quem você acusa de cometer o crime?")
        for i, (char_id, name) in enumerate(suspects):
            print(f"{i+1}. {name}")
        
        print(f"{len(suspects)+1}. Cancelar")
        
        try:
            choice = int(input("\nEscolha um suspeito: "))
            if choice == len(suspects) + 1:
                return
            
            if 1 <= choice <= len(suspects):
                suspect_id, suspect_name = suspects[choice-1]
                
                # Verificar se é o culpado correto
                is_correct = False
                for char_id, char in self.data["personagens"].items():
                    if int(char_id) == int(suspect_id) and char.get("is_culprit", False):
                        is_correct = True
                        break
                
                # Pedir motivo
                print(f"\nQual foi o motivo de {suspect_name} para cometer o crime?")
                motivo = input("> ").strip()
                
                # Pedir método
                print(f"\nQual método {suspect_name} utilizou para cometer o crime?")
                metodo = input("> ").strip()
                
                # Processar a acusação
                self.process_accusation(suspect_id, suspect_name, motivo, metodo, is_correct)
            else:
                print("Escolha inválida.")
                input("Pressione Enter para continuar...")
        except ValueError:
            print("Por favor, digite um número.")
            input("Pressione Enter para continuar...")
    
    def process_accusation(self, suspect_id, suspect_name, motivo, metodo, is_correct):
        """Processa o resultado da acusação"""
        clear_screen()
        print_title("Resultado da Acusação")
        
        # Verificar se as respostas do jogador contêm palavras-chave corretas
        success_criteria = self.data["historia_base"].get("solution_criteria", {})
        
        # Verificar o culpado
        culprit_correct = int(suspect_id) == success_criteria.get("culprit_id", 0)
        
        # Verificar o motivo
        motive_keywords = success_criteria.get("motive_keywords", [])
        motivo_lower = motivo.lower()
        motive_correct = any(keyword.lower() in motivo_lower for keyword in motive_keywords)
        
        # Verificar o método
        method_keywords = success_criteria.get("method_keywords", [])
        metodo_lower = metodo.lower()
        method_correct = any(keyword.lower() in metodo_lower for keyword in method_keywords)
        
        # Determinar pontuação
        score = 0
        if culprit_correct:
            score += 50
        if motive_correct:
            score += 25
        if method_correct:
            score += 25
        
        # Determinar resultado final
        if score >= 75:  # Culpado correto e pelo menos um dos outros corretos
            # Final bem-sucedido
            conclusion = self.enhance_text_with_ollama(
                "Conclusão bem-sucedida",
                self.data["historia_base"].get("conclusion", "Você resolveu o mistério!"),
                "Adapte esta conclusão para refletir que o jogador acertou em sua acusação."
            )
            print_colored("Parabéns! Sua acusação está substancialmente correta!", "green")
            print_colored(f"\nPontuação: {score}/100", "yellow")
            print_colored(f"\n{conclusion}", "cyan")
            
            # Registrar vitória nos dados do jogador
            self.player_data["case_solved"] = True
            self.player_data["final_score"] = score
            self.player_data["solved_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Salvar jogo
            self.save_game()
            
            input("\nPressione Enter para continuar...")
            
            # Finalizar jogo
            if confirm("\nDeseja encerrar o jogo agora?"):
                clear_screen()
                print_title("Fim de Jogo")
                print("Obrigado por jogar O Segredo da Estalagem do Cervo Negro!")
                print(f"Pontuação final: {score}/100")
                sys.exit()
        else:
            # Acusação incorreta ou incompleta
            print_colored("Sua acusação não é conclusiva. Você não tem evidências suficientes ou sua teoria está incompleta.", "red")
            print_colored(f"\nPontuação: {score}/100", "yellow")
            
            # Fornecer dicas sobre o que está errado
            if not culprit_correct:
                print_colored("\nSuas evidências não apontam conclusivamente para esta pessoa como o culpado.", "yellow")
            if not motive_correct:
                print_colored("\nSeu entendimento do motivo parece incompleto ou incorreto.", "yellow")
            if not method_correct:
                print_colored("\nSua explicação do método utilizado não corresponde às evidências encontradas.", "yellow")
            
            print("\nContinue investigando para descobrir mais pistas.")
            input("\nPressione Enter para continuar...")
    
    # Funções auxiliares para gerenciar o estado do jogo
    def get_location_discovery_level(self, area_id):
        """Retorna o nível de descoberta de uma área"""
        return self.player_data["location_levels"].get(str(area_id), 0)
    
    def increase_location_discovery(self, area_id):
        """Aumenta o nível de descoberta de uma área"""
        current_level = self.get_location_discovery_level(area_id)
        self.player_data["location_levels"][str(area_id)] = min(current_level + 1, 3)
    
    def get_object_discovery_level(self, object_id):
        """Retorna o nível de descoberta de um objeto"""
        return self.player_data["object_levels"].get(str(object_id), 0)
    
    def increase_object_discovery_level(self, object_id):
        """Aumenta o nível de descoberta de um objeto"""
        current_level = self.get_object_discovery_level(object_id)
        obj = self.get_object_by_id(object_id)
        if obj and current_level < len(obj["levels"]) - 1:
            self.player_data["object_levels"][str(object_id)] = current_level + 1
            return True
        return False
    
    def get_character_level(self, character_id):
        """Retorna o nível de relacionamento com um personagem"""
        return self.player_data["character_levels"].get(character_id, 0)
    
    def get_characters_in_area(self, location_id, area_id):
        """Retorna os personagens presentes em uma área"""
        chars = []
        for char_id, char in self.data["personagens"].items():
            if char.get("area_id") == area_id:
                chars.append(char)
        return chars
    
    def get_objects_in_area(self, location_id, area_id):
        """Retorna os objetos presentes em uma área"""
        objs = []
        for obj in self.data["objetos"]:
            if obj.get("initial_location_id") == location_id and obj.get("initial_area_id") == area_id:
                # Verificar se o objeto é coletável e já está no inventário
                if obj.get("is_collectible", False) and obj["object_id"] in self.player_data["inventory"]:
                    continue
                objs.append(obj)
        return objs
    
    def get_object_by_id(self, object_id):
        """Retorna um objeto pelo seu ID"""
        for obj in self.data["objetos"]:
            if obj["object_id"] == object_id:
                return obj
        return None
    
    def get_clue_by_id(self, clue_id):
        """Retorna uma pista pelo seu ID"""
        for clue in self.data["pistas"]:
            if clue["clue_id"] == clue_id:
                return clue
        return None
    
    def discover_clue_by_detail(self, location_id, area_id, detail_id):
        """Descobre uma pista ao explorar um detalhe específico"""
        for clue in self.data["pistas"]:
            conditions = clue.get("discovery_conditions", {})
            if isinstance(conditions, dict):
                if (conditions.get("location_id") == location_id and 
                    conditions.get("area_id") == area_id and 
                    conditions.get("detail_id") == detail_id):
                    if clue["clue_id"] not in self.player_data["discovered_clues"]:
                        self.player_data["discovered_clues"].append(clue["clue_id"])
                        print_colored(f"\nVocê descobriu uma nova pista: {clue['name']}!", "green")
                        return True
            elif isinstance(conditions, list):
                for condition in conditions:
                    if (condition.get("location_id") == location_id and 
                        condition.get("area_id") == area_id and 
                        condition.get("detail_id") == detail_id):
                        if clue["clue_id"] not in self.player_data["discovered_clues"]:
                            self.player_data["discovered_clues"].append(clue["clue_id"])
                            print_colored(f"\nVocê descobriu uma nova pista: {clue['name']}!", "green")
                            return True
        return False
    
    def discover_clues_by_character(self, character_id):
        """Descobre pistas associadas a um personagem quando seu nível aumenta"""
        for clue in self.data["pistas"]:
            conditions = clue.get("discovery_conditions", {})
            if isinstance(conditions, dict) and conditions.get("character_id") == character_id:
                if clue["clue_id"] not in self.player_data["discovered_clues"]:
                    self.player_data["discovered_clues"].append(clue["clue_id"])
                    print_colored(f"\nVocê descobriu uma nova pista: {clue['name']}!", "green")
    
    def check_dialogue_requirements(self, trigger):
        """Verifica se o jogador atende aos requisitos para o diálogo bem-sucedido"""
        if "requirements" not in trigger:
            return True
        
        for req in trigger["requirements"]:
            req_type = req.get("requirement_type", "")
            
            if req_type == "evidence" and "required_object_id" in req:
                # Verificar se tem os objetos necessários no inventário
                required_objects = req["required_object_id"]
                if isinstance(required_objects, list):
                    if not any(obj_id in self.player_data["inventory"] for obj_id in required_objects):
                        return False
                elif required_objects not in self.player_data["inventory"]:
                    return False
            
            elif req_type == "knowledge" and "required_object_id" in req:
                # Verificar se tem conhecimento específico (objeto em certo nível)
                required_objects = req["required_object_id"]
                if isinstance(required_objects, list):
                    if not any(self.get_object_discovery_level(obj_id) > 0 for obj_id in required_objects):
                        return False
                elif self.get_object_discovery_level(required_objects) == 0:
                    return False
            
            elif req_type == "observation" and "required_detail_id" in req:
                # Verificar se observou determinado detalhe
                detail_id = req.get("required_detail_id")
                area_id = req.get("required_area_id")
                
                # Se for uma lista, verificar se observou pelo menos um
                if isinstance(detail_id, list):
                    found = False
                    for d_id in detail_id:
                        for area_key, details in self.player_data["last_seen_details"].items():
                            if d_id in details:
                                found = True
                                break
                        if found:
                            break
                    if not found:
                        return False
                # Se for um único ID, verificar se foi observado
                elif area_id and str(area_id) in self.player_data["last_seen_details"]:
                    if detail_id not in self.player_data["last_seen_details"][str(area_id)]:
                        return False
                else:
                    # Verificar em todas as áreas
                    found = False
                    for area_key, details in self.player_data["last_seen_details"].items():
                        if detail_id in details:
                            found = True
                            break
                    if not found:
                        return False
        
        return True
    
    def increase_skill_by_object(self, object_id):
        """Aumenta habilidades baseado na interação com objetos"""
        # Implementar sistema baseado no sistema-especializacao.json
        skill_mapping = {
            1: "conhecimento_historico",    # Baú Misterioso
            2: "conexao_informacoes",       # Diário de Thaddeus
            3: "analise_evidencias",        # Frasco de Veneno
            4: "conhecimento_historico",    # Chave Ornamentada
            5: "conexao_informacoes",       # Carta Selada
            6: "conhecimento_historico",    # Mapa Antigo
            7: "conhecimento_historico",    # Medalhão de Família Reed
            8: "descoberta_ambiental",      # Livro de Botânica
            9: "interpretacao_comportamento", # Caderno de Anotações
            10: "analise_evidencias",       # Taça de Vinho
            11: "analise_evidencias",       # Almofariz com Resíduos
            12: "conhecimento_historico",   # Árvore Genealógica
            13: "conexao_informacoes",      # Registro de Contas
            14: "conexao_informacoes",      # Páginas Arrancadas do Diário
            15: "analise_evidencias",       # Garrafa de Vinho Especial
            16: "conexao_informacoes",      # Nota Cifrada
            17: "conhecimento_historico",   # Escritura Original
            18: "analise_evidencias",       # Relatório Médico
            19: "conexao_informacoes",      # Documento Falsificado
            20: "analise_evidencias"        # Lençóis Manchados
        }
        
        if object_id in skill_mapping:
            skill = skill_mapping[object_id]
            self.player_data["skills"][skill] += 10
            
            # Mostrar mensagem só se o objeto não foi examinado antes
            if str(object_id) not in self.player_data.get("examined_objects", []):
                skill_names = {
                    "analise_evidencias": "Análise de Evidências",
                    "conhecimento_historico": "Conhecimento Histórico",
                    "interpretacao_comportamento": "Interpretação de Comportamento",
                    "descoberta_ambiental": "Descoberta Ambiental",
                    "conexao_informacoes": "Conexão de Informações"
                }
                print_colored(f"\nSua habilidade de {skill_names.get(skill, skill)} aumentou!", "yellow")
                
                # Marcar objeto como examinado
                if "examined_objects" not in self.player_data:
                    self.player_data["examined_objects"] = []
                self.player_data["examined_objects"].append(str(object_id))
    
    def save_game(self):
        """Salva o estado atual do jogo em um arquivo JSON"""
        if not self.save_file:
            return False
            
        save_data = {
            "current_location": self.current_location,
            "current_area": self.current_area,
            "player_data": self.player_data,
            "dynamic_details_cache": self.dynamic_details_cache,
            "last_saved": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao salvar jogo: {e}")
            return False
    
    def load_game(self):
        """Carrega o estado do jogo de um arquivo JSON"""
        if not self.save_file or not os.path.exists(self.save_file):
            return False
            
        try:
            with open(self.save_file, "r", encoding="utf-8") as f:
                save_data = json.load(f)
                
            self.current_location = save_data["current_location"]
            self.current_area = save_data["current_area"]
            self.player_data = save_data["player_data"]
            
            # Carregar cache de detalhes dinâmicos se existir
            if "dynamic_details_cache" in save_data:
                self.dynamic_details_cache = save_data["dynamic_details_cache"]
            
            return True
        except Exception as e:
            print(f"Erro ao carregar jogo: {e}")
            return False
    
    def list_saved_games(self):
        """Lista todos os jogos salvos disponíveis"""
        saves = []
        for file in os.listdir():
            if file.startswith("save_") and file.endswith(".json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    player_id = file.replace("save_", "").replace(".json", "")
                    last_saved = data.get("last_saved", "Data desconhecida")
                    
                    # Obter informações adicionais
                    location_name = "Desconhecido"
                    if "current_location" in data:
                        loc_id = data["current_location"]
                        for loc in self.data.get("ambientes", {}).values():
                            if loc.get("location_id") == loc_id:
                                location_name = loc.get("name", "Desconhecido")
                                break
                    
                    clues_count = len(data.get("player_data", {}).get("discovered_clues", []))
                    case_solved = data.get("player_data", {}).get("case_solved", False)
                    
                    saves.append({
                        "player_id": player_id,
                        "file": file,
                        "last_saved": last_saved,
                        "location": location_name,
                        "clues": clues_count,
                        "solved": case_solved
                    })
                except:
                    continue
        
        return saves

# Funções auxiliares para a interface
def clear_screen():
    """Limpa a tela do console"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_title(text):
    """Imprime um título formatado"""
    print("\033[1m\033[95m" + text + "\033[0m")
    print("-" * len(text))

def print_colored(text, color):
    """Imprime texto colorido"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m"
    }
    print(colors.get(color, "") + text + "\033[0m")

def confirm(message):
    """Pede confirmação ao usuário"""
    response = input(f"{message} (s/n): ").lower()
    return response in ["s", "sim", "y", "yes"]

def generate_player_id():
    """Gera um ID único para o jogador"""
    return uuid.uuid4().hex[:8]

# Função principal
def main():
    # Caminho para a história
    historia_path = "./historias/o_segredo_da_estalagem_do_cervo_negro"
    
    # ASCII Art para o título
    ascii_art = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██████╗     ███████╗███████╗ ██████╗ ██████╗ ███████╗   ║
    ║  ██╔═══██╗    ██╔════╝██╔════╝██╔════╝██╔══██╗██╔════╝    ║
    ║  ██║   ██║    ███████╗█████╗  ██║     ██████╔╝█████╗      ║
    ║  ██║   ██║    ╚════██║██╔══╝  ██║     ██╔══██╗██╔══╝      ║
    ║  ╚██████╔╝    ███████║███████╗╚██████╗██║  ██║███████╗    ║
    ║   ╚═════╝     ╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝    ║                                                           ║
    ║       O SEGREDO DA ESTALAGEM DO CERVO NEGRO               ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
"""
    
    # Verificar se o diretório existe
    if not os.path.exists(historia_path):
        print(f"Erro: O diretório '{historia_path}' não foi encontrado.")
        print("Verifique se você está executando o script do diretório correto.")
        return
    
    # Iniciar o motor do jogo e carregar dados básicos para menus iniciais
    game = GameEngine(historia_path)
    game.load_game_data()
    
    while True:
        clear_screen()
        print(ascii_art)
        print("\nUm mistério interativo com auxílio de IA")
        
        # Menu inicial
        print("\n1. Novo Jogo")
        print("2. Carregar Jogo")
        print("3. Sair")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == "1":
            # Pedir ID do jogador
            clear_screen()
            print_title("Novo Jogo")
            
            print("Por favor, escolha um identificador único para seu jogador.")
            print("Este ID será usado para salvar e carregar seu progresso.")
            print("Deixe em branco para gerar um ID automático.")
            
            player_id = input("\nID do jogador: ").strip()
            if not player_id:
                player_id = generate_player_id()
                print(f"ID gerado automaticamente: {player_id}")
            
            # Verificar se já existe um save com este ID
            save_file = f"save_{player_id}.json"
            if os.path.exists(save_file):
                if not confirm(f"Já existe um jogo salvo com o ID '{player_id}'. Deseja sobrescrevê-lo?"):
                    continue
            
            # Configurar o jogador e iniciar o jogo
            game.set_player_id(player_id)
            try:
                # Iniciar o jogo
                game.start_game()
            except Exception as e:
                print(f"Erro inesperado: {e}")
                import traceback
                traceback.print_exc()
        
        elif choice == "2":
            saves = game.list_saved_games()
            
            if not saves:
                print("\nNenhum jogo salvo encontrado.")
                input("Pressione Enter para voltar...")
                continue
            
            clear_screen()
            print_title("Carregar Jogo")
            
            print("Jogos salvos disponíveis:")
            for i, save in enumerate(saves):
                status = "✓ Resolvido" if save["solved"] else f"📜 {save['clues']} pistas"
                print(f"{i+1}. Jogador: {save['player_id']} | Último local: {save['location']} | {status}")
                print(f"   Último salvamento: {save['last_saved']}")
            
            print(f"{len(saves)+1}. Voltar")
            
            try:
                choice_num = int(input("\nEscolha um jogo para carregar: "))
                if choice_num == len(saves) + 1:
                    continue
                
                if 1 <= choice_num <= len(saves):
                    save = saves[choice_num - 1]
                    game.set_player_id(save["player_id"])
                    
                    if game.load_game():
                        print("Jogo carregado com sucesso!")
                        sleep(1)
                        game.game_loop()
                    else:
                        print("Erro ao carregar o jogo salvo.")
                        input("Pressione Enter para voltar...")
                else:
                    print("Opção inválida.")
                    input("Pressione Enter para voltar...")
            except ValueError:
                print("Por favor, digite um número.")
                input("Pressione Enter para voltar...")
        
        elif choice == "3":
            print("\nObrigado por jogar O Segredo da Estalagem do Cervo Negro!")
            break
        
        else:
            print("\nOpção inválida.")
            sleep(1)

if __name__ == "__main__":
    main()