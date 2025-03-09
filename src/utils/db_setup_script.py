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
from sqlalchemy import exc
import uuid
from sqlalchemy.orm import Session 
from src.models.db_models import PlayerProgress
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))



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


def load_story_data(session: Session, story_dir: str) -> None:
    """
    Carrega os dados da história no banco de dados.
    """
    logger = logging.getLogger('setup_db')
    logger.info(f"Carregando dados da história do diretório: {story_dir}")
    
    try:
        # Carregar historia_base.json
        historia_path = Path(story_dir) / "historia_base.json"
        if not historia_path.exists():
            raise FileNotFoundError(f"Arquivo historia_base.json não encontrado em {story_dir}")
            
        with open(historia_path, 'r', encoding='utf-8') as f:
            story_data = json.load(f)
            
        # Criar objeto Story
        story = Story(
            title=story_data['title'],
            description=story_data['description'],
            introduction=story_data['introduction'],
            conclusion=story_data.get('conclusion'),
            difficulty_level=story_data.get('difficulty_level', 1),
            solution_criteria=story_data.get('solution_criteria', {}),
            specialization_config=story_data.get('specialization_config', {}),
            is_active=True
        )
        
        session.add(story)
        session.flush()  # Para obter o ID da história
        
        logger.info(f"História base carregada: {story.title}")
        
        # Carregar outros dados usando as funções corretas
        load_environments(session, story, Path(story_dir))
        load_characters(session, story, Path(story_dir))
        load_objects_and_clues(session, story, Path(story_dir))
        load_qrcodes(session, story, Path(story_dir))
        
        logger.info("Dados da história carregados com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados da história: {str(e)}")
        raise

def create_and_add_story(session, story_data, specialization_config):
    try:
        story = Story(
            title=story_data.get('title', 'História sem título'),
            # ... (rest of your Story object creation) ...
        )
        session.add(story)
        session.flush()  # Get the ID of the story
        return story
    except exc.IntegrityError as e:
        logger.error(f"Integrity error inserting story: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Error creating or inserting story: {e}")
        session.rollback()
        return None

def load_story(session, story_dir):
    story_path = Path(story_dir)
    story_data = load_story_data(story_path)

    if story_data is None:
      return None

    specialization_config = load_specialization_config(story_path)

    story = create_and_add_story(session, story_data, specialization_config)

    if story:
        load_story_components(session, story, story_path)
        try:
            session.commit()
            return story
        except Exception as e:
            logger.error(f"Error committing changes for story: {e}")
            session.rollback()
            return None
    else:
        return None


    

def load_specialization_config(story_path):
    """
    Carrega a configuração do sistema de especialização de um arquivo JSON.

    Args:
        story_path: Um objeto Path apontando para o diretório da história.

    Returns:
        Um dicionário contendo a configuração de especialização, ou um dicionário vazio ({}) em caso de erro.
    """
    sistema_especializacao_path = story_path / "data" / "sistema-especializacao.json"

    if not sistema_especializacao_path.exists():
        logger.warning(f"Arquivo de configuração de especialização não encontrado: {sistema_especializacao_path}")
        return {}  # Retorna um dicionário vazio

    logger.info(f"Carregando configuração de especialização de {sistema_especializacao_path}")
    try:
        with open(sistema_especializacao_path, 'r', encoding='utf-8') as file:
            specialization_config = json.load(file)
        return specialization_config
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON em {sistema_especializacao_path}: {e}")
        return {}  # Retorna um dicionário vazio
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar configuração de especialização: {e}")
        return {} # Return empty dict.

def load_story_components(session, story, story_path):
    load_environments(session, story, story_path)
    load_characters(session, story, story_path)
    load_objects_and_clues(session, story, story_path)
    load_qrcodes(session, story, story_path)

