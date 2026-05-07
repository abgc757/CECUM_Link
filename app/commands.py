import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import User, UserRole


@click.command("create-admin")
@click.option("--username", prompt=True, help="Nombre de usuario administrador")
@click.option("--email", prompt=True, help="Correo administrador")
@click.option("--password", default="", show_default=False, help="Contrasena inicial (opcional)")
@with_appcontext
def create_admin_command(username: str, email: str, password: str):
    existing = User.query.filter((User.username == username) | (User.email == email.lower())).first()
    if existing:
        if existing.role != UserRole.ADMIN.value:
            existing.role = UserRole.ADMIN.value
            if password:
                existing.set_password(password)
            db.session.commit()
            click.echo(f"Usuario existente promovido a administrador: @{existing.username}")
            return
        if password and existing.needs_password_setup:
            existing.set_password(password)
            db.session.commit()
            click.echo(f"Contrasena inicial configurada para administrador: @{existing.username}")
            return
        click.echo(f"Administrador ya existe: @{existing.username}")
        return

    user = User(username=username.strip(), email=email.strip().lower(), role=UserRole.ADMIN.value)
    if password:
        user.set_password(password)
    else:
        user.password_hash = ""
    db.session.add(user)
    db.session.commit()
    if password:
        click.echo(f"Administrador creado: @{user.username}")
    else:
        click.echo(f"Administrador creado sin contrasena inicial: @{user.username}. Debe definirla en primer login.")
