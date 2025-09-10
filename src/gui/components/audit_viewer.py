import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
from datetime import datetime
import pandas as pd

class AuditViewer(tk.Toplevel):
    """Ventana para mostrar datos de auditoría desencriptados"""

    def __init__(self, parent, table_name, audit_manager, log_viewer=None):
        super().__init__(parent)
        self.title(f"Auditoría: {table_name}")
        self.geometry("1200x600")
        self.resizable(True, True)

        self.table_name = table_name
        self.audit_manager = audit_manager
        self.log_viewer = log_viewer
        self.logger = logging.getLogger(__name__)
        
        # Variables para manejo de columnas y ordenamiento
        self.encrypted_columns = []
        self.display_columns = []
        self.column_mapping = {}  # mapeo de nombre_display -> nombre_encriptado
        self.current_sort_column = None
        self.current_sort_order = "ASC"

        self._create_widgets()
        self._load_audit_data()

    def _log(self, msg, level="INFO"):
        """Logging interno"""
        print(f"[AuditViewer] {msg}")
        if self.log_viewer:
            self.log_viewer.add_message(msg, level)

    def _create_widgets(self):
        """Crear widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Botón de actualizar
        refresh_btn = ttk.Button(main_frame, text="Actualizar", command=self._load_audit_data)
        refresh_btn.pack(pady=(0, 10))

        # Botón de exportar a Excel
        export_btn = ttk.Button(main_frame, text="Exportar a Excel", command=self._export_to_excel)
        export_btn.pack(pady=(0, 10))

        # Treeview con scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(tree_frame, show="headings")
        
        # Bind del evento de click en headers para ordenamiento
        self.tree.bind('<Button-1>', self._on_header_click)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars y tree
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def _get_encryption_key(self):
        """Obtener clave de encriptación desde la base de datos"""
        try:
            query = "SELECT clave FROM clave_secreta LIMIT 1"
            result = self.audit_manager.db_connection.execute_query(query)
            if result and len(result) > 0:
                return result[0]['clave']
            else:
                raise Exception("No se encontró clave en clave_secreta")
        except Exception as e:
            self._log(f"Error obteniendo clave: {e}", "ERROR")
            raise

    def _get_original_table_columns(self):
        """Obtener columnas de la tabla original"""
        try:
            structure_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """
            columns_result = self.audit_manager.db_connection.execute_query(
                structure_query, (self.table_name.lower(),)
            )
            
            if not columns_result:
                raise Exception(f"No se pudieron obtener las columnas de la tabla original '{self.table_name}'")
            
            original_columns = [col['column_name'] for col in columns_result]
            
            # Agregar columnas de auditoría estándar
            audit_columns = ['usuario', 'fecha', 'accion']
            
            return original_columns + audit_columns
            
        except Exception as e:
            self._log(f"Error obteniendo columnas originales: {e}", "ERROR")
            raise

    def _get_audit_table_info(self):
        """Obtener información de la tabla de auditoría"""
        try:
            key = self._get_encryption_key()
            
            # Obtener nombre encriptado de la tabla
            enc_table_name = self.audit_manager.audit_functions._encrypt_name(self.table_name, key)
            audit_table_name = f"aud_{enc_table_name}".lower()
            
            # Verificar que la tabla existe
            check_query = """
                SELECT COUNT(*) as exists 
                FROM information_schema.tables 
                WHERE table_name = %s AND table_schema = 'public'
            """
            result = self.audit_manager.db_connection.execute_query(check_query, (audit_table_name,))
            
            if not result or result[0]['exists'] == 0:
                raise Exception(f"Tabla de auditoría '{audit_table_name}' no existe")
            
            return audit_table_name, key
            
        except Exception as e:
            self._log(f"Error obteniendo info de tabla de auditoría: {e}", "ERROR")
            raise

    def _create_column_mapping(self, audit_table_name):
        """Crear mapeo entre nombres display y nombres encriptados"""
        try:
            # Obtener columnas encriptadas de la tabla de auditoría
            structure_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """
            columns_result = self.audit_manager.db_connection.execute_query(
                structure_query, (audit_table_name,)
            )
            
            self.encrypted_columns = [col['column_name'] for col in columns_result]
            
            # Obtener nombres originales para mostrar
            self.display_columns = self._get_original_table_columns()
            
            # Crear mapeo (asumiendo mismo orden)
            self.column_mapping = {}
            for i, display_name in enumerate(self.display_columns):
                if i < len(self.encrypted_columns):
                    self.column_mapping[display_name] = self.encrypted_columns[i]
            
            self._log(f"Mapeo de columnas creado: {len(self.column_mapping)} columnas", "INFO")
            
        except Exception as e:
            self._log(f"Error creando mapeo de columnas: {e}", "ERROR")
            raise

    def _on_header_click(self, event):
        """Manejar click en header de columna para ordenamiento"""
        try:
            # Identificar en qué columna se hizo click
            region = self.tree.identify_region(event.x, event.y)
            if region != "heading":
                return
            
            column = self.tree.identify_column(event.x, event.y)
            if not column:
                return
            
            # Obtener nombre de la columna
            column_index = int(column.replace('#', '')) - 1
            if column_index < 0 or column_index >= len(self.display_columns):
                return
            
            display_column = self.display_columns[column_index]
            
            # Determinar orden (alternar ASC/DESC)
            if self.current_sort_column == display_column:
                self.current_sort_order = "DESC" if self.current_sort_order == "ASC" else "ASC"
            else:
                self.current_sort_column = display_column
                self.current_sort_order = "ASC"
            
            # Recargar datos con ordenamiento
            self._load_audit_data()
            
            # Actualizar indicador visual en el header
            self._update_header_indicators()
            
        except Exception as e:
            self._log(f"Error en ordenamiento por columna: {e}", "ERROR")

    def _update_header_indicators(self):
        """Actualizar indicadores visuales de ordenamiento en headers"""
        try:
            for i, display_name in enumerate(self.display_columns):
                if display_name == self.current_sort_column:
                    indicator = " ▲" if self.current_sort_order == "ASC" else " ▼"
                    header_text = display_name + indicator
                else:
                    header_text = display_name
                
                self.tree.heading(f"#{i+1}", text=header_text)
                
        except Exception as e:
            self._log(f"Error actualizando indicadores de header: {e}", "WARNING")

    def _build_order_clause(self):
        """Construir cláusula ORDER BY usando nombres encriptados"""
        if not self.current_sort_column:
            # Ordenamiento por defecto (primera columna descendente)
            if self.encrypted_columns:
                return f"ORDER BY pgp_sym_decrypt({self.encrypted_columns[0]}, (SELECT clave FROM clave_secreta LIMIT 1)) DESC"
            return ""
        
        # Obtener nombre encriptado correspondiente
        encrypted_name = self.column_mapping.get(self.current_sort_column)
        if not encrypted_name:
            return ""
        
        return f"ORDER BY pgp_sym_decrypt({encrypted_name}, (SELECT clave FROM clave_secreta LIMIT 1)) {self.current_sort_order}"

    def _load_audit_data(self):
        """Cargar y mostrar datos de auditoría desencriptados"""
        try:
            # Limpiar tree existente
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            audit_table_name, key = self._get_audit_table_info()
            
            # Crear mapeo de columnas
            self._create_column_mapping(audit_table_name)
            
            if not self.encrypted_columns:
                raise Exception("No se pudieron obtener las columnas de la tabla de auditoría")
            
            # Configurar columnas del Treeview con nombres originales
            self.tree["columns"] = [f"#{i+1}" for i in range(len(self.display_columns))]
            for i, display_name in enumerate(self.display_columns):
                self.tree.heading(f"#{i+1}", text=display_name)
                self.tree.column(f"#{i+1}", width=120, anchor="w", minwidth=80)
            
            # Consulta para obtener datos desencriptados usando pgp_sym_decrypt
            select_parts = []
            for enc_col in self.encrypted_columns:
                select_parts.append(f"pgp_sym_decrypt({enc_col}, (SELECT clave FROM clave_secreta LIMIT 1)) as {enc_col}")
            
            # Construir consulta con ordenamiento
            order_clause = self._build_order_clause()
            if not order_clause:
                order_clause = f"ORDER BY pgp_sym_decrypt({self.encrypted_columns[0]}, (SELECT clave FROM clave_secreta LIMIT 1)) DESC"
            
            data_query = f"""
                SELECT {', '.join(select_parts)}
                FROM {audit_table_name} 
                {order_clause}
                LIMIT 100
            """
            
            self._log("Ejecutando consulta de auditoría...")
            
            # Ejecutar consulta
            audit_data = self.audit_manager.db_connection.execute_query(data_query)
            
            if not audit_data:
                self._log("No hay datos de auditoría para mostrar", "INFO")
                messagebox.showinfo("Información", "No hay registros de auditoría para esta tabla")
                return
            
            # Insertar datos en el Treeview
            for row in audit_data:
                values = []
                for enc_col in self.encrypted_columns:
                    try:
                        # El valor ya viene desencriptado por pgp_sym_decrypt
                        val = row.get(enc_col, "")
                        if val is None:
                            val = "<NULL>"
                        elif isinstance(val, (bytes, memoryview)):
                            # Si aún viene como bytes, intentar decodificar
                            try:
                                val = val.decode('utf-8')
                            except:
                                val = "<binary_data>"
                        else:
                            val = str(val)
                        
                        values.append(val)
                    except Exception as e:
                        self._log(f"Error procesando valor para columna {enc_col}: {e}", "WARNING")
                        values.append("<error>")
                
                self.tree.insert("", "end", values=values)
            
            # Actualizar indicadores de ordenamiento
            self._update_header_indicators()
            
            sort_info = f" (ordenado por {self.current_sort_column} {self.current_sort_order})" if self.current_sort_column else ""
            self._log(f"Cargados {len(audit_data)} registros de auditoría{sort_info}", "INFO")
            
        except Exception as e:
            error_msg = f"Error cargando datos de auditoría: {str(e)}"
            self._log(error_msg, "ERROR")
            messagebox.showerror("Error", error_msg)

    def _export_to_excel(self):
        """Exportar datos de auditoría a Excel"""
        try:
            # Verificar que hay datos para exportar
            if not self.tree.get_children():
                messagebox.showwarning("Advertencia", "No hay datos para exportar")
                return
            
            # Obtener datos actuales del Treeview
            data = []
            for child in self.tree.get_children():
                values = self.tree.item(child)['values']
                data.append(values)
            
            if not data:
                messagebox.showwarning("Advertencia", "No hay datos para exportar")
                return
            
            # Crear DataFrame con pandas
            df = pd.DataFrame(data, columns=self.display_columns)
            
            # Generar nombre de archivo por defecto
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"auditoria_{self.table_name}_{timestamp}.xlsx"
            
            # Pedir ubicación del archivo
            file_path = filedialog.asksaveasfilename(
                title="Guardar auditoría como Excel",
                defaultextension=".xlsx",
                filetypes=[
                    ("Excel files", "*.xlsx"),
                    ("Excel files (legacy)", "*.xls"),
                    ("All files", "*.*")
                ],
                initialfile=default_filename
            )
            
            if not file_path:
                return  # Usuario canceló
            
            # Exportar a Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Hoja principal con datos
                df.to_excel(writer, sheet_name='Auditoría', index=False)
                
                # Hoja de metadatos
                metadata = {
                    'Tabla': [self.table_name],
                    'Fecha de Exportación': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    'Total de Registros': [len(data)],
                    'Columnas Exportadas': [len(self.display_columns)],
                    'Ordenamiento Actual': [f"{self.current_sort_column} {self.current_sort_order}" if self.current_sort_column else "Sin ordenamiento específico"]
                }
                
                # Si es EnhancedAuditViewer, agregar info de filtros
                if hasattr(self, 'filters') and any(self.filters.values()):
                    filter_info = []
                    for key, value in self.filters.items():
                        if value:
                            filter_info.append(f"{key}: {value}")
                    metadata['Filtros Aplicados'] = ["; ".join(filter_info) if filter_info else "Ninguno"]
                else:
                    metadata['Filtros Aplicados'] = ["Ninguno"]
                
                metadata_df = pd.DataFrame(metadata)
                metadata_df.to_excel(writer, sheet_name='Información', index=False)
                
                # Ajustar ancho de columnas en la hoja principal
                worksheet = writer.sheets['Auditoría']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    # Establecer ancho mínimo y máximo
                    adjusted_width = min(max(max_length + 2, 10), 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            self._log(f"Datos exportados exitosamente a: {file_path}", "INFO")
            messagebox.showinfo(
                "Exportación Exitosa", 
                f"Los datos de auditoría se han exportado correctamente.\n\n"
                f"Archivo: {os.path.basename(file_path)}\n"
                f"Registros exportados: {len(data)}\n"
                f"Ubicación: {file_path}"
            )
            
        except ImportError:
            error_msg = "Error: Se requiere pandas y openpyxl para exportar a Excel.\n\nInstale con: pip install pandas openpyxl"
            self._log(error_msg, "ERROR")
            messagebox.showerror("Error de Dependencias", error_msg)
            
        except PermissionError:
            error_msg = "Error: No se puede escribir el archivo. Verifique que no esté abierto en Excel y que tenga permisos de escritura."
            self._log(error_msg, "ERROR")
            messagebox.showerror("Error de Permisos", error_msg)
            
        except Exception as e:
            error_msg = f"Error exportando a Excel: {str(e)}"
            self._log(error_msg, "ERROR")
            messagebox.showerror("Error", error_msg)

    def _view_audit(self):
        """Método para compatibilidad - mostrar ventana de auditoría"""
        selected_tables = self.table_selector.get_selected_tables()
        if not selected_tables:
            messagebox.showwarning("Advertencia", "No hay tablas seleccionadas")
            return
        table = selected_tables[0]
        AuditViewer(self.root, table, self.audit_manager, log_viewer=self.log_viewer)


class EnhancedAuditViewer(AuditViewer):
    """Versión mejorada del visualizador de auditoría con filtros"""
    
    def __init__(self, parent, table_name, audit_manager, log_viewer=None):
        self.filters = {}
        super().__init__(parent, table_name, audit_manager, log_viewer)
    
    def _create_widgets(self):
        """Crear widgets con filtros adicionales"""
        # Frame principal
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 10))
        
        # Botón de actualizar
        refresh_btn = ttk.Button(button_frame, text="Actualizar", command=self._load_audit_data)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Botón de exportar a Excel
        export_btn = ttk.Button(button_frame, text="Exportar a Excel", command=self._export_to_excel)
        export_btn.pack(side=tk.LEFT)

        # Treeview con scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(tree_frame, show="headings")
        
        # Bind del evento de click en headers para ordenamiento
        self.tree.bind('<Button-1>', self._on_header_click)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars y tree
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Frame para filtros
        filter_frame = ttk.LabelFrame(self, text="Filtros", padding="5")
        filter_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Filtro por usuario
        ttk.Label(filter_frame, text="Usuario:").grid(row=0, column=0, sticky="w", padx=5)
        self.user_filter = ttk.Entry(filter_frame, width=20)
        self.user_filter.grid(row=0, column=1, padx=5)
        
        # Filtro por acción
        ttk.Label(filter_frame, text="Acción:").grid(row=0, column=2, sticky="w", padx=5)
        self.action_filter = ttk.Combobox(filter_frame, values=["", "INSERT", "UPDATE", "DELETE"], width=15)
        self.action_filter.grid(row=0, column=3, padx=5)
        
        # Botón aplicar filtros
        apply_btn = ttk.Button(filter_frame, text="Aplicar Filtros", command=self._apply_filters)
        apply_btn.grid(row=0, column=4, padx=10)
        
        # Botón limpiar filtros
        clear_btn = ttk.Button(filter_frame, text="Limpiar", command=self._clear_filters)
        clear_btn.grid(row=0, column=5, padx=5)
    
    def _apply_filters(self):
        """Aplicar filtros a los datos"""
        self.filters = {
            'usuario': self.user_filter.get().strip(),
            'accion': self.action_filter.get().strip()
        }
        self._load_audit_data()
    
    def _clear_filters(self):
        """Limpiar todos los filtros"""
        self.user_filter.delete(0, tk.END)
        self.action_filter.set("")
        self.filters = {}
        self._load_audit_data()
    
    def _build_filtered_query(self, base_query, encrypted_columns):
        """Construir consulta con filtros aplicados"""
        if not self.filters:
            return base_query
        
        where_conditions = []
        
        if self.filters.get('usuario'):
            # Buscar la columna de usuario por nombre display
            if 'usuario' in self.column_mapping:
                enc_col = self.column_mapping['usuario']
                where_conditions.append(
                    f"pgp_sym_decrypt({enc_col}, (SELECT clave FROM clave_secreta LIMIT 1)) ILIKE '%{self.filters['usuario']}%'"
                )
        
        if self.filters.get('accion'):
            # Buscar la columna de acción por nombre display
            if 'accion' in self.column_mapping:
                enc_col = self.column_mapping['accion']
                where_conditions.append(
                    f"pgp_sym_decrypt({enc_col}, (SELECT clave FROM clave_secreta LIMIT 1)) = '{self.filters['accion']}'"
                )
        
        if where_conditions:
            # Insertar WHERE antes del ORDER BY
            if "ORDER BY" in base_query:
                parts = base_query.split("ORDER BY")
                return f"{parts[0].replace('LIMIT 100', '')} WHERE {' AND '.join(where_conditions)} ORDER BY {parts[1]}"
            else:
                return base_query.replace("LIMIT 100", f"WHERE {' AND '.join(where_conditions)} LIMIT 100")
        
        return base_query

    def _load_audit_data(self):
        """Cargar y mostrar datos de auditoría desencriptados con filtros"""
        try:
            # Limpiar tree existente
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            audit_table_name, key = self._get_audit_table_info()
            
            # Crear mapeo de columnas
            self._create_column_mapping(audit_table_name)
            
            if not self.encrypted_columns:
                raise Exception("No se pudieron obtener las columnas de la tabla de auditoría")
            
            # Configurar columnas del Treeview con nombres originales
            self.tree["columns"] = [f"#{i+1}" for i in range(len(self.display_columns))]
            for i, display_name in enumerate(self.display_columns):
                self.tree.heading(f"#{i+1}", text=display_name)
                self.tree.column(f"#{i+1}", width=120, anchor="w", minwidth=80)
            
            # Consulta para obtener datos desencriptados usando pgp_sym_decrypt
            select_parts = []
            for enc_col in self.encrypted_columns:
                select_parts.append(f"pgp_sym_decrypt({enc_col}, (SELECT clave FROM clave_secreta LIMIT 1)) as {enc_col}")
            
            # Construir consulta con ordenamiento
            order_clause = self._build_order_clause()
            if not order_clause:
                order_clause = f"ORDER BY pgp_sym_decrypt({self.encrypted_columns[0]}, (SELECT clave FROM clave_secreta LIMIT 1)) DESC"
            
            data_query = f"""
                SELECT {', '.join(select_parts)}
                FROM {audit_table_name} 
                {order_clause}
                LIMIT 100
            """
            
            # Aplicar filtros si existen
            data_query = self._build_filtered_query(data_query, self.encrypted_columns)
            
            self._log("Ejecutando consulta de auditoría con filtros...")
            
            # Ejecutar consulta
            audit_data = self.audit_manager.db_connection.execute_query(data_query)
            
            if not audit_data:
                self._log("No hay datos de auditoría para mostrar", "INFO")
                messagebox.showinfo("Información", "No hay registros de auditoría para esta tabla")
                return
            
            # Insertar datos en el Treeview
            for row in audit_data:
                values = []
                for enc_col in self.encrypted_columns:
                    try:
                        # El valor ya viene desencriptado por pgp_sym_decrypt
                        val = row.get(enc_col, "")
                        if val is None:
                            val = "<NULL>"
                        elif isinstance(val, (bytes, memoryview)):
                            # Si aún viene como bytes, intentar decodificar
                            try:
                                val = val.decode('utf-8')
                            except:
                                val = "<binary_data>"
                        else:
                            val = str(val)
                        
                        values.append(val)
                    except Exception as e:
                        self._log(f"Error procesando valor para columna {enc_col}: {e}", "WARNING")
                        values.append("<error>")
                
                self.tree.insert("", "end", values=values)
            
            # Actualizar indicadores de ordenamiento
            self._update_header_indicators()
            
            sort_info = f" (ordenado por {self.current_sort_column} {self.current_sort_order})" if self.current_sort_column else ""
            filter_info = f" con filtros aplicados" if any(self.filters.values()) else ""
            self._log(f"Cargados {len(audit_data)} registros de auditoría{sort_info}{filter_info}", "INFO")
            
        except Exception as e:
            error_msg = f"Error cargando datos de auditoría: {str(e)}"
            self._log(error_msg, "ERROR")
            messagebox.showerror("Error", error_msg)