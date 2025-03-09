# src/interfaces/terminal/cli.py
import os
import sys
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# Importações dos componentes existentes
from src.repositories.story_repository import StoryRepository
from src.repositories.character_repository import CharacterRepository
from src.repositories.dialogue_repository import DialogueRepository
from src.repositories.location_repository import LocationRepository
from src.repositories.object_repository import ObjectRepository
from src.repositories.player_progress_repository import PlayerProgressRepository
from src.repositories.qrcode_repository import QRCodeRepository

from src.managers.character_manager import CharacterManager
from src.managers.qrcode_manager import QRCodeManager

from src.interfaces.terminal.commands import CommandProcessor
from src.interfaces.terminal.cli_helpers import display_header, clear_screen, pause, get_input
from src.interfaces.terminal.formatters import color_text, style_text

from typing import Optional, Dict, Any
from .cli_helpers import CLIHelper
from .formatters import TextFormatter

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
            story_title = self.story_repository.get_by_id(self.db_session, session['story_id'])['title']
            print(f"{i}. {story_title} - {session['created_at']} ({session['game_status']})")
        
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
                player_id=player.player_id,  # Agora usa o player_id do objeto
                story_id=story_id
            )
            
            if not result["success"]:
                print(f"Erro ao criar sessão: {result.get('error', '')}")
                return
            
            self.session_id = result["session_id"]
            
            # Inicializar estado do jogo
            self.game_state = self.player_repository.get_session_state(
                self.db_session,
                self.session_id
            )
            
            if not self.game_state["success"]:
                print(f"Erro ao carregar estado do jogo: {self.game_state['error']}")
                return
                
            # Exibir introdução da história
            self.display_introduction()
            
            # Iniciar loop do jogo
            self.game_loop()
            
        except Exception as e:
            print(f"Erro ao iniciar nova sessão: {e}")
    
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
            self.game_state = self.player_repository.get_session_state(
                self.db_session, self.session_id
            )
            
            if not self.game_state:
                return False
            
            # Extrair informações importantes
            session_data = self.game_state.get("session", {})
            self.player_id = session_data.get("player_id")
            self.story_id = session_data.get("story_id")
            
            # Carregar story
            story = self.story_repository.get_by_id(self.db_session, self.story_id)
            if not story:
                return False
            
            return True
        except Exception as e:
            print(f"Erro ao carregar estado do jogo: {str(e)}")
            return False
    
    def display_introduction(self) -> None:
        """Exibe a introdução da história."""
        clear_screen()
        
        story = self.story_repository.get_by_id(self.db_session, self.story_id)
        if not story:
            print("Erro: História não encontrada!")
            pause()
            return
        
        display_header(story['title'])
        
        print("\n" + style_text(story['description'], bold=True))
        pause()
        
        print("\n" + story['introduction'])
        pause()
        
        # Exibir informação do local inicial
        if self.game_state and self.game_state.get("current_location"):
            print(f"\nVocê está no {self.game_state['current_location']['name']}")
            print(self.game_state['current_location']['description'])
            pause()
    
    def game_loop(self) -> None:
        """Loop principal do jogo."""
        while not self.should_exit and self.session_id:
            try:
                # Atualiza o estado do jogo
                self.load_game_state()
                
                # Exibe o estado atual
                self.display_current_state()
                
                # Solicita comando
                command = get_input("\n> ").strip()
                
                # Processa o comando
                if command.lower() == "sair":
                    if get_input("Tem certeza que deseja sair? (s/n): ").lower() == "s":
                        self.should_exit = True
                        continue
                else:
                    self.process_command(command)
            except Exception as e:
                print(f"Erro no loop do jogo: {str(e)}")
                pause()
    
    def display_current_state(self) -> None:
        """Exibe o estado atual do jogo"""
        if not self.game_state["current_location_id"]:
            return
            
        location_data = self.location_repository.get_location(
            self.db_session,
            self.game_state["current_location_id"]
        )
        
        self.helper.display_location_info(location_data)
    
    def process_command(self, command: str) -> None:
        """Processa um comando do usuário."""
        if not command:
            return
            
        self.command_processor.process(command)