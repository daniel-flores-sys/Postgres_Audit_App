"""
Componente para visualizar logs y mensajes
"""

import tkinter as tk
from tkinter import ttk, scrolledtext

class LogViewer:
    """Visualizador de logs en tiempo real"""
    
    def __init__(self, parent):
        """Inicializar visualizador de logs"""
        self.parent = parent
        self._create_widgets()
    
    def _create_widgets(self):
        """Crear widgets del visualizador"""
        # Frame principal
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Frame superior - Controles
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Botones de control
        ttk.Button(control_frame, text="Limpiar Logs", 
                  command=self._clear_logs).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Guardar Logs", 
                  command=self._save_logs).pack(side="left", padx=5)
        
        # Filtros de nivel
        ttk.Label(control_frame, text="Filtro:").pack(side="left", padx=(20, 5))
        
        self.filter_var = tk.StringVar(value="Todos")
        filter_combo = ttk.Combobox(control_frame, textvariable=self.filter_var,
                                   values=["Todos", "INFO", "WARNING", "ERROR", "DEBUG"],
                                   state="readonly", width=10)
        filter_combo.pack(side="left", padx=5)
        filter_combo.bind('<<ComboboxSelected>>', self._apply_filter)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Auto-scroll", 
                       variable=self.auto_scroll_var).pack(side="right", padx=5)
        
        # Área de texto para logs
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.text_widget = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=('Consolas', 10),
            bg='black',
            fg='white'
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        
        # Configurar colores para diferentes niveles
        self._configure_tags()
        
        # Almacenar mensajes originales para filtrado
        self.all_messages = []
    
    def _configure_tags(self):
        """Configurar tags para colorear diferentes niveles de log"""
        self.text_widget.tag_configure("INFO", foreground="lightgreen")
        self.text_widget.tag_configure("WARNING", foreground="yellow")
        self.text_widget.tag_configure("ERROR", foreground="red")
        self.text_widget.tag_configure("DEBUG", foreground="lightblue")
        self.text_widget.tag_configure("TIMESTAMP", foreground="gray")
    
    def add_message(self, message, level="INFO"):
        """Agregar mensaje al visualizador"""
        # Almacenar mensaje original
        self.all_messages.append((message, level))
        
        # Aplicar filtro actual
        current_filter = self.filter_var.get()
        if current_filter != "Todos" and level != current_filter:
            return
        
        # Agregar al widget de texto
        self.text_widget.config(state=tk.NORMAL)
        
        # Obtener timestamp del mensaje si existe
        if " - " in message:
            parts = message.split(" - ", 2)
            if len(parts) >= 3:
                timestamp = parts[0]
                level_part = parts[1]
                content = " - ".join(parts[2:])
                
                # Insertar con colores
                self.text_widget.insert(tk.END, timestamp, "TIMESTAMP")
                self.text_widget.insert(tk.END, " - ")
                self.text_widget.insert(tk.END, level_part, level)
                self.text_widget.insert(tk.END, " - " + content + "\n")
            else:
                self.text_widget.insert(tk.END, message + "\n", level)
        else:
            self.text_widget.insert(tk.END, message + "\n", level)
        
        self.text_widget.config(state=tk.DISABLED)
        
        # Auto-scroll si está habilitado
        if self.auto_scroll_var.get():
            self.text_widget.see(tk.END)
    
    def _clear_logs(self):
        """Limpiar todos los logs"""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.config(state=tk.DISABLED)
        self.all_messages.clear()
    
    def _save_logs(self):
        """Guardar logs a archivo"""
        from tkinter import filedialog
        from datetime import datetime
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
                initialname=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    content = self.text_widget.get(1.0, tk.END)
                    f.write(content)
                
                self.add_message(f"Logs guardados en: {filename}", "INFO")
                
        except Exception as e:
            self.add_message(f"Error guardando logs: {str(e)}", "ERROR")
    
    def _apply_filter(self, event=None):
        """Aplicar filtro de nivel de log"""
        current_filter = self.filter_var.get()
        
        # Limpiar contenido actual
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        
        # Mostrar mensajes filtrados
        for message, level in self.all_messages:
            if current_filter == "Todos" or level == current_filter:
                # Replicar lógica de add_message pero sin almacenar
                if " - " in message:
                    parts = message.split(" - ", 2)
                    if len(parts) >= 3:
                        timestamp = parts[0]
                        level_part = parts[1]
                        content = " - ".join(parts[2:])
                        
                        self.text_widget.insert(tk.END, timestamp, "TIMESTAMP")
                        self.text_widget.insert(tk.END, " - ")
                        self.text_widget.insert(tk.END, level_part, level)
                        self.text_widget.insert(tk.END, " - " + content + "\n")
                    else:
                        self.text_widget.insert(tk.END, message + "\n", level)
                else:
                    self.text_widget.insert(tk.END, message + "\n", level)
        
        self.text_widget.config(state=tk.DISABLED)
        
        # Auto-scroll al final
        if self.auto_scroll_var.get():
            self.text_widget.see(tk.END)