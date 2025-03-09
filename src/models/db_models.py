# src/models/db_models.py
"""
Definição dos modelos SQLAlchemy para o sistema Enigma Hunter.
Este arquivo contém todas as entidades do banco de dados para o sistema,
seguindo padrões de design consistentes para armazenamento e relacionamentos.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, Table, JSON, LargeBinary, 
    UniqueConstraint, Index, CheckConstraint, func, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from datetime import datetime
import json

Base = declarative_base()

# Tabelas de associação para relacionamentos many-to-many
story_character_association = Table(
    'story_character', Base.metadata,
    Column('story_id', Integer, ForeignKey('story.story_id', ondelete='CASCADE'), primary_key=True),
    Column('character_id', Integer, ForeignKey('character.character_id', ondelete='CASCADE'), primary_key=True),
    Index('idx_story_character', 'story_id', 'character_id')
)

story_location_association = Table(
    'story_location_association',
    Base.metadata,
    Column('story_id', Integer, ForeignKey('story.story_id')),
    Column('location_id', Integer, ForeignKey('location.location_id'))
)

player_game_association = Table(
    'player_game', Base.metadata,
    Column('player_id', Integer, ForeignKey('player.player_id', ondelete='CASCADE'), primary_key=True),
    Column('game_session_id', Integer, ForeignKey('game_session.game_session_id', ondelete='CASCADE'), primary_key=True),
    Index('idx_player_game', 'player_id', 'game_session_id')
)

class JSONMixin:
    """Mixin para lidar com campos JSON de forma padronizada."""

    @staticmethod
    def serialize_json(data):
        """Serializa dados para armazenamento em formato JSON."""
        if data is None:
            return None
        if isinstance(data, (dict, list)):
            return json.dumps(data)
        return data

    @staticmethod
    def deserialize_json(data):
        """Deserializa dados JSON para objetos Python."""
        if not data:
            return {}
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        return data

class TimestampMixin:
    """Mixin para adicionar timestamps de criação e atualização."""
    
    created_at = Column(DateTime, default=func.now, nullable=False)
    updated_at = Column(DateTime, default=func.now, onupdate=func.now, nullable=False)

class SoftDeleteMixin:
    """Mixin para suporte a exclusão lógica."""
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

class Story(Base, TimestampMixin, JSONMixin):
    """
    Representa uma história/caso completo para jogar.
    Contém informações sobre o enredo, introdução, conclusão e critérios de solução.
    """
    __tablename__ = 'story'
    
    story_id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    introduction = Column(Text)
    conclusion = Column(Text)
    difficulty_level = Column(Integer, default=1)
    solution_criteria = Column(JSON, default={})
    specialization_config = Column(JSON, default={})
    is_active = Column(Boolean, default=True, index=True)
    
    # Relacionamentos
    player_progress = relationship("PlayerProgress", back_populates="story")
    characters = relationship("Character", secondary=story_character_association, back_populates="stories")
    objects = relationship("GameObject", back_populates="story", cascade="all, delete-orphan")
    clues = relationship("Clue", back_populates="story", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="story")
    prompt_templates = relationship("PromptTemplate", back_populates="story", cascade="all, delete-orphan")
    locations = relationship("Location", 
                           secondary=story_location_association,
                           back_populates="stories")

    @validates('title')
    def validate_title(self, key, title):
        """Valida o título da história."""
        if not title:
            raise ValueError("O título da história não pode estar vazio")
        return title
    
    def __repr__(self):
        return f"<Story(id={self.story_id}, title='{self.title}', difficulty={self.difficulty_level})>"

class Location(Base, JSONMixin):
    """
    Representa um ambiente navegável do jogo.
    Define localizações que os jogadores podem explorar.
    """
    __tablename__ = 'location'
    
    location_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_locked = Column(Boolean, default=False)
    unlock_condition = Column(String(255))
    navigation_map = Column(JSON, default={})
    is_starting_location = Column(Boolean, default=False, index=True)
    
    # Relacionamentos
    stories = relationship("Story", 
                         secondary=story_location_association,
                         back_populates="locations")
    areas = relationship("LocationArea", back_populates="location", 
                        cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_location_starting', 'is_starting_location'),
    )
    
    def __repr__(self):
        return f"<Location(id={self.location_id}, name='{self.name}', locked={self.is_locked})>"

class LocationArea(Base, JSONMixin):
    """
    Representa uma subárea dentro de uma localização.
    Permite a exploração detalhada de diferentes partes de uma localização.
    """
    __tablename__ = 'location_area'
    
    area_id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey('location.location_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    initially_visible = Column(Boolean, default=True)
    connected_areas = Column(JSON, default=[])
    discovery_level_required = Column(Integer, default=0)
    
    # Relacionamentos
    location = relationship("Location", back_populates="areas")
    details = relationship("AreaDetail", back_populates="area", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="area")
    
    # Índices
    __table_args__ = (
        Index('idx_area_location', 'location_id'),
        Index('idx_area_discovery', 'discovery_level_required'),
    )
    
    def __repr__(self):
        return f"<LocationArea(id={self.area_id}, location_id={self.location_id}, name='{self.name}')>"

class AreaDetail(Base):
    """
    Representa detalhes específicos dentro de uma área.
    Permite a definição de elementos interativos dentro das áreas.
    """
    __tablename__ = 'area_detail'
    
    detail_id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey('location_area.area_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    discovery_level_required = Column(Integer, default=0)
    has_clue = Column(Boolean, default=False, index=True)
    clue_id = Column(Integer, ForeignKey('clue.clue_id', ondelete='SET NULL'), nullable=True)
    
    # Relacionamentos
    area = relationship("LocationArea", back_populates="details")
    clue = relationship("Clue", back_populates="area_details")
    
    # Índices
    __table_args__ = (
        Index('idx_detail_area', 'area_id'),
        Index('idx_detail_discovery', 'discovery_level_required'),
        Index('idx_detail_clue', 'has_clue'),
    )
    
    def __repr__(self):
        return f"<AreaDetail(id={self.detail_id}, area_id={self.area_id}, name='{self.name}')>"

class Character(Base, JSONMixin):
    """
    Representa um personagem NPC do jogo.
    Define personagens interativos com diferentes níveis de conhecimento e comportamento.
    """
    __tablename__ = 'character'
    
    character_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    character_type = Column(String(50))
    area_id = Column(Integer, ForeignKey('location_area.area_id'))  # Mudado de location_id
    is_active = Column(Boolean, default=True)
    dialogue_state = Column(String(50), default='neutral')
    importance_level = Column(Integer, default=1)
    base_description = Column(Text)
    personality = Column(Text)
    appearance = Column(Text)
    is_culprit = Column(Boolean, default=False)
    motive = Column(Text)
    
    # Relacionamentos
    area = relationship("LocationArea", back_populates="characters") 
    stories = relationship("Story", secondary=story_character_association, back_populates="characters")
    levels = relationship("CharacterLevel", back_populates="character", cascade="all, delete-orphan")
    dialogue_history = relationship("DialogueHistory", back_populates="character")
    
    # Índices
    __table_args__ = (
        Index('idx_character_culprit', 'is_culprit'),
    )
    
    def __repr__(self):
        return f"<Character(id={self.character_id}, name='{self.name}', culprit={self.is_culprit})>"

class CharacterLevel(Base, JSONMixin):
    """
    Representa um nível de conhecimento ou interação com um personagem.
    Define o que um personagem sabe e como se comporta em cada nível de interação.
    """
    __tablename__ = 'character_level'
    
    level_id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('character.character_id', ondelete='CASCADE'), nullable=False)
    level_number = Column(Integer, default=0, nullable=False)
    knowledge_scope = Column(Text)
    narrative_stance = Column(Text)
    is_defensive = Column(Boolean, default=False)
    dialogue_parameters = Column(Text)
    ia_instruction_set = Column(JSON, default={})
    
    # Relacionamentos
    character = relationship("Character", back_populates="levels")
    triggers = relationship("EvolutionTrigger", back_populates="character_level", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_level_character', 'character_id'),
        Index('idx_level_number', 'level_number'),
        UniqueConstraint('character_id', 'level_number', name='uq_character_level'),
    )
    
    def __repr__(self):
        return f"<CharacterLevel(id={self.level_id}, character_id={self.character_id}, level={self.level_number})>"

class EvolutionTrigger(Base):
    """
    Representa gatilhos para evolução de personagem.
    Define as condições que fazem um personagem evoluir para o próximo nível.
    """
    __tablename__ = 'evolution_trigger'
    
    trigger_id = Column(Integer, primary_key=True)
    level_id = Column(Integer, ForeignKey('character_level.level_id', ondelete='CASCADE'), nullable=False)
    trigger_keyword = Column(String(255), index=True)
    contextual_condition = Column(Text)
    defensive_response = Column(Text)
    challenge_question = Column(Text)
    success_response = Column(Text)
    fail_response = Column(Text)
    multi_step_verification = Column(Boolean, default=False)
    
    # Relacionamentos
    character_level = relationship("CharacterLevel", back_populates="triggers")
    requirements = relationship("EvidenceRequirement", back_populates="trigger", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_trigger_level', 'level_id'),
        Index('idx_trigger_keyword', 'trigger_keyword'),
    )
    
    def __repr__(self):
        return f"<EvolutionTrigger(id={self.trigger_id}, level_id={self.level_id}, keyword='{self.trigger_keyword}')>"

class EvidenceRequirement(Base, JSONMixin):
    """
    Representa requisitos de evidência para gatilhos de evolução.
    Define as evidências necessárias para ativar um gatilho de evolução.
    """
    __tablename__ = 'evidence_requirement'
    
    req_id = Column(Integer, primary_key=True)
    trigger_id = Column(Integer, ForeignKey('evolution_trigger.trigger_id', ondelete='CASCADE'), nullable=False)
    requirement_type = Column(String(50), nullable=False)
    required_object_id = Column(JSON)
    required_knowledge = Column(JSON, default={})
    verification_method = Column(Text)
    hint_if_incorrect = Column(Text)
    minimum_presentation_level = Column(Integer, default=0)
    
    # Relacionamentos
    trigger = relationship("EvolutionTrigger", back_populates="requirements")
    
    # Índices
    __table_args__ = (
        Index('idx_requirement_trigger', 'trigger_id'),
        Index('idx_requirement_type', 'requirement_type'),
    )
    
    def __repr__(self):
        return f"<EvidenceRequirement(id={self.req_id}, trigger_id={self.trigger_id}, type='{self.requirement_type}')>"

class GameObject(Base):
    """
    Representa um objeto interativo no jogo.
    Define objetos que os jogadores podem encontrar, coletar e usar.
    """
    __tablename__ = 'game_object'
    
    object_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    base_description = Column(Text)
    is_collectible = Column(Boolean, default=True, index=True)
    initial_location_id = Column(Integer, ForeignKey('location.location_id', ondelete='SET NULL'), nullable=True)
    initial_area_id = Column(Integer, ForeignKey('location_area.area_id', ondelete='SET NULL'), nullable=True)
    discovery_condition = Column(String(255))
    
    # Relacionamentos
    story = relationship("Story", back_populates="objects")
    levels = relationship("ObjectLevel", back_populates="object", cascade="all, delete-orphan")
    player_inventories = relationship("PlayerInventory", back_populates="object")
    initial_location = relationship("Location")
    initial_area = relationship("LocationArea")
    
    # Índices
    __table_args__ = (
        Index('idx_object_story', 'story_id'),
        Index('idx_object_collectible', 'is_collectible'),
        Index('idx_object_location', 'initial_location_id'),
    )
    
    def __repr__(self):
        return f"<GameObject(id={self.object_id}, name='{self.name}', collectible={self.is_collectible})>"

class ObjectLevel(Base, JSONMixin):
    """
    Representa um nível de conhecimento sobre um objeto.
    Define os diferentes níveis de conhecimento que um jogador pode ter sobre um objeto.
    """
    __tablename__ = 'object_level'
    
    level_id = Column(Integer, primary_key=True)
    object_id = Column(Integer, ForeignKey('game_object.object_id', ondelete='CASCADE'), nullable=False)
    level_number = Column(Integer, default=0, nullable=False)
    level_description = Column(Text)
    level_attributes = Column(JSON, default={})
    evolution_trigger = Column(String(255))
    related_clue_id = Column(Integer, ForeignKey('clue.clue_id', ondelete='SET NULL'), nullable=True)
    
    # Relacionamentos
    object = relationship("GameObject", back_populates="levels")
    related_clue = relationship("Clue")
    
    # Índices
    __table_args__ = (
        Index('idx_obj_level_object', 'object_id'),
        Index('idx_obj_level_number', 'level_number'),
        UniqueConstraint('object_id', 'level_number', name='uq_object_level'),
    )
    
    def __repr__(self):
        return f"<ObjectLevel(id={self.level_id}, object_id={self.object_id}, level={self.level_number})>"

class Clue(Base, JSONMixin):
    """
    Representa uma pista ou evidência no jogo.
    Define pistas que os jogadores podem descobrir durante a investigação.
    """
    __tablename__ = 'clue'
    
    clue_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    type = Column(String(50), index=True)
    relevance = Column(Integer, default=1)
    is_key_evidence = Column(Boolean, default=False, index=True)
    related_aspect = Column(String(50), index=True)
    discovery_conditions = Column(JSON, default={})
    
    # Relacionamentos
    story = relationship("Story", back_populates="clues")
    area_details = relationship("AreaDetail", back_populates="clue")
    
    # Índices
    __table_args__ = (
        Index('idx_clue_story', 'story_id'),
        Index('idx_clue_key_evidence', 'is_key_evidence'),
        Index('idx_clue_aspect', 'related_aspect'),
    )
    
    def __repr__(self):
        return f"<Clue(id={self.clue_id}, name='{self.name}', key_evidence={self.is_key_evidence})>"

class QRCode(Base, JSONMixin):
    """
    Representa um QR Code físico que pode ser escaneado pelos jogadores.
    Define códigos QR que conectam elementos físicos aos digitais.
    """
    __tablename__ = 'qr_code'
    
    qr_id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    parameters = Column(JSON, default={})
    access_requirements = Column(JSON, default={})
    location_requirement = Column(JSON, default={})
    story_id = Column(Integer, ForeignKey('story.story_id', ondelete='CASCADE'), nullable=True)
    
    # Relacionamentos
    scans = relationship("QRCodeScan", back_populates="qr_code", cascade="all, delete-orphan")
    story = relationship("Story")
    
    # Índices
    __table_args__ = (
        Index('idx_qrcode_uuid', 'uuid'),
        Index('idx_qrcode_target', 'target_type', 'target_id'),
        Index('idx_qrcode_story', 'story_id'),
    )
    
    def __repr__(self):
        return f"<QRCode(id={self.qr_id}, uuid='{self.uuid}', target_type='{self.target_type}', target_id={self.target_id})>"

class Player(Base, TimestampMixin, SoftDeleteMixin):
    """
    Representa um usuário do sistema.
    Armazena informações sobre os jogadores e seu histórico.
    """
    __tablename__ = 'player'
    
    player_id = Column(String(36), primary_key=True) 
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True) 
    last_login = Column(DateTime)
    games_played = Column(Integer, default=0)
    games_completed = Column(Integer, default=0)
    
    # Relacionamentos
    sessions = relationship("PlayerSession", back_populates="player", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", secondary="player_game", back_populates="players")
    feedback = relationship("PlayerFeedback", back_populates="player", cascade="all, delete-orphan")
    progress = relationship("PlayerProgress", back_populates="player", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_player_username', 'username'),
        Index('idx_player_email', 'email'),
    )
    
    @validates('username')
    def validate_username(self, key, username):
        """Valida o nome de usuário."""
        if not username:
            raise ValueError("O nome de usuário não pode estar vazio")
        if len(username) < 3:
            raise ValueError("O nome de usuário deve ter pelo menos 3 caracteres")
        return username
    
    @validates('email')
    def validate_email(self, key, email):
        """Valida o email do usuário."""
        if email and '@' not in email:
            raise ValueError("Endereço de email inválido")
        return email
    
    def __repr__(self):
        return f"<Player(id={self.player_id}, username='{self.username}')>"

class GameSession(Base, TimestampMixin):
    """
    Representa uma sessão de jogo gerenciada por um mestre.
    Define uma sessão completa de jogo que pode incluir múltiplos jogadores.
    """
    __tablename__ = 'game_session'
    
    game_session_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id', ondelete='CASCADE'), nullable=False)
    game_master_id = Column(Integer, ForeignKey('game_master.gm_id', ondelete='SET NULL'), nullable=True)
    start_time = Column(DateTime, default=func.now, nullable=False)
    end_time = Column(DateTime, nullable=True)
    game_status = Column(String(50), default='active', index=True)
    player_count = Column(Integer, default=0)
    is_public = Column(Boolean, default=False)
    session_code = Column(String(10), unique=True)
    
    # Relacionamentos
    story = relationship("Story", back_populates="game_sessions")
    game_master = relationship("GameMaster", back_populates="sessions")
    player_sessions = relationship("PlayerSession", back_populates="game_session", cascade="all, delete-orphan")
    players = relationship("Player", secondary="player_game", back_populates="game_sessions")
    
    # Índices
    __table_args__ = (
        Index('idx_session_story', 'story_id'),
        Index('idx_session_status', 'game_status'),
        Index('idx_session_code', 'session_code'),
    )
    
    def __repr__(self):
        return f"<GameSession(id={self.game_session_id}, story_id={self.story_id}, status='{self.game_status}')>"

class PlayerSession(Base, TimestampMixin, JSONMixin):
    """
    Representa uma sessão individual de um jogador.
    Armazena o progresso e estado de um jogador específico dentro de uma sessão de jogo.
    """
    __tablename__ = 'player_session'
    
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    player_id = Column(Integer, ForeignKey('player.player_id', ondelete='CASCADE'), nullable=False)
    game_session_id = Column(Integer, ForeignKey('game_session.game_session_id', ondelete='CASCADE'), nullable=False)
    story_id = Column(Integer, ForeignKey('story.story_id', ondelete='CASCADE'), nullable=False)
    last_activity = Column(DateTime, default=func.now, onupdate=func.now, nullable=False)
    game_status = Column(String(50), default='active', index=True)
    solution_submitted = Column(Boolean, default=False)
    attempt_number = Column(Integer, default=1)
    current_location_id = Column(Integer, ForeignKey('location.location_id', ondelete='SET NULL'), nullable=True)
    current_area_id = Column(Integer, ForeignKey('location_area.area_id', ondelete='SET NULL'), nullable=True)
    
    # Dados serializados do estado da sessão
    session_data = Column(JSON, default={})
    discovered_locations = Column(JSON, default=[])
    discovered_areas = Column(JSON, default={})
    inventory = Column(JSON, default=[])
    discovered_clues = Column(JSON, default=[])
    scanned_qr_codes = Column(JSON, default=[])
    
    # Relacionamentos
    player = relationship("Player", back_populates="sessions")
    game_session = relationship("GameSession", back_populates="player_sessions")
    story = relationship("Story")
    current_location = relationship("Location", foreign_keys=[current_location_id])
    current_area = relationship("LocationArea", foreign_keys=[current_area_id])
    inventory_items = relationship("PlayerInventory", back_populates="session", cascade="all, delete-orphan")
    location_records = relationship("PlayerLocation", back_populates="session", cascade="all, delete-orphan")
    object_progress = relationship("PlayerObjectLevel", back_populates="session", cascade="all, delete-orphan")
    character_progress = relationship("PlayerCharacterLevel", back_populates="session", cascade="all, delete-orphan")
    environment_progress = relationship("PlayerEnvironmentLevel", back_populates="session", cascade="all, delete-orphan")
    dialogue_history = relationship("DialogueHistory", back_populates="session", cascade="all, delete-orphan")
    qr_scans = relationship("QRCodeScan", back_populates="session", cascade="all, delete-orphan")
    solutions = relationship("PlayerSolution", back_populates="session", cascade="all, delete-orphan")
    specializations = relationship("PlayerSpecialization", back_populates="session", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_player_session_player', 'player_id'),
        Index('idx_player_session_game', 'game_session_id'),
        Index('idx_player_session_story', 'story_id'),
        Index('idx_player_session_status', 'game_status'),
        Index('idx_player_session_location', 'current_location_id'),
    )
    
    def to_dict(self):
        """Converte a sessão em um dicionário."""
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "game_session_id": self.game_session_id,
            "story_id": self.story_id,
            "start_time": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "game_status": self.game_status,
            "current_location_id": self.current_location_id,
            "current_area_id": self.current_area_id,
            "discovered_locations": self.discovered_locations,
            "discovered_areas": self.discovered_areas,
            "inventory": self.inventory,
            "discovered_clues": self.discovered_clues,
            "scanned_qr_codes": self.scanned_qr_codes,
            "solution_submitted": self.solution_submitted
        }
    
    def __repr__(self):
        return f"<PlayerSession(id='{self.session_id}', player_id={self.player_id}, status='{self.game_status}')>"

class PlayerInventory(Base, TimestampMixin):
    """
    Representa os itens coletados por um jogador.
    Armazena os objetos que um jogador coletou durante o jogo.
    """
    __tablename__ = 'player_inventory'
    
    inventory_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    object_id = Column(Integer, ForeignKey('game_object.object_id', ondelete='CASCADE'), nullable=False)
    acquisition_method = Column(String(50), default='discovered')
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="inventory_items")
    object = relationship("GameObject", back_populates="player_inventories")
    knowledge = relationship("ItemKnowledge", back_populates="inventory_item", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_inventory_session', 'session_id'),
        Index('idx_inventory_object', 'object_id'),
        UniqueConstraint('session_id', 'object_id', name='uq_inventory_item'),
    )
    
    def __repr__(self):
        return f"<PlayerInventory(id={self.inventory_id}, session_id='{self.session_id}', object_id={self.object_id})>"

class ItemKnowledge(Base, TimestampMixin):
    """
    Representa o conhecimento específico sobre um item no inventário.
    Armazena detalhes específicos que um jogador descobriu sobre um objeto.
    """
    __tablename__ = 'item_knowledge'
    
    knowledge_id = Column(Integer, primary_key=True)
    inventory_id = Column(Integer, ForeignKey('player_inventory.inventory_id', ondelete='CASCADE'), nullable=False)
    knowledge_key = Column(String(100), nullable=False)
    knowledge_value = Column(Text)
    was_revealed = Column(Boolean, default=False)
    discovery_method = Column(String(50))
    
    # Relacionamentos
    inventory_item = relationship("PlayerInventory", back_populates="knowledge")
    
    # Índices
    __table_args__ = (
        Index('idx_knowledge_inventory', 'inventory_id'),
        Index('idx_knowledge_key', 'knowledge_key'),
        UniqueConstraint('inventory_id', 'knowledge_key', name='uq_item_knowledge'),
    )
    
    def __repr__(self):
        return f"<ItemKnowledge(id={self.knowledge_id}, inventory_id={self.inventory_id}, key='{self.knowledge_key}')>"

class PlayerLocation(Base, TimestampMixin, JSONMixin):
    """
    Representa o rastreamento de localização do jogador.
    Armazena o histórico de localizações visitadas pelo jogador durante o jogo.
    """
    __tablename__ = 'player_location'
    
    location_record_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    current_location_id = Column(Integer, ForeignKey('location.location_id', ondelete='CASCADE'), nullable=False)
    current_area_id = Column(Integer, ForeignKey('location_area.area_id', ondelete='SET NULL'), nullable=True)
    entered_time = Column(DateTime, default=func.now, nullable=False)
    exploration_history = Column(JSON, default=[])
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="location_records")
    current_location = relationship("Location")
    current_area = relationship("LocationArea")
    
    # Índices
    __table_args__ = (
        Index('idx_player_location_session', 'session_id'),
        Index('idx_player_location_location', 'current_location_id'),
    )
    
    def __repr__(self):
        return f"<PlayerLocation(id={self.location_record_id}, session_id='{self.session_id}', location_id={self.current_location_id})>"

class PlayerObjectLevel(Base, TimestampMixin, JSONMixin):
    """
    Representa o progresso do jogador em objetos.
    Armazena o nível de conhecimento do jogador sobre objetos específicos.
    """
    __tablename__ = 'player_object_level'
    
    obj_progress_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    object_id = Column(Integer, ForeignKey('game_object.object_id', ondelete='CASCADE'), nullable=False)
    current_level = Column(Integer, default=0, nullable=False)
    unlocked_details = Column(JSON, default=[])
    last_interaction = Column(DateTime, default=func.now, nullable=False)
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="object_progress")
    object = relationship("GameObject")
    
    # Índices
    __table_args__ = (
        Index('idx_obj_progress_session', 'session_id'),
        Index('idx_obj_progress_object', 'object_id'),
        UniqueConstraint('session_id', 'object_id', name='uq_object_progress'),
    )
    
    def __repr__(self):
        return f"<PlayerObjectLevel(id={self.obj_progress_id}, session_id='{self.session_id}', object_id={self.object_id}, level={self.current_level})>"

class PlayerCharacterLevel(Base, TimestampMixin, JSONMixin):
    """
    Representa o progresso do jogador com personagens.
    Armazena o nível de relacionamento do jogador com personagens específicos.
    """
    __tablename__ = 'player_character_level'
    
    char_progress_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    character_id = Column(Integer, ForeignKey('character.character_id', ondelete='CASCADE'), nullable=False)
    current_level = Column(Integer, default=0, nullable=False)
    last_interaction = Column(DateTime, default=func.now, nullable=False)
    triggered_keywords = Column(JSON, default=[])
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="character_progress")
    character = relationship("Character")
    
    # Índices
    __table_args__ = (
        Index('idx_char_progress_session', 'session_id'),
        Index('idx_char_progress_character', 'character_id'),
        UniqueConstraint('session_id', 'character_id', name='uq_character_progress'),
    )
    
    def __repr__(self):
        return f"<PlayerCharacterLevel(id={self.char_progress_id}, session_id='{self.session_id}', character_id={self.character_id}, level={self.current_level})>"

class PlayerEnvironmentLevel(Base, TimestampMixin, JSONMixin):
    """
    Representa o progresso do jogador na exploração de ambientes.
    Armazena o nível de exploração do jogador em localizações específicas.
    """
    __tablename__ = 'player_environment_level'
    
    env_progress_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.location_id', ondelete='CASCADE'), nullable=False)
    exploration_level = Column(Integer, default=0, nullable=False)
    discovered_areas = Column(JSON, default=[])
    discovered_details = Column(JSON, default=[])
    last_exploration = Column(DateTime, default=func.now, nullable=False)
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="environment_progress")
    location = relationship("Location")
    
    # Índices
    __table_args__ = (
        Index('idx_env_progress_session', 'session_id'),
        Index('idx_env_progress_location', 'location_id'),
        UniqueConstraint('session_id', 'location_id', name='uq_environment_progress'),
    )
    
    def __repr__(self):
        return f"<PlayerEnvironmentLevel(id={self.env_progress_id}, session_id='{self.session_id}', location_id={self.location_id}, level={self.exploration_level})>"

class DialogueHistory(Base, TimestampMixin, JSONMixin):
    """
    Representa o histórico de diálogos com personagens.
    Armazena conversas do jogador com personagens NPC.
    """
    __tablename__ = 'dialogue_history'
    
    dialogue_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    character_id = Column(Integer, ForeignKey('character.character_id', ondelete='CASCADE'), nullable=False)
    player_statement = Column(Text)
    character_response = Column(Text)
    detected_keywords = Column(JSON, default=[])
    triggered_verification = Column(Boolean, default=False)
    verification_passed = Column(Boolean, default=False)
    evidence_presented = Column(JSON, default=[])
    character_level = Column(Integer, default=0)
    is_key_interaction = Column(Boolean, default=False, index=True)
    trigger_id = Column(Integer, ForeignKey('evolution_trigger.trigger_id', ondelete='SET NULL'), nullable=True)
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="dialogue_history")
    character = relationship("Character", back_populates="dialogue_history")
    trigger = relationship("EvolutionTrigger")
    
    # Índices
    __table_args__ = (
        Index('idx_dialogue_session', 'session_id'),
        Index('idx_dialogue_character', 'character_id'),
        Index('idx_dialogue_timestamp', 'created_at'),
        Index('idx_dialogue_key', 'is_key_interaction'),
    )
    
    def __repr__(self):
        return f"<DialogueHistory(id={self.dialogue_id}, session_id='{self.session_id}', character_id={self.character_id})>"

class QRCodeScan(Base, TimestampMixin, JSONMixin):
    """
    Representa o registro de escaneamento de QR code.
    Armazena informações sobre QR codes escaneados pelo jogador.
    """
    __tablename__ = 'qr_code_scan'
    
    scan_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    qr_uuid = Column(String(36), ForeignKey('qr_code.uuid', ondelete='CASCADE'), nullable=False)
    access_granted = Column(Boolean, default=True)
    denial_reason = Column(String(255), nullable=True)
    returned_content = Column(JSON, default={})
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="qr_scans")
    qr_code = relationship("QRCode", back_populates="scans")
    
    # Índices
    __table_args__ = (
        Index('idx_qrscan_session', 'session_id'),
        Index('idx_qrscan_uuid', 'qr_uuid'),
        Index('idx_qrscan_timestamp', 'created_at'),
    )
    
    def __repr__(self):
        return f"<QRCodeScan(id={self.scan_id}, session_id='{self.session_id}', qr_uuid='{self.qr_uuid}')>"

class PlayerSolution(Base, TimestampMixin, JSONMixin):
    """
    Representa uma solução submetida pelo jogador.
    Armazena tentativas de solução do mistério feitas pelo jogador.
    """
    __tablename__ = 'player_solution'
    
    solution_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    accused_character_id = Column(Integer, ForeignKey('character.character_id', ondelete='CASCADE'), nullable=False)
    method_description = Column(Text)
    motive_explanation = Column(Text)
    supporting_evidence = Column(JSON, default=[])
    is_correct = Column(Boolean, default=False, index=True)
    feedback = Column(Text)
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="solutions")
    accused_character = relationship("Character")
    
    # Índices
    __table_args__ = (
        Index('idx_solution_session', 'session_id'),
        Index('idx_solution_character', 'accused_character_id'),
        Index('idx_solution_correct', 'is_correct'),
    )
    
    def __repr__(self):
        return f"<PlayerSolution(id={self.solution_id}, session_id='{self.session_id}', correct={self.is_correct})>"

class PlayerSpecialization(Base, TimestampMixin, JSONMixin):
    """
    Representa a especialização do jogador em diferentes áreas.
    Armazena o progresso do jogador em diferentes habilidades de investigação.
    """
    __tablename__ = 'player_specialization'
    
    spec_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    category_id = Column(String(50), nullable=False)
    points = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=0, nullable=False)
    bonus_multiplier = Column(Float, default=1.0)
    completed_interactions = Column(JSON, default={})
    
    # Relacionamentos
    session = relationship("PlayerSession", back_populates="specializations")
    
    # Índices
    __table_args__ = (
        Index('idx_spec_session', 'session_id'),
        Index('idx_spec_category', 'category_id'),
        Index('idx_spec_level', 'level'),
        UniqueConstraint('session_id', 'category_id', name='uq_specialization'),
    )
    
    def __repr__(self):
        return f"<PlayerSpecialization(id={self.spec_id}, session_id='{self.session_id}', category='{self.category_id}', level={self.level})>"

class GameMaster(Base, TimestampMixin, SoftDeleteMixin):
    """
    Representa um mestre do jogo/administrador.
    Armazena informações sobre usuários que podem gerenciar sessões de jogo.
    """
    __tablename__ = 'game_master'
    
    gm_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    is_admin = Column(Boolean, default=False, index=True)
    
    # Relacionamentos
    sessions = relationship("GameSession", back_populates="game_master")
    
    # Índices
    __table_args__ = (
        Index('idx_gm_admin', 'is_admin'),
    )
    
    @validates('username')
    def validate_username(self, key, username):
        """Valida o nome de usuário."""
        if not username:
            raise ValueError("O nome de usuário não pode estar vazio")
        if len(username) < 3:
            raise ValueError("O nome de usuário deve ter pelo menos 3 caracteres")
        return username
    
    @validates('email')
    def validate_email(self, key, email):
        """Valida o email do usuário."""
        if email and '@' not in email:
            raise ValueError("Endereço de email inválido")
        return email
    
    def __repr__(self):
        return f"<GameMaster(id={self.gm_id}, username='{self.username}', admin={self.is_admin})>"

class SystemLog(Base, TimestampMixin):
    """
    Representa um registro de atividades do sistema.
    Armazena logs para monitoramento e depuração.
    """
    __tablename__ = 'system_log'
    
    log_id = Column(Integer, primary_key=True)
    log_type = Column(String(50), index=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='SET NULL'), nullable=True)
    player_id = Column(Integer, ForeignKey('player.player_id', ondelete='SET NULL'), nullable=True)
    action = Column(Text)
    details = Column(JSON, default={})
    ip_address = Column(String(50), nullable=True)
    severity = Column(String(20), default='INFO', index=True)
    
    # Relacionamentos
    session = relationship("PlayerSession")
    player = relationship("Player")
    
    # Índices
    __table_args__ = (
        Index('idx_log_type', 'log_type'),
        Index('idx_log_timestamp', 'created_at'),
        Index('idx_log_severity', 'severity'),
    )
    
    def __repr__(self):
        return f"<SystemLog(id={self.log_id}, type='{self.log_type}', timestamp='{self.created_at}')>"

class PlayerFeedback(Base, TimestampMixin):
    """
    Representa feedback dos jogadores sobre a experiência.
    Armazena avaliações e comentários feitos pelos jogadores.
    """
    __tablename__ = 'player_feedback'
    
    feedback_id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.player_id', ondelete='CASCADE'), nullable=False)
    story_id = Column(Integer, ForeignKey('story.story_id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='SET NULL'), nullable=True)
    rating = Column(Integer, CheckConstraint('rating >= 1 AND rating <= 5'))
    comments = Column(Text)
    
    # Relacionamentos
    player = relationship("Player", back_populates="feedback")
    story = relationship("Story")
    session = relationship("PlayerSession")
    
    # Índices
    __table_args__ = (
        Index('idx_feedback_player', 'player_id'),
        Index('idx_feedback_story', 'story_id'),
        Index('idx_feedback_session', 'session_id'),
        Index('idx_feedback_rating', 'rating'),
    )
    
    def __repr__(self):
        return f"<PlayerFeedback(id={self.feedback_id}, player_id={self.player_id}, rating={self.rating})>"

class PromptTemplate(Base, TimestampMixin, JSONMixin):
    """
    Template de prompt para interações com IA.
    Define a estrutura base dos prompts usados para diferentes tipos de interação.
    """
    __tablename__ = 'prompt_template'
    
    template_id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey('story.story_id', ondelete='CASCADE'), nullable=True)
    template_name = Column(String(100), nullable=False, index=True)
    template_type = Column(String(50), index=True)
    context_level = Column(Integer, default=0)
    prompt_structure = Column(Text, nullable=False)
    variables = Column(JSON, default={})
    purpose = Column(String(255))
    usage_instructions = Column(Text)
    
    # Relacionamentos
    story = relationship("Story", back_populates="prompt_templates")
    logs = relationship("IAConversationLog", back_populates="template", cascade="all, delete-orphan")

    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_template_type', 'template_type'),
        Index('idx_template_story', 'story_id'),
    )
    logs = relationship("IAConversationLog", back_populates="template", cascade="all, delete-orphan")

    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_template_type', 'template_type'),
        Index('idx_template_story', 'story_id'),
    )
    logs = relationship("IAConversationLog", back_populates="template", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_template_type', 'template_type'),
        Index('idx_template_story', 'story_id'),
    )
    logs = relationship("IAConversationLog", back_populates="template", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_template_type', 'template_type'),
        Index('idx_template_story', 'story_id'),
    )
    logs = relationship("IAConversationLog", back_populates="template", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_template_type', 'template_type'),
        Index('idx_template_story', 'story_id'),
    )
    logs = relationship("IAConversationLog", back_populates="template", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_template_type', 'template_type'),
        Index('idx_template_story', 'story_id'),
    )
    logs = relationship("IAConversationLog", back_populates="template", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_template_type', 'template_type'),
        Index('idx_template_story', 'story_id'),
    )
    
    def __repr__(self):
        return f"<PromptTemplate(id={self.template_id}, name='{self.template_name}', type='{self.template_type}')>"

class IAConversationLog(Base, TimestampMixin):
    """
    Representa registros de conversas com a IA.
    Armazena logs de interações com o modelo de IA para análise e melhoria.
    """
    __tablename__ = 'ia_conversation_log'
    
    log_id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey('player_session.session_id', ondelete='CASCADE'), nullable=False)
    character_id = Column(Integer, ForeignKey('character.character_id', ondelete='SET NULL'), nullable=True)
    template_id = Column(Integer, ForeignKey('prompt_template.template_id', ondelete='SET NULL'), nullable=True)
    interaction_type = Column(String(50), index=True)
    player_input = Column(Text)
    prompt_sent = Column(Text)
    ia_response = Column(Text)
    filtered_response = Column(Text)
    tokens_used = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Relacionamentos
    session = relationship("PlayerSession")
    character = relationship("Character")
    template = relationship("PromptTemplate", back_populates="logs")
    
    # Índices
    __table_args__ = (
        Index('idx_ia_log_session', 'session_id'),
        Index('idx_ia_log_character', 'character_id'),
        Index('idx_ia_log_timestamp', 'created_at'),
        Index('idx_ia_log_type', 'interaction_type'),
    )
    
    def __repr__(self):
        return f"<IAConversationLog(id={self.log_id}, session_id='{self.session_id}', type='{self.interaction_type}')>"


class PlayerProgress(Base, TimestampMixin, JSONMixin):
    """
    Representa o progresso geral do jogador.
    Armazena métricas e estatísticas do progresso do jogador durante o jogo.
    """
    __tablename__ = 'player_progress'

    progress_id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.player_id'), nullable=False)
    story_id = Column(Integer, ForeignKey('story.story_id'), nullable=False)
    session_id = Column(String(36), nullable=False, unique=True)
    game_status = Column(String(20), default='active') 
    
    # Campos de localização
    current_location_id = Column(Integer, ForeignKey('location.location_id'))
    current_area_id = Column(Integer, ForeignKey('location_area.area_id'))
    discovered_locations = Column(JSON, default=list)
    discovered_areas = Column(JSON, default=dict)
    location_exploration_level = Column(JSON, default=dict)
    area_exploration_level = Column(JSON, default=dict)
    
    # Inventário e níveis
    inventory = Column(JSON, default=list)
    object_level = Column(JSON, default=dict)
    character_level = Column(JSON, default=dict)
    
    # Histórico e progresso
    dialogue_history = Column(JSON, default=dict)
    discovered_clues = Column(JSON, default=list)
    scanned_qr_codes = Column(JSON, default=list)
    action_history = Column(JSON, default=list)
    
    # Sistema de especialização
    specialization_points = Column(JSON, default=dict)
    specialization_levels = Column(JSON, default=dict)
    
    # Tracking de interações
    completed_interactions = Column(JSON, default=lambda: {
        "objetos": [], 
        "personagens": [], 
        "areas": [], 
        "pistas": [], 
        "combinacoes": []
    })
    
    # Timestamps
    start_time = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, nullable=False)
    
    # Métricas de progresso
    locations_visited = Column(JSON, default=[])
    objects_collected = Column(JSON, default=[])
    clues_discovered = Column(JSON, default=[]) 
    completion_percentage = Column(Float, default=0.0)
    total_time_played = Column(Integer, default=0)  # Em segundos
    current_score = Column(Integer, default=0)
    achievements = Column(JSON, default=[])
    
    # Relacionamentos
    player = relationship("Player", back_populates="progress")
    story = relationship("Story", back_populates="player_progress")
    current_location = relationship("Location", foreign_keys=[current_location_id])
    current_area = relationship("LocationArea", foreign_keys=[current_area_id])
    
    
    # Índices
    __table_args__ = (
        Index('idx_progress_player', 'player_id'),
        Index('idx_progress_story', 'story_id'),
        Index('idx_progress_session', 'session_id'),
        UniqueConstraint('player_id', 'story_id', 'session_id', name='uq_player_progress')
    )
    
    def __repr__(self):
        return f"<PlayerProgress(id={self.progress_id}, player_id={self.player_id}, completion={self.completion_percentage}%)>"

# Event listeners

@event.listens_for(SoftDeleteMixin, 'before_update', propagate=True)
def set_deleted_timestamp(mapper, connection, target):
    """Configura o timestamp de exclusão quando is_deleted é definido como True."""
    if target.is_deleted and not target.deleted_at:
        target.deleted_at = func.now
    elif not target.is_deleted and target.deleted_at:
        target.deleted_at = None