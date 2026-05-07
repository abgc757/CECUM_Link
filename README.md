# CECUM Link

CECUM Link es una red social escolar construida con Flask, modularizada con Blueprints.

## Modulos incluidos

- `auth`: registro, inicio y cierre de sesion.
- `posts`: feed cronologico, reacciones y comentarios con etiquetas.
- `events`: calendario y gestion de eventos escolares.
- `chat`: mensajeria privada/grupal base con SocketIO.
- `notifications`: panel centralizado de alertas.
- `admin`: moderacion de usuarios y publicaciones.
- `admin/review`: revision de posts/comentarios archivados por moderadores.
- `admin/db-console`: consola SQL de solo lectura para consultas operativas.
- `api`: REST API inicial para posts y eventos.

## Stack tecnico

- Flask + Jinja2 + Bootstrap
- SQLAlchemy (SQLite por defecto, PostgreSQL via `DATABASE_URL`)
- Flask-Login, Flask-WTF (CSRF), hashing de contrasenas con Werkzeug
- Flask-SocketIO para tiempo real (chat/notificaciones)
- Subida multimedia local (imagen/video) con un unico campo en publicaciones

## Ejecutar proyecto

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app run.py db init
flask --app run.py db migrate -m "init schema" 
flask --app run.py db upgrade
python run.py
```

Abre: `http://127.0.0.1:5000`

## Administrador del sistema

- El usuario administrador principal usa rol `admin`.
- Solo `admin` puede promover usuarios a moderadores desde el panel de admin.
- En el primer inicio de sesion del admin (si no tiene contrasena), se abre flujo para definirla.
- Puedes crear/promover el admin con:

```bash
flask --app run.py create-admin --username admin --email admin@cecum.link --password ChangeMe123!
```

- Tambien puedes definir en `.env`:
  - `ADMIN_USERNAME`
  - `ADMIN_EMAIL`
  - `ADMIN_PASSWORD` (opcional)

## Consola y API para BI

- Consola web (solo moderadores): `http://127.0.0.1:5000/admin/db-console`
- Endpoint para herramientas BI: `POST /api/v1/bi/query`
- Autenticacion BI por header: `X-BI-API-KEY: <BI_API_KEY>`

Ejemplo de payload:

```json
{
  "query": "SELECT id, username, role, created_at FROM user ORDER BY id DESC",
  "limit": 1000
}
```

La consola y el endpoint aceptan solo consultas de lectura (`SELECT`, `WITH`, `PRAGMA`).

## Primer despliegue limpio (recomendado)

Si quieres arrancar el proyecto desde cero sin residuos:

```bash
rmdir /s /q venv
rmdir /s /q .venv
del /q *.db
del /q *.sqlite3
rmdir /s /q migrations
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app run.py db init
flask --app run.py db migrate -m "init schema"
flask --app run.py db upgrade
python run.py
```

Tambien puedes usar el script automatizado:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\first_deploy_clean.ps1
```

O con doble clic / CMD:

```bat
.\scripts\first_deploy_clean.bat
```

Opciones utiles:

```powershell
# Fuerza recreacion de entorno virtual
powershell -ExecutionPolicy Bypass -File .\scripts\first_deploy_clean.ps1 -RecreateVenv

# Reutiliza paquetes ya instalados
powershell -ExecutionPolicy Bypass -File .\scripts\first_deploy_clean.ps1 -SkipPipInstall
```
