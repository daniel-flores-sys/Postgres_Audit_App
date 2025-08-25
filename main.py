#!/usr/bin/env python3
"""
Aplicación de Auditoría PostgreSQL
Punto de entrada principal
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.logger import setup_logger
from src.utils.config import Config
from src.gui.main_window import MainWindow
from src.security.key_manager import KeyManager

def main():
    """Función principal de la aplicación"""
    try:
        # Configurar logging
        logger = setup_logger()
        logger.info("Iniciando aplicación de auditoría PostgreSQL")
        
        # Cargar configuración
        config = Config()
        
        # Verificar o generar llaves de encriptación
        if not KeyManager.keys_exist():
            logger.info("Generando llaves de encriptación...")
            KeyManager.generate_keys()
            logger.info("Llaves generadas exitosamente")
        
        # Crear aplicación tkinter
        root = tk.Tk()
        app = MainWindow(root, config, logger)
        
        logger.info("Aplicación iniciada correctamente")
        
        # Ejecutar loop principal
        root.mainloop()
        
    except Exception as e:
        error_msg = f"Error al iniciar aplicación: {str(e)}"
        print(error_msg)
        messagebox.showerror("Error", error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()