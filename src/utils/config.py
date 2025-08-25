"""
Módulo de configuración
"""

import os
from dotenv import load_dotenv
from .exceptions import ConfigurationError

class Config:
    """Clase para manejo de configuraciones"""
    
    def __init__(self):
        """Inicializar configuración"""
        load_dotenv()
        self._validate_config()
    
    @property
    def db_host(self):
        return os.getenv('DB_HOST', 'localhost')
    
    @property
    def db_port(self):
        return int(os.getenv('DB_PORT', '5450'))
    
    @property
    def db_name(self):
        return os.getenv('DB_NAME', 'postgres')
    
    @property
    def db_user(self):
        return os.getenv('DB_USER', 'postgres')
    
    @property
    def db_password(self):
        return os.getenv('DB_PASSWORD', '')
    
    @property
    def db_schema(self):
        return os.getenv('DB_SCHEMA', 'public')
    
    @property
    def log_level(self):
        return os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def keys_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'keys')
    
    @property
    def logs_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    
    def _validate_config(self):
        """Validar configuración requerida"""
        required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ConfigurationError(f"Variables de entorno faltantes: {', '.join(missing_vars)}")
    
    def get_connection_string(self):
        """Obtener string de conexión PostgreSQL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"