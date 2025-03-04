# src/models/db_models.py
"""
Definição dos modelos SQLAlchemy para o sistema Enigma Hunter.
Este arquivo contém todas as entidades do banco de dados para o sistema.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Table, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
import datetime
import uuid
import json
import os

Base = declarative_base()

# Tabelas de associação para relacionamentos many-to-many
story_character_association = Table(
    'story_character', Base.metadata,
    Column('story_id', Integer, ForeignKey('story.story_id')),
    Column('character_id', Integer, ForeignKey('character.character_id'))
)

story_location_association = Table(
    'story_location', Base.metadata,
    Column('story_id', Integer, ForeignKey('story.story_id')),
    Column('location_id', Integer, ForeignKey('location.location_id'))
)

player_game_association = Table(
    'player_game', Base.metadata,
    Column('player_id', Integer, ForeignKey('player.player_id')),
    Column('game_session_id', Integer, ForeignKey('game_session.game_session_id'))
)

# Entidades principais
class Story(Base):
    """História/caso completo para jogar"""
    __tablename__ = 'story'
    
    story_id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    introduction = Column(Text)
    conclusion = Column(Text)
    difficulty_level = Column(Integer, default=1)
    created_date = Column(DateTime, default=func.now())
    solution_criteria = Column(JSON)  # Critérios de vitória
    is_active = Column(Boolean, default=True)
    
    # Configurações de especialização específicas desta história
    specialization_config = Column(JSON)  # Categorias, pontos, níveis específicos desta história
    
    # Relacionamentos
    locations = relationship("Location", secondary=story_location_association, back_populates="stories")
    characters = relationship("Character", secondary=story_character_association, back_populates="stories")
    objects = relationship("GameObject", back_populates="story")
    clues = relationship("Clue", back_populates="story")
    game_sessions = relationship("GameSession", back_populates="story")
    prompt_templates = relationship("PromptTemplate", back_populates="story")


class Location(Base):
    """Ambiente navegável do jogo"""
    __tablename__ = 'location'
    
    location_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_locked = Column(Boolean, default=False)
    unlock_condition = Column(String(255))
    navigation_map = Column(JSON)  # Mapa de conexões com outras localizações
    is_starting_location = Column(Boolean, default=False)
    
    # Relacionamentos
    stories = relationship("Story", secondary=story_location_association, back_populates="locations")
    areas = relationship("LocationArea", back_populates="location")
    

class LocationArea(Base):
    """Subárea dentro de uma localização"""
    __tablename__ = 'location_area'
    
    area_id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey('location.location_id'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    initially_visible = Column(Boolean, default=True)
    connected_areas = Column(JSON)  # IDs de áreas conectadas
    discovery_level_required = Column(Integer, default=0)
    
    # Relacionamentos
    location = relationship("Location", back_populates="areas")
    details = relationship("AreaDetail", back_populates="area")
    

class AreaDetail(Base):
    """Detalhes específicos dentro de uma área"""
    __tablename__ = 'area_detail'
    
    detail_id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey('location_area.area_id'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    discovery_level_required = Column(Integer, default=0)
    has_clue = Column(Boolean, default=False)
    clue_id = Column(Integer, ForeignKey('clue.clue_id'), nullable=True)
    
    # Relacionamentos
    area = relationship("LocationArea", back_populates="details")
    clue = relationship("Clue", back_populates="area_details")


class Character(Base):
    """Personagem NPC do jogo"""
    __tablename__ = 'character'
    
    character_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    base_description = Column(Text)
    personality = Column(Text)
    appearance = Column(Text)
    is_culprit = Column(Boolean, default=False)
    motive = Column(Text)
    location_schedule = Column(JSON)  # Programação de localização do personagem
    
    # Relacionamentos
    stories = relationship("Story", secondary=story_character_association, back_populates="characters")
    levels = relationship("CharacterLevel", back_populates="character")
    dialogue_history = relationship("DialogueHistory", back_populates="character")
    

class CharacterLevel(Base):
    """Nível de conhecimento/interação com um personagem"""
    __tablename__ = 'character_level'
    
    level_id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('character.character_id'))
    level_number = Column(Integer, default=0)
    knowledge_scope = Column(Text)  # O que o personagem sabe neste nível
    narrative_stance = Column(Text)  # Como o personagem se comporta
    is_defensive = Column(Boolean, default=False)
    dialogue_parameters = Column(Text)  # Parâmetros para diálogo neste nível
    ia_instruction_set = Column(JSON)  # Instruções para a IA
    
    # Relacionamentos
    character = relationship("Character", back_populates="levels")
    triggers = relationship("EvolutionTrigger", back_populates="character_level")


class EvolutionTrigger(Base):
    """Gatilhos para evolução de personagem"""
    __tablename__ = 'evolution_trigger'
    
    trigger_id = Column(Integer, primary_key=True)
    level_id = Column(Integer, ForeignKey('character_level.level_id'))
    trigger_keyword = Column(String(255))
    contextual_condition = Column(Text)
    defensive_response = Column(Text)
    challenge_question = Column(Text)
    success_response = Column(Text)
    fail_response = Column(Text)
    multi_step_verification = Column(Boolean, default=False)
    
    # Relacionamentos
    character_level = relationship("CharacterLevel", back_populates="triggers")
    requirements = relationship("EvidenceRequirement", back_populates="trigger")


class EvidenceRequirement(Base):
    """Requisitos de evidência para gatilhos de evolução"""
    __tablename__ = 'evidence_requirement'
    
    req_id = Column(Integer, primary_key=True)
    trigger_id = Column(Integer, ForeignKey('evolution_trigger.trigger_id'))
    requirement_type = Column(String(50))  # object, knowledge, location, etc.
    required_object_id = Column(Integer, ForeignKey('game_object.object_id'), nullable=True)
    required_knowledge = Column(JSON)  # Conhecimento específico necessário
    verification_method = Column(Text)  # Como verificar se o requisito foi cumprido
    hint_if_incorrect = Column(Text)  # Dica se o jogador errar
    minimum_presentation_level = Column(Integer, default=0)  # Nível mínimo de apresentação
    
    # Relacionamentos
    trigger = relationship("EvolutionTrigger", back_populates="requirements")
    required_object = relationship("GameObject")


class GameObject(Base):
    """Objeto interativo no jogo"""
    __tablename__ = 'game_object'
    
    object_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id'))
    name = Column(String(255), nullable=False)
    base_description = Column(Text)
    is_collectible = Column(Boolean, default=True)
    initial_location_id = Column(Integer, ForeignKey('location.location_id'))
    initial_area_id = Column(Integer, ForeignKey('location_area.area_id'), nullable=True)
    discovery_condition = Column(String(255))
    
    # Relacionamentos
    story = relationship("Story", back_populates="objects")
    levels = relationship("ObjectLevel", back_populates="object")
    player_inventories = relationship("PlayerInventory", back_populates="object")
    initial_location = relationship("Location")
    initial_area = relationship("LocationArea")


class ObjectLevel(Base):
    """Nível de conhecimento sobre um objeto"""
    __tablename__ = 'object_level'
    
    level_id = Column(Integer, primary_key=True)
    object_id = Column(Integer, ForeignKey('game_object.object_id'))
    level_number = Column(Integer, default=0)
    level_description = Column(Text)
    level_attributes = Column(JSON)  # Atributos específicos do nível
    evolution_trigger = Column(String(255))  # Condição para evolução
    related_clue_id = Column(Integer, ForeignKey('clue.clue_id'), nullable=True)
    
    # Relacionamentos
    object = relationship("GameObject", back_populates="levels")
    related_clue = relationship("Clue")


class Clue(Base):
    """Pista ou evidência no jogo"""
    __tablename__ = 'clue'
    
    clue_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50))  # Tipo de pista: física, testemunho, etc.
    relevance = Column(Integer, default=1)  # Importância para a solução
    is_key_evidence = Column(Boolean, default=False)
    related_aspect = Column(String(50))  # Relacionado a culpado, método, motivo
    discovery_conditions = Column(JSON)  # Condições para descoberta
    
    # Relacionamentos
    story = relationship("Story", back_populates="clues")
    area_details = relationship("AreaDetail", back_populates="clue")


class QRCode(Base):
    """Representação de QR Code físico"""
    __tablename__ = 'qr_code'
    
    qr_id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    target_type = Column(String(50))  # location, area, character, object
    target_id = Column(Integer)
    action = Column(String(50))  # enter, explore, talk, examine, collect
    parameters = Column(JSON)  # Parâmetros adicionais para a ação
    access_requirements = Column(JSON)  # Requisitos para acesso
    location_requirement = Column(JSON)  # Localização necessária
    
    # Relacionamentos
    scans = relationship("QRCodeScan", back_populates="qr_code")


class Player(Base):
    """Usuário do sistema"""
    __tablename__ = 'player'
    
    player_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    password_hash = Column(String(255))
    joined_date = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    games_played = Column(Integer, default=0)
    games_completed = Column(Integer, default=0)
    
    # Relacionamentos
    sessions = relationship("PlayerSession", back_populates="player")
    game_sessions = relationship("GameSession", secondary=player_game_association)
    feedback = relationship("PlayerFeedback", back_populates="player")


class GameSession(Base):
    """Sessão de jogo gerenciada por um mestre"""
    __tablename__ = 'game_session'
    
    game_session_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id'))
    game_master_id = Column(Integer, ForeignKey('game_master.gm_id'))
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), default='active')
    player_count = Column(Integer, default=0)
    is_public = Column(Boolean, default=False)
    session_code = Column(String(10), unique=True)  # Código para jogadores entrarem
    
    # Relacionamentos
    story = relationship("Story", back_populates="game_sessions")
    game_master = relationship("GameMaster", back_populates="sessions")
    player_sessions = relationship("PlayerSession", back_populates="game_session")
    players = relationship("Player", secondary=player_game_association)


class PlayerSession(Base):
    """Sessão individual de um jogador"""
    __tablename__ = 'player_session'
    
    session_id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.player_id'))
    game_session_id = Column(Integer, ForeignKey('game_session.game_session_id'))
    start_time = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now())
    game_status = Column(String(50), default='active')
    solution_submitted = Column(Boolean, default=False)
    attempt_number = Column(Integer, default=1)
    session_data = Column(JSON)  # Dados serializados da sessão
    
    # Relacionamentos
    player = relationship("Player", back_populates="sessions")
    game_session = relationship("GameSession", back_populates="player_sessions")
    inventory = relationship("PlayerInventory", back_populates="session")
    location_records = relationship("PlayerLocation", back_populates="session")
    object_progress = relationship("PlayerObjectLevel", back_populates="session")
    character_progress = relationship("PlayerCharacterLevel", back_populates="session")
    environment_progress = relationship("PlayerEnvironmentLevel", back_populates="session")
    dialogue_history = relationship("DialogueHistory", back_populates="session")
    qr_scans = relationship("QRCodeScan", back_populates="session")
    solutions = relationship("PlayerSolution", back_populates="session")
    specializations = relationship("PlayerSpecialization", back_populates="session")


class PlayerInventory(Base):
    """Itens coletados por um jogador"""
    __tablename__ = 'player_inventory'
    
    inventory_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    object_id = Column(Integer, ForeignKey('game_object.object_id'))
    acquired_time = Column(DateTime, default=func.now())
    acquisition_method = Column(String(50))  # Como o item foi adquirido
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="inventory")
    object = relationship("GameObject", back_populates="player_inventories")
    knowledge = relationship("ItemKnowledge", back_populates="inventory_item")


class ItemKnowledge(Base):
    """Conhecimento específico sobre um item no inventário"""
    __tablename__ = 'item_knowledge'
    
    knowledge_id = Column(Integer, primary_key=True)
    inventory_id = Column(Integer, ForeignKey('player_inventory.inventory_id'))
    knowledge_key = Column(String(100))
    knowledge_value = Column(Text)
    was_revealed = Column(Boolean, default=False)
    discovery_time = Column(DateTime, default=func.now())
    discovery_method = Column(String(50))
    
    # Relacionamentos
    inventory_item = relationship("PlayerInventory", back_populates="knowledge")


class PlayerLocation(Base):
    """Rastreamento de localização do jogador"""
    __tablename__ = 'player_location'
    
    location_record_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    current_location_id = Column(Integer, ForeignKey('location.location_id'))
    current_area_id = Column(Integer, ForeignKey('location_area.area_id'), nullable=True)
    entered_time = Column(DateTime, default=func.now())
    exploration_history = Column(JSON)  # Histórico de áreas exploradas
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="location_records")
    current_location = relationship("Location")
    current_area = relationship("LocationArea")


class PlayerObjectLevel(Base):
    """Progresso do jogador em objetos"""
    __tablename__ = 'player_object_level'
    
    obj_progress_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    object_id = Column(Integer, ForeignKey('game_object.object_id'))
    current_level = Column(Integer, default=0)
    unlocked_details = Column(JSON)  # Detalhes desbloqueados
    last_interaction = Column(DateTime, default=func.now())
    interaction_history = Column(JSON)  # Histórico de interações
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="object_progress")
    object = relationship("GameObject")


class PlayerCharacterLevel(Base):
    """Progresso do jogador com personagens"""
    __tablename__ = 'player_character_level'
    
    char_progress_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    character_id = Column(Integer, ForeignKey('character.character_id'))
    current_level = Column(Integer, default=0)
    last_interaction = Column(DateTime, default=func.now())
    triggered_keywords = Column(JSON)  # Palavras-chave acionadas
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="character_progress")
    character = relationship("Character")


class PlayerEnvironmentLevel(Base):
    """Progresso do jogador na exploração de ambientes"""
    __tablename__ = 'player_environment_level'
    
    env_progress_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    location_id = Column(Integer, ForeignKey('location.location_id'))
    exploration_level = Column(Integer, default=0)
    discovered_areas = Column(JSON)  # Áreas descobertas
    discovered_details = Column(JSON)  # Detalhes descobertos
    last_exploration = Column(DateTime, default=func.now())
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="environment_progress")
    location = relationship("Location")


class DialogueHistory(Base):
    """Histórico de diálogos com personagens"""
    __tablename__ = 'dialogue_history'
    
    history_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    character_id = Column(Integer, ForeignKey('character.character_id'))
    timestamp = Column(DateTime, default=func.now())
    player_statement = Column(Text)
    character_response = Column(Text)
    detected_keywords = Column(JSON)  # Palavras-chave detectadas
    triggered_verification = Column(Boolean, default=False)
    verification_passed = Column(Boolean, default=False)
    evidence_presented = Column(JSON)  # Evidências apresentadas
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="dialogue_history")
    character = relationship("Character", back_populates="dialogue_history")


class QRCodeScan(Base):
    """Registro de escaneamento de QR code"""
    __tablename__ = 'qr_code_scan'
    
    scan_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    qr_uuid = Column(String(36), ForeignKey('qr_code.uuid'))
    scan_time = Column(DateTime, default=func.now())
    access_granted = Column(Boolean, default=True)
    denial_reason = Column(String(255), nullable=True)
    returned_content = Column(JSON)  # Conteúdo retornado ao jogador
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="qr_scans")
    qr_code = relationship("QRCode", back_populates="scans")


class PlayerSolution(Base):
    """Solução submetida pelo jogador"""
    __tablename__ = 'player_solution'
    
    solution_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    accused_character_id = Column(Integer, ForeignKey('character.character_id'))
    method_description = Column(Text)
    motive_explanation = Column(Text)
    supporting_evidence = Column(JSON)  # Evidências de suporte
    is_correct = Column(Boolean, default=False)
    submitted_time = Column(DateTime, default=func.now())
    feedback = Column(Text)  # Feedback sobre a solução
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="solutions")
    accused_character = relationship("Character")


class PlayerSpecialization(Base):
    """Especialização do jogador em diferentes áreas"""
    __tablename__ = 'player_specialization'
    
    spec_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    category_id = Column(String(50))  # ID da categoria de especialização
    points = Column(Integer, default=0)  # Pontos acumulados
    level = Column(Integer, default=0)  # Nível atual
    bonus_multiplier = Column(Float, default=1.0)  # Multiplicador de bônus
    completed_interactions = Column(JSON)  # Interações completadas
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="specializations")


class GameMaster(Base):
    """Mestre do jogo/administrador"""
    __tablename__ = 'game_master'
    
    gm_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    password_hash = Column(String(255))
    is_admin = Column(Boolean, default=False)
    created_date = Column(DateTime, default=func.now())
    
    # Relacionamentos
    sessions = relationship("GameSession", back_populates="game_master")


class SystemLog(Base):
    """Registro de atividades do sistema"""
    __tablename__ = 'system_log'
    
    log_id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now())
    log_type = Column(String(50))
    session_id = Column(Integer, ForeignKey('player_session.session_id'), nullable=True)
    player_id = Column(Integer, ForeignKey('player.player_id'), nullable=True)
    action = Column(Text)
    details = Column(JSON)
    ip_address = Column(String(50), nullable=True)


class PlayerFeedback(Base):
    """Feedback dos jogadores sobre a experiência"""
    __tablename__ = 'player_feedback'
    
    feedback_id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.player_id'))
    story_id = Column(Integer, ForeignKey('story.story_id'))
    session_id = Column(Integer, ForeignKey('player_session.session_id'), nullable=True)
    rating = Column(Integer)  # Classificação numérica (1-5)
    comments = Column(Text)
    submitted_time = Column(DateTime, default=func.now())
    
    # Relacionamentos
    player = relationship("Player", back_populates="feedback")


class PromptTemplate(Base):
    """Templates de prompt para a IA"""
    __tablename__ = 'prompt_template'
    
    template_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id'), nullable=True)
    template_name = Column(String(100), nullable=False)
    template_type = Column(String(50))  # character, location, object, etc.
    context_level = Column(Integer, default=0)  # Nível de contexto aplicável
    prompt_structure = Column(Text, nullable=False)
    variables = Column(JSON)  # Variáveis para substituição
    purpose = Column(String(255))
    usage_instructions = Column(Text)
    
    # Relacionamentos
    story = relationship("Story", back_populates="prompt_templates")
    logs = relationship("IAConversationLog", back_populates="template")


class IAConversationLog(Base):
    """Registros de conversas com a IA"""
    __tablename__ = 'ia_conversation_log'
    
    log_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    character_id = Column(Integer, ForeignKey('character.character_id'), nullable=True)
    template_id = Column(Integer, ForeignKey('prompt_template.template_id'), nullable=True)
    timestamp = Column(DateTime, default=func.now())
    interaction_type = Column(String(50))  # dialogue, description, examination
    player_input = Column(Text)
    prompt_sent = Column(Text)
    ia_response = Column(Text)
    filtered_response = Column(Text)
    tokens_used = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Relacionamentos
    template = relationship("PromptTemplate", back_populates="logs")