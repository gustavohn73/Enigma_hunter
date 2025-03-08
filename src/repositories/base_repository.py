# src/repositories/base_repository.py
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any, Tuple, Callable
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect
from sqlalchemy import func
import logging

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
        self.logger = logging.getLogger(f"{__name__}.{model_class.__name__}")
    
    def get_by_id(self, db: Session, id_value: Any) -> Optional[T]:
        """
        Busca uma entidade pelo seu ID.
        
        Args:
            db: Sessão do banco de dados
            id_value: Valor do ID primário da entidade
            
        Returns:
            A entidade encontrada ou None se não existir
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            mapper = inspect(self.model_class)
            pk_attr = getattr(self.model_class, mapper.primary_key[0].name)
            return db.query(self.model_class).filter(pk_attr == id_value).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar {self.model_class.__name__} por ID: {str(e)}")
            raise
    
    def get_all(self, db: Session, limit: int = None, offset: int = None) -> List[T]:
        """
        Retorna todas as entidades deste tipo, com suporte a paginação.
        
        Args:
            db: Sessão do banco de dados
            limit: Limite de resultados (opcional)
            offset: Deslocamento inicial (opcional)
            
        Returns:
            Lista de entidades
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(self.model_class)
            
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
                
            return query.all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar todos os {self.model_class.__name__}: {str(e)}")
            raise
    
    def count(self, db: Session, filter_condition=None) -> int:
        """
        Conta o número de entidades, opcionalmente filtradas.
        
        Args:
            db: Sessão do banco de dados
            filter_condition: Condição de filtro opcional
            
        Returns:
            Contagem de entidades
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(func.count(self._get_primary_key()))
            
            if filter_condition is not None:
                query = query.filter(filter_condition)
                
            return query.scalar()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao contar {self.model_class.__name__}: {str(e)}")
            raise
    
    def create(self, db: Session, entity: T) -> T:
        """
        Cria uma nova entidade no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser criada
            
        Returns:
            A entidade criada com ID atualizado
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            db.add(entity)
            db.commit()
            db.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar {self.model_class.__name__}: {str(e)}")
            raise
    
    def bulk_create(self, db: Session, entities: List[T]) -> List[T]:
        """
        Cria múltiplas entidades no banco de dados.
        
        Args:
            db: Sessão do banco de dados
            entities: Lista de entidades a serem criadas
            
        Returns:
            Lista de entidades criadas
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        if not entities:
            return []
            
        try:
            db.add_all(entities)
            db.commit()
            
            for entity in entities:
                db.refresh(entity)
                
            return entities
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar em lote {self.model_class.__name__}: {str(e)}")
            raise
    
    def update(self, db: Session, entity: T) -> T:
        """
        Atualiza uma entidade existente.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser atualizada
            
        Returns:
            A entidade atualizada
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            db.add(entity)
            db.commit()
            db.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao atualizar {self.model_class.__name__}: {str(e)}")
            raise
    
    def delete(self, db: Session, entity: T) -> bool:
        """
        Remove uma entidade do banco de dados.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser removida
            
        Returns:
            True se a entidade foi removida com sucesso
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            db.delete(entity)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao deletar {self.model_class.__name__}: {str(e)}")
            raise
    
    def delete_by_id(self, db: Session, id_value: Any) -> bool:
        """
        Remove uma entidade do banco de dados pelo ID.
        
        Args:
            db: Sessão do banco de dados
            id_value: ID da entidade a ser removida
            
        Returns:
            True se a entidade foi removida, False se não foi encontrada
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            entity = self.get_by_id(db, id_value)
            if entity:
                return self.delete(db, entity)
            return False
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao deletar {self.model_class.__name__} por ID: {str(e)}")
            raise
    
    def create_or_update(self, db: Session, entity: T) -> Tuple[T, bool]:
        """
        Cria uma entidade se ela não existir, ou atualiza se já existir.
        
        Args:
            db: Sessão do banco de dados
            entity: Entidade a ser criada ou atualizada
            
        Returns:
            Tupla (entidade, created) onde created é True se foi criada, False se atualizada
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            mapper = inspect(self.model_class)
            pk_attr = getattr(self.model_class, mapper.primary_key[0].name)
            pk_value = getattr(entity, mapper.primary_key[0].name)
            
            if pk_value is None:
                # Se não tem ID, é uma nova entidade
                created = True
                self.create(db, entity)
            else:
                # Se tem ID, verifica se existe
                existing = db.query(self.model_class).filter(pk_attr == pk_value).first()
                created = existing is None
                
                # Adiciona a entidade à sessão (create ou update)
                db.add(entity)
                db.commit()
                db.refresh(entity)
                
            return entity, created
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Erro ao criar ou atualizar {self.model_class.__name__}: {str(e)}")
            raise
    
    def exists(self, db: Session, id_value: Any) -> bool:
        """
        Verifica se uma entidade com o ID fornecido existe.
        
        Args:
            db: Sessão do banco de dados
            id_value: Valor do ID primário a verificar
            
        Returns:
            True se a entidade existir, False caso contrário
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            mapper = inspect(self.model_class)
            pk_attr = getattr(self.model_class, mapper.primary_key[0].name)
            return db.query(self.model_class).filter(pk_attr == id_value).first() is not None
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao verificar existência de {self.model_class.__name__}: {str(e)}")
            raise
    
    def find_by(self, db: Session, **kwargs) -> List[T]:
        """
        Busca entidades com base em parâmetros de filtro.
        
        Args:
            db: Sessão do banco de dados
            **kwargs: Pares chave-valor representando atributos e valores a filtrar
            
        Returns:
            Lista de entidades que correspondem aos critérios
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(self.model_class)
            
            for key, value in kwargs.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.all()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar {self.model_class.__name__} por atributos: {str(e)}")
            raise
    
    def find_one_by(self, db: Session, **kwargs) -> Optional[T]:
        """
        Busca uma única entidade com base em parâmetros de filtro.
        
        Args:
            db: Sessão do banco de dados
            **kwargs: Pares chave-valor representando atributos e valores a filtrar
            
        Returns:
            A primeira entidade que corresponde aos critérios ou None
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(self.model_class)
            
            for key, value in kwargs.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            
            return query.first()
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar único {self.model_class.__name__} por atributos: {str(e)}")
            raise
    
    def execute_with_transaction(self, db: Session, operation: Callable[[Session], T]) -> T:
        """
        Executa uma operação dentro de uma transação.
        
        Args:
            db: Sessão do banco de dados
            operation: Função que recebe a sessão e executa a operação desejada
            
        Returns:
            Resultado da operação
        
        Raises:
            Exception: Qualquer exceção que ocorra durante a operação
        """
        try:
            result = operation(db)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            self.logger.error(f"Erro na transação: {str(e)}")
            raise
            
    def get_paginated(self, db: Session, page: int = 1, page_size: int = 10, 
                    filter_condition=None, order_by=None) -> Tuple[List[T], int, int]:
        """
        Obtém uma página de resultados com informações de paginação.
        
        Args:
            db: Sessão do banco de dados
            page: Número da página (começando em 1)
            page_size: Tamanho da página
            filter_condition: Condição de filtro opcional
            order_by: Atributo para ordenação opcional
            
        Returns:
            Tupla (itens, total, total_pages)
        
        Raises:
            SQLAlchemyError: Erro ao acessar o banco de dados
        """
        try:
            query = db.query(self.model_class)
            
            if filter_condition is not None:
                query = query.filter(filter_condition)
                
            # Conta o total antes de aplicar paginação
            total = query.count()
            total_pages = (total + page_size - 1) // page_size  # Arredonda para cima
            
            # Aplica ordenação se fornecida
            if order_by is not None:
                query = query.order_by(order_by)
                
            # Aplica paginação
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()
            
            return items, total, total_pages
        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao obter página de {self.model_class.__name__}: {str(e)}")
            raise
            
    def _get_primary_key(self):
        """
        Obtém o atributo de chave primária do modelo.
        
        Returns:
            Atributo de chave primária
        """
        mapper = inspect(self.model_class)
        pk_attr = mapper.primary_key[0]
        return getattr(self.model_class, pk_attr.name)