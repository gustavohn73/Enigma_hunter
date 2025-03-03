#src/models/dB-models-init.py
"""
Exporta todos os modelos do banco de dados para fácil importação
"""

from .db_models import (
    Base,
    Story, Location, LocationArea, AreaDetail,
    Character, CharacterLevel, EvolutionTrigger, EvidenceRequirement,
    GameObject, ObjectLevel, Clue, QRCode,
    Player, GameSession, PlayerSession, PlayerInventory,
    ItemKnowledge, PlayerLocation, PlayerObjectLevel,
    PlayerCharacterLevel, PlayerEnvironmentLevel,
    DialogueHistory, QRCodeScan, PlayerSolution,
    PlayerSpecialization, GameMaster, SystemLog,
    PlayerFeedback, PromptTemplate, IAConversationLog,
    PlayerClueDiscovery, PlayerTheory, HintRequest,
    GameMetrics, EvidenceUse, ObjectCombination,
    CombinationComponent, ActionLog
)