def load_environment_data(arquivo):
    """Carrega os dados de um único arquivo JSON de ambiente."""
    try:
        with open(arquivo, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Erro ao carregar ou decodificar arquivo de ambiente {arquivo}: {e}")
        return None

def create_and_add_location(session, story, location_data):
    """Cria um objeto Location e o insere no banco de dados."""
    try:
        location = Location(
            location_id=location_data.get("location_id"),
            story_id=story.story_id,  # Definir explicitamente o story_id
            name=location_data.get("name", "Ambiente sem nome"),
            description=location_data.get("description", ""),
            is_locked=location_data.get("is_locked", False),
            unlock_condition=location_data.get("unlock_condition"),
            navigation_map=json.dumps(location_data.get("navigation_map", {})),
            is_starting_location=location_data.get("is_starting_location", False)
        )
        session.add(location)
        session.flush()  # Para obter o ID
        logger.info(f"Criado ambiente: {location.name} (ID: {location.location_id}, "
                   f"Story ID: {location.story_id}, Starting: {location.is_starting_location})")
        return location
    except Exception as e:
        logger.error(f"Erro ao criar ambiente: {e}")
        session.rollback()
        return None

def create_and_add_area(session, location, area_data):
    """Cria um objeto LocationArea e o insere no banco de dados."""
    try:
        area = LocationArea(
            area_id=area_data.get("area_id"),
            location_id=location.location_id,
            name=area_data.get("name", "Área sem nome"),
            description=area_data.get("description", ""),
            initially_visible=area_data.get("initially_visible", True),
            connected_areas=json.dumps(area_data.get("connected_areas", [])),
            discovery_level_required=area_data.get("discovery_level_required", 0)
        )
        session.add(area)
        session.flush()
        return area
    except KeyError as e:
        logger.error(f"Chave faltando nos dados da área: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir área: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir área: {e}")
        session.rollback()
        return None

def create_and_add_detail(session, area, detail_data):
    """Cria um objeto AreaDetail e o insere no banco de dados."""
    try:
        detail = AreaDetail(
            detail_id=detail_data.get("detail_id"),
            area_id=area.area_id,
            name=detail_data.get("name", "Detalhe sem nome"),
            description=detail_data.get("description", ""),
            discovery_level_required=detail_data.get("discovery_level_required", 0),
            has_clue=detail_data.get("has_clue", False),
            clue_id=detail_data.get("clue_id")
        )
        session.add(detail)
        return detail
    except KeyError as e:
        logger.error(f"Chave faltando nos dados do detalhe: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir detalhe: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir detalhe: {e}")
        session.rollback()
        return None

def load_environments(session, story, story_path):
    """Carrega ambientes da história"""
    ambientes_dir = story_path / "ambientes"
    if not ambientes_dir.exists():
        logger.warning(f"Diretório de ambientes não encontrado: {ambientes_dir}")
        return

    logger.info(f"Carregando ambientes para história {story.story_id}...")
    
    for arquivo in ambientes_dir.glob("Ambiente_*.json"):
        logger.info(f"Processando arquivo: {arquivo}")
        ambiente_data_list = load_environment_data(arquivo)
        
        if ambiente_data_list is None:
            continue

        # Garante que ambiente_data_list seja uma lista
        if not isinstance(ambiente_data_list, list):
            ambiente_data_list = [ambiente_data_list]

        for ambiente_data in ambiente_data_list:
            # Garantir que story_id está definido
            ambiente_data['story_id'] = story.story_id
            
            location = create_and_add_location(session, story, ambiente_data)
            if location is None:
                logger.error(f"Falha ao criar ambiente do arquivo {arquivo}")
                continue
            
            # Log detalhado
            logger.info(f"Ambiente criado: {location.name}")
            logger.info(f"- ID: {location.location_id}")
            logger.info(f"- Story ID: {location.story_id}")
            logger.info(f"- Is Starting: {location.is_starting_location}")
            
            # Processar áreas
            for area_data in ambiente_data.get("areas", []):
                area = create_and_add_area(session, location, area_data)
                if area:
                    logger.info(f"- Área adicionada: {area.name}")

    # Commit ao final para garantir que tudo foi salvo
    try:
        session.commit()
        logger.info("Todos os ambientes foram carregados com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar ambientes: {e}")
        session.rollback()

def load_character_data(arquivo):    
    """Carrega os dados de um único arquivo JSON de personagem."""
    try:
        with open(arquivo, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Erro ao carregar ou decodificar arquivo de personagem {arquivo}: {e}")
        return None
    
def create_and_add_character(session, story, character_data):
    """Cria um objeto Character e o insere no banco de dados."""
    try:
        character = Character(
            character_id=character_data.get("character_id"),
            name=character_data.get("name", "Personagem sem nome"),
            base_description=character_data.get("base_description", ""),
            personality=character_data.get("personality", ""),
            appearance=character_data.get("appearance", ""),
            is_culprit=character_data.get("is_culprit", False),
            motive=character_data.get("motive", ""),
            location_schedule=json.dumps(character_data.get("location_schedule", {}))
        )
        character.stories.append(story)
        session.add(character)
        session.flush()
        return character
    except KeyError as e:
        logger.error(f"Chave faltando nos dados do personagem: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir personagem: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir personagem: {e}")
        session.rollback()
        return None
    
def create_and_add_character_level(session, character, level_data):
    """Creates a CharacterLevel object and adds it to the database."""
    try:
        level = CharacterLevel(
            character_id=character.character_id,
            level_number=level_data.get("level_number", 0),
            knowledge_scope=level_data.get("knowledge_scope", ""),
            narrative_stance=level_data.get("narrative_stance", ""),
            is_defensive=level_data.get("is_defensive", False),
            dialogue_parameters=level_data.get("dialogue_parameters", ""),
            ia_instruction_set=json.dumps(level_data.get("ia_instruction_set", {}))
        )
        session.add(level)
        session.flush()
        return level
    except KeyError as e:
        logger.error(f"Missing key in character level data: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Integrity error inserting character level: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Unexpected error inserting character level: {e}")
        session.rollback()
        return None

def create_and_add_evolution_trigger(session, level, trigger_data):
    """Creates an EvolutionTrigger object and adds it to the database."""
    try:
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
        return trigger
    except KeyError as e:
        logger.error(f"Missing key in evolution trigger data: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Integrity error inserting evolution trigger: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Unexpected error inserting evolution trigger: {e}")
        session.rollback()
        return None

def create_and_add_evidence_requirement(session, trigger, req_data):
    """Creates an EvidenceRequirement object and adds it to the database."""
    try:
        req = EvidenceRequirement(
            trigger_id=trigger.trigger_id,
            requirement_type=req_data.get("requirement_type", ""),
            required_object_id=json.dumps(req_data.get("required_object_id")),  # Convert to JSON string
            required_knowledge=json.dumps(req_data.get("required_knowledge", {})), # Convert to JSON string
            verification_method=req_data.get("verification_method", ""),
            hint_if_incorrect=req_data.get("hint_if_incorrect", ""),
            minimum_presentation_level=req_data.get("minimum_presentation_level", 0)
        )
        session.add(req)
        return req
    except KeyError as e:
        logger.error(f"Missing key in evidence requirement data: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Integrity error inserting evidence requirement: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Unexpected error inserting evidence requirement: {e}")
        session.rollback()
        return None


def load_characters(session, story, story_path):
    """Loads characters from JSON files and inserts them into the database."""
    personagens_dir = story_path / "personagens"
    if not personagens_dir.exists():
        logger.warning(f"Character directory not found: {personagens_dir}")
        return

    logger.info("Loading characters...")
    for arquivo in personagens_dir.glob("Personagem_*.json"):
        character_data_list = load_character_data(arquivo)

        if character_data_list is None:
            continue #if error continue.

        for character_data in character_data_list if isinstance(character_data_list, list) else [character_data_list]:
            character = create_and_add_character(session, story, character_data)
            if character is None:
                continue

            for level_data in character_data.get("levels", []):
                level = create_and_add_character_level(session, character, level_data)
                if level is None:
                    continue

                for trigger_data in level_data.get("triggers", []):
                    trigger = create_and_add_evolution_trigger(session, level, trigger_data)
                    if trigger is None:
                        continue

                    for req_data in trigger_data.get("requirements", []):
                        create_and_add_evidence_requirement(session, trigger, req_data)
        # Add this condition.
        if character:
            logger.info(f"Carregado personagem: {character.name} (ID: {character.character_id})")


def load_objects_data(data_dir):
    """Carrega os dados de objetos do arquivo objetos.json."""
    objetos_path = data_dir / "objetos.json"
    if not objetos_path.exists():
        logger.warning(f"Arquivo de objetos não encontrado: {objetos_path}")
        return None
    
    try:
        with open(objetos_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON no arquivo de objetos {objetos_path}: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"Erro ao carregar arquivo de objetos {objetos_path}: {e}")
        return None

def load_clues_data(data_dir):
    """Carrega os dados de pistas do arquivo pistas.json."""
    pistas_path = data_dir / "pistas.json"
    if not pistas_path.exists():
        logger.warning(f"Arquivo de pistas não encontrado: {pistas_path}")
        return None

    try:
        with open(pistas_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON no arquivo de pistas {pistas_path}: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"Erro ao carregar arquivo de pistas {pistas_path}: {e}")
        return None

def create_and_add_game_object(session, story, object_data):
    """Cria um objeto GameObject e o insere no banco de dados."""
    try:
        game_object = GameObject(
            object_id=object_data.get("object_id"),
            story_id=story.story_id,
            name=object_data.get("name", "Objeto sem nome"),
            base_description=object_data.get("base_description", ""),
            is_collectible=object_data.get("is_collectible", True),
            initial_location_id=object_data.get("initial_location_id"),
            initial_area_id=object_data.get("initial_area_id"),
            discovery_condition=object_data.get("discovery_condition", "")
        )
        session.add(game_object)
        session.flush()
        return game_object
    except KeyError as e:
        logger.error(f"Chave faltando nos dados do objeto: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir objeto: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir objeto: {e}")
        session.rollback()
        return None

def create_and_add_object_level(session, game_object, level_data):
    """Cria um objeto ObjectLevel e o insere no banco de dados."""
    try:
        level = ObjectLevel(
            object_id=game_object.object_id,
            level_number=level_data.get("level_number", 0),
            level_description=level_data.get("level_description", ""),
            level_attributes=json.dumps(level_data.get("level_attributes", {})),
            evolution_trigger=level_data.get("evolution_trigger", ""),
            related_clue_id=level_data.get("related_clue_id")
        )
        session.add(level)
        return level
    except KeyError as e:
        logger.error(f"Chave faltando nos dados do nível do objeto: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir nível do objeto: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir nível do objeto: {e}")
        session.rollback()
        return None

def create_and_add_clue(session, story, clue_data):
    """Cria um objeto Clue e o insere no banco de dados."""
    try:
        clue = Clue(
            clue_id=clue_data.get("clue_id"),
            story_id=story.story_id,
            name=clue_data.get("name", "Pista sem nome"),
            description=clue_data.get("description", ""),
            type=clue_data.get("type", ""),
            relevance=clue_data.get("relevance", 1),
            is_key_evidence=clue_data.get("is_key_evidence", False),
            related_aspect=clue_data.get("related_aspect", ""),
            discovery_conditions=json.dumps(clue_data.get("discovery_conditions", {}))
        )
        session.add(clue)
        return clue
    except KeyError as e:
        logger.error(f"Chave faltando nos dados da pista: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir pista: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir pista: {e}")
        session.rollback()
        return None

def load_objects_and_clues(session, story, story_path):
    """Carrega objetos e pistas da história"""
    data_dir = story_path / "data"
    if not data_dir.exists():
        logger.warning(f"Diretório de dados não encontrado: {data_dir}")
        return
    
    # Load Objects
    objetos_data = load_objects_data(data_dir)

    if objetos_data:
        logger.info("Carregando objetos...")
        for objeto_data in objetos_data:
            game_object = create_and_add_game_object(session, story, objeto_data)
            if game_object is None:
                continue

            for level_data in objeto_data.get("levels", []):
                create_and_add_object_level(session, game_object, level_data)
            logger.info(f"Carregado objeto: {game_object.name} (ID: {game_object.object_id})")

    # Load Clues
    clues_data = load_clues_data(data_dir)
    if clues_data:
        logger.info("Carregando pistas...")
        for clue_data in clues_data:
            clue = create_and_add_clue(session, story, clue_data)
            if clue is not None:
                logger.info(f"Carregada pista: {clue.name} (ID: {clue.clue_id})")

def load_qrcodes_data(data_dir):
    """Carrega os dados de QR codes do arquivo qrcodes.json."""
    qrcodes_path = data_dir / "qrcodes.json"
    if not qrcodes_path.exists():
        logger.warning(f"Arquivo de QR codes não encontrado: {qrcodes_path}")
        return None

    try:
        with open(qrcodes_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON no arquivo de QR codes {qrcodes_path}: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"Erro ao carregar arquivo de QR codes {qrcodes_path}: {e}")
        return None


def create_and_add_qrcode(session, qrcode_data):
    """Cria um objeto QRCode e o insere no banco de dados."""
    try:
        qrcode = QRCode(
            uuid=qrcode_data.get("uuid"),
            target_type=qrcode_data.get("target_type", ""),
            target_id=qrcode_data.get("target_id"),
            action=qrcode_data.get("action", ""),
            parameters=json.dumps(qrcode_data.get("parameters", {})),
            access_requirements=json.dumps(qrcode_data.get("access_requirements", {})),
            location_requirement=json.dumps(qrcode_data.get("location_requirement", {}))
        )
        session.add(qrcode)
        return qrcode
    except KeyError as e:
        logger.error(f"Chave faltando nos dados do QR code: {e}")
        session.rollback()
        return None
    except exc.IntegrityError as e:
        logger.error(f"Erro de integridade ao inserir QR code: {e}")
        session.rollback()
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir QR code: {e}")
        session.rollback()
        return None


def load_qrcodes(session, story, story_path):
    """Carrega QR codes da história"""
    data_dir = story_path / "data"
    qrcodes_data = load_qrcodes_data(data_dir)

    if qrcodes_data:
        logger.info("Carregando QR codes...")
        for qrcode_data in qrcodes_data:
            qrcode = create_and_add_qrcode(session, qrcode_data)
            if qrcode is not None:
                logger.info(f"Carregado QR code: {qrcode.uuid} (Tipo: {qrcode.target_type}, ID: {qrcode.target_id})")


def main(db_url: str, story_dir: str, reset: bool = False):
    """Função principal de setup do banco de dados"""
    logger = logging.getLogger('setup_db')
    
    try:
        logger.info(f"Iniciando setup com URL: {db_url}")
        logger.info(f"Diretório da história: {story_dir}")
        
        # Criar engine
        engine = create_engine(db_url)
        logger.info("Engine criada")
        
        if reset:
            logger.info("Dropping todas as tabelas...")
            Base.metadata.drop_all(engine)
        
        logger.info("Criando todas as tabelas...")
        Base.metadata.create_all(engine)
        
        # Criar sessão
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            logger.info("Configurando templates...")
            setup_templates(session)
            
            logger.info("Carregando dados da história...")
            load_story_data(session, story_dir)
            
            session.commit()
            logger.info("Setup concluído com sucesso!")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Erro durante o setup: {str(e)}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Erro durante a inicialização do banco de dados: {str(e)}")
        raise