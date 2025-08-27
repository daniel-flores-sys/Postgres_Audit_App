"""
Funciones SQL para crear auditorías en PostgreSQL
"""

import logging
from ...utils.exceptions import AuditCreationError

class AuditFunctions:
    """Funciones para crear estructuras de auditoría en PostgreSQL"""
    
    def __init__(self, db_connection):
        """Inicializar funciones de auditoría"""
        self.db_connection = db_connection
        self.logger = logging.getLogger(__name__)
    
    def create_base_functions(self):
        """Crear funciones base de auditoría"""
        try:
            # Función para obtener campos de una tabla
            campos_function = """
                CREATE OR REPLACE FUNCTION get_table_columns(schema_name TEXT, table_name TEXT) 
                RETURNS TEXT AS $$
                DECLARE 
                    column_def TEXT;
                    columns_text TEXT := '';
                    rec RECORD;
                BEGIN 
                    FOR rec IN 
                        SELECT column_name, data_type, 
                               CASE 
                                   WHEN data_type IN ('character varying', 'varchar', 'character', 'char') 
                                   THEN data_type || '(' || COALESCE(character_maximum_length::TEXT, '255') || ')'
                                   WHEN data_type = 'numeric' 
                                   THEN data_type || '(' || COALESCE(numeric_precision::TEXT, '10') || ',' || COALESCE(numeric_scale::TEXT, '0') || ')'
                                   ELSE data_type
                               END as full_type
                        FROM information_schema.columns 
                        WHERE table_schema = schema_name AND table_name = table_name
                        ORDER BY ordinal_position
                    LOOP
                        IF columns_text != '' THEN
                            columns_text := columns_text || ', ';
                        END IF;
                        columns_text := columns_text || rec.column_name || ' ' || rec.full_type;
                    END LOOP;
                    
                    -- Agregar campos de auditoría
                    columns_text := columns_text || ', usuario_accion VARCHAR(100), fecha_accion TIMESTAMP, accion_sql VARCHAR(20)';
                    
                    RETURN columns_text;
                END;
                $$ LANGUAGE plpgsql;
            """
            
            # Función para obtener nombres de columnas para INSERT
            columns_function = """
                CREATE OR REPLACE FUNCTION get_column_names(schema_name TEXT, table_name TEXT, prefix TEXT DEFAULT '') 
                RETURNS TEXT AS $$
                DECLARE 
                    columns_text TEXT := '';
                    rec RECORD;
                BEGIN 
                    FOR rec IN 
                        SELECT column_name
                        FROM information_schema.columns 
                        WHERE table_schema = schema_name AND table_name = table_name
                        ORDER BY ordinal_position
                    LOOP
                        IF columns_text != '' THEN
                            columns_text := columns_text || ', ';
                        END IF;
                        
                        IF prefix != '' THEN
                            columns_text := columns_text || prefix || '.' || rec.column_name;
                        ELSE
                            columns_text := columns_text || rec.column_name;
                        END IF;
                    END LOOP;
                    
                    -- Agregar campos de auditoría
                    columns_text := columns_text || ', SESSION_USER, NOW()';
                    
                    RETURN columns_text;
                END;
                $$ LANGUAGE plpgsql;
            """
            
            self.db_connection.execute_query(campos_function, fetch_results=False)
            self.db_connection.execute_query(columns_function, fetch_results=False)
            
            self.logger.info("Funciones base de auditoría creadas")
            
        except Exception as e:
            raise AuditCreationError(f"Error creando funciones base: {str(e)}")
    
    def get_table_structure(self, table_name):
        """Obtener estructura de una tabla"""
        try:
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'  # O el esquema por defecto de tu config
                table = table_name

            query = """
                SELECT column_name, data_type, character_maximum_length, 
                       numeric_precision, numeric_scale, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """

            result = self.db_connection.execute_query(query, (schema, table))
            return result

        except Exception as e:
            raise AuditCreationError(f"Error obteniendo estructura de {table_name}: {str(e)}")
    
    def create_audit_table(self, original_table, audit_table_name, table_structure):
        """Crear tabla de auditoría"""
        try:
            if '.' in original_table:
                schema, table = original_table.split('.', 1)
            else:
                schema = 'public'
                table = original_table

            # Eliminar tabla de auditoría si existe
            drop_query = f"DROP TABLE IF EXISTS {audit_table_name}"
            self.db_connection.execute_query(drop_query, fetch_results=False)

            # Construir definición de columnas
            columns_def = self._build_column_definitions(table_structure)

            create_query = f"""
                CREATE TABLE {audit_table_name} (
                    {columns_def}
                    usuario_accion VARCHAR(100),
                    fecha_accion TIMESTAMP DEFAULT NOW(),
                    accion_sql VARCHAR(20)
                )
            """

            self.db_connection.execute_query(create_query, fetch_results=False)
            self.logger.info(f"Tabla de auditoría creada: {audit_table_name}")

        except Exception as e:
            raise AuditCreationError(f"Error creando tabla de auditoría {audit_table_name}: {str(e)}")
    
    def _build_column_definitions(self, table_structure):
        """Construir definiciones de columnas"""
        columns = []

        for column in table_structure:
            col_name = column['column_name']
            data_type = column['data_type']

            # Construir tipo completo
            if data_type in ('character varying', 'varchar', 'character', 'char'):
                max_length = column['character_maximum_length']
                if max_length:
                    col_def = f"{col_name} {data_type}({max_length})"
                else:
                    col_def = f"{col_name} {data_type}(255)"

            elif data_type == 'numeric':
                precision = column['numeric_precision'] or 10
                scale = column['numeric_scale'] or 0
                col_def = f"{col_name} {data_type}({precision},{scale})"

            else:
                col_def = f"{col_name} {data_type}"

            columns.append(col_def)

        return ',\n    '.join(columns) + ',\n    '
    
    def create_audit_function(self, table_name, audit_table_name):
        """Crear función de trigger para auditoría"""
        try:
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'
                table = table_name
            function_name = f"{schema}.{table}_audit"

            # Eliminar función si existe
            drop_function_query = f"DROP FUNCTION IF EXISTS {function_name}()"
            self.db_connection.execute_query(drop_function_query, fetch_results=False)

            # Crear función de trigger
            function_query = f"""
                CREATE OR REPLACE FUNCTION {function_name}()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF TG_OP = 'INSERT' THEN
                        INSERT INTO {audit_table_name}
                        SELECT NEW.*, SESSION_USER, NOW(), 'INSERT';
                        RETURN NEW;
                    ELSIF TG_OP = 'UPDATE' THEN
                        INSERT INTO {audit_table_name}
                        SELECT NEW.*, SESSION_USER, NOW(), 'UPDATE';
                        RETURN NEW;
                    ELSIF TG_OP = 'DELETE' THEN
                        INSERT INTO {audit_table_name}
                        SELECT OLD.*, SESSION_USER, NOW(), 'DELETE';
                        RETURN OLD;
                    END IF;
                    RETURN NULL;
                END;
                $$ LANGUAGE plpgsql;
            """

            self.db_connection.execute_query(function_query, fetch_results=False)
            self.logger.info(f"Función de auditoría creada: {function_name}")

        except Exception as e:
            raise AuditCreationError(f"Error creando función de auditoría: {str(e)}")
    
    def create_audit_triggers(self, table_name):
        """Crear triggers de auditoría"""
        try:
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'
                table = table_name
            function_name = f"{schema}.{table}_audit"

        # Nombres de triggers
            insert_trigger = f"{table}_audit_insert"
            update_trigger = f"{table}_audit_update"
            delete_trigger = f"{table}_audit_delete"

            # Eliminar triggers existentes
            drop_triggers = [
                f"DROP TRIGGER IF EXISTS {insert_trigger} ON {table_name}",
                f"DROP TRIGGER IF EXISTS {update_trigger} ON {table_name}",
                f"DROP TRIGGER IF EXISTS {delete_trigger} ON {table_name}"
            ]

            for drop_query in drop_triggers:
                self.db_connection.execute_query(drop_query, fetch_results=False)

            # Crear triggers
            triggers = [
                f"""
                CREATE TRIGGER {insert_trigger}
                    AFTER INSERT ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION {function_name}()
                """,
                f"""
                CREATE TRIGGER {update_trigger}
                    AFTER UPDATE ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION {function_name}()
                """,
                f"""
                CREATE TRIGGER {delete_trigger}
                    BEFORE DELETE ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION {function_name}()
                """
            ]

            for trigger_query in triggers:
                self.db_connection.execute_query(trigger_query, fetch_results=False)

            self.logger.info(f"Triggers de auditoría creados para: {table_name}")

        except Exception as e:
            raise AuditCreationError(f"Error creando triggers: {str(e)}")
    
    def drop_audit_triggers(self, table_name):
        """Eliminar triggers de auditoría"""
        try:
            schema, table = table_name.split('.')
            
            triggers = [
                f"{table}_audit_insert",
                f"{table}_audit_update", 
                f"{table}_audit_delete"
            ]
            
            for trigger in triggers:
                drop_query = f"DROP TRIGGER IF EXISTS {trigger} ON {table_name}"
                self.db_connection.execute_query(drop_query, fetch_results=False)
            
            self.logger.info(f"Triggers eliminados para: {table_name}")
            
        except Exception as e:
            self.logger.warning(f"Error eliminando triggers de {table_name}: {str(e)}")
    
    def drop_audit_function(self, table_name):
        """Eliminar función de auditoría"""
        try:
            schema, table = table_name.split('.')
            function_name = f"{schema}.{table}_audit"
            
            drop_query = f"DROP FUNCTION IF EXISTS {function_name}()"
            self.db_connection.execute_query(drop_query, fetch_results=False)
            
            self.logger.info(f"Función eliminada: {function_name}")
            
        except Exception as e:
            self.logger.warning(f"Error eliminando función de {table_name}: {str(e)}")
    
    def check_triggers_exist(self, table_name):
        """Verificar si existen los triggers de auditoría"""
        try:
            schema, table = table_name.split('.')
            
            query = """
                SELECT COUNT(*) as trigger_count
                FROM information_schema.triggers
                WHERE event_object_schema = %s 
                AND event_object_table = %s
                AND trigger_name LIKE %s
            """
            
            result = self.db_connection.execute_query(query, (schema, table, f"{table}_audit_%"))
            return result[0]['trigger_count'] > 0
            
        except Exception:
            return False
    
    def check_function_exists(self, table_name):
        """Verificar si existe la función de auditoría"""
        try:
            schema, table = table_name.split('.')
            function_name = f"{table}_audit"
            
            query = """
                SELECT COUNT(*) as function_count
                FROM information_schema.routines
                WHERE routine_schema = %s 
                AND routine_name = %s
            """
            
            result = self.db_connection.execute_query(query, (schema, function_name))
            return result[0]['function_count'] > 0
            
        except Exception:
            return False