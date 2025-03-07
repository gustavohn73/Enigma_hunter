from typing import List, Optional, Dict, Any, Set
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.models.db_models import (
    PlayerProgress, Player, Story, Location, Area, 
    GameObject, Clue, SpecializationProgress
)
from src.repositories.base_repository import BaseRepository

class PlayerProgressRepository(BaseRepository[PlayerProgress]):
    """
    Repositório para operações de banco de dados relacionadas ao progresso dos jogadores.
    Gerencia especializações, inventário, áreas descobertas e outros aspectos do progresso.
    """
    
    def __init__(self):
        super().__init__(PlayerProgress)
    
    def get_by_id(self, db: Session, progress_id: int) -> Optional[PlayerProgress]:
        """
        Busca um progresso pelo ID.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            
        Returns:
            Progresso encontrado ou None
        """
        return db.query(PlayerProgress).filter(
            PlayerProgress.progress_id == progress_id
        ).first()
    
    def get_player_progress(self, db: Session, player_id: int, story_id: int) -> Optional[PlayerProgress]:
        """
        Busca o progresso de um jogador em uma história específica.
        
        Args:
            db: Sessão do banco de dados
            player_id: ID do jogador
            story_id: ID da história
            
        Returns:
            Progresso do jogador ou None
        """
        return db.query(PlayerProgress).filter(
            PlayerProgress.player_id == player_id,
            PlayerProgress.story_id == story_id
        ).first()
    
    def get_specializations(self, db: Session, progress_id: int) -> Dict[str, int]:
        """
        Obtém as especializações do jogador.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            
        Returns:
            Dicionário com categorias e níveis de especialização
        """
        specializations = db.query(SpecializationProgress).filter(
            SpecializationProgress.progress_id == progress_id
        ).all()
        
        return {spec.category: spec.level for spec in specializations}
    
    def update_specialization(self, db: Session, progress_id: int, category: str, points: int) -> bool:
        """
        Atualiza os pontos de especialização de uma categoria.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            category: Categoria de especialização
            points: Pontos a serem adicionados
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        spec = db.query(SpecializationProgress).filter(
            SpecializationProgress.progress_id == progress_id,
            SpecializationProgress.category == category
        ).first()
        
        if not spec:
            spec = SpecializationProgress(
                progress_id=progress_id,
                category=category,
                points=points,
                level=1
            )
            db.add(spec)
        else:
            spec.points += points
            # Atualiza o nível com base nos pontos
            spec.level = self._calculate_level(spec.points)
        
        db.commit()
        return True
    
    def get_inventory(self, db: Session, progress_id: int) -> List[GameObject]:
        """
        Obtém o inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            
        Returns:
            Lista de objetos no inventário
        """
        progress = self.get_by_id(db, progress_id)
        if not progress:
            return []
            
        return db.query(GameObject).filter(
            GameObject.object_id.in_(progress.inventory)
        ).all()
    
    def add_to_inventory(self, db: Session, progress_id: int, object_id: int) -> bool:
        """
        Adiciona um objeto ao inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            object_id: ID do objeto
            
        Returns:
            True se adicionado com sucesso, False caso contrário
        """
        progress = self.get_by_id(db, progress_id)
        if not progress:
            return False
            
        if object_id not in progress.inventory:
            progress.inventory.append(object_id)
            db.commit()
            
        return True
    
    def discover_location(self, db: Session, progress_id: int, location_id: int) -> bool:
        """
        Registra uma localização como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            location_id: ID da localização
            
        Returns:
            True se registrado com sucesso, False caso contrário
        """
        progress = self.get_by_id(db, progress_id)
        if not progress:
            return False
            
        if location_id not in progress.discovered_locations:
            progress.discovered_locations.append(location_id)
            db.commit()
            
        return True
    
    def discover_area(self, db: Session, progress_id: int, area_id: int) -> bool:
        """
        Registra uma área como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            area_id: ID da área
            
        Returns:
            True se registrado com sucesso, False caso contrário
        """
        progress = self.get_by_id(db, progress_id)
        if not progress:
            return False
            
        if area_id not in progress.discovered_areas:
            progress.discovered_areas.append(area_id)
            db.commit()
            
        return True
    
    def discover_clue(self, db: Session, progress_id: int, clue_id: int) -> bool:
        """
        Registra uma pista como descoberta pelo jogador.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            clue_id: ID da pista
            
        Returns:
            True se registrado com sucesso, False caso contrário
        """
        progress = self.get_by_id(db, progress_id)
        if not progress:
            return False
            
        if clue_id not in progress.discovered_clues:
            progress.discovered_clues.append(clue_id)
            # Atualiza pontos de especialização baseado na pista
            clue = db.query(Clue).filter(Clue.clue_id == clue_id).first()
            if clue and clue.specialization_category:
                self.update_specialization(
                    db, 
                    progress_id, 
                    clue.specialization_category, 
                    clue.specialization_points
                )
            db.commit()
            
        return True
    
    def get_progress_summary(self, db: Session, progress_id: int) -> Dict[str, Any]:
        """
        Obtém um resumo do progresso do jogador.
        
        Args:
            db: Sessão do banco de dados
            progress_id: ID do progresso
            
        Returns:
            Dicionário com resumo do progresso
        """
        progress = self.get_by_id(db, progress_id)
        if not progress:
            return {}
            
        return {
            "specializations": self.get_specializations(db, progress_id),
            "inventory_count": len(progress.inventory),
            "discovered_locations": len(progress.discovered_locations),
            "discovered_areas": len(progress.discovered_areas),
            "discovered_clues": len(progress.discovered_clues),
            "total_points": sum(spec.points for spec in progress.specializations),
            "last_activity": progress.last_activity
        }
    
    def _calculate_level(self, points: int) -> int:
        """
        Calcula o nível com base nos pontos.
        
        Args:
            points: Pontos acumulados
            
        Returns:
            Nível calculado
        """
        if points < 20:
            return 1
        elif points < 50:
            return 2
        elif points < 100:
            return 3
        else:
            return 4