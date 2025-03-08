import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .interfaces.terminal.cli import EnigmaHunterCLI
from .config import DATABASE_URL

def setup_logging():
    """Configura o sistema de logs"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('enigma_hunter.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Função principal para iniciar o jogo"""
    try:
        # Configurar logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Iniciando Enigma Hunter CLI...")
        
        # Conectar ao banco de dados usando URL da config
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Iniciar CLI
        cli = EnigmaHunterCLI(session)
        
        # Exibir banner
        print("""
╔═══════════════════════════════════════╗
║           ENIGMA HUNTER CLI           ║
║        Investigação Terminal          ║
╚═══════════════════════════════════════╝
        """)
        
        # Iniciar loop principal
        cli.main_menu()
        
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
        print("\nOcorreu um erro inesperado. Consulte os logs para mais detalhes.")
        sys.exit(1)
    finally:
        if 'session' in locals():
            session.close()
            
if __name__ == "__main__":
    main()