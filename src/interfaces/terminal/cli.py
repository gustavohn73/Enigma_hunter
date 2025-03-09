# src/interfaces/terminal/cli.py
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from uuid import uuid4

# Importações dos repositórios
from src.repositories.story_repository import StoryRepository
from src.repositories.character_repository import CharacterRepository
from src.repositories.dialogue_repository import DialogueRepository
from src.repositories.location_repository import LocationRepository
from src.repositories.object_repository import ObjectRepository
from src.repositories.player_progress_repository import PlayerProgressRepository
from src.repositories.qrcode_repository import QRCodeRepository

# Importações dos managers
from src.managers.character_manager import CharacterManager
from src.managers.qrcode_manager import QRCodeManager

# Importações da interface
from src.interfaces.terminal.commands import CommandProcessor
from src.interfaces.terminal.cli_helpers import (
    display_header, 
    clear_screen, 
    pause, 
    get_input,
    CLIHelper
)
from src.interfaces.terminal.formatters import TextFormatter, color_text, style_text

class EnigmaHunterCLI:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.formatter = TextFormatter()
        self.helper = CLIHelper(self.formatter)
        
        # Inicializar repositórios primeiro
        self.story_repository = StoryRepository()
        self.character_repository = CharacterRepository()
        self.dialogue_repository = DialogueRepository()
        self.location_repository = LocationRepository()
        self.object_repository = ObjectRepository()
        self.player_repository = PlayerProgressRepository()
        self.qrcode_repository = QRCodeRepository()
        
        # Inicializar gerenciadores com todos os parâmetros necessários
        self.character_manager = CharacterManager(
            character_repository=self.character_repository,
            dialogue_repository=self.dialogue_repository,
            ai_model="llama3",  # valores padrão
            api_url="http://localhost:11434/api/generate",
            max_retries=3,
            retry_delay=2,
            timeout=30
        )
        
        self.qrcode_manager = QRCodeManager(
            self.qrcode_repository,
            self.player_repository
        )
        
        # Inicializar o processor de comandos depois dos managers
        self.command_processor = CommandProcessor(self)
        
        # Inicializar estado do jogo
        self.game_session = None
        self.game_state = {
            "current_location_id": None,
            "visited_locations": set()
        }
        self.player_id = None
        self.player_name = None
        self.story_id = None
        self.session_id = None
        self.should_exit = False
        
    def main_menu(self) -> None:
        """Exibe o menu principal do jogo."""
        while not self.should_exit:
            clear_screen()
            display_header("ENIGMA HUNTER")
            
            print("\n" + style_text("MENU PRINCIPAL", bold=True))
            print("\n1. Nova Sessão")
            print("2. Carregar Sessão")
            print("3. Sair")
            
            choice = get_input("\nEscolha uma opção: ")
            
            if choice == "1":
                self.new_session_menu()
            elif choice == "2":
                self.load_session_menu()
            elif choice == "3":
                self.should_exit = True
                print("Obrigado por jogar Enigma Hunter!")
            else:
                print("Opção inválida. Tente novamente.")
                pause()
    
    def new_session_menu(self) -> None:
        """Menu para criar uma nova sessão de jogo."""
        clear_screen()
        display_header("NOVA SESSÃO")
        
        # Obter nome do jogador
        self.player_name = get_input("Digite seu nome: ")
        if not self.player_name:
            print("Nome inválido!")
            pause()
            return
        
        # Listar histórias disponíveis
        stories = self.story_repository.get_all(self.db_session, include_inactive=False)
        
        if not stories:
            print("Não há histórias disponíveis.")
            pause()
            return
            
        print("\nHistórias Disponíveis:")
        for i, story in enumerate(stories, 1):
            print(f"{i}. {story['title']} (Dificuldade: {story['difficulty_level']})")
        
        # Selecionar história
        story_choice = get_input("\nEscolha uma história (número): ")
        try:
            story_idx = int(story_choice) - 1
            if 0 <= story_idx < len(stories):
                self.story_id = stories[story_idx]['story_id']
                self.start_new_session(self.player_name, self.story_id)
            else:
                print("Escolha inválida!")
                pause()
        except ValueError:
            print("Entrada inválida!")
            pause()
    
    def load_session_menu(self) -> None:
        """Menu para carregar uma sessão existente."""
        clear_screen()
        display_header("CARREGAR SESSÃO")
        
        # Solicitar nome do jogador
        player_name = get_input("Digite seu nome: ")
        if not player_name:
            print("Nome inválido!")
            pause()
            return
            
        # Buscar sessões do jogador
        sessions = self.player_repository.list_player_sessions(self.db_session, player_name)
        
        if not sessions:
            print(f"Não há sessões salvas para {player_name}.")
            pause()
            return
            
        print("\nSessões Disponíveis:")
        for i, session in enumerate(sessions, 1):
            # A história já vem com o título no dicionário da sessão
            print(f"{i}. {session['story_title']} - {session['created_at']} ({session['game_status']})")
        
        # Selecionar sessão
        session_choice = get_input("\nEscolha uma sessão (número): ")
        try:
            session_idx = int(session_choice) - 1
            if 0 <= session_idx < len(sessions):
                self.load_session(sessions[session_idx]['session_id'])
            else:
                print("Escolha inválida!")
                pause()
        except ValueError:
            print("Entrada inválida!")
            pause()
    
    def start_new_session(self, player_name: str, story_id: int) -> None:
        """Inicia uma nova sessão de jogo."""
        try:
            # Criar jogador se não existir
            player = self.player_repository.get_or_create_player(
                self.db_session, 
                username=player_name
            )
            
            # Criar sessão
            result = self.player_repository.create_player_session(
                self.db_session,
                player_id=player.player_id,
                story_id=story_id
            )
            
            if not result["success"]:
                print(f"Erro ao criar sessão: {result.get('error', '')}")
                pause()
                return
            
            self.session_id = result["session_id"]
            
            # Inicializar estado do jogo
            self.game_state = self.player_repository.get_session_state(
                self.db_session,
                self.session_id
            )
            
            if not self.game_state["success"]:
                print(f"Erro ao carregar estado do jogo: {self.game_state['error']}")
                pause()
                return
                
            # Exibir introdução da história
            self.display_introduction()
            
            # Resetar estado de saída
            self.should_exit = False
            
            # Iniciar loop do jogo
            self.game_loop()
            
            # Ao sair do loop, retornar ao menu principal
            self.return_to_main_menu()
            
        except Exception as e:
            print(f"Erro ao iniciar nova sessão: {e}")
            pause()

    def return_to_main_menu(self) -> None:
        """Reseta o estado do jogo e retorna ao menu principal."""
        self.game_state = {
            "current_location_id": None,
            "visited_locations": set()
        }
        self.player_id = None
        self.player_name = None
        self.story_id = None
        self.session_id = None
        self.should_exit = False
    
    def load_session(self, session_id: str) -> None:
        """Carrega uma sessão existente."""
        self.session_id = session_id
        
        # Carregar estado do jogo
        success = self.load_game_state()
        
        if not success:
            print("Erro ao carregar sessão!")
            pause()
            return
        
        print(f"Sessão carregada com sucesso!")
        pause()
        
        # Iniciar loop do jogo
        self.game_loop()
    
    def load_game_state(self) -> bool:
        """Carrega o estado atual do jogo."""
        try:
            # Obter state do jogador
            state = self.player_repository.get_session_state(
                self.db_session, self.session_id
            )
            
            if not state or not state.get("success", False):
                print("Erro ao carregar estado da sessão.")
                return False
            
            # Atualizar o estado interno
            self.game_state = state
            
            # Extrair informações importantes
            session_data = state.get("session", {})
            self.player_id = session_data.get("player_id")
            self.story_id = session_data.get("story_id")
            
            return True
        except Exception as e:
            print(f"Erro ao carregar estado do jogo: {str(e)}")
            return False
    
    def display_introduction(self) -> None:
        """Exibe a introdução da história."""
        clear_screen()
        story = self.story_repository.get_by_id(self.db_session, self.story_id)
        if story:
            print(f"\n{style_text('='*41, bold=True)}")
            print(f"{style_text(story['title'], bold=True)}")
            print(f"{style_text('='*41, bold=True)}\n")
            print(f"{story['introduction']}\n")
            pause()
            
            if story.get('initial_scene'):
                print(f"\n{story['initial_scene']}\n")
                pause()
    
    def game_loop(self) -> None:
        """Loop principal do jogo."""
        while not self.should_exit:
            try:
                self.display_current_state()
                command = get_input("\n> ")
                
                if command.lower() == 'sair':
                    if get_input("Tem certeza que deseja sair? (s/n): ").lower() == 's':
                        self.save_game()
                        self.should_exit = True
                        print("\nRetornando ao menu principal...")
                        pause()
                        break  # Sai do loop para retornar ao menu
                else:
                    self.process_command(command)
                    
            except Exception as e:
                print(f"Erro no loop do jogo: {e}")
                pause()
    
    def display_current_state(self) -> None:
        """Exibe o estado atual do jogo."""
        clear_screen()
        
        if not self.game_state.get("current_location"):
            print("Erro: Localização atual não encontrada!")
            return
            
        # Exibir localização atual
        location = self.game_state["current_location"]
        print(f"\n= {style_text(location['name'], bold=True)} =")
        print(f"{location['description']}\n")
        
        # Se estiver em uma área específica
        if self.game_state.get("current_area"):
            area = self.game_state["current_area"]
            print(f"\n[{style_text(area['name'], bold=True)}]")
            print(f"{area['description']}\n")
            
            # Mostrar personagens na área
            characters = self.character_repository.get_characters_in_area(
                self.db_session,
                area['id']
            )
            if characters:
                print(style_text("\nPersonagens Presentes (use 'falar'):", bold=True))
                for i, char in enumerate(characters, 1):
                    print(f"{i}. {char['name']}")
            
            # Mostrar objetos na área
            objects = self.object_repository.get_objects_in_area(
                self.db_session,
                area['id']
            )
            if objects:
                print(style_text("\nObjetos Visíveis (use 'examinar'):", bold=True))
                for i, obj in enumerate(objects, 1):
                    print(f"{i}. {obj['name']}")
        else:
            # Mostrar áreas do ambiente atual
            areas = self.location_repository.get_available_areas(
                self.db_session, 
                location["id"]
            )
            if areas:
                print(style_text("\nÁreas Disponíveis (use 'ir'):", bold=True))
                for i, area in enumerate(areas, 1):
                    print(f"{i}. {area['name']}")
            
            # Mostrar ambientes conectados
            connected_locations = self.location_repository.get_connected_locations(
                self.db_session,
                location["id"]
            )
            if connected_locations:
                print(style_text("\nAmbientes Conectados (use 'ir'):", bold=True))
                base_index = len(areas) + 1
                for i, loc in enumerate(connected_locations, base_index):
                    print(f"{i}. {loc['name']}")
        
        print(f"\n{style_text('Digite ajuda para ver os comandos disponíveis', bold=True)}")
    
    def process_command(self, command: str) -> None:
        """Processa um comando do usuário."""
        try:
            if not command:
                return
                
            # Usar diretamente o CommandProcessor
            result = self.command_processor.process(command)
            
            # Se o processador de comandos não conseguiu lidar com o comando
            if not result:
                print("Comando não reconhecido. Digite 'ajuda' para ver os comandos disponíveis.")
            
            # Recarregar o estado do jogo após o comando bem-sucedido
            if result:
                self.load_game_state()
            
        except Exception as e:
            print(f"Erro ao processar comando: {e}")

    def return_to_location(self) -> None:
        """Retorna ao ambiente principal da área atual."""
        self.game_state["current_area"] = None
        self.game_state = self.player_repository.get_session_state(
            self.db_session,
            self.session_id
        )

    def save_game(self) -> None:
        try:
            progress = self.player_repository.get_by_session_id(
                self.db_session, 
                self.session_id
            )
            if progress:
                progress.game_status = 'saved'  # Usando status ao invés de game_status
                self.db_session.commit()
                print("Jogo salvo com sucesso!")
        except Exception as e:
            print(f"Erro ao salvar jogo: {e}")