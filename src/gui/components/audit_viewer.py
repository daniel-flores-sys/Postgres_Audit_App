import tkinter as tk
from tkinter import ttk, messagebox
import logging

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

        # Treeview con scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(tree_frame, show="headings")
        
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

    def _decrypt_column_name(self, encrypted_name, key):
        """Desencriptar nombre de columna usando el mismo método que AuditFunctions"""
        try:
            # Usar el método de AuditFunctions para desencriptar
            return self.audit_manager.audit_functions._decrypt_name(encrypted_name, key)
        except Exception as e:
            self._log(f"Error desencriptando nombre '{encrypted_name}': {e}", "WARNING")
            return encrypted_name

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

    def _load_audit_data(self):
        """Cargar y mostrar datos de auditoría desencriptados"""
        try:
            # Limpiar tree existente
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            audit_table_name, key = self._get_audit_table_info()
            
            # Obtener estructura de la tabla de auditoría (columnas encriptadas)
            structure_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """
            columns_result = self.audit_manager.db_connection.execute_query(
                structure_query, (audit_table_name,)
            )
            
            if not columns_result:
                raise Exception("No se pudieron obtener las columnas de la tabla de auditoría")
            
            encrypted_columns = [col['column_name'] for col in columns_result]
            
            # Desencriptar nombres de columnas para mostrar
            display_columns = []
            for enc_col in encrypted_columns:
                try:
                    dec_col = self._decrypt_column_name(enc_col, key)
                    display_columns.append(dec_col)
                except:
                    display_columns.append(enc_col)  # Si falla, usar el nombre encriptado
            
            # Configurar columnas del Treeview
            self.tree["columns"] = display_columns
            for i, col in enumerate(display_columns):
                self.tree.heading(col, text=col)
                self.tree.column(col, width=120, anchor="w", minwidth=80)
            
            # Consulta para obtener datos desencriptados usando pgp_sym_decrypt
            select_parts = []
            for enc_col in encrypted_columns:
                select_parts.append(f"pgp_sym_decrypt({enc_col}, (SELECT clave FROM clave_secreta LIMIT 1)) as {enc_col}")
            
            data_query = f"""
                SELECT {', '.join(select_parts)}
                FROM {audit_table_name} 
                ORDER BY pgp_sym_decrypt({encrypted_columns[0]}, (SELECT clave FROM clave_secreta LIMIT 1)) DESC
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
                for enc_col in encrypted_columns:
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
            
            self._log(f"Cargados {len(audit_data)} registros de auditoría", "INFO")
            
        except Exception as e:
            error_msg = f"Error cargando datos de auditoría: {str(e)}"
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
        super()._create_widgets()
        
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
            # Buscar la columna de usuario encriptada
            for enc_col in encrypted_columns:
                try:
                    key = self._get_encryption_key()
                    dec_name = self._decrypt_column_name(enc_col, key)
                    if 'usuario' in dec_name.lower():
                        where_conditions.append(
                            f"pgp_sym_decrypt({enc_col}, (SELECT clave FROM clave_secreta LIMIT 1)) ILIKE '%{self.filters['usuario']}%'"
                        )
                        break
                except:
                    continue
        
        if self.filters.get('accion'):
            # Buscar la columna de acción encriptada
            for enc_col in encrypted_columns:
                try:
                    key = self._get_encryption_key()
                    dec_name = self._decrypt_column_name(enc_col, key)
                    if 'accion' in dec_name.lower():
                        where_conditions.append(
                            f"pgp_sym_decrypt({enc_col}, (SELECT clave FROM clave_secreta LIMIT 1)) = '{self.filters['accion']}'"
                        )
                        break
                except:
                    continue
        
        if where_conditions:
            return base_query.replace("LIMIT 100", f"WHERE {' AND '.join(where_conditions)} LIMIT 100")
        
        return base_query