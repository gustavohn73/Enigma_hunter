# src/interfaces/terminal/commands.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import shlex

from src.interfaces.terminal.cli_helpers import pause, get_input, clear_screen
from src.interfaces.terminal.formatters import color_text, style_text
from src.interfaces.terminal.dialogue_handler import DialogueHandler
from ...repositories.location_repository import LocationRepository

class CommandProcessor:
    def __init__(self, cli):
        self.cli = cli
        self.dialogue_handler = DialogueHandler(cli, cli.character_manager)
        self.location_repository = LocationRepository()
        
        # Dicionário de comandos
        self.commands = {
            "ajuda": self.cmd_help,
            "sair": self.cmd_exit,
            "ir": self.cmd_go_to,
            "falar": self.cmd_talk_to,
            "examinar": self.cmd_examine,
            "pegar": self.cmd_take,
            "inventario": self.cmd_inventory,
            "inventário": self.cmd_inventory,
            "habilidades": self.cmd_skills,
            "areas": self.cmd_areas,
            "áreas": self.cmd_areas,
            "teoria": self.cmd_theory,
            "acusar": self.cmd_accuse,
            "salvar": self.cmd_save,
            "progresso": self.cmd_progress,
            "combinar": self.cmd_combine,
            "ajuda": self.cmd_help,
            "debug": self.cmd_debug,
            "explorar": self.cmd_explore
        }
        
        # Sinônimos de comandos
        self.synonyms = {
            "mover": "ir",
            "andar": "ir",
            "conversar": "falar",
            "dialogar": "falar",
            "olhar": "examinar",
            "investigar": "examinar",
            "inspecionar": "examinar",
            "coletar": "pegar",
            "itens": "inventario",
            "objetos": "inventario",
            "especialidades": "habilidades",
            "explorar": "examinar",
            "ver": "examinar",
            "misturar": "combinar",
            "juntar": "combinar"
        }
    
    def process(self, command_string: str) -> bool:
        """Processa um comando do usuário."""
        try:
            # Divide o comando por espaços preservando citações
            parts = shlex.split(command_string)
            if not parts:
                return False
                
            cmd = parts[0].lower()
            args = parts[1:]
            
            # Verifica sinônimos
            if cmd in self.synonyms:
                cmd = self.synonyms[cmd]
                
            # Executa o comando
            if cmd in self.commands:
                result = self.commands[cmd](args)
                
                # Se o comando foi bem-sucedido, recarrega o estado do jogo
                if result:
                    self.cli.load_game_state()
                    
                return result
            else:
                print("Comando não reconhecido. Digite 'ajuda' para ver os comandos disponíveis.")
                return False
        except Exception as e:
            print(f"Erro ao processar comando: {str(e)}")
            return False
    
    def cmd_help(self, args: List[str]) -> bool:
        """Exibe ajuda sobre comandos disponíveis."""
        clear_screen()
        print(style_text("AJUDA DO ENIGMA HUNTER", bold=True))
        
        if not args:
            # Ajuda geral
            print("\nComandos disponíveis:")
            print("  ajuda [comando]      - Exibe ajuda geral ou sobre um comando específico")
            print("  ir <local/área>      - Move-se para um local ou área")
            print("  falar <personagem>   - Inicia diálogo com um personagem")
            print("  examinar <alvo>      - Examina um local, área ou objeto")
            print("  pegar <objeto>       - Pega um objeto e adiciona ao inventário")
            print("  inventário           - Mostra os objetos em seu inventário")
            print("  habilidades          - Mostra suas especializações e níveis")
            print("  áreas                - Lista áreas visíveis na localização atual")
            print("  teoria               - Registra uma teoria sobre o caso")
            print("  acusar <personagem>  - Acusa um personagem (apenas com evidências suficientes)")
            print("  salvar               - Salva o progresso atual")
            print("  progresso            - Mostra seu progresso na história")
            print("  combinar <obj1> <obj2> - Tenta combinar dois objetos do inventário")
            print("  sair                 - Sai do jogo")
        else:
            # Ajuda específica
            cmd = args[0].lower()
            if cmd in self.synonyms:
                cmd = self.synonyms[cmd]
                
            if cmd == "ir":
                print("\nComando: ir <local/área>")
                print("Uso: Move o jogador para um local ou área específica.")
                print("Exemplos:")
                print("  ir Sala Principal")
                print("  ir Cozinha")
            elif cmd == "falar":
                print("\nComando: falar <personagem>")
                print("Uso: Inicia um diálogo com um personagem presente no local.")
                print("Exemplos:")
                print("  falar Bartender")
                print("  falar Guarda")
            # ... outras ajudas específicas
        
        pause()
        return True
    
    def cmd_exit(self, args: List[str]) -> bool:
        """Sai do jogo após confirmação e salva o progresso."""
        confirm = get_input("Tem certeza que deseja sair? (s/n): ")
        if confirm.lower() == "s":
            # Salvar jogo antes de sair
            result = self.cli.player_repository.save_game_state(
                self.cli.db_session,
                self.cli.session_id
            )
            
            if not result["success"]:
                print(f"Erro ao salvar jogo: {result.get('error', 'Erro desconhecido')}")
            
            self.cli.should_exit = True
            print("\nRetornando ao menu principal...")
        return True
    
    def cmd_go_to(self, args: List[str]) -> bool:
        """Move o jogador para um local ou área."""
        if not args:
            print("Para onde você quer ir? (Use 'ir <número>')")
            return False
        
        try:
            target_num = int(args[0])
            print(f"\nTentando mover para posição {target_num}...")
            
            current_location = self.cli.game_state.get("current_location")
            if not current_location:
                print("Erro: Você não está em nenhum local!")
                return False
            
            # Buscar áreas disponíveis
            areas = self.cli.location_repository.get_available_areas(
                self.cli.db_session,
                current_location["id"]
            )
            
            if not areas:
                print("Erro: Não há áreas disponíveis neste local!")
                return False
            
            if 1 <= target_num <= len(areas):
                area = areas[target_num - 1]
                print(f"Tentando mover para: {area['name']}")
                
                result = self.cli.player_repository.move_to_area(
                    self.cli.db_session,
                    self.cli.session_id,
                    area['id']
                )
                
                if result["success"]:
                    print(f"\nVocê se move para {result['area_name']}.")
                    if result.get('area_description'):
                        print(f"\n{result['area_description']}")
                    return True
                else:
                    print(f"Erro ao mover: {result.get('message', 'Erro desconhecido')}")
                    return False
            
            print(f"Número inválido. Use um número entre 1 e {len(areas)}.")
            return False
            
        except ValueError:
            print("Por favor, use um número para se mover.")
            return False
        except Exception as e:
            print(f"Erro ao mover: {str(e)}")
            return False
    
    def cmd_talk_to(self, args: List[str]) -> bool:
        """Inicia diálogo com um personagem."""
        if not args:
            print("Com quem você quer falar? (Use 'falar <número>')")
            return False

        try:
            target_num = int(args[0])
            available_npcs = self.cli.game_state.get("available_npcs", [])

            if not available_npcs:
                print("Não há personagens disponíveis para conversar aqui.")
                return False

            if target_num < 1 or target_num > len(available_npcs):
                print(f"Número inválido. Use um número entre 1 e {len(available_npcs)}.")
                return False

            npc = available_npcs[target_num - 1]
            print(f"\nIniciando conversa com {npc['name']}...")

            # Iniciar diálogo usando o character_id
            result = self.cli.character_manager.start_conversation(
                self.cli.db_session,
                self.cli.session_id,
                npc['id']
            )

            if result.get("success"):
                print(f"\n{npc['name']}: {result['message']}\n")  # Alterado aqui
                return True
            else:
                print(f"Erro ao iniciar diálogo: {result.get('message', 'Erro desconhecido')}")  # Alterado aqui
                return False

        except ValueError:
            print("Por favor, use um número para selecionar o personagem.")
            return False
        except Exception as e:
            print(f"Erro ao iniciar diálogo: {e}")
            return False
    
    def cmd_examine(self, args: List[str]) -> bool:
        """Examina um local, área ou objeto."""
        if not args:
            # Examina o local atual
            current_location_id = self.cli.game_state.get("current_location_id")
            if current_location_id:
                location = self.cli.location_repository.get_by_id(
                    self.cli.db_session, current_location_id
                )
                print(f"\n{location['description']}")
                return True
            return False
        
        target = " ".join(args).lower()
        
        # Verifica se é um objeto no inventário
        inventory = self.cli.game_state.get("inventory", [])
        for obj_id in inventory:
            obj = self.cli.object_repository.get_by_id(self.cli.db_session, obj_id)
            if obj and obj['name'].lower() == target:
                # Examina o objeto e potencialmente evolui o conhecimento
                obj_level = self.cli.player_repository.get_object_level_data(
                    self.cli.db_session, self.cli.session_id, obj_id
                )
                
                print(f"\n{obj['name']}: {obj_level.get('description', obj['base_description'])}")
                
                # Atualiza especialização
                self.cli.player_repository.update_specialization(
                    self.cli.db_session,
                    self.cli.session_id,
                    "analise",
                    5,
                    "exame_objeto",
                    str(obj_id)
                )
                
                # Verifica evolução
                result = self.cli.object_repository.check_object_evolution(
                    self.cli.db_session, obj_id, obj_level.get("level", 0)
                )
                
                if result.get("can_evolve", False):
                    self.cli.player_repository.update_object_level(
                        self.cli.db_session,
                        self.cli.session_id,
                        obj_id,
                        result["next_level"]
                    )
                    print(color_text("\nVocê percebe novos detalhes sobre este objeto!", "green"))
                
                return True
        
        # Verifica se é um objeto visível no local
        current_location_id = self.cli.game_state.get("current_location_id")
        current_area_id = self.cli.game_state.get("current_area_id")
        
        objects = self.cli.object_repository.get_by_location(
            self.cli.db_session, current_location_id, current_area_id
        )
        
        for obj in objects:
            if obj['name'].lower() == target:
                print(f"\n{obj['name']}: {obj['base_description']}")
                return True
        
        # Verifica se é uma área visível
        areas = self.cli.location_repository.get_areas_by_location(
            self.cli.db_session, current_location_id
        )
        
        for area in areas:
            if area['name'].lower() == target:
                print(f"\n{area['name']}: {area['description']}")
                
                # Atualiza especialização
                self.cli.player_repository.update_specialization(
                    self.cli.db_session,
                    self.cli.session_id,
                    "exploracao",
                    5,
                    "exame_area",
                    str(area['area_id'])
                )
                
                return True
        
        print(f"Você não consegue examinar '{target}'.")
        return False
    
    def cmd_take(self, args: List[str]) -> bool:
        """Pega um objeto e adiciona ao inventário."""
        if not args:
            print("O que você quer pegar? (Use 'pegar <objeto>')")
            return False
            
        target = " ".join(args).lower()
        
        # Verifica objetos visíveis no local
        current_location_id = self.cli.game_state.get("current_location_id")
        current_area_id = self.cli.game_state.get("current_area_id")
        
        objects = self.cli.object_repository.get_by_location(
            self.cli.db_session, current_location_id, current_area_id
        )
        
        for obj in objects:
            if obj['name'].lower() == target:
                if not obj['is_collectible']:
                    print(f"Você não pode pegar {obj['name']}.")
                    return False
                    
                # Adiciona ao inventário
                result = self.cli.player_repository.add_to_inventory(
                    self.cli.db_session, self.cli.session_id, obj['object_id']
                )
                
                if result["success"]:
                    if result.get("is_new", True):
                        print(f"Você pegou {obj['name']} e adicionou ao seu inventário.")
                    else:
                        print(f"Você já tem {obj['name']} em seu inventário.")
                    return True
                else:
                    print(f"Não foi possível pegar {obj['name']}. {result.get('message', '')}")
                    return False
        
        print(f"Não há nada chamado '{target}' para pegar aqui.")
        return False
    
    def cmd_inventory(self, args: List[str]) -> bool:
        """Mostra os objetos no inventário."""
        inventory = self.cli.player_repository.get_inventory(
            self.cli.db_session, self.cli.session_id
        )
        
        if not inventory:
            print("Seu inventário está vazio.")
            return True
            
        print(style_text("\nINVENTÁRIO:", bold=True))
        for item in inventory:
            print(f"- {item['name']}")
            
        return True
    
    def cmd_skills(self, args: List[str]) -> bool:
        """Mostra as especializações e níveis do jogador."""
        specializations = self.cli.player_repository.get_specializations(
            self.cli.db_session, self.cli.session_id
        )
        
        if not specializations:
            print("Você ainda não desenvolveu nenhuma especialização.")
            return True
            
        print(style_text("\nESPECIALIZAÇÕES:", bold=True))
        for category, data in specializations.items():
            level_label = "★" * data["level"]
            print(f"- {category.capitalize()}: {level_label} (Nível {data['level']}, {data['points']} pontos)")
            
        return True
    
    def cmd_areas(self, args: List[str]) -> bool:
        """Lista áreas visíveis na localização atual."""
        current_location_id = self.cli.game_state.get("current_location_id")
        
        if not current_location_id:
            print("Você não está em nenhum local. Algo deu errado!")
            return False
            
        areas = self.cli.location_repository.get_areas_by_location(
            self.cli.db_session, current_location_id
        )
        
        # Filtra por nível de exploração
        env_level = self.cli.player_repository.get_location_exploration_level(
            self.cli.db_session, self.cli.session_id, current_location_id
        )
        
        visible_areas = [area for area in areas if area['discovery_level_required'] <= env_level]
        
        if not visible_areas:
            print("Você não vê nenhuma área específica para explorar.")
            return True
            
        print(style_text("\nÁREAS VISÍVEIS:", bold=True))
        for area in visible_areas:
            print(f"- {area['name']}")
            
        return True
    
    # Implementações adicionais dos outros comandos
    def cmd_theory(self, args: List[str]) -> bool:
        """Registra uma teoria sobre o caso."""
        print("Função de teoria ainda não implementada.")
        return True
    
    def cmd_accuse(self, args: List[str]) -> bool:
        """Acusa um personagem."""
        print("Função de acusação ainda não implementada.")
        return True
    
    def cmd_save(self, args: List[str]) -> bool:
        """Salva o progresso atual."""
        print("O jogo é salvo automaticamente a cada ação importante.")
        return True
    
    def cmd_progress(self, args: List[str]) -> bool:
        """Mostra o progresso na história."""
        print("Função de progresso ainda não implementada.")
        return True
    
    def cmd_combine(self, args: List[str]) -> bool:
        """Tenta combinar dois objetos do inventário."""
        print("Função de combinação ainda não implementada.")
        return True
    
    def cmd_debug(self, args: List[str]) -> bool:
        """Comandos de depuração."""
        if not args:
            print("Comando de depuração requer argumentos.")
            return False
        
        subcmd = args[0].lower()
        
        if subcmd == "state":
            print(f"Estado do jogo: {self.cli.game_state}")
        elif subcmd == "reload":
            self.cli.load_game_state()
            print("Estado recarregado.")
        else:
            print(f"Subcomando de depuração desconhecido: {subcmd}")
            
        return True
    
    def cmd_explore(self, args: List[str]) -> bool:
        """Explora uma área ou localização."""
        try:
            current_location = self.cli.game_state.get("current_location")
            if not current_location:
                print("Você não está em nenhum local!")
                return False
                
            areas = self.cli.location_repository.get_available_areas(
                self.cli.db_session, 
                current_location["id"]
            )
            
            if not areas:
                print("\nNão há áreas disponíveis para explorar aqui.")
                return False
                
            print("\nÁreas disponíveis para explorar:")
            for i, area in enumerate(areas, 1):
                print(f"{i}. {area['name']}")
            
            choice = get_input("\nEscolha uma área para explorar (0 para voltar): ")
            if choice == "0":
                return True
                
            try:
                idx = int(choice)
                if 1 <= idx <= len(areas):
                    return self.cmd_go_to([str(idx)])
            except ValueError:
                print("Escolha inválida!")
            
            return False
        except Exception as e:
            print(f"Erro ao explorar: {e}")
            return False
    
    def _check_location_requirements(self, location_id: int) -> bool:
        """Verifica se os requisitos para acessar um local foram cumpridos"""
        # Implementar verificação de requisitos
        return True