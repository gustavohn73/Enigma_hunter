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
    player_discoveries = relationship("PlayerClueDiscovery", back_populates="clue")


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
    hint_requests = relationship("HintRequest", back_populates="session")


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


# NOVAS TABELAS PARA EXPANSÕES

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


class PlayerClueDiscovery(Base):
    """Registro de pistas descobertas por jogadores"""
    __tablename__ = 'player_clue_discovery'
    
    discovery_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    clue_id = Column(Integer, ForeignKey('clue.clue_id'))
    discovery_time = Column(DateTime, default=func.now())
    discovery_method = Column(String(50))  # Como a pista foi encontrada
    related_object_id = Column(Integer, ForeignKey('game_object.object_id'), nullable=True)
    related_location_id = Column(Integer, ForeignKey('location.location_id'), nullable=True)
    related_character_id = Column(Integer, ForeignKey('character.character_id'), nullable=True)
    
    # Relacionamentos
    clue = relationship("Clue", back_populates="player_discoveries")


class PlayerTheory(Base):
    """Teorias formuladas pelos jogadores"""
    __tablename__ = 'player_theory'
    
    theory_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    title = Column(String(255))
    description = Column(Text)
    suspect_character_id = Column(Integer, ForeignKey('character.character_id'), nullable=True)
    method_hypothesis = Column(Text)
    motive_hypothesis = Column(Text)
    connected_clues = Column(JSON)  # Lista de IDs de pistas conectadas
    confidence_level = Column(Integer)  # 1-5
    created_time = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now())
    system_feedback = Column(Text)  # Feedback do sistema


class HintRequest(Base):
    """Solicitações de dicas dos jogadores"""
    __tablename__ = 'hint_request'
    
    hint_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    request_time = Column(DateTime, default=func.now())
    hint_type = Column(String(50))  # general, location, character, object
    hint_level = Column(Integer)  # 1-3, crescente em especificidade
    target_id = Column(Integer, nullable=True)  # ID do alvo da dica (local, personagem, etc.)
    context = Column(JSON)  # Contexto da solicitação
    hint_provided = Column(Text)  # Dica fornecida
    penalty_applied = Column(JSON)  # Penalidades aplicadas
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="hint_requests")


class GameMetrics(Base):
    """Métricas agregadas de jogabilidade"""
    __tablename__ = 'game_metrics'
    
    metric_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id'))
    date = Column(DateTime, default=func.now())
    total_sessions = Column(Integer, default=0)
    avg_completion_time_minutes = Column(Float)
    success_rate = Column(Float)  # Porcentagem de soluções corretas
    most_missed_clues = Column(JSON)  # Pistas frequentemente não descobertas
    common_blockers = Column(JSON)  # Pontos de bloqueio comuns
    popular_characters = Column(JSON)  # Personagens mais interagidos
    hint_usage_stats = Column(JSON)  # Estatísticas de uso de dicas


class EvidenceUse(Base):
    """Registro de usos de evidência em diálogos"""
    __tablename__ = 'evidence_use'
    
    use_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    dialogue_id = Column(Integer, ForeignKey('dialogue_history.history_id'))
    object_id = Column(Integer, ForeignKey('game_object.object_id'))
    character_id = Column(Integer, ForeignKey('character.character_id'))
    timestamp = Column(DateTime, default=func.now())
    presentation_context = Column(Text)  # Contexto da apresentação
    object_level = Column(Integer)  # Nível do objeto no momento da apresentação
    character_reaction = Column(Text)  # Reação do personagem
    was_effective = Column(Boolean)  # Se a evidência foi efetiva
    
    # Relacionamentos
    session = relationship("PlayerSession")
    dialogue = relationship("DialogueHistory")
    object = relationship("GameObject")
    character = relationship("Character")


class ObjectCombination(Base):
    """Registro de combinações de objetos pelo jogador"""
    __tablename__ = 'object_combination'
    
    combination_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    timestamp = Column(DateTime, default=func.now())
    combination_type = Column(String(50))  # Tipo de combinação
    result_object_id = Column(Integer, ForeignKey('game_object.object_id'), nullable=True)
    success = Column(Boolean, default=True)
    specialization_points_awarded = Column(Integer, default=0)
    
    # Relacionamentos
    session = relationship("PlayerSession")
    result_object = relationship("GameObject")
    components = relationship("CombinationComponent", back_populates="combination")


class CombinationComponent(Base):
    """Objetos usados em uma combinação"""
    __tablename__ = 'combination_component'
    
    component_id = Column(Integer, primary_key=True)
    combination_id = Column(Integer, ForeignKey('object_combination.combination_id'))
    object_id = Column(Integer, ForeignKey('game_object.object_id'))
    
    # Relacionamentos
    combination = relationship("ObjectCombination", back_populates="components")
    object = relationship("GameObject")


class ActionLog(Base):
    """Registro detalhado de ações do jogador"""
    __tablename__ = 'action_log'
    
    action_id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('player_session.session_id'))
    timestamp = Column(DateTime, default=func.now())
    action_type = Column(String(50))
    action_target_type = Column(String(50), nullable=True)  # character, object, location
    action_target_id = Column(Integer, nullable=True)
    action_details = Column(JSON)
    action_success = Column(Boolean, default=True)
    action_result = Column(JSON, nullable=True)
    
    # Relacionamentos
    session = relationship("PlayerSession")


class SpecializationCategory(Base):
    """Categorias de especialização disponíveis"""
    __tablename__ = 'specialization_category'
    
    category_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(100), nullable=True)
    level_thresholds = Column(JSON)  # Limiares de pontos para níveis
    
    # Relacionamentos
    interactions = relationship("SpecializationInteraction", back_populates="category")


class SpecializationInteraction(Base):
    """Mapeamento de interações para categorias de especialização"""
    __tablename__ = 'specialization_interaction'
    
    interaction_id = Column(Integer, primary_key=True)
    category_id = Column(String(50), ForeignKey('specialization_category.category_id'))
    interaction_type = Column(String(50))  # object, character, area, clue, combination
    target_id = Column(String(50))  # ID do alvo da interação
    points = Column(Integer, default=10)
    interaction_description = Column(Text)
    
    # Relacionamentos
    category = relationship("SpecializationCategory", back_populates="interactions")


# Funções de inicialização do banco de dados

def init_db(db_url='sqlite:///enigma_hunter.db'):
    """Inicializa o banco de dados com o esquema definido"""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


def create_session(engine):
    """Cria uma sessão SQLAlchemy"""
    Session = sessionmaker(bind=engine)
    return Session()


def setup_default_data(session):
    """Configura dados padrão necessários para o funcionamento do sistema"""
    # Adicionar categorias de especialização padrão
    categories = [
        SpecializationCategory(
            category_id="cat_1",
            name="Análise de Evidências",
            description="Capacidade de examinar e compreender pistas físicas e vestígios",
            level_thresholds=json.dumps({
                "1": 15,
                "2": 40,
                "3": 80
            })
        ),
        SpecializationCategory(
            category_id="cat_2",
            name="Conhecimento Histórico",
            description="Compreensão de eventos passados, famílias e propriedades da região",
            level_thresholds=json.dumps({
                "1": 20,
                "2": 50,
                "3": 90
            })
        ),
        SpecializationCategory(
            category_id="cat_3",
            name="Interpretação de Comportamento",
            description="Habilidade de avaliar motivações, detectar mentiras e interpretar relações",
            level_thresholds=json.dumps({
                "1": 15,
                "2": 45,
                "3": 85
            })
        ),
        SpecializationCategory(
            category_id="cat_4",
            name="Descoberta Ambiental",
            description="Capacidade de encontrar e interpretar elementos do ambiente e natureza",
            level_thresholds=json.dumps({
                "1": 10,
                "2": 35,
                "3": 75
            })
        ),
        SpecializationCategory(
            category_id="cat_5",
            name="Conexão de Informações",
            description="Habilidade de relacionar pistas e formar conclusões coerentes",
            level_thresholds=json.dumps({
                "1": 25,
                "2": 60,
                "3": 100
            })
        ),
    ]
    
    for category in categories:
        existing = session.query(SpecializationCategory).filter_by(category_id=category.category_id).first()
        if not existing:
            session.add(category)
    
    # Adicionar templates de prompt padrão
    default_prompts = [
        PromptTemplate(
            template_name="character_dialogue_base",
            template_type="character",
            context_level=0,
            prompt_structure="""Você é {character_name}, {character_description}.

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
            variables=json.dumps([
                "character_name", "character_description", "character_context", 
                "character_personality", "character_level", "available_knowledge", 
                "knowledge_restrictions", "conversation_history", "player_input"
            ]),
            purpose="Diálogo básico com personagem",
            usage_instructions="Use este template para conversas iniciais com personagens"
        ),
        PromptTemplate(
            template_name="location_description",
            template_type="location",
            context_level=0,
            prompt_structure="""Descreva a seguinte localização para o jogador:

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
            variables=json.dumps([
                "location_name", "location_description", "exploration_level", 
                "visible_details", "atmosphere", "notable_elements"
            ]),
            purpose="Descrição de ambientes",
            usage_instructions="Use este template para descrever localizações com base no nível de exploração"
        ),
        PromptTemplate(
            template_name="object_examination",
            template_type="object",
            context_level=0,
            prompt_structure="""Descreva o seguinte objeto para o jogador:

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
            variables=json.dumps([
                "object_name", "object_description", "object_level", 
                "level_knowledge", "observable_details", "known_context"
            ]),
            purpose="Exame de objetos",
            usage_instructions="Use este template para descrever objetos com base no nível de conhecimento"
        ),
    ]
    
    for prompt in default_prompts:
        existing = session.query(PromptTemplate).filter_by(template_name=prompt.template_name).first()
        if not existing:
            session.add(prompt)
    
    # Commit as mudanças
    session.commit()


def load_story_from_json(session, story_file_path):
    """Carrega uma história a partir de um arquivo JSON"""
    with open(story_file_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
    
    # Criar objeto Story
    story = Story(
        title=story_data.get('title', 'História sem título'),
        description=story_data.get('description', ''),
        introduction=story_data.get('introduction', ''),
        conclusion=story_data.get('conclusion', ''),
        difficulty_level=story_data.get('difficulty_level', 1),
        solution_criteria=json.dumps(story_data.get('solution_criteria', {})),
        is_active=True
    )
    
    session.add(story)
    session.commit()
    
    print(f"História '{story.title}' carregada com ID {story.story_id}")
    return story


# Script principal para criar o banco de dados e configurar dados iniciais
if __name__ == "__main__":
    engine = init_db()
    session = create_session(engine)
    
    try:
        # Configurar dados padrão
        setup_default_data(session)
        
        # Carregar história de exemplo se o arquivo existir
        sample_story_path = 'historias/estalagem_cervo_negro/historia_base.json'
        if os.path.exists(sample_story_path):
            load_story_from_json(session, sample_story_path)
        
        print("Banco de dados inicializado com sucesso!")
    except Exception as e:
        print(f"Erro durante a inicialização do banco de dados: {e}")
    finally:
        session.close()