"""
Manejo de conexiones PostgreSQL
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from ..utils.exceptions import DatabaseConnectionError
import logging

class DatabaseConnection:
    """Manejador de conexiones PostgreSQL"""
    
    def __init__(self, config, logger=None):
        """Inicializar conexión"""
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._connection = None
        self._test_connection()
    
    def _test_connection(self):
        """Probar conexión inicial"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            self.logger.info("Conexión a PostgreSQL establecida correctamente")
        except Exception as e:
            error_msg = f"Error conectando a PostgreSQL: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseConnectionError(error_msg)
    
    @contextmanager
    def get_connection(self):
        """Context manager para obtener conexión"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                database=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
                cursor_factory=RealDictCursor
            )
            yield conn
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            error_msg = f"Error de base de datos: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseConnectionError(error_msg)
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query, params=None, fetch_results=True):
        """Ejecutar consulta SQL"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.debug(f"Ejecutando query: {query}")
                    cur.execute(query, params)
                    
                    if fetch_results:
                        results = cur.fetchall()
                        self.logger.debug(f"Query retornó {len(results)} filas")
                        return results
                    else:
                        conn.commit()
                        self.logger.debug("Query ejecutada sin retorno de resultados")
                        return None
                        
        except Exception as e:
            error_msg = f"Error ejecutando query: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseConnectionError(error_msg)
    
    def execute_multiple(self, queries):
        """Ejecutar múltiples consultas en una transacción"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for query in queries:
                        if isinstance(query, tuple):
                            sql, params = query
                            self.logger.debug(f"Ejecutando query: {sql}")
                            cur.execute(sql, params)
                        else:
                            self.logger.debug(f"Ejecutando query: {query}")
                            cur.execute(query)
                    
                    conn.commit()
                    self.logger.info(f"Ejecutadas {len(queries)} consultas exitosamente")
                    
        except Exception as e:
            error_msg = f"Error ejecutando múltiples queries: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseConnectionError(error_msg)
    
    def get_tables(self):
        """Obtener lista de tablas del esquema actual"""
        try:
            query = """
                SELECT schemaname||'.'||tablename as nombre 
                FROM pg_tables 
                WHERE schemaname = %s
                AND tablename NOT LIKE 'aud_%'
                ORDER BY tablename
            """
            results = self.execute_query(query, (self.config.db_schema,))
            tables = [row['nombre'] for row in results]
            self.logger.info(f"Encontradas {len(tables)} tablas")
            return tables
            
        except Exception as e:
            error_msg = f"Error obteniendo tablas: {str(e)}"
            self.logger.error(error_msg)
            raise DatabaseConnectionError(error_msg)
    
    def table_exists(self, table_name):
        """Verificar si una tabla existe"""
        try:
            schema, table = table_name.split('.')
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                )
            """
            result = self.execute_query(query, (schema, table))
            return result[0]['exists']
            
        except Exception as e:
            self.logger.error(f"Error verificando tabla {table_name}: {str(e)}")
            return False