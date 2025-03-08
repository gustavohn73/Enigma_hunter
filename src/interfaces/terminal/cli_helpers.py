import os
from typing import List, Dict, Any, Optional
from .formatters import TextFormatter

def clear_screen() -> None:
    """Limpa a tela do terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def pause() -> None:
    """Pausa a execução até o usuário pressionar Enter."""
    input("\nPressione Enter para continuar...")

def get_input(prompt: str) -> str:
    """
    Obtém entrada do usuário com um prompt formatado.
    
    Args:
        prompt: Texto a ser exibido como prompt
    
    Returns:
        str: Entrada do usuário
    """
    return input(f"{prompt}").strip()

def display_header(text: str) -> None:
    """
    Exibe um cabeçalho formatado.
    
    Args:
        text: Texto do cabeçalho
    """
    width = len(text) + 4
    border = "=" * width
    print(f"\n{border}")
    print(f"  {text}")
    print(f"{border}\n")

class CLIHelper:
    def __init__(self, formatter: TextFormatter):
        self.formatter = formatter
        
    def display_location_info(self, location_data: Dict[str, Any]) -> None:
        """Exibe informações sobre a localização atual."""
        print("\n" + self.formatter.header(f"= {location_data['name']} ="))
        print(self.formatter.text(location_data['description']))
        
        # Exibe áreas disponíveis
        if location_data.get('areas'):
            print("\n" + self.formatter.subheader("Áreas Visíveis:"))
            for area in location_data['areas']:
                print(self.formatter.highlight(f"- {area['name']}"))
                
        # Exibe personagens presentes
        if location_data.get('characters'):
            print("\n" + self.formatter.subheader("Personagens Presentes:"))
            for char in location_data['characters']:
                print(self.formatter.character(f"- {char['name']}"))
                
    def display_inventory(self, items: List[Dict[str, Any]]) -> None:
        """Exibe o inventário do jogador."""
        if not items:
            print(self.formatter.info("Seu inventário está vazio."))
            return
            
        print("\n" + self.formatter.header("= Inventário ="))
        for item in items:
            print(self.formatter.item(f"- {item['name']}"))
            if item.get('description'):
                print(self.formatter.text(f"  {item['description']}"))
                
    def display_help(self, commands: Dict[str, str], synonyms: Dict[str, str]) -> None:
        """Exibe ajuda sobre comandos disponíveis."""
        print("\n" + self.formatter.header("= Comandos Disponíveis ="))
        
        for cmd, desc in commands.items():
            print(f"\n{self.formatter.command(cmd)}")
            print(self.formatter.text(desc))
            
            # Exibe sinônimos se existirem
            cmd_synonyms = [k for k, v in synonyms.items() if v == cmd]
            if cmd_synonyms:
                print(self.formatter.info(f"Sinônimos: {', '.join(cmd_synonyms)}"))
                
    def confirm_action(self, message: str) -> bool:
        """Solicita confirmação do usuário para uma ação."""
        response = input(f"\n{self.formatter.warning(message)} (s/n): ").lower()
        return response in ['s', 'sim', 'y', 'yes']
        
    def display_error(self, message: str) -> None:
        """Exibe mensagem de erro formatada."""
        print(self.formatter.error(f"\nErro: {message}"))
        
    def display_success(self, message: str) -> None:
        """Exibe mensagem de sucesso formatada."""
        print(self.formatter.success(f"\n{message}"))