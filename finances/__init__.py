import os
import secrets
from datetime import timedelta

from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect

from . import defaults
from .models import Category, Setting, User, db

MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "main.login"
login_manager.login_message = "Entre para continuar."


def database_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///finances.db")
    # Render entrega postgres:// ou postgresql://; o SQLAlchemy precisa do driver psycopg 3
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def brl(value):
    v = float(value or 0)
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-R$ " if v < 0 else "R$ ") + s


def pct(value):
    return "-" if value is None else f"{float(value) * 100:.0f}%"


def mes(d):
    return f"{MONTHS_PT[d.month - 1]}/{d.year % 100:02d}"


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=database_url(),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=bool(os.environ.get("RENDER")),
        REMEMBER_COOKIE_DURATION=timedelta(days=30),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    app.jinja_env.filters.update(brl=brl, pct=pct, mes=mes)

    from .routes import bp
    app.register_blueprint(bp)

    from .cli import register_cli
    register_cli(app)

    with app.app_context():
        db.create_all()
        bootstrap()
    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def bootstrap():
    """Cria categorias, configurações e usuários que ainda não existem."""
    if not Category.query.first():
        for i, (name, desc, group, c, r, m) in enumerate(defaults.CATEGORIES):
            db.session.add(Category(name=name, description=desc, group=group, limit_casal=c,
                                    limit_rodrigo=r, limit_mayane=m, sort=i))
    existing = {s.key for s in Setting.query.all()}
    for i, (key, (value, label)) in enumerate(defaults.SETTINGS.items()):
        if key not in existing:
            db.session.add(Setting(key=key, value=str(value), label=label, sort=i))
    # usuários vêm das variáveis de ambiente RODRIGO_PASSWORD e MAYANE_PASSWORD
    for person in ("Rodrigo", "Mayane"):
        password = os.environ.get(f"{person.upper()}_PASSWORD")
        if not password:
            continue
        user = User.query.filter_by(username=person.lower()).first()
        if user is None:
            user = User(username=person.lower(), person=person)
            user.set_password(password)
            db.session.add(user)
        elif os.environ.get("RESET_PASSWORDS") == "1":
            user.set_password(password)
    db.session.commit()
