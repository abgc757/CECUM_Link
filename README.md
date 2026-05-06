# CECUM Link

CECUM Link es una red social escolar construida con Flask, modularizada con Blueprints.

## Modulos incluidos

- `auth`: registro, inicio y cierre de sesion.
- `posts`: feed cronologico, reacciones y comentarios con etiquetas.
- `events`: calendario y gestion de eventos escolares.
- `chat`: mensajeria privada/grupal base con SocketIO.
- `notifications`: panel centralizado de alertas.
- `admin`: moderacion de usuarios y publicaciones.
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
