# src/repositories/base_repository.py
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeBase

T = TypeVar('T', bound=DeclarativeBase)

class BaseRepository(Generic[T]):
    """
    Repositório base que fornece operações comuns de CRUD para entidades.
    Esta classe serve como base para todos os outros repositórios específicos.
    """
    
    def __init__(self, model_class: Type[T]):
        """
        Inicializa o repositório com a classe de modelo especificada.
        
        Args:
            model_class: A classe do modelo SQLAlchemy associada a este repositório
        """
        self.model_class = model_class
    
    def get_by_id(self, db: Session, id_value: Any) -> Optional[T]:
        """
        Busca uma entidade pelo seu ID.
        
        Args:
            db: Sessão do banco de dados
            id_value: Valor do ID primário da entidade
            
        Returns:
            A entidade encontrada ou None se não existir
        """
        return db.query(self.model_class).get(id_value)
    
    def get_all(self, db: Session) -> List[T]:
        """
        Retorna todas as entidades deste tipo.
        
        Args:
            db: Sessão do banco de dados
            
        Returns:
            Lista de todas as entidades
        """
        return db.query(self.model_class).all()
    
    def create(self, db: Session, entity: T) -> T:
        """
        Cria uma nova entidade no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser criada
            
        Returns:
            A entidade criada com ID atualizado
        """
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity
    
    def update(self, db: Session, entity: T) -> T:
        """
        Atualiza uma entidade existente.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser atualizada
            
        Returns:
            A entidade atualizada
        """
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity
    
    def delete(self, db: Session, entity: T) -> bool:
        """
        Remove uma entidade do banco de dados.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser removida
            
        Returns:
            True se a entidade foi removida com sucesso
        """
        db.delete(entity)
        db.commit()
        return True
    
    def create_or_update(self, db: Session, entity: T) -> T:
        """
        Cria uma entidade se ela não existir, ou atualiza se já existir.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser criada ou atualizada
            
        Returns:
            A entidade atualizada
        """
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity
    
    def exists(self, db: Session, id_value: Any) -> bool:
        """
        Verifica se uma entidade com o ID fornecido existe.
        
        Args:
            db: Sessão do banco de dados
            id_value: Valor do ID primário a verificar
            
        Returns:
            True se a entidade existir, False caso contrário
        """
        return db.query(self.model_class).filter(
            self.model_class.get_primary_key() == id_value
        ).first() is not None