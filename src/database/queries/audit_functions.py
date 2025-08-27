"""
Funciones SQL para crear auditorías en PostgreSQL
"""

import logging
from ...utils.exceptions import AuditCreationError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64

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
    
    def _get_encryption_key(self):
        """Obtener la clave de encriptación desde la base de datos"""
        query = "SELECT clave FROM clave_secreta LIMIT 1"
        result = self.db_connection.execute_query(query)
        if result and result[0].get('clave'):
            return result[0]['clave']
        raise AuditCreationError("No se encontró clave de encriptación en clave_secreta")

    def _encrypt_name(self, name, key):
        """Encriptar nombre usando AES (simétrico) y base64 seguro para identificadores SQL"""
        key_bytes = key.encode('utf-8')[:32]
        iv = b'\x00' * 16
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv))
        encryptor = cipher.encryptor()
        pad_len = 16 - (len(name.encode('utf-8')) % 16)
        padded = name.encode('utf-8') + bytes([pad_len] * pad_len)
        encrypted = encryptor.update(padded) + encryptor.finalize()
        # Base64 estándar y solo caracteres válidos para identificadores
        b64 = base64.b64encode(encrypted).decode('utf-8')
        # Reemplazar caracteres inválidos por guión bajo
        safe = ''.join(c if c.isalnum() else '_' for c in b64)
        # Opcional: agregar prefijo para evitar que empiece por número
        if not safe[0].isalpha():
            safe = 'a_' + safe
        return safe

    def create_audit_table(self, original_table, audit_table_name=None, table_structure=None):
        """Crear tabla de auditoría con nombres encriptados"""
        try:
            key = self._get_encryption_key()
            enc_table_name = self._encrypt_name(original_table, key)
            audit_table_name = f"aud_{enc_table_name}"

            # Todas las columnas como BYTEA
            columns = []
            for column in table_structure:
                enc_col_name = self._encrypt_name(column['column_name'], key)
                col_def = f"{enc_col_name} BYTEA"
                columns.append(col_def)

            # Campos de auditoría también como BYTEA
            for extra in ['usuario_accion', 'fecha_accion', 'accion_sql']:
                enc_extra = self._encrypt_name(extra, key)
                columns.append(f"{enc_extra} BYTEA")

            columns_def = ',\n    '.join(columns)

            drop_query = f"DROP TABLE IF EXISTS {audit_table_name}"
            self.db_connection.execute_query(drop_query, fetch_results=False)

            create_query = f"CREATE TABLE {audit_table_name} (\n    {columns_def}\n)"
            self.db_connection.execute_query(create_query, fetch_results=False)
            self.logger.info(f"Tabla de auditoría creada: {audit_table_name}")

        except Exception as e:
            raise AuditCreationError(f"Error creando tabla de auditoría: {str(e)}")

    def create_audit_function(self, table_name, audit_table_name=None):
        """Crear función de trigger para auditoría con nombres encriptados"""
        try:
            key = self._get_encryption_key()
            enc_table_name = self._encrypt_name(table_name, key)
            audit_table_name = f"aud_{enc_table_name}"
            function_name = f"{enc_table_name}_audit"

            # Obtener estructura de la tabla original
            table_structure = self.get_table_structure(table_name)

            # Generar lista de campos y valores encriptados
            encrypted_fields = []
            for column in table_structure:
                orig_col = column['column_name']
                enc_col = self._encrypt_name(orig_col, key)
                encrypted_fields.append(f"pgp_sym_encrypt(NEW.{orig_col}::TEXT, key)")

            # Campos de auditoría
            enc_usuario = self._encrypt_name('usuario_accion', key)
            enc_fecha = self._encrypt_name('fecha_accion', key)
            enc_accion = self._encrypt_name('accion_sql', key)

            encrypted_fields.append(f"pgp_sym_encrypt(SESSION_USER::TEXT, key)")
            encrypted_fields.append(f"pgp_sym_encrypt(NOW()::TEXT, key)")
            encrypted_fields.append(f"pgp_sym_encrypt(TG_OP, key)")

            values_str = ',\n                            '.join(encrypted_fields)

            drop_function_query = f"DROP FUNCTION IF EXISTS {function_name}()"
            self.db_connection.execute_query(drop_function_query, fetch_results=False)

            function_query = f"""
                CREATE OR REPLACE FUNCTION {function_name}()
                RETURNS TRIGGER AS $$
                DECLARE
                    key TEXT;
                BEGIN
                    SELECT clave INTO key FROM clave_secreta LIMIT 1;
                    IF TG_OP = 'INSERT' THEN
                        INSERT INTO {audit_table_name} VALUES (
                            {values_str}
                        );
                        RETURN NEW;
                    ELSIF TG_OP = 'UPDATE' THEN
                        INSERT INTO {audit_table_name} VALUES (
                            {values_str}
                        );
                        RETURN NEW;
                    ELSIF TG_OP = 'DELETE' THEN
                        INSERT INTO {audit_table_name} VALUES (
                            {values_str.replace('NEW.', 'OLD.')}
                        );
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
            key = self._get_encryption_key()
            enc_table_name = self._encrypt_name(table_name, key)
            function_name = f"{enc_table_name}_audit"

            insert_trigger = f"{table_name}_audit_insert"
            update_trigger = f"{table_name}_audit_update"
            delete_trigger = f"{table_name}_audit_delete"

            drop_triggers = [
                f"DROP TRIGGER IF EXISTS {insert_trigger} ON {table_name}",
                f"DROP TRIGGER IF EXISTS {update_trigger} ON {table_name}",
                f"DROP TRIGGER IF EXISTS {delete_trigger} ON {table_name}"
            ]

            for drop_query in drop_triggers:
                self.db_connection.execute_query(drop_query, fetch_results=False)

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
            key = self._get_encryption_key()
            enc_table_name = self._encrypt_name(table_name, key)
            function_name = f"{enc_table_name}_audit"
            
            drop_query = f"DROP FUNCTION IF EXISTS {function_name}() CASCADE"
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