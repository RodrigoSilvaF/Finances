from datetime import date, datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

PEOPLE = ("Rodrigo", "Mayane")
OWNERS = ("Casal", "Rodrigo", "Mayane")
GROUPS = ("Necessidade", "Desejo")
METHODS = ("Cartão XP", "Cartão Nubank", "Pix / débito", "Vale (Mayane)", "Dinheiro", "Outro cartão")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    person = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    description = db.Column(db.String(200), default="")
    group = db.Column(db.String(20), nullable=False, default="Desejo")
    limit_casal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    limit_rodrigo = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    limit_mayane = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    sort = db.Column(db.Integer, nullable=False, default=0)

    def limit_for(self, owner):
        return {"Casal": self.limit_casal, "Rodrigo": self.limit_rodrigo, "Mayane": self.limit_mayane}[owner]


class Expense(db.Model):
    """Gasto do dia a dia. Conta no mês da data da compra."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category = db.relationship("Category")
    owner = db.Column(db.String(20), nullable=False)       # Casal / Rodrigo / Mayane
    paid_by = db.Column(db.String(20), nullable=False)     # Rodrigo / Mayane
    method = db.Column(db.String(30), default="")
    notes = db.Column(db.String(200), default="")
    created_by = db.Column(db.String(20), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class FixedCost(db.Model):
    """Conta que se repete todo mês (aluguel, financiamento...)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    description = db.Column(db.String(200), default="")
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    owner = db.Column(db.String(20), nullable=False, default="Rodrigo")
    paid_by = db.Column(db.String(20), nullable=False, default="Rodrigo")
    group = db.Column(db.String(20), nullable=False, default="Necessidade")
    end_month = db.Column(db.Date, nullable=True)   # último mês pago (ex.: financiamento); vazio = sem fim
    inflates = db.Column(db.Boolean, nullable=False, default=True)  # reajusta com a inflação na projeção


class Installment(db.Model):
    """Compra parcelada. first_month = mês de pagamento da parcela 1."""
    id = db.Column(db.Integer, primary_key=True)
    card = db.Column(db.String(30), default="")
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200), default="")
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    first_month = db.Column(db.Date, nullable=False)
    owner = db.Column(db.String(20), nullable=False, default="Rodrigo")
    paid_by = db.Column(db.String(20), nullable=False, default="Rodrigo")
    group = db.Column(db.String(20), nullable=False, default="Desejo")


class Setting(db.Model):
    key = db.Column(db.String(40), primary_key=True)
    value = db.Column(db.String(60), nullable=False)
    label = db.Column(db.String(120), default="")
    sort = db.Column(db.Integer, default=0)
