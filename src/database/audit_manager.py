"""
Gestor principal de auditoría
"""

import logging
from .queries.audit_functions import AuditFunctions
from ..utils.exceptions import AuditCreationError, TableNotFoundError
from ..security.encryption import EncryptionService

class AuditManager:
    """Gestor principal para crear y manejar auditorías"""
    
    def __init__(self, db_connection, logger=None):
        """Inicializar gestor de auditoría"""
        self.db_connection = db_connection
        self.logger = logger or logging.getLogger(__name__)
        self.audit_functions = AuditFunctions(db_connection)
        self.encryption_service = EncryptionService()
        
        # Crear funciones base si no existen
        self._setup_audit_functions()
    
    def _setup_audit_functions(self):
        """Configurar funciones base de auditoría"""
        try:
            self.logger.info("Configurando funciones base de auditoría...")
            self.audit_functions.create_base_functions()
            self.logger.info("Funciones base configuradas correctamente")
        except Exception as e:
            self.logger.error(f"Error configurando funciones base: {str(e)}")
            raise AuditCreationError(f"Error en setup: {str(e)}")
    
    def create_audit_for_table(self, table_name):
        """Crear auditoría completa para una tabla"""
        try:
            # Verificar que la tabla existe
            if not self.db_connection.table_exists(table_name):
                raise TableNotFoundError(f"Tabla no encontrada: {table_name}")
            
            self.logger.info(f"Iniciando creación de auditoría para tabla: {table_name}")
            
            # Obtener estructura de la tabla
            table_structure = self.audit_functions.get_table_structure(table_name)
            
            # Crear tabla de auditoría
            audit_table_name = self._get_audit_table_name(table_name)
            self.audit_functions.create_audit_table(table_name, audit_table_name, table_structure)
            
            # Crear función de trigger
            self.audit_functions.create_audit_function(table_name, audit_table_name)
            
            # Crear triggers
            self.audit_functions.create_audit_triggers(table_name)
            
            self.logger.info(f"Auditoría creada exitosamente para tabla: {table_name}")
            
        except Exception as e:
            error_msg = f"Error creando auditoría para {table_name}: {str(e)}"
            self.logger.error(error_msg)
            raise AuditCreationError(error_msg)
    
    def remove_audit_for_table(self, table_name):
        """Eliminar auditoría de una tabla"""
        try:
            self.logger.info(f"Eliminando auditoría para tabla: {table_name}")
            
            # Eliminar triggers
            self.audit_functions.drop_audit_triggers(table_name)
            
            # Eliminar función de trigger
            self.audit_functions.drop_audit_function(table_name)
            
            # Eliminar tabla de auditoría (opcional - comentado para preservar datos)
            # audit_table_name = self._get_audit_table_name(table_name)
            # self.audit_functions.drop_audit_table(audit_table_name)
            
            self.logger.info(f"Auditoría eliminada para tabla: {table_name}")
            
        except Exception as e:
            error_msg = f"Error eliminando auditoría para {table_name}: {str(e)}"
            self.logger.error(error_msg)
            raise AuditCreationError(error_msg)
    
    def get_audit_status(self, table_name):
        """Obtener estado de auditoría de una tabla"""
        try:
            audit_table_name = self._get_audit_table_name(table_name)
            
            status = {
                'table_exists': self.db_connection.table_exists(table_name),
                'audit_table_exists': self.db_connection.table_exists(audit_table_name),
                'triggers_exist': self.audit_functions.check_triggers_exist(table_name),
                'function_exists': self.audit_functions.check_function_exists(table_name)
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado de auditoría para {table_name}: {str(e)}")
            return None
    
    def get_audit_data(self, table_name, limit=100, decrypt_sensitive=False):
        """Obtener datos de auditoría de una tabla"""
        try:
            audit_table_name = self._get_audit_table_name(table_name)
            
            if not self.db_connection.table_exists(audit_table_name):
                return []
            
            query = f"""
                SELECT * FROM {audit_table_name}
                ORDER BY fecha_accion DESC
                LIMIT %s
            """
            
            results = self.db_connection.execute_query(query, (limit,))
            
            # Desencriptar campos sensibles si se solicita
            if decrypt_sensitive and results:
                sensitive_fields = self._get_sensitive_fields(table_name)
                for row in results:
                    try:
                        decrypted_row = self.encryption_service.decrypt_sensitive_fields(
                            dict(row), sensitive_fields
                        )
                        row.update(decrypted_row)
                    except Exception:
                        # Si falla la desencriptación, mantener datos originales
                        pass
            
            return results
            
        except Exception as e:
            error_msg = f"Error obteniendo datos de auditoría para {table_name}: {str(e)}"
            self.logger.error(error_msg)
            return []
    
    def _get_audit_table_name(self, table_name):
        """Generar nombre de tabla de auditoría encriptado"""
        key = self.audit_functions._get_encryption_key()
        enc_table_name = self.audit_functions._encrypt_name(table_name, key)
        return f"aud_{enc_table_name}".lower()
    
    def _get_sensitive_fields(self, table_name):
        """Obtener campos sensibles que deben encriptarse"""
        # Esta lista podría configurarse por tabla o globalmente
        # Por ahora, definimos algunos campos comunes
        sensitive_patterns = [
            'password', 'passwd', 'contraseña',
            'email', 'correo',
            'telefono', 'phone', 'celular',
            'dni', 'cedula', 'ssn', 'rfc',
            'tarjeta', 'card', 'cuenta', 'account'
        ]
        
        try:
            # Obtener estructura de tabla para identificar campos sensibles
            structure = self.audit_functions.get_table_structure(table_name)
            sensitive_fields = []
            
            for column in structure:
                column_name = column['column_name'].lower()
                for pattern in sensitive_patterns:
                    if pattern in column_name:
                        sensitive_fields.append(column['column_name'])
                        break
            
            return sensitive_fields
            
        except Exception:
            return []
    
    def create_bulk_audit(self, table_names, progress_callback=None):
        """Crear auditoría para múltiples tablas"""
        results = {
            'success': [],
            'failed': [],
            'total': len(table_names)
        }
        
        for i, table_name in enumerate(table_names):
            try:
                self.create_audit_for_table(table_name)
                results['success'].append(table_name)
                self.logger.info(f"Progreso: {i+1}/{len(table_names)} - Éxito: {table_name}")
                
            except Exception as e:
                results['failed'].append({
                    'table': table_name,
                    'error': str(e)
                })
                self.logger.error(f"Progreso: {i+1}/{len(table_names)} - Error: {table_name} - {str(e)}")
            
            # Callback de progreso si se proporciona
            if progress_callback:
                progress_callback(i + 1, len(table_names), table_name)
        
        return results