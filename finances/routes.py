from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import calc, services
from .models import (GROUPS, METHODS, OWNERS, PEOPLE, Category, Expense, FixedCost, Installment, Setting,
                     User, db)

bp = Blueprint("main", __name__)


# ---------- helpers ----------
def selected_month():
    """?m=2026-11 -> date(2026, 11, 1); padrão = mês atual."""
    raw = request.args.get("m")
    try:
        y, m = map(int, raw.split("-"))
        return date(y, m, 1)
    except (AttributeError, ValueError):
        return calc.month_start(date.today())


def month_nav(month):
    return {"prev": calc.add_months(month, -1), "next": calc.add_months(month, 1), "current": month}


def money(field, required=True):
    raw = (request.form.get(field) or "").strip().replace("R$", "").replace(" ", "")
    if "," in raw:  # aceita 1.234,56 e 1234,56
        raw = raw.replace(".", "").replace(",", ".")
    if not raw and not required:
        return Decimal("0")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"Valor inválido: {request.form.get(field)!r}")
    return value.quantize(Decimal("0.01"))


def choice(field, options):
    value = request.form.get(field)
    if value not in options:
        raise ValueError(f"Escolha inválida em {field}")
    return value


def parse_date(field):
    try:
        return datetime.strptime(request.form.get(field, ""), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Data inválida")


def parse_month(field, required=True):
    raw = request.form.get(field, "")
    if not raw and not required:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m").date()
    except ValueError:
        raise ValueError("Mês inválido")


# ---------- auth ----------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip().lower()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=True)
            return redirect(url_for("main.dashboard"))
        flash("Usuário ou senha incorretos.", "error")
    return render_template("login.html", no_users=User.query.count() == 0)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


# ---------- painel ----------
@bp.route("/")
@login_required
def dashboard():
    month = selected_month()
    return render_template("dashboard.html", d=services.dashboard(month), nav=month_nav(month))


# ---------- gastos ----------
@bp.route("/gastos")
@login_required
def expenses():
    month = selected_month()
    items = services.month_expenses(month)
    owner = request.args.get("dono")
    if owner in OWNERS:
        items = [e for e in items if e.owner == owner]
    return render_template("expenses.html", items=items, nav=month_nav(month), owner=owner,
                           total=sum(float(e.amount) for e in items))


@bp.route("/gastos/novo", methods=["GET", "POST"])
@bp.route("/gastos/<int:id>", methods=["GET", "POST"])
@login_required
def expense_form(id=None):
    item = db.session.get(Expense, id) if id else None
    if id and item is None:
        abort(404)
    cats = services.categories()
    if request.method == "POST":
        try:
            data = dict(
                date=parse_date("date"),
                description=request.form.get("description", "").strip()[:120],
                amount=money("amount"),
                category_id=int(request.form.get("category_id", 0)),
                owner=choice("owner", OWNERS),
                paid_by=choice("paid_by", PEOPLE),
                method=request.form.get("method", "")[:30],
                notes=request.form.get("notes", "").strip()[:200],
            )
            if not data["description"]:
                raise ValueError("Descreva o gasto")
            if data["amount"] <= 0:
                raise ValueError("O valor precisa ser maior que zero")
            if not db.session.get(Category, data["category_id"]):
                raise ValueError("Escolha uma categoria")
        except ValueError as e:
            flash(str(e), "error")
            return render_template("expense_form.html", item=item, cats=cats, form=request.form,
                                   owners=OWNERS, people=PEOPLE, methods=METHODS), 400
        if item is None:
            item = Expense(created_by=current_user.person)
            db.session.add(item)
        for k, v in data.items():
            setattr(item, k, v)
        db.session.commit()
        flash("Gasto salvo.", "ok")
        if request.form.get("again"):
            return redirect(url_for("main.expense_form"))
        return redirect(url_for("main.dashboard", m=item.date.strftime("%Y-%m")))
    if item is None:
        form = {"date": date.today().isoformat(), "paid_by": current_user.person, "owner": "Casal"}
    else:
        form = {"date": item.date.isoformat(), "description": item.description, "amount": f"{item.amount:.2f}",
                "category_id": str(item.category_id), "owner": item.owner, "paid_by": item.paid_by,
                "method": item.method, "notes": item.notes}
    return render_template("expense_form.html", item=item, cats=cats, form=form,
                           owners=OWNERS, people=PEOPLE, methods=METHODS)


@bp.post("/gastos/<int:id>/apagar")
@login_required
def expense_delete(id):
    item = db.session.get(Expense, id) or abort(404)
    m = item.date.strftime("%Y-%m")
    db.session.delete(item)
    db.session.commit()
    flash("Gasto apagado.", "ok")
    return redirect(url_for("main.expenses", m=m))


# ---------- 50/30/20 ----------
@bp.route("/50-30-20")
@login_required
def fifty():
    month = selected_month()
    person = request.args.get("p") if request.args.get("p") in PEOPLE else current_user.person
    return render_template("fifty.html", r=services.fifty_thirty_twenty(month, person), person=person,
                           nav=month_nav(month))


# ---------- parcelas ----------
@bp.route("/parcelas")
@login_required
def installments():
    month = selected_month()
    s = services.settings()
    rows = []
    for i in Installment.query.order_by(Installment.card, Installment.name).all():
        rows.append({"i": i, "number": calc.installment_number(i.first_month, month),
                     "due": calc.installment_due(i, month),
                     "remaining": calc.installment_remaining(i, month),
                     "last": calc.add_months(i.first_month, i.total - 1),
                     "mine": calc.share(calc.installment_due(i, month), i.owner, "Rodrigo", s["split_rodrigo"])})
    active = [r for r in rows if r["remaining"] > 0]
    finished = [r for r in rows if r["remaining"] == 0]
    owed = sum(r["remaining"] * calc.share(r["i"].amount, r["i"].owner, "Rodrigo", s["split_rodrigo"])
               for r in active)
    return render_template("installments.html", active=active, finished=finished, nav=month_nav(month),
                           total=sum(r["due"] for r in active), mine=sum(r["mine"] for r in active), owed=owed)


@bp.route("/parcelas/nova", methods=["GET", "POST"])
@bp.route("/parcelas/<int:id>", methods=["GET", "POST"])
@login_required
def installment_form(id=None):
    item = db.session.get(Installment, id) if id else None
    if id and item is None:
        abort(404)
    if request.method == "POST":
        try:
            total = int(request.form.get("total", 0))
            number = int(request.form.get("number", 1))
            if total < 1 or not 1 <= number <= total:
                raise ValueError("Confira o número da parcela e o total")
            month = parse_month("month")
            data = dict(card=request.form.get("card", "")[:30], name=request.form.get("name", "").strip()[:80],
                        description=request.form.get("description", "").strip()[:200], amount=money("amount"),
                        total=total, first_month=calc.add_months(month, -(number - 1)),
                        owner=choice("owner", OWNERS), paid_by=choice("paid_by", PEOPLE),
                        group=choice("group", GROUPS))
            if not data["name"]:
                raise ValueError("Dê um nome para a parcela")
        except ValueError as e:
            flash(str(e), "error")
            return render_template("installment_form.html", item=item, form=request.form, owners=OWNERS,
                                   people=PEOPLE, groups=GROUPS), 400
        if item is None:
            item = Installment()
            db.session.add(item)
        for k, v in data.items():
            setattr(item, k, v)
        db.session.commit()
        flash("Parcela salva.", "ok")
        return redirect(url_for("main.installments"))
    if item is None:
        form = {"month": date.today().strftime("%Y-%m"), "number": 1, "owner": "Rodrigo",
                "paid_by": "Rodrigo", "group": "Desejo"}
    else:
        this_month = calc.month_start(date.today())
        number = calc.installment_number(item.first_month, this_month)
        month = this_month if 1 <= number <= item.total else item.first_month
        form = {"card": item.card, "name": item.name, "description": item.description,
                "amount": f"{item.amount:.2f}", "total": item.total,
                "number": number if 1 <= number <= item.total else 1, "month": month.strftime("%Y-%m"),
                "owner": item.owner, "paid_by": item.paid_by, "group": item.group}
    return render_template("installment_form.html", item=item, form=form, owners=OWNERS, people=PEOPLE,
                           groups=GROUPS)


@bp.post("/parcelas/<int:id>/apagar")
@login_required
def installment_delete(id):
    db.session.delete(db.session.get(Installment, id) or abort(404))
    db.session.commit()
    flash("Parcela apagada.", "ok")
    return redirect(url_for("main.installments"))


# ---------- contas fixas ----------
@bp.route("/fixas")
@login_required
def fixed():
    month = selected_month()
    s = services.settings()
    items = FixedCost.query.order_by(FixedCost.owner, FixedCost.name).all()
    rows = [{"f": f, "active": calc.fixed_active(f, month),
             "mine": calc.share(f.amount, f.owner, "Rodrigo", s["split_rodrigo"]),
             "hers": calc.share(f.amount, f.owner, "Mayane", s["split_rodrigo"])} for f in items]
    act = [r for r in rows if r["active"]]
    return render_template("fixed.html", rows=rows, nav=month_nav(month),
                           total=sum(float(r["f"].amount) for r in act),
                           mine=sum(r["mine"] for r in act), hers=sum(r["hers"] for r in act))


@bp.route("/fixas/nova", methods=["GET", "POST"])
@bp.route("/fixas/<int:id>", methods=["GET", "POST"])
@login_required
def fixed_form(id=None):
    item = db.session.get(FixedCost, id) if id else None
    if id and item is None:
        abort(404)
    if request.method == "POST":
        try:
            data = dict(name=request.form.get("name", "").strip()[:60],
                        description=request.form.get("description", "").strip()[:200],
                        amount=money("amount"), owner=choice("owner", OWNERS), paid_by=choice("paid_by", PEOPLE),
                        group=choice("group", GROUPS), end_month=parse_month("end_month", required=False),
                        inflates=bool(request.form.get("inflates")))
            if not data["name"]:
                raise ValueError("Dê um nome para a conta")
        except ValueError as e:
            flash(str(e), "error")
            return render_template("fixed_form.html", item=item, form=request.form, owners=OWNERS,
                                   people=PEOPLE, groups=GROUPS), 400
        if item is None:
            item = FixedCost()
            db.session.add(item)
        for k, v in data.items():
            setattr(item, k, v)
        db.session.commit()
        flash("Conta salva.", "ok")
        return redirect(url_for("main.fixed"))
    if item is None:
        form = {"owner": "Rodrigo", "paid_by": "Rodrigo", "group": "Necessidade", "inflates": "1"}
    else:
        form = {"name": item.name, "description": item.description, "amount": f"{item.amount:.2f}",
                "owner": item.owner, "paid_by": item.paid_by, "group": item.group,
                "end_month": item.end_month.strftime("%Y-%m") if item.end_month else "",
                "inflates": "1" if item.inflates else ""}
    return render_template("fixed_form.html", item=item, form=form, owners=OWNERS, people=PEOPLE, groups=GROUPS)


@bp.post("/fixas/<int:id>/apagar")
@login_required
def fixed_delete(id):
    db.session.delete(db.session.get(FixedCost, id) or abort(404))
    db.session.commit()
    flash("Conta apagada.", "ok")
    return redirect(url_for("main.fixed"))


# ---------- limites ----------
@bp.route("/limites", methods=["GET", "POST"])
@login_required
def limits():
    cats = services.categories()
    if request.method == "POST":
        try:
            for c in cats:
                c.group = choice(f"group_{c.id}", GROUPS)
                for owner in ("casal", "rodrigo", "mayane"):
                    setattr(c, f"limit_{owner}", money(f"{owner}_{c.id}", required=False))
            new_name = request.form.get("new_name", "").strip()[:60]
            if new_name:
                if Category.query.filter_by(name=new_name).first():
                    raise ValueError("Já existe uma categoria com esse nome")
                db.session.add(Category(name=new_name, group=choice("new_group", GROUPS),
                                        description=request.form.get("new_description", "")[:200],
                                        sort=len(cats)))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
            return redirect(url_for("main.limits"))
        db.session.commit()
        flash("Limites salvos.", "ok")
        return redirect(url_for("main.limits"))
    split = services.settings()["split_rodrigo"]
    tot = {k: sum(float(getattr(c, f"limit_{k}")) for c in cats) for k in ("casal", "rodrigo", "mayane")}
    return render_template("limits.html", cats=cats, groups=GROUPS, tot=tot, split=split)


# ---------- projeção ----------
@bp.route("/projecao")
@login_required
def projection():
    return render_template("projection.html", p=services.projection())


# ---------- configurações ----------
@bp.route("/config", methods=["GET", "POST"])
@login_required
def config():
    items = Setting.query.order_by(Setting.sort).all()
    if request.method == "POST":
        try:
            for s in items:
                raw = request.form.get(s.key, s.value).strip().replace(",", ".")
                s.value = str(float(raw))
        except ValueError:
            db.session.rollback()
            flash("Use só números (ex.: 0.751 ou 5.10).", "error")
            return redirect(url_for("main.config"))
        db.session.commit()
        flash("Configurações salvas.", "ok")
        return redirect(url_for("main.config"))
    s = services.settings()
    return render_template("config.html", items=items, net=calc.net_salary(s),
                           mayane=calc.income(s, "Mayane"))
