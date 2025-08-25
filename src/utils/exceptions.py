"""
Excepciones personalizadas del sistema
"""

class AuditSystemError(Exception):
    """Excepción base del sistema de auditoría"""
    pass

class DatabaseConnectionError(AuditSystemError):
    """Error de conexión a base de datos"""
    pass

class ConfigurationError(AuditSystemError):
    """Error de configuración"""
    pass

class EncryptionError(AuditSystemError):
    """Error de encriptación"""
    pass

class AuditCreationError(AuditSystemError):
    """Error al crear estructura de auditoría"""
    pass

class TableNotFoundError(AuditSystemError):
    """Tabla no encontrada"""
    pass