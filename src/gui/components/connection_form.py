"""
Formulario de conexión a base de datos
"""

import tkinter as tk
from tkinter import ttk

class ConnectionForm:
    """Formulario para configurar conexión a PostgreSQL"""
    
    def __init__(self, parent, config, on_connect_callback):
        """Inicializar formulario de conexión"""
        self.parent = parent
        self.config = config
        self.on_connect = on_connect_callback
        
        self._create_widgets()
        self._load_default_values()
    
    def _create_widgets(self):
        """Crear widgets del formulario"""
        # Variables para los campos
        self.host_var = tk.StringVar()
        self.port_var = tk.StringVar()
        self.database_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.schema_var = tk.StringVar()
        
        # Frame principal
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill="x", expand=True)
        
        # Frame izquierdo - Campos de conexión
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="x", expand=True)
        
        # Campos de entrada
        row = 0
        
        # Host
        ttk.Label(left_frame, text="Host:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(left_frame, textvariable=self.host_var, width=15).grid(row=row, column=1, padx=5, pady=2)
        
        # Puerto
        ttk.Label(left_frame, text="Puerto:").grid(row=row, column=2, sticky="w", padx=5, pady=2)
        ttk.Entry(left_frame, textvariable=self.port_var, width=8).grid(row=row, column=3, padx=5, pady=2)
        
        row += 1
        
        # Base de datos
        ttk.Label(left_frame, text="Base de datos:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(left_frame, textvariable=self.database_var, width=15).grid(row=row, column=1, padx=5, pady=2)
        
        # Esquema
        ttk.Label(left_frame, text="Esquema:").grid(row=row, column=2, sticky="w", padx=5, pady=2)
        ttk.Entry(left_frame, textvariable=self.schema_var, width=8).grid(row=row, column=3, padx=5, pady=2)
        
        row += 1
        
        # Usuario
        ttk.Label(left_frame, text="Usuario:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(left_frame, textvariable=self.user_var, width=15).grid(row=row, column=1, padx=5, pady=2)
        
        # Contraseña
        ttk.Label(left_frame, text="Contraseña:").grid(row=row, column=2, sticky="w", padx=5, pady=2)
        ttk.Entry(left_frame, textvariable=self.password_var, width=15, show="*").grid(row=row, column=3, padx=5, pady=2)
        
        # Frame derecho - Botones y estado
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", padx=10)
        
        # Botón conectar
        self.connect_btn = ttk.Button(right_frame, text="Conectar", command=self._connect)
        self.connect_btn.pack(pady=5)
        
        # Botón probar conexión
        ttk.Button(right_frame, text="Probar", command=self._test_connection).pack(pady=2)
        
        # Estado de conexión
        self.status_label = ttk.Label(right_frame, text="Desconectado", foreground="red")
        self.status_label.pack(pady=5)
    
    def _load_default_values(self):
        """Cargar valores por defecto desde configuración"""
        self.host_var.set(self.config.db_host)
        self.port_var.set(str(self.config.db_port))
        self.database_var.set(self.config.db_name)
        self.user_var.set(self.config.db_user)
        self.password_var.set(self.config.db_password)
        self.schema_var.set(self.config.db_schema)
    
    def _get_connection_data(self):
        """Obtener datos de conexión del formulario"""
        return {
            'db_host': self.host_var.get().strip(),
            'db_port': int(self.port_var.get().strip()),
            'db_name': self.database_var.get().strip(),
            'db_user': self.user_var.get().strip(),
            'db_password': self.password_var.get(),
            'db_schema': self.schema_var.get().strip()
        }
    
    def _validate_form(self):
        """Validar campos del formulario"""
        data = self._get_connection_data()
        
        required_fields = ['db_host', 'db_name', 'db_user', 'db_schema']
        for field in required_fields:
            if not data[field]:
                raise ValueError(f"Campo requerido: {field}")
        
        if not isinstance(data['db_port'], int) or data['db_port'] <= 0:
            raise ValueError("Puerto debe ser un número válido")
        
        return data
    
    def _connect(self):
        """Conectar a la base de datos"""
        try:
            connection_data = self._validate_form()
            self.set_status("Conectando...", "orange")
            self.connect_btn.config(state="disabled")
            
            # Llamar callback de conexión
            self.on_connect(connection_data)
            
        except ValueError as e:
            self.set_status("Error en formulario", "red")
            tk.messagebox.showerror("Error", str(e))
            self.connect_btn.config(state="normal")
        except Exception as e:
            self.set_status("Error de conexión", "red")
            tk.messagebox.showerror("Error", f"Error de conexión: {str(e)}")
            self.connect_btn.config(state="normal")
    
    def _test_connection(self):
        """Probar conexión sin establecerla permanentemente"""
        try:
            connection_data = self._validate_form()
            self.set_status("Probando...", "orange")
            
            # Aquí podrías hacer una conexión de prueba rápida
            # Por simplicidad, usa el mismo callback
            self.on_connect(connection_data)
            
        except ValueError as e:
            self.set_status("Error en formulario", "red")
            tk.messagebox.showerror("Error", str(e))
        except Exception as e:
            self.set_status("Error de prueba", "red")
            tk.messagebox.showerror("Error", f"Error probando conexión: {str(e)}")
    
    def set_status(self, message, color="black"):
        """Establecer estado de conexión"""
        self.status_label.config(text=message, foreground=color)
        
        if message == "Conectado":
            self.connect_btn.config(state="normal", text="Reconectar")
        else:
            self.connect_btn.config(state="normal", text="Conectar")
        
        self.parent.update_idletasks()