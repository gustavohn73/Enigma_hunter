# src/interfaces/terminal/dialogue_handler.py

from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from ...managers.character_manager import CharacterManager

class DialogueHandler:
    """Handles dialogue interactions with characters in the CLI interface"""
    
    def __init__(self, cli, character_manager: CharacterManager):
        self.cli = cli
        self.character_manager = character_manager
        self.in_dialogue = False
        self.current_character: Optional[Dict[str, Any]] = None
        self.challenge_mode = False
        
    def start_dialogue(self, character_id: int) -> bool:
        """
        Initiates a dialogue with a character.
        
        Args:
            character_id: ID of the character to talk to
            
        Returns:
            bool: True if dialogue started successfully, False otherwise
        """
        try:
            # Get character data
            character_data = self.character_manager.get_character(
                self.cli.db_session, 
                character_id
            )
            
            if not character_data:
                print("Personagem não encontrado.")
                return False
                
            self.current_character = character_data
            self.in_dialogue = True
            
            # Start conversation with character
            result = self.character_manager.start_conversation(
                self.cli.db_session,
                self.cli.game_session.session_id,
                character_id
            )
            
            print(f"\n{character_data['name']}: {result['message']}")
            print("\nDigite 'sair diálogo' para encerrar a conversa.")
            
            # Enter dialogue loop
            self.dialogue_loop()
            return True
            
        except Exception as e:
            print(f"Erro ao iniciar diálogo: {str(e)}")
            return False
            
    def dialogue_loop(self) -> None:
        """Main dialogue loop for interacting with characters"""
        while self.in_dialogue and self.current_character:
            try:
                user_input = input("\nVocê: ").strip()
                
                # Check for special commands
                if user_input.lower() in ["sair diálogo", "sair dialogo"]:
                    print(f"\nEncerrando conversa com {self.current_character['name']}.")
                    self.in_dialogue = False
                    return
                
                # Send message to character
                result = self.character_manager.send_message(
                    self.cli.db_session,
                    self.cli.game_session.session_id,
                    self.current_character['id'],
                    user_input
                )
                
                # Display character response
                print(f"\n{self.current_character['name']}: {result['response']}")
                
                # Check for character evolution
                if result.get("evolution", False):
                    print(f"\n[PERSONAGEM EVOLUIU PARA NÍVEL {result['new_level']}]")
                    print("O personagem mudou sua postura e pode revelar novas informações.")
                
                # Check for challenge activation
                if result.get("challenge_activated", False):
                    print("\n[DESAFIO ATIVADO!]")
                    print("Demonstre seu conhecimento ou apresente evidências apropriadas.")
                    
                    if result.get("challenge_question"):
                        print(f"Pergunta do desafio: {result['challenge_question']}")
                
            except Exception as e:
                print(f"Erro durante o diálogo: {str(e)}")
                print("Tentando continuar conversa...")