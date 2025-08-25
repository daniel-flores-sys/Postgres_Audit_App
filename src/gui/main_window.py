"""
Ventana principal de la aplicación
"""

import tkinter as tk
import logging
from tkinter import ttk, messagebox, scrolledtext
from .components.connection_form import ConnectionForm
from .components.table_selector import TableSelector
from .components.log_viewer import LogViewer
from ..database.connection import DatabaseConnection
from ..database.audit_manager import AuditManager
from ..utils.logger import GUILogHandler
import threading

class MainWindow:
    """Ventana principal de la aplicación"""
    
    def __init__(self, root, config, logger):
        """Inicializar ventana principal"""
        self.root = root
        self.config = config
        self.logger = logger
        self.db_connection = None
        self.audit_manager = None
        
        self._setup_window()
        self._create_widgets()
        self._setup_logging()
        
        # Intentar conexión automática si hay configuración
        self._try_auto_connect()
    
    def _setup_window(self):
        """Configurar ventana principal"""
        self.root.title("Sistema de Auditoría PostgreSQL")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Configurar grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
    
    def _create_widgets(self):
        """Crear widgets de la interfaz"""
        # Frame superior - Conexión
        connection_frame = ttk.LabelFrame(self.root, text="Conexión a Base de Datos", padding="10")
        connection_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.connection_form = ConnectionForm(connection_frame, self.config, self._on_connect)
        
        # Frame principal - Contenido
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Notebook para pestañas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        
        # Pestaña de Auditoría
        self.audit_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.audit_frame, text="Auditoría")
        self._create_audit_tab()
        
        # Pestaña de Logs
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="Logs")
        self._create_log_tab()
        
        # Frame de botones
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        ttk.Button(button_frame, text="Salir", command=self.root.quit).pack(side="right", padx=5)
    
    def _create_audit_tab(self):
        """Crear contenido de la pestaña de auditoría"""
        self.audit_frame.grid_columnconfigure(0, weight=1)
        self.audit_frame.grid_rowconfigure(0, weight=1)
        
        # Selector de tablas
        table_frame = ttk.LabelFrame(self.audit_frame, text="Seleccionar Tablas", padding="10")
        table_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        self.table_selector = TableSelector(table_frame, self._on_tables_selected)
        
        # Frame de acciones
        action_frame = ttk.LabelFrame(self.audit_frame, text="Acciones", padding="10")
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        ttk.Button(action_frame, text="Crear Auditoría", 
                  command=self._create_audit, state="disabled").pack(side="left", padx=5)
        ttk.Button(action_frame, text="Eliminar Auditoría", 
                  command=self._remove_audit, state="disabled").pack(side="left", padx=5)
        
        self.create_btn = action_frame.winfo_children()[0]
        self.remove_btn = action_frame.winfo_children()[1]
    
    def _create_log_tab(self):
        """Crear contenido de la pestaña de logs"""
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)
        
        self.log_viewer = LogViewer(self.log_frame)
    
    def _setup_logging(self):
        """Configurar logging para GUI"""
        gui_handler = GUILogHandler(self.log_viewer.text_widget)
        gui_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(formatter)
        self.logger.addHandler(gui_handler)
    
    def _try_auto_connect(self):
        """Intentar conexión automática"""
        try:
            self.db_connection = DatabaseConnection(self.config, self.logger)
            self.audit_manager = AuditManager(self.db_connection, self.logger)
            self._on_connect_success()
        except Exception as e:
            self.logger.warning(f"Conexión automática fallida: {str(e)}")
    
    def _on_connect(self, connection_data):
        """Callback cuando se intenta conectar"""
        def connect_thread():
            try:
                # Actualizar configuración temporal
                temp_config = type(self.config)()
                for key, value in connection_data.items():
                    setattr(temp_config, f'__{key}', value)
                
                self.db_connection = DatabaseConnection(temp_config, self.logger)
                self.audit_manager = AuditManager(self.db_connection, self.logger)
                
                # Ejecutar en hilo principal
                self.root.after(0, self._on_connect_success)
                
            except Exception as e:
                error_msg = f"Error de conexión: {str(e)}"
                self.root.after(0, lambda: self._on_connect_error(error_msg))
        
        # Ejecutar conexión en hilo separado
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def _on_connect_success(self):
        """Callback cuando la conexión es exitosa"""
        self.logger.info("Conexión establecida correctamente")
        
        # Cargar tablas
        try:
            tables = self.db_connection.get_tables()
            self.table_selector.load_tables(tables)
            self.connection_form.set_status("Conectado", "green")
            
        except Exception as e:
            self.logger.error(f"Error cargando tablas: {str(e)}")
            messagebox.showerror("Error", f"Error cargando tablas: {str(e)}")
    
    def _on_connect_error(self, error_msg):
        """Callback cuando hay error de conexión"""
        self.logger.error(error_msg)
        self.connection_form.set_status("Error de conexión", "red")
        messagebox.showerror("Error de Conexión", error_msg)
    
    def _on_tables_selected(self, selected_tables):
        """Callback cuando se seleccionan tablas"""
        if selected_tables:
            self.create_btn.config(state="normal")
            self.remove_btn.config(state="normal")
        else:
            self.create_btn.config(state="disabled")
            self.remove_btn.config(state="disabled")
    
    def _create_audit(self):
        """Crear auditoría para tablas seleccionadas"""
        def create_thread():
            try:
                selected_tables = self.table_selector.get_selected_tables()
                if not selected_tables:
                    self.root.after(0, lambda: messagebox.showwarning("Advertencia", "No hay tablas seleccionadas"))
                    return
                
                self.logger.info(f"Creando auditoría para {len(selected_tables)} tablas...")
                
                for table in selected_tables:
                    self.audit_manager.create_audit_for_table(table)
                    self.logger.info(f"Auditoría creada para tabla: {table}")
                
                self.root.after(0, lambda: messagebox.showinfo("Éxito", 
                    f"Auditoría creada para {len(selected_tables)} tablas"))
                
            except Exception as e:
                error_msg = f"Error creando auditoría: {str(e)}"
                self.logger.error(error_msg)
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        
        thread = threading.Thread(target=create_thread)
        thread.daemon = True
        thread.start()
    
    def _remove_audit(self):
        """Eliminar auditoría de tablas seleccionadas"""
        def remove_thread():
            try:
                selected_tables = self.table_selector.get_selected_tables()
                if not selected_tables:
                    self.root.after(0, lambda: messagebox.showwarning("Advertencia", "No hay tablas seleccionadas"))
                    return
                
                # Confirmar eliminación
                if not messagebox.askyesno("Confirmar", 
                    f"¿Eliminar auditoría de {len(selected_tables)} tablas?"):
                    return
                
                self.logger.info(f"Eliminando auditoría para {len(selected_tables)} tablas...")
                
                for table in selected_tables:
                    self.audit_manager.remove_audit_for_table(table)
                    self.logger.info(f"Auditoría eliminada para tabla: {table}")
                
                self.root.after(0, lambda: messagebox.showinfo("Éxito", 
                    f"Auditoría eliminada para {len(selected_tables)} tablas"))
                
            except Exception as e:
                error_msg = f"Error eliminando auditoría: {str(e)}"
                self.logger.error(error_msg)
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        
        thread = threading.Thread(target=remove_thread)
        thread.daemon = True
        thread.start()