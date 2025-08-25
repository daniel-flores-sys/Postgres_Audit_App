"""
Gestión de llaves de encriptación
"""

import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from ..utils.exceptions import EncryptionError

class KeyManager:
    """Gestor de llaves de encriptación RSA"""
    
    @staticmethod
    def get_keys_dir():
        """Obtener directorio de llaves"""
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'keys')
    
    @staticmethod
    def get_private_key_path():
        """Ruta de llave privada"""
        return os.path.join(KeyManager.get_keys_dir(), 'private_key.pem')
    
    @staticmethod
    def get_public_key_path():
        """Ruta de llave pública"""
        return os.path.join(KeyManager.get_keys_dir(), 'public_key.pem')
    
    @staticmethod
    def keys_exist():
        """Verificar si existen las llaves"""
        private_path = KeyManager.get_private_key_path()
        public_path = KeyManager.get_public_key_path()
        return os.path.exists(private_path) and os.path.exists(public_path)
    
    @staticmethod
    def generate_keys():
        """Generar par de llaves RSA"""
        try:
            # Crear directorio si no existe
            keys_dir = KeyManager.get_keys_dir()
            if not os.path.exists(keys_dir):
                os.makedirs(keys_dir)
            
            # Generar llave privada
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Obtener llave pública
            public_key = private_key.public_key()
            
            # Serializar llave privada
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Serializar llave pública
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Guardar llaves
            with open(KeyManager.get_private_key_path(), 'wb') as f:
                f.write(private_pem)
            
            with open(KeyManager.get_public_key_path(), 'wb') as f:
                f.write(public_pem)
            
            # Crear .gitignore para llaves
            gitignore_path = os.path.join(keys_dir, '.gitignore')
            with open(gitignore_path, 'w') as f:
                f.write("*.pem\n*.key\n")
            
        except Exception as e:
            raise EncryptionError(f"Error generando llaves: {str(e)}")
    
    @staticmethod
    def load_private_key():
        """Cargar llave privada"""
        try:
            with open(KeyManager.get_private_key_path(), 'rb') as f:
                return serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
        except Exception as e:
            raise EncryptionError(f"Error cargando llave privada: {str(e)}")
    
    @staticmethod
    def load_public_key():
        """Cargar llave pública"""
        try:
            with open(KeyManager.get_public_key_path(), 'rb') as f:
                return serialization.load_pem_public_key(f.read())
        except Exception as e:
            raise EncryptionError(f"Error cargando llave pública: {str(e)}")