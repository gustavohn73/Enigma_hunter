# src/repositories/object_repository.py
from typing import List, Optional, Dict, Any, Tuple, Set
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
import json
import logging

from src.models.db_models import GameObject, ObjectLevel, Clue, PlayerInventory, PlayerObjectLevel, AreaDetail
from src.repositories.base_repository import BaseRepository

class ObjectRepository(BaseRepository[GameObject]):
    """
    Repositório para operações de banco de dados relacionadas a objetos do jogo.
    Gerencia objetos, seus diferentes níveis de conhecimento e o inventário dos jogadores.
    """
    
    def __init__(self):
        super().__init__(GameObject)
        self.logger = logging.getLogger(__name__)
    
    def get_by_id(self, db: Session, object_id: int) -> Optional[GameObject]:
        """
        Busca um objeto pelo ID.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            
        Returns:
            Objeto encontrado ou None
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(GameObject).filter(GameObject.object_id == object_id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objeto por ID {object_id}: {str(e)}")
            raise
    
    def get_all_by_story(self, db: Session, story_id: int) -> List[GameObject]:
        """
        Busca todos os objetos de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de objetos da história
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(GameObject).filter(
                GameObject.story_id == story_id
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos da história {story_id}: {str(e)}")
            raise
    
    def get_by_location(self, db: Session, location_id: int, area_id: Optional[int] = None) -> List[GameObject]:
        """
        Busca objetos por localização e, opcionalmente, por área específica.
        
        Args:
            db: Sessão do banco de dados
            location_id: ID da localização
            area_id: ID da área (opcional)
            
        Returns:
            Lista de objetos na localização/área
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(GameObject).filter(GameObject.initial_location_id == location_id)
            
            if area_id is not None:
                query = query.filter(GameObject.initial_area_id == area_id)
                
            return query.all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos por localização {location_id}, área {area_id}: {str(e)}")
            raise
    
    def get_by_type(self, db: Session, story_id: int, object_type: str) -> List[GameObject]:
        """
        Busca objetos por tipo (categoria).
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            object_type: Tipo/categoria do objeto
            
        Returns:
            Lista de objetos do tipo especificado
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Assumindo que o tipo/categoria esteja em um campo JSON 'attributes'
            return db.query(GameObject).filter(
                GameObject.story_id == story_id,
                GameObject.base_description.like(f'%{object_type}%')
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos por tipo {object_type}: {str(e)}")
            raise
    
    def get_object_with_levels(self, db: Session, object_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém um objeto com todos os seus níveis de conhecimento.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            
        Returns:
            Dicionário com dados do objeto e seus níveis ou None se não encontrado
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Usa joinedload para evitar o problema N+1
            game_object = db.query(GameObject).options(
                joinedload(GameObject.levels)
            ).filter(
                GameObject.object_id == object_id
            ).first()
            
            if not game_object:
                return None
            
            # Constrói o dicionário de resposta
            result = {
                "object": {
                    "object_id": game_object.object_id,
                    "story_id": game_object.story_id,
                    "name": game_object.name,
                    "base_description": game_object.base_description,
                    "is_collectible": game_object.is_collectible,
                    "initial_location_id": game_object.initial_location_id,
                    "initial_area_id": game_object.initial_area_id,
                    "discovery_condition": game_object.discovery_condition
                },
                "levels": []
            }
            
            # Adiciona níveis ao resultado
            for level in game_object.levels:
                level_data = {
                    "level_id": level.level_id,
                    "level_number": level.level_number,
                    "level_description": level.level_description,
                    "level_attributes": self._parse_json_field(level.level_attributes),
                    "evolution_trigger": level.evolution_trigger,
                    "related_clue_id": level.related_clue_id
                }
                result["levels"].append(level_data)
            
            # Ordena os níveis por número
            result["levels"].sort(key=lambda x: x["level_number"])
            
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objeto com níveis para ID {object_id}: {str(e)}")
            raise
    
    def get_object_level(self, db: Session, object_id: int, level_number: int) -> Optional[ObjectLevel]:
        """
        Obtém um nível específico de conhecimento sobre um objeto.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            level_number: Número do nível
            
        Returns:
            Nível do objeto ou None
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(ObjectLevel).filter(
                ObjectLevel.object_id == object_id,
                ObjectLevel.level_number == level_number
            ).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar nível {level_number} do objeto {object_id}: {str(e)}")
            raise
    
    def get_next_level(self, db: Session, object_id: int, current_level: int) -> Optional[ObjectLevel]:
        """
        Obtém o próximo nível de um objeto com base no nível atual.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            current_level: Nível atual
            
        Returns:
            Próximo nível ou None se não houver
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(ObjectLevel).filter(
                ObjectLevel.object_id == object_id,
                ObjectLevel.level_number == current_level + 1
            ).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar próximo nível para objeto {object_id}: {str(e)}")
            raise
    
    def get_max_level(self, db: Session, object_id: int) -> int:
        """
        Obtém o nível máximo disponível para um objeto.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            
        Returns:
            Número do nível máximo
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            result = db.query(func.max(ObjectLevel.level_number)).filter(
                ObjectLevel.object_id == object_id
            ).scalar()
            
            return result or 0
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar nível máximo para objeto {object_id}: {str(e)}")
            raise
    
    def get_next_level_requirements(self, db: Session, object_id: int, current_level: int) -> Dict[str, Any]:
        """
        Obtém os requisitos para evoluir um objeto para o próximo nível.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            current_level: Nível atual do objeto
            
        Returns:
            Dicionário com requisitos para evolução ou None se não houver próximo nível
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            next_level = self.get_next_level(db, object_id, current_level)
            
            if not next_level:
                return None
            
            # Se houver uma pista relacionada, a obtemos
            related_clue = None
            if next_level.related_clue_id:
                related_clue = db.query(Clue).filter(
                    Clue.clue_id == next_level.related_clue_id
                ).first()
            
            return {
                "level": next_level,
                "evolution_trigger": next_level.evolution_trigger,
                "related_clue": related_clue
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar requisitos do próximo nível para objeto {object_id}: {str(e)}")
            raise
    
    def get_collectible_objects(self, db: Session, story_id: int) -> List[GameObject]:
        """
        Obtém todos os objetos coletáveis de uma história.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            
        Returns:
            Lista de objetos coletáveis
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(GameObject).filter(
                GameObject.story_id == story_id,
                GameObject.is_collectible == True
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos coletáveis da história {story_id}: {str(e)}")
            raise
    
    def get_objects_related_to_clue(self, db: Session, clue_id: int) -> List[GameObject]:
        """
        Obtém objetos relacionados a uma pista específica.
        
        Args:
            db: Sessão do banco de dados
            clue_id: ID da pista
            
        Returns:
            Lista de objetos relacionados à pista
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(GameObject).join(
                ObjectLevel, GameObject.object_id == ObjectLevel.object_id
            ).filter(
                ObjectLevel.related_clue_id == clue_id
            ).distinct().all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos relacionados à pista {clue_id}: {str(e)}")
            raise
    
    def check_object_evolution(self, db: Session, object_id: int, current_level: int, 
                             trigger_value: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifica se um objeto pode evoluir para o próximo nível com base no gatilho.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            current_level: Nível atual do objeto
            trigger_value: Valor do gatilho a verificar (opcional)
            
        Returns:
            Dicionário com resultado da verificação
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            next_level_requirements = self.get_next_level_requirements(db, object_id, current_level)
            
            if not next_level_requirements:
                return {
                    "can_evolve": False,
                    "reason": "Objeto já está no nível máximo",
                    "next_level": None
                }
            
            # Extrai o gatilho necessário
            required_trigger = next_level_requirements.get("evolution_trigger", "")
            
            # Se não há trigger_value e não há evolution_trigger definido, 
            # assumimos que o objeto pode evoluir automaticamente
            if not trigger_value and not required_trigger:
                return {
                    "can_evolve": True,
                    "reason": "Evolução automática",
                    "next_level": current_level + 1,
                    "next_level_data": next_level_requirements.get("level")
                }
            
            # Se há evolution_trigger, verificamos se o trigger_value corresponde
            if trigger_value and required_trigger:
                matches = trigger_value.lower() == required_trigger.lower()
                return {
                    "can_evolve": matches,
                    "reason": "Gatilho correspondente" if matches else "Gatilho não correspondente",
                    "next_level": current_level + 1 if matches else current_level,
                    "next_level_data": next_level_requirements.get("level") if matches else None
                }
            
            # Caso nenhuma das condições anteriores seja atendida
            return {
                "can_evolve": False,
                "reason": "Condições de evolução não atendidas",
                "next_level": current_level
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao verificar evolução do objeto {object_id}: {str(e)}")
            raise
    
    def get_player_objects(self, db: Session, session_id: str) -> List[Dict[str, Any]]:
        """
        Obtém todos os objetos no inventário de um jogador com seus níveis atuais.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            
        Returns:
            Lista de objetos com dados de nível
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Busca os objetos no inventário do jogador
            inventory_items = db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id
            ).all()
            
            result = []
            for item in inventory_items:
                # Busca o objeto
                game_object = db.query(GameObject).filter(
                    GameObject.object_id == item.object_id
                ).first()
                
                if not game_object:
                    continue
                
                # Busca o nível atual do objeto para o jogador
                object_level = db.query(PlayerObjectLevel).filter(
                    PlayerObjectLevel.session_id == session_id,
                    PlayerObjectLevel.object_id == item.object_id
                ).first()
                
                current_level = object_level.current_level if object_level else 0
                
                # Busca detalhes do nível atual
                level_details = self.get_object_level(db, item.object_id, current_level)
                
                # Adiciona ao resultado
                result.append({
                    "inventory_id": item.inventory_id,
                    "object_id": item.object_id,
                    "name": game_object.name,
                    "description": game_object.base_description,
                    "current_level": current_level,
                    "level_description": level_details.level_description if level_details else "",
                    "acquisition_time": item.acquired_time,
                    "acquisition_method": item.acquisition_method
                })
            
            return result
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos do jogador {session_id}: {str(e)}")
            raise
    
    def create_object(self, db: Session, object_data: Dict[str, Any]) -> GameObject:
        """
        Cria um novo objeto no jogo.
        
        Args:
            db: Sessão do banco de dados
            object_data: Dados do novo objeto
            
        Returns:
            Objeto criado
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Cria o objeto
            game_object = GameObject(
                story_id=object_data.get("story_id"),
                name=object_data.get("name", "Objeto sem nome"),
                base_description=object_data.get("base_description", ""),
                is_collectible=object_data.get("is_collectible", True),
                initial_location_id=object_data.get("initial_location_id"),
                initial_area_id=object_data.get("initial_area_id"),
                discovery_condition=object_data.get("discovery_condition", "")
            )
            
            db.add(game_object)
            db.commit()
            db.refresh(game_object)
            
            return game_object
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar objeto: {str(e)}")
            raise
    
    def update_object(self, db: Session, object_id: int, object_data: Dict[str, Any]) -> Optional[GameObject]:
        """
        Atualiza um objeto existente.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            object_data: Dados atualizados
            
        Returns:
            Objeto atualizado ou None se não encontrado
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            game_object = self.get_by_id(db, object_id)
            
            if not game_object:
                return None
            
            # Atualiza campos fornecidos
            if "name" in object_data:
                game_object.name = object_data["name"]
            if "base_description" in object_data:
                game_object.base_description = object_data["base_description"]
            if "is_collectible" in object_data:
                game_object.is_collectible = object_data["is_collectible"]
            if "initial_location_id" in object_data:
                game_object.initial_location_id = object_data["initial_location_id"]
            if "initial_area_id" in object_data:
                game_object.initial_area_id = object_data["initial_area_id"]
            if "discovery_condition" in object_data:
                game_object.discovery_condition = object_data["discovery_condition"]
            
            db.commit()
            db.refresh(game_object)
            
            return game_object
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar objeto {object_id}: {str(e)}")
            raise
    
    def add_object_level(self, db: Session, object_id: int, level_data: Dict[str, Any]) -> Optional[ObjectLevel]:
        """
        Adiciona um novo nível a um objeto.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            level_data: Dados do novo nível
            
        Returns:
            Nível de objeto criado ou None se o objeto não existir
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Verifica se o objeto existe
            if not self.exists(db, object_id):
                self.logger.warning(f"Tentativa de adicionar nível a objeto inexistente: {object_id}")
                return None
            
            # Prepara o campo JSON
            level_attributes = level_data.get("level_attributes", {})
            if isinstance(level_attributes, dict):
                level_attributes_json = json.dumps(level_attributes)
            else:
                level_attributes_json = level_attributes
            
            # Cria o nível
            object_level = ObjectLevel(
                object_id=object_id,
                level_number=level_data.get("level_number", 0),
                level_description=level_data.get("level_description", ""),
                level_attributes=level_attributes_json,
                evolution_trigger=level_data.get("evolution_trigger", ""),
                related_clue_id=level_data.get("related_clue_id")
            )
            
            db.add(object_level)
            db.commit()
            db.refresh(object_level)
            
            return object_level
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar nível ao objeto {object_id}: {str(e)}")
            raise
    
    def update_object_level(self, db: Session, level_id: int, level_data: Dict[str, Any]) -> Optional[ObjectLevel]:
        """
        Atualiza um nível de objeto existente.
        
        Args:
            db: Sessão do banco de dados
            level_id: ID do nível
            level_data: Dados atualizados
            
        Returns:
            Nível atualizado ou None se não encontrado
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Busca o nível
            level = db.query(ObjectLevel).filter(ObjectLevel.level_id == level_id).first()
            
            if not level:
                return None
            
            # Atualiza campos fornecidos
            if "level_number" in level_data:
                level.level_number = level_data["level_number"]
            if "level_description" in level_data:
                level.level_description = level_data["level_description"]
            if "level_attributes" in level_data:
                attributes = level_data["level_attributes"]
                if isinstance(attributes, dict):
                    level.level_attributes = json.dumps(attributes)
                else:
                    level.level_attributes = attributes
            if "evolution_trigger" in level_data:
                level.evolution_trigger = level_data["evolution_trigger"]
            if "related_clue_id" in level_data:
                level.related_clue_id = level_data["related_clue_id"]
            
            db.commit()
            db.refresh(level)
            
            return level
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar nível {level_id}: {str(e)}")
            raise
    
    def delete_object(self, db: Session, object_id: int) -> bool:
        """
        Remove um objeto e todos os seus níveis.
        
        Args:
            db: Sessão do banco de dados
            object_id: ID do objeto
            
        Returns:
            True se removido com sucesso
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Remove os níveis primeiro
            db.query(ObjectLevel).filter(ObjectLevel.object_id == object_id).delete()
            
            # Remove o objeto
            result = db.query(GameObject).filter(GameObject.object_id == object_id).delete()
            
            db.commit()
            
            return result > 0
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao remover objeto {object_id}: {str(e)}")
            raise
    
    def delete_object_level(self, db: Session, level_id: int) -> bool:
        """
        Remove um nível de objeto específico.
        
        Args:
            db: Sessão do banco de dados
            level_id: ID do nível
            
        Returns:
            True se removido com sucesso
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            result = db.query(ObjectLevel).filter(ObjectLevel.level_id == level_id).delete()
            db.commit()
            return result > 0
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao remover nível {level_id}: {str(e)}")
            raise
    
    def bulk_create_objects(self, db: Session, objects_data: List[Dict[str, Any]]) -> List[GameObject]:
        """
        Cria múltiplos objetos de uma vez.
        
        Args:
            db: Sessão do banco de dados
            objects_data: Lista de dados de objetos
            
        Returns:
            Lista de objetos criados
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Cria os objetos
            objects = []
            for data in objects_data:
                game_object = GameObject(
                    story_id=data.get("story_id"),
                    name=data.get("name", "Objeto sem nome"),
                    base_description=data.get("base_description", ""),
                    is_collectible=data.get("is_collectible", True),
                    initial_location_id=data.get("initial_location_id"),
                    initial_area_id=data.get("initial_area_id"),
                    discovery_condition=data.get("discovery_condition", "")
                )
                objects.append(game_object)
            
            # Adiciona todos ao banco
            db.add_all(objects)
            db.commit()
            
            # Atualiza IDs
            for obj in objects:
                db.refresh(obj)
            
            return objects
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar objetos em lote: {str(e)}")
            raise
    
    def bulk_add_to_inventory(self, db: Session, session_id: str, object_ids: List[int], 
                            acquisition_method: str = "discovered") -> List[PlayerInventory]:
        """
        Adiciona múltiplos objetos ao inventário de um jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_ids: Lista de IDs de objetos
            acquisition_method: Método de aquisição dos objetos
            
        Returns:
            Lista de itens de inventário adicionados
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Verifica quais objetos já estão no inventário
            existing_items = db.query(PlayerInventory.object_id).filter(
                PlayerInventory.session_id == session_id,
                PlayerInventory.object_id.in_(object_ids)
            ).all()
            
            existing_ids = {item.object_id for item in existing_items}
            
            # Filtra apenas os objetos que ainda não estão no inventário
            new_object_ids = [obj_id for obj_id in object_ids if obj_id not in existing_ids]
            
            if not new_object_ids:
                return []
            
            # Cria os novos itens de inventário
            inventory_items = []
            for obj_id in new_object_ids:
                item = PlayerInventory(
                    session_id=session_id,
                    object_id=obj_id,
                    acquisition_method=acquisition_method
                )
                inventory_items.append(item)
            
            # Adiciona todos ao banco
            db.add_all(inventory_items)
            db.commit()
            
            # Atualiza IDs
            for item in inventory_items:
                db.refresh(item)
            
            return inventory_items
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao adicionar objetos em lote ao inventário: {str(e)}")
            raise
    
    def is_in_inventory(self, db: Session, session_id: str, object_id: int) -> bool:
        """
        Verifica se um objeto está no inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_id: ID do objeto
            
        Returns:
            True se o objeto estiver no inventário
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id,
                PlayerInventory.object_id == object_id
            ).first() is not None
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao verificar objeto {object_id} no inventário: {str(e)}")
            raise
    
    def get_inventory_count(self, db: Session, session_id: str) -> int:
        """
        Conta quantos objetos o jogador tem no inventário.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            
        Returns:
            Número de objetos no inventário
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(func.count(PlayerInventory.inventory_id)).filter(
                PlayerInventory.session_id == session_id
            ).scalar() or 0
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao contar objetos no inventário: {str(e)}")
            raise
    
    def _parse_json_field(self, field_value: Any) -> Any:
        """
        Analisa um campo que pode estar armazenado como JSON.
        
        Args:
            field_value: Valor do campo que pode ser string JSON ou outra coisa
            
        Returns:
            Valor decodificado ou o valor original
        """
        if not field_value:
            return {}
            
        if isinstance(field_value, str):
            try:
                return json.loads(field_value)
            except json.JSONDecodeError:
                return field_value
        
        return field_value
    def get_object_by_name(self, db: Session, story_id: int, name: str) -> Optional[GameObject]:
        """
        Busca um objeto pelo nome dentro de uma história específica.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            name: Nome do objeto (busca insensível a maiúsculas/minúsculas)
            
        Returns:
            Objeto encontrado ou None
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(GameObject).filter(
                GameObject.story_id == story_id,
                func.lower(GameObject.name) == name.lower()
            ).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objeto por nome '{name}': {str(e)}")
            raise
    
    def find_objects_by_keyword(self, db: Session, story_id: int, keyword: str) -> List[GameObject]:
        """
        Busca objetos que contenham uma palavra-chave no nome ou descrição.
        
        Args:
            db: Sessão do banco de dados
            story_id: ID da história
            keyword: Palavra-chave para busca
            
        Returns:
            Lista de objetos correspondentes
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            return db.query(GameObject).filter(
                GameObject.story_id == story_id,
                (
                    GameObject.name.ilike(f"%{keyword}%") | 
                    GameObject.base_description.ilike(f"%{keyword}%")
                )
            ).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos por palavra-chave '{keyword}': {str(e)}")
            raise
    
    def combine_objects(self, db: Session, session_id: str, object_ids: List[int], 
                      result_object_id: int) -> Dict[str, Any]:
        """
        Combina objetos para criar um novo objeto no inventário do jogador.
        
        Args:
            db: Sessão do banco de dados
            session_id: ID da sessão do jogador
            object_ids: IDs dos objetos a serem combinados
            result_object_id: ID do objeto resultante
            
        Returns:
            Resultado da combinação
            
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            # Verifica se todos os objetos existem no inventário
            inventory_objects = db.query(PlayerInventory).filter(
                PlayerInventory.session_id == session_id,
                PlayerInventory.object_id.in_(object_ids)
            ).all()
            
            found_ids = {item.object_id for item in inventory_objects}
            
            # Se algum objeto não estiver no inventário, não pode combinar
            if len(found_ids) != len(object_ids):
                missing_ids = set(object_ids) - found_ids
                return {
                    "success": False,
                    "message": f"Objetos não encontrados no inventário: {missing_ids}"
                }
            
            # Verifica se o objeto resultante existe
            result_object = self.get_by_id(db, result_object_id)
            if not result_object:
                return {
                    "success": False,
                    "message": f"Objeto resultante não encontrado: {result_object_id}"
                }
            
            # Adiciona o objeto resultante ao inventário
            # (Não remove os objetos originais - caso seja necessário, 
            # adicione a lógica de remoção aqui)
            new_item = PlayerInventory(
                session_id=session_id,
                object_id=result_object_id,
                acquisition_method="combined"
            )
            
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            
            return {
                "success": True,
                "message": f"Objetos combinados com sucesso: {result_object.name}",
                "result_object": {
                    "object_id": result_object.object_id,
                    "name": result_object.name,
                    "description": result_object.base_description
                },
                "inventory_id": new_item.inventory_id
            }
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao combinar objetos {object_ids}: {str(e)}")
            raise

    def get_objects_in_area(self, db: Session, area_id: int) -> List[Dict[str, Any]]:
        """
        Obtém os objetos visíveis em uma área específica.
        
        Args:
            db: Sessão do banco de dados
            area_id: ID da área
            
        Returns:
            Lista de objetos na área
        """
        try:
            area_details = db.query(AreaDetail).filter(
                AreaDetail.area_id == area_id,
                AreaDetail.discovery_level_required == 0  # Apenas objetos inicialmente visíveis
            ).all()
            
            result = []
            for detail in area_details:
                if detail.has_clue:  # Se o detalhe contém uma pista ou objeto interativo
                    result.append({
                        "id": detail.detail_id,
                        "name": detail.name,
                        "description": detail.description,
                        "area_id": detail.area_id,
                        "discovery_level": detail.discovery_level_required,
                        "has_clue": detail.has_clue
                    })
            
            self.logger.debug(f"Encontrados {len(result)} objetos na área {area_id}")
            return result
            
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar objetos na área {area_id}: {e}")
            return []