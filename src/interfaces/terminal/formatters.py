def color_text(text: str, color: str) -> str:
    """
    Colore um texto usando códigos ANSI.
    
    Args:
        text: Texto a ser colorido
        color: Nome da cor ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan')
    
    Returns:
        str: Texto colorido
    """
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m'
    }
    
    if color not in COLORS:
        return text
        
    return f"{COLORS[color]}{text}\033[0m"

def style_text(text: str, bold: bool = False, underline: bool = False) -> str:
    """
    Aplica estilos ao texto.
    
    Args:
        text: Texto a ser estilizado
        bold: Se True, aplica negrito
        underline: Se True, aplica sublinhado
        
    Returns:
        Texto estilizado
    """
    result = text
    if bold:
        result = f"\033[1m{result}"
    if underline:
        result = f"\033[4m{result}"
    if bold or underline:
        result = f"{result}\033[0m"
    return result

class TextFormatter:
    """Formata texto para exibição no terminal usando cores ANSI."""
    
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m'
    }
    
    def header(self, text: str) -> str:
        """Formata cabeçalhos principais."""
        return f"{self.COLORS['bold']}{self.COLORS['cyan']}{text}{self.COLORS['reset']}"
        
    def subheader(self, text: str) -> str:
        """Formata subcabeçalhos."""
        return f"{self.COLORS['bold']}{self.COLORS['blue']}{text}{self.COLORS['reset']}"
        
    def text(self, text: str) -> str:
        """Formata texto normal."""
        return text
        
    def highlight(self, text: str) -> str:
        """Destaca texto importante."""
        return f"{self.COLORS['yellow']}{text}{self.COLORS['reset']}"
        
    def character(self, text: str) -> str:
        """Formata nomes de personagens."""
        return f"{self.COLORS['magenta']}{text}{self.COLORS['reset']}"
        
    def item(self, text: str) -> str:
        """Formata nomes de itens."""
        return f"{self.COLORS['green']}{text}{self.COLORS['reset']}"
        
    def command(self, text: str) -> str:
        """Formata comandos."""
        return f"{self.COLORS['bold']}{self.COLORS['cyan']}{text}{self.COLORS['reset']}"
        
    def error(self, text: str) -> str:
        """Formata mensagens de erro."""
        return f"{self.COLORS['red']}{text}{self.COLORS['reset']}"
        
    def success(self, text: str) -> str:
        """Formata mensagens de sucesso."""
        return f"{self.COLORS['green']}{text}{self.COLORS['reset']}"
        
    def warning(self, text: str) -> str:
        """Formata avisos."""
        return f"{self.COLORS['yellow']}{text}{self.COLORS['reset']}"
        
    def info(self, text: str) -> str:
        """Formata informações."""
        return f"{self.COLORS['blue']}{text}{self.COLORS['reset']}"

