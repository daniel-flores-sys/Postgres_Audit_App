"""
Manejo de conexiones PostgreSQL
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from ..utils.exceptions import DatabaseConnectionError
import logging
from typing import List

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
    
    def get_tables(self) -> List[str]:
        """Obtener tablas de PostgreSQL excluyendo las de auditoría"""
        query = """
        SELECT tablename
        FROM pg_tables 
        WHERE schemaname = %s
          AND tablename NOT LIKE 'aud_%%'
          AND tablename NOT LIKE 'pg_%%'
        ORDER BY tablename
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (self.config.db_schema,))
                    result = cursor.fetchall()
            if result:
                tables = [row['tablename'] if isinstance(row, dict) else row[0] for row in result]
                self.logger.info(f"Encontradas {len(tables)} tablas en esquema '{self.config.db_schema}'")
                return tables
            return []
        except Exception as e:
            self.logger.error(f"Error obteniendo tablas: {e}")
            return []
    
    def _get_tables_fallback(self):
        """Método alternativo para obtener tablas si falla el principal"""
        try:
            self.logger.info("Intentando método alternativo para obtener tablas...")
            
            query = """
                SELECT table_name
                FROM information_schema.tables 
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
                AND table_name NOT LIKE 'aud_%'
                ORDER BY table_name
            """
            results = self.execute_query(query, (self.config.db_schema,))
            
            self.logger.debug(f"Resultados de consulta alternativa: {results}")
            
            tables = []
            for row in results:
                self.logger.debug(f"Procesando fila alternativa: {row}")
                try:
                    if isinstance(row, dict) and 'table_name' in row:
                        table_name = row['table_name']
                    elif isinstance(row, dict):
                        table_name = next(iter(row.values()))
                    else:
                        self.logger.error(f"Fila inesperada (no dict): {row}")
                        continue
                    
                    full_name = f"{self.config.db_schema}.{table_name}"
                    tables.append(full_name)
                    
                except Exception as e:
                    self.logger.error(f"Error procesando fila alternativa: {row}, Error: {str(e)}")
                    continue
        
            self.logger.info(f"Método alternativo encontró {len(tables)} tablas")
            return tables
        
        except Exception as e:
            error_msg = f"Error en método alternativo para obtener tablas: {str(e)}"
            self.logger.error(error_msg)
            return []  # Retornar lista vacía en lugar de lanzar excepción
    
    def table_exists(self, table_name):
        """Verificar si una tabla existe"""
        try:
            if '.' in table_name:
                schema, table = table_name.split('.')
            else:
                schema = self.config.db_schema
                table = table_name
                
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                )
            """
            result = self.execute_query(query, (schema, table))
            
            if result and len(result) > 0:
                if isinstance(result[0], dict) and 'exists' in result[0]:
                    return result[0]['exists']
                elif hasattr(result[0], 'exists'):
                    return result[0].exists
                else:
                    return bool(result[0][0])
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error verificando tabla {table_name}: {str(e)}")
            return False