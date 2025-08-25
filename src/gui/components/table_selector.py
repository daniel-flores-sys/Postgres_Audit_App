"""
Componente para seleccionar tablas
"""

import tkinter as tk
from tkinter import ttk

class TableSelector:
    """Selector de tablas con opciones múltiples"""
    
    def __init__(self, parent, on_selection_callback):
        """Inicializar selector de tablas"""
        self.parent = parent
        self.on_selection = on_selection_callback
        self.tables = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Crear widgets del selector"""
        # Frame principal
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill="both", expand=True)
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Frame superior - Controles
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Botones de selección
        ttk.Button(control_frame, text="Seleccionar Todas", 
                  command=self._select_all).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Deseleccionar Todas", 
                  command=self._deselect_all).pack(side="left", padx=5)
        
        # Filtro de búsqueda
        ttk.Label(control_frame, text="Filtrar:").pack(side="left", padx=(20, 5))
        self.filter_var = tk.StringVar()
        self.filter_var.trace('w', self._filter_tables)
        ttk.Entry(control_frame, textvariable=self.filter_var, width=20).pack(side="left", padx=5)
        
        # Frame de tablas - Lista con checkboxes
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        # Scrollable frame para las tablas
        self.canvas = tk.Canvas(table_frame)
        self.scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Frame de información
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        self.info_label = ttk.Label(info_frame, text="No hay tablas cargadas")
        self.info_label.pack(side="left")
        
        self.selected_label = ttk.Label(info_frame, text="Seleccionadas: 0")
        self.selected_label.pack(side="right")
        
        # Variables para checkboxes
        self.table_vars = {}
        self.table_checkboxes = {}
    
    def load_tables(self, tables):
        """Cargar lista de tablas"""
        self.tables = tables
        self._clear_table_list()
        self._populate_table_list()
        self._update_info()
    
    def _clear_table_list(self):
        """Limpiar lista de tablas"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.table_vars.clear()
        self.table_checkboxes.clear()
    
    def _populate_table_list(self):
        """Poblar lista de tablas con checkboxes"""
        for i, table in enumerate(self.tables):
            var = tk.BooleanVar()
            var.trace('w', self._on_table_selection_changed)
            
            checkbox = ttk.Checkbutton(
                self.scrollable_frame,
                text=table,
                variable=var
            )
            checkbox.grid(row=i, column=0, sticky="w", padx=10, pady=2)
            
            self.table_vars[table] = var
            self.table_checkboxes[table] = checkbox
    
    def _filter_tables(self, *args):
        """Filtrar tablas según texto de búsqueda"""
        filter_text = self.filter_var.get().lower()
        
        for table, checkbox in self.table_checkboxes.items():
            if filter_text in table.lower():
                checkbox.grid()
            else:
                checkbox.grid_remove()
    
    def _select_all(self):
        """Seleccionar todas las tablas visibles"""
        filter_text = self.filter_var.get().lower()
        
        for table, var in self.table_vars.items():
            if filter_text in table.lower():
                var.set(True)
    
    def _deselect_all(self):
        """Deseleccionar todas las tablas"""
        for var in self.table_vars.values():
            var.set(False)
    
    def _on_table_selection_changed(self, *args):
        """Callback cuando cambia la selección de tablas"""
        selected_tables = self.get_selected_tables()
        self._update_selected_count()
        
        # Notificar al callback externo
        if self.on_selection:
            self.on_selection(selected_tables)
    
    def _update_info(self):
        """Actualizar información de tablas"""
        total_tables = len(self.tables)
        self.info_label.config(text=f"Total de tablas: {total_tables}")
        self._update_selected_count()
    
    def _update_selected_count(self):
        """Actualizar contador de tablas seleccionadas"""
        selected_count = len(self.get_selected_tables())
        self.selected_label.config(text=f"Seleccionadas: {selected_count}")
    
    def get_selected_tables(self):
        """Obtener lista de tablas seleccionadas"""
        selected = []
        for table, var in self.table_vars.items():
            if var.get():
                selected.append(table)
        return selected
    
    def set_selected_tables(self, tables):
        """Establecer tablas seleccionadas"""
        # Deseleccionar todas primero
        self._deselect_all()
        
        # Seleccionar las especificadas
        for table in tables:
            if table in self.table_vars:
                self.table_vars[table].set(True)