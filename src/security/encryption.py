"""
Sistema de encriptación asimétrica
"""

import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from .key_manager import KeyManager
from ..utils.exceptions import EncryptionError

class EncryptionService:
    """Servicio de encriptación RSA"""
    
    def __init__(self):
        """Inicializar servicio de encriptación"""
        self._private_key = None
        self._public_key = None
    
    def _ensure_keys_loaded(self):
        """Asegurar que las llaves estén cargadas"""
        if not self._private_key or not self._public_key:
            self._private_key = KeyManager.load_private_key()
            self._public_key = KeyManager.load_public_key()
    
    def encrypt(self, data):
        """Encriptar datos usando llave pública"""
        try:
            self._ensure_keys_loaded()
            
            # Convertir string a bytes si es necesario
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Encriptar datos
            encrypted = self._public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Codificar en base64 para almacenamiento
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            raise EncryptionError(f"Error encriptando datos: {str(e)}")
    
    def decrypt(self, encrypted_data):
        """Desencriptar datos usando llave privada"""
        try:
            self._ensure_keys_loaded()
            
            # Decodificar base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Desencriptar datos
            decrypted = self._private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            raise EncryptionError(f"Error desencriptando datos: {str(e)}")
    
    def encrypt_sensitive_fields(self, data_dict, sensitive_fields):
        """Encriptar campos sensibles en un diccionario"""
        encrypted_dict = data_dict.copy()
        
        for field in sensitive_fields:
            if field in encrypted_dict and encrypted_dict[field] is not None:
                encrypted_dict[field] = self.encrypt(str(encrypted_dict[field]))
        
        return encrypted_dict
    
    def decrypt_sensitive_fields(self, encrypted_dict, sensitive_fields):
        """Desencriptar campos sensibles en un diccionario"""
        decrypted_dict = encrypted_dict.copy()
        
        for field in sensitive_fields:
            if field in decrypted_dict and decrypted_dict[field] is not None:
                try:
                    decrypted_dict[field] = self.decrypt(decrypted_dict[field])
                except EncryptionError:
                    # Si no se puede desencriptar, mantener el valor original
                    pass
        
        return decrypted_dict