# Postgres Audit App

## Descripción
**Postgres Audit App** es una herramienta desarrollada en Python (versión 1.0.0) que permite **auditar bases de datos PostgreSQL** de manera automatizada.  
Su funcionamiento se basa en tres características principales:

1. Conexión a una base de datos PostgreSQL existente.
2. Generación de **tablas espejo** que incluyen columnas adicionales de auditoría (`usuario`, `fecha`, `acción`).
3. Aplicación de **encriptación** sobre las tablas espejo, con la posibilidad de **visualizar los datos desencriptados** directamente desde la aplicación.

El objetivo principal de esta herramienta es facilitar la implementación de auditorías en proyectos que manejan datos sensibles, asegurando trazabilidad y seguridad de la información.

---

## Requisitos
Antes de usar la aplicación, asegúrate de contar con lo siguiente:

- Python 3.8 o superior
- PostgreSQL instalado y una base de datos existente
- Paquetes de Python incluidos en `requirements.txt`, por ejemplo:
  - `psycopg2`
  - `cryptography`
  - Otros especificados en el repositorio

---

## Instalación
Sigue los siguientes pasos para instalar y preparar el entorno:

```bash
# Clonar el repositorio
git clone https://github.com/daniel-flores-sys/Postgres_Audit_App.git
cd Postgres_Audit_App

# (Opcional) Crear un entorno virtual
python -m venv venv
# Activar entorno (Windows)
venv\Scripts\activate
# Activar entorno (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Uso
Para iniciar la aplicación:

```bash
python main.py
```

El programa te guiará mediante un **menú interactivo** donde podrás:

1. Conectarte a la base de datos PostgreSQL (ingresando host, puerto, usuario, contraseña y nombre de la base de datos).
2. Generar las tablas espejo con las columnas de auditoría.
3. Visualizar los datos desencriptados desde la propia herramienta.

---

## Funcionamiento Interno
- Las **tablas espejo** se crean automáticamente en la base de datos seleccionada.
- Cada tabla espejo añade las columnas:
  - `usuario`: identifica al usuario que realizó la acción.
  - `fecha`: registra el momento de la acción.
  - `acción`: describe la operación realizada (ej. INSERT, UPDATE, DELETE).
- Los datos en las tablas espejo se guardan **encriptados** para mayor seguridad.
- Desde la aplicación se pueden **desencriptar y visualizar** los datos de forma clara.

---

## Seguridad
- Las credenciales de la base de datos se solicitan en tiempo de ejecución y **no se almacenan** en archivos locales.
- Se recomienda configurar un archivo `.env` para proyectos de producción con variables de entorno seguras.

---

## Limitaciones
- Actualmente, la aplicación solo soporta **PostgreSQL**.
- La auditoría se limita a la creación de **tablas espejo** con encriptación básica y su lectura desencriptada.

---

## Futuro
Se planea agregar nuevas características:
- Compatibilidad con otros motores de bases de datos.
- Interfaz gráfica más amigable para usuarios no técnicos.
- Reportes exportables en PDF o CSV.
- Configuración avanzada de algoritmos de encriptación.

---

## Licencia
Este proyecto es de **código abierto** y se distribuye bajo la licencia MIT.  
¡Eres libre de usarlo, modificarlo y mejorarlo!

---

## Autor
Desarrollado por **Daniel Flores**  
Versión: **1.0.0**
