# src/utils/db-setup-script.py
"""
Script para inicializar o banco de dados do Enigma Hunter e carregar dados iniciais.
Este script cria as tabelas no banco de dados e carrega os dados de histórias,
ambientes, personagens, objetos e QR codes a partir dos arquivos JSON.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Adiciona o diretório pai ao path para importações relativas
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importa os modelos definidos
from src.models.db_models import Base, Story, Location, LocationArea, AreaDetail, Character, CharacterLevel
from src.models.db_models import EvolutionTrigger, EvidenceRequirement, GameObject, ObjectLevel, Clue
from src.models.db_models import QRCode, PromptTemplate, IAConversationLog

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup_db')

# Constantes
DATABASE_DIR = Path(__file__).resolve().parent.parent.parent / "database"

def init_db(db_url):
    """Inicializa o banco de dados com o esquema definido"""
    logger.info(f"Conectando ao banco de dados: {db_url}")
    
    # Certifica-se que o diretório database existe
    DATABASE_DIR.mkdir(exist_ok=True, parents=True)
    
    engine = create_engine(db_url)
    
    logger.info("Criando tabelas...")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    return Session()

def setup_templates(session):
    """Configura templates de prompt padrão para a IA"""
    logger.info("Configurando templates de prompt para IA...")
    
    default_prompts = [
        {
            "template_name": "character_dialogue_base",
            "template_type": "character",
            "context_level": 0,
            "prompt_structure": """Você é {character_name}, {character_description}.

CONTEXTO DO PERSONAGEM:
{character_context}

PERSONALIDADE:
{character_personality}

CONHECIMENTO DISPONÍVEL NESTE ESTÁGIO ({character_level}):
{available_knowledge}

RESTRIÇÕES:
{knowledge_restrictions}

INSTRUÇÕES ESPECIAIS:
1. Mantenha-se fiel ao personagem e seu estágio atual de conhecimento.
2. Não revele informações além do que o personagem sabe no estágio atual.
3. Responda de forma natural e conversacional, mantendo o estilo de fala do personagem.
4. Suas respostas devem ter no máximo 3 parágrafos.

HISTÓRICO DA CONVERSA:
{conversation_history}

Jogador: {player_input}

{character_name}:""",
            "variables": [
                "character_name", "character_description", "character_context", 
                "character_personality", "character_level", "available_knowledge", 
                "knowledge_restrictions", "conversation_history", "player_input"
            ],
            "purpose": "Diálogo básico com personagem",
            "usage_instructions": "Use este template para conversas iniciais com personagens"
        },
        {
            "template_name": "location_description",
            "template_type": "location",
            "context_level": 0,
            "prompt_structure": """Descreva a seguinte localização para o jogador:

LOCALIZAÇÃO: {location_name}

DESCRIÇÃO BASE:
{location_description}

DETALHES VISÍVEIS NO NÍVEL {exploration_level}:
{visible_details}

ATMOSFERA:
{atmosphere}

ELEMENTOS NOTÁVEIS:
{notable_elements}

INSTRUÇÕES:
1. Descreva a localização de forma imersiva e atmosférica.
2. Destaque apenas elementos visíveis no nível atual de exploração.
3. Não mencione áreas ou objetos que requerem nível de exploração maior.
4. Use linguagem envolvente que estimule os sentidos.
5. Mantenha a descrição em até 4 parágrafos.

RESULTADO:""",
            "variables": [
                "location_name", "location_description", "exploration_level", 
                "visible_details", "atmosphere", "notable_elements"
            ],
            "purpose": "Descrição de ambientes",
            "usage_instructions": "Use este template para descrever localizações com base no nível de exploração"
        },
        {
            "template_name": "object_examination",
            "template_type": "object",
            "context_level": 0,
            "prompt_structure": """Descreva o seguinte objeto para o jogador:

OBJETO: {object_name}

DESCRIÇÃO BASE:
{object_description}

CONHECIMENTO NO NÍVEL {object_level}:
{level_knowledge}

DETALHES OBSERVÁVEIS:
{observable_details}

HISTÓRIA/CONTEXTO CONHECIDO:
{known_context}

INSTRUÇÕES:
1. Descreva o objeto de forma detalhada e tangível.
2. Revele apenas informações apropriadas ao nível atual de conhecimento.
3. Não mencione propriedades ou usos que requerem nível maior.
4. Use linguagem precisa e descritiva.
5. Mantenha a descrição em até 3 parágrafos.

RESULTADO:""",
            "variables": [
                "object_name", "object_description", "object_level", 
                "level_knowledge", "observable_details", "known_context"
            ],
            "purpose": "Exame de objetos",
            "usage_instructions": "Use este template para descrever objetos com base no nível de conhecimento"
        },
    ]
    
    for prompt_data in default_prompts:
        variables = prompt_data.pop("variables")
        prompt_data["variables"] = json.dumps(variables)
        
        prompt = PromptTemplate(**prompt_data)
        existing = session.query(PromptTemplate).filter_by(template_name=prompt.template_name).first()
        if not existing:
            session.add(prompt)
            logger.info(f"Adicionado template de prompt: {prompt.template_name}")
    
    # Commit as mudanças
    session.commit()
    logger.info("Templates de prompt configurados com sucesso")

def load_story(session, story_dir):
    """Carrega uma história a partir do diretório fornecido"""
    story_path = Path(story_dir)
    historia_base_path = story_path / "historia_base.json"
    
    if not historia_base_path.exists():
        logger.error(f"Arquivo historia_base.json não encontrado em {story_path}")
        return None
    
    logger.info(f"Carregando história de {historia_base_path}")
    with open(historia_base_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
    
    # Carregar configuração de especialização da história
    specialization_config = {}
    sistema_especializacao_path = story_path / "data" / "sistema-especializacao.json"
    if sistema_especializacao_path.exists():
        try:
            with open(sistema_especializacao_path, 'r', encoding='utf-8') as file:
                specialization_config = json.load(file)
            logger.info(f"Configuração de especialização carregada de {sistema_especializacao_path}")
        except Exception as e:
            logger.warning(f"Erro ao carregar configuração de especialização: {e}")
    
    # Criar objeto Story
    story = Story(
        title=story_data.get('title', 'História sem título'),
        description=story_data.get('description', ''),
        introduction=story_data.get('introduction', ''),
        conclusion=story_data.get('conclusion', ''),
        difficulty_level=story_data.get('difficulty_level', 1),
        solution_criteria=json.dumps(story_data.get('solution_criteria', {})),
        specialization_config=json.dumps(specialization_config),
        is_active=True
    )
    
    session.add(story)
    session.flush()  # Para obter o ID da história
    logger.info(f"História '{story.title}' criada com ID {story.story_id}")
    
    # Agora carrega os componentes da história
    load_environments(session, story, story_path)
    load_characters(session, story, story_path)
    load_objects_and_clues(session, story, story_path)
    load_qrcodes(session, story, story_path)
    
    session.commit()
    logger.info(f"História '{story.title}' carregada completamente")
    return story

def load_environments(session, story, story_path):
    """Carrega ambientes da história"""
    ambientes_dir = story_path / "ambientes"
    if not ambientes_dir.exists():
        logger.warning(f"Diretório de ambientes não encontrado: {ambientes_dir}")
        return
    
    logger.info("Carregando ambientes...")
    for arquivo in ambientes_dir.glob("Ambiente_*.json"):
        with open(arquivo, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            for ambiente_data in data if isinstance(data, list) else [data]:
                location_id = ambiente_data.get("location_id")
                if not location_id:
                    continue
                
                # Criar objeto Location
                location = Location(
                    location_id=location_id,
                    name=ambiente_data.get("name", "Ambiente sem nome"),
                    description=ambiente_data.get("description", ""),
                    is_locked=ambiente_data.get("is_locked", False),
                    unlock_condition=ambiente_data.get("unlock_condition"),
                    navigation_map=json.dumps(ambiente_data.get("navigation_map", {})),
                    is_starting_location=ambiente_data.get("is_starting_location", False)
                )
                
                # Associar à história
                location.stories.append(story)
                session.add(location)
                session.flush()  # Para obter o ID da localização
                
                # Processar áreas
                for area_data in ambiente_data.get("areas", []):
                    area_id = area_data.get("area_id")
                    if not area_id:
                        continue
                    
                    # Criar objeto LocationArea
                    area = LocationArea(
                        area_id=area_id,
                        location_id=location.location_id,
                        name=area_data.get("name", "Área sem nome"),
                        description=area_data.get("description", ""),
                        initially_visible=area_data.get("initially_visible", True),
                        connected_areas=json.dumps(area_data.get("connected_areas", [])),
                        discovery_level_required=area_data.get("discovery_level_required", 0)
                    )
                    session.add(area)
                    session.flush()
                    
                    # Processar detalhes
                    for detail_data in area_data.get("details", []):
                        detail_id = detail_data.get("detail_id")
                        if not detail_id:
                            continue
                        
                        # Criar objeto AreaDetail
                        detail = AreaDetail(
                            detail_id=detail_id,
                            area_id=area.area_id,
                            name=detail_data.get("name", "Detalhe sem nome"),
                            description=detail_data.get("description", ""),
                            discovery_level_required=detail_data.get("discovery_level_required", 0),
                            has_clue=detail_data.get("has_clue", False),
                            clue_id=detail_data.get("clue_id")
                        )
                        session.add(detail)
                
                logger.info(f"Carregado ambiente: {location.name} (ID: {location.location_id})")

def load_characters(session, story, story_path):
    """Carrega personagens da história"""
    personagens_dir = story_path / "personagens"
    if not personagens_dir.exists():
        logger.warning(f"Diretório de personagens não encontrado: {personagens_dir}")
        return
    
    logger.info("Carregando personagens...")
    for arquivo in personagens_dir.glob("Personagem_*.json"):
        with open(arquivo, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            for personagem_data in data if isinstance(data, list) else [data]:
                character_id = personagem_data.get("character_id")
                if not character_id:
                    continue
                
                # Criar objeto Character
                character = Character(
                    character_id=character_id,
                    name=personagem_data.get("name", "Personagem sem nome"),
                    base_description=personagem_data.get("base_description", ""),
                    personality=personagem_data.get("personality", ""),
                    appearance=personagem_data.get("appearance", ""),
                    is_culprit=personagem_data.get("is_culprit", False),
                    motive=personagem_data.get("motive", ""),
                    location_schedule=json.dumps(personagem_data.get("location_schedule", {}))
                )
                
                # Associar à história
                character.stories.append(story)
                session.add(character)
                session.flush()
                
                # Processar níveis do personagem
                for level_data in personagem_data.get("levels", []):
                    level_number = level_data.get("level_number", 0)
                    
                    # Criar objeto CharacterLevel
                    level = CharacterLevel(
                        character_id=character.character_id,
                        level_number=level_number,
                        knowledge_scope=level_data.get("knowledge_scope", ""),
                        narrative_stance=level_data.get("narrative_stance", ""),
                        is_defensive=level_data.get("is_defensive", False),
                        dialogue_parameters=level_data.get("dialogue_parameters", ""),
                        ia_instruction_set=json.dumps(level_data.get("ia_instruction_set", {}))
                    )
                    session.add(level)
                    session.flush()
                    
                    # Processar gatilhos de evolução
                    for trigger_data in level_data.get("triggers", []):
                        # Criar objeto EvolutionTrigger
                        trigger = EvolutionTrigger(
                            level_id=level.level_id,
                            trigger_keyword=trigger_data.get("trigger_keyword", ""),
                            contextual_condition=trigger_data.get("contextual_condition", ""),
                            defensive_response=trigger_data.get("defensive_response", ""),
                            challenge_question=trigger_data.get("challenge_question", ""),
                            success_response=trigger_data.get("success_response", ""),
                            fail_response=trigger_data.get("fail_response", ""),
                            multi_step_verification=trigger_data.get("multi_step_verification", False)
                        )
                        session.add(trigger)
                        session.flush()
                        
                        # Processar requisitos de evidência
                        for req_data in trigger_data.get("requirements", []):
                            # Criar objeto EvidenceRequirement
                            req = EvidenceRequirement(
                                trigger_id=trigger.trigger_id,
                                requirement_type=req_data.get("requirement_type", ""),
                                required_object_id=req_data.get("required_object_id"),
                                required_knowledge=json.dumps(req_data.get("required_knowledge", {})),
                                verification_method=req_data.get("verification_method", ""),
                                hint_if_incorrect=req_data.get("hint_if_incorrect", ""),
                                minimum_presentation_level=req_data.get("minimum_presentation_level", 0)
                            )
                            session.add(req)
                
                logger.info(f"Carregado personagem: {character.name} (ID: {character.character_id})")

def load_objects_and_clues(session, story, story_path):
    """Carrega objetos e pistas da história"""
    data_dir = story_path / "data"
    if not data_dir.exists():
        logger.warning(f"Diretório de dados não encontrado: {data_dir}")
        return
    
    # Carrega objetos
    objetos_path = data_dir / "objetos.json"
    if objetos_path.exists():
        logger.info("Carregando objetos...")
        with open(objetos_path, 'r', encoding='utf-8') as file:
            objetos_data = json.load(file)
            
            for objeto_data in objetos_data:
                object_id = objeto_data.get("object_id")
                if not object_id:
                    continue
                
                # Criar objeto GameObject
                game_object = GameObject(
                    object_id=object_id,
                    story_id=story.story_id,
                    name=objeto_data.get("name", "Objeto sem nome"),
                    base_description=objeto_data.get("base_description", ""),
                    is_collectible=objeto_data.get("is_collectible", True),
                    initial_location_id=objeto_data.get("initial_location_id"),
                    initial_area_id=objeto_data.get("initial_area_id"),
                    discovery_condition=objeto_data.get("discovery_condition", "")
                )
                session.add(game_object)
                session.flush()
                
                # Processar níveis do objeto
                for level_data in objeto_data.get("levels", []):
                    level_number = level_data.get("level_number", 0)
                    
                    # Criar objeto ObjectLevel
                    level = ObjectLevel(
                        object_id=game_object.object_id,
                        level_number=level_number,
                        level_description=level_data.get("level_description", ""),
                        level_attributes=json.dumps(level_data.get("level_attributes", {})),
                        evolution_trigger=level_data.get("evolution_trigger", ""),
                        related_clue_id=level_data.get("related_clue_id")
                    )
                    session.add(level)
                
                logger.info(f"Carregado objeto: {game_object.name} (ID: {game_object.object_id})")
    
    # Carrega pistas
    pistas_path = data_dir / "pistas.json"
    if pistas_path.exists():
        logger.info("Carregando pistas...")
        with open(pistas_path, 'r', encoding='utf-8') as file:
            pistas_data = json.load(file)
            
            for pista_data in pistas_data:
                clue_id = pista_data.get("clue_id")
                if not clue_id:
                    continue
                
                # Criar objeto Clue
                clue = Clue(
                    clue_id=clue_id,
                    story_id=story.story_id,
                    name=pista_data.get("name", "Pista sem nome"),
                    description=pista_data.get("description", ""),
                    type=pista_data.get("type", ""),
                    relevance=pista_data.get("relevance", 1),
                    is_key_evidence=pista_data.get("is_key_evidence", False),
                    related_aspect=pista_data.get("related_aspect", ""),
                    discovery_conditions=json.dumps(pista_data.get("discovery_conditions", {}))
                )
                session.add(clue)
                
                logger.info(f"Carregada pista: {clue.name} (ID: {clue.clue_id})")

def load_qrcodes(session, story, story_path):
    """Carrega QR codes da história"""
    data_dir = story_path / "data"
    qrcodes_path = data_dir / "qrcodes.json"
    if not qrcodes_path.exists():
        logger.warning(f"Arquivo de QR codes não encontrado: {qrcodes_path}")
        return
    
    logger.info("Carregando QR codes...")
    with open(qrcodes_path, 'r', encoding='utf-8') as file:
        qrcodes_data = json.load(file)
        
        for qrcode_data in qrcodes_data:
            uuid = qrcode_data.get("uuid")
            if not uuid:
                continue
            
            # Criar objeto QRCode
            qrcode = QRCode(
                uuid=uuid,
                target_type=qrcode_data.get("target_type", ""),
                target_id=qrcode_data.get("target_id"),
                action=qrcode_data.get("action", ""),
                parameters=json.dumps(qrcode_data.get("parameters", {})),
                access_requirements=json.dumps(qrcode_data.get("access_requirements", {})),
                location_requirement=json.dumps(qrcode_data.get("location_requirement", {}))
            )
            session.add(qrcode)
            
            logger.info(f"Carregado QR code: {uuid} (Tipo: {qrcode.target_type}, ID: {qrcode.target_id})")

def main():
    parser = argparse.ArgumentParser(description='Inicializar banco de dados do Enigma Hunter')
    parser.add_argument('--db', default=f'sqlite:///{DATABASE_DIR}/enigma_hunter.db', 
                      help='URL de conexão do banco de dados')
    parser.add_argument('--story-dir', help='Diretório da história para carregar')
    parser.add_argument('--reset', action='store_true', help='Resetar banco de dados existente')
    args = parser.parse_args()
    
    # Reseta o banco se solicitado
    db_file = Path(args.db.replace('sqlite:///', ''))
    if args.reset and db_file.exists():
        logger.info(f"Removendo banco de dados existente: {db_file}")
        db_file.unlink()
    
    # Inicializar banco de dados
    session = init_db(args.db)
    
    try:
        # Configurar templates de prompt padrão
        setup_templates(session)
        
        # Carregar história se diretório fornecido
        if args.story_dir:
            story = load_story(session, args.story_dir)
            if story:
                logger.info(f"História '{story.title}' carregada com sucesso")
        
        logger.info("Inicialização do banco de dados concluída com sucesso!")
    except Exception as e:
        logger.error(f"Erro durante a inicialização do banco de dados: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()