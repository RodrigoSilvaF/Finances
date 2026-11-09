"""Consultas ao banco + regras de calc.py para montar cada tela."""
from datetime import date

from . import calc
from .models import Category, Expense, FixedCost, Installment, Setting


def settings():
    return {s.key: float(s.value) for s in Setting.query.all()}


def month_expenses(month):
    return (Expense.query.filter(Expense.date >= month, Expense.date <= calc.month_end(month))
            .order_by(Expense.date.desc(), Expense.id.desc()).all())


def categories():
    return Category.query.order_by(Category.sort, Category.name).all()


def dashboard(month, today=None):
    s = settings()
    split = s["split_rodrigo"]
    today = today or date.today()
    expenses = month_expenses(month)
    cats = categories()

    rows = []
    for c in cats:
        row = {"category": c}
        for owner in ("Casal", "Rodrigo", "Mayane"):
            spent = sum(float(e.amount) for e in expenses if e.category_id == c.id and e.owner == owner)
            limit = float(c.limit_for(owner))
            row[owner] = {"limit": limit, "spent": spent, "left": limit - spent,
                          "used": spent / limit if limit else ("nolimit" if spent else None)}
        rows.append(row)

    totals = {o: {k: sum(r[o][k] for r in rows) for k in ("limit", "spent", "left")}
              for o in ("Casal", "Rodrigo", "Mayane")}
    casal_limit = totals["Casal"]["limit"]
    cards = {
        "Casal": {"limit": casal_limit, "spent": totals["Casal"]["spent"],
                  "what": "Gasto total do casal, antes de dividir"},
        "Rodrigo": {"limit": totals["Rodrigo"]["limit"] + casal_limit * split,
                    "spent": sum(calc.share(e.amount, e.owner, "Rodrigo", split) for e in expenses),
                    "what": f"Só dele + {split * 100:.1f}% do casal".replace(".", ",")},
        "Mayane": {"limit": totals["Mayane"]["limit"] + casal_limit * (1 - split),
                   "spent": sum(calc.share(e.amount, e.owner, "Mayane", split) for e in expenses),
                   "what": f"Só dela + {(1 - split) * 100:.1f}% do casal".replace(".", ",")},
    }
    days = calc.days_left(month, today)
    for c in cards.values():
        c["left"] = c["limit"] - c["spent"]
        c["used"] = c["spent"] / c["limit"] if c["limit"] else None
        c["per_day"] = max(0, c["left"]) / days if days else None
    return {"cards": cards, "rows": rows, "totals": totals, "days_left": days, "split": split,
            "settle": settle(month, s, expenses), "count": len(expenses)}


def settle(month, s=None, expenses=None):
    """Acerto do mês: positivo = Mayane transfere ao Rodrigo."""
    s = s or settings()
    split = s["split_rodrigo"]
    expenses = month_expenses(month) if expenses is None else expenses
    parts = {
        "Gastos do mês": sum(calc.settle_amount(e.amount, e.owner, e.paid_by, split) for e in expenses),
        "Contas fixas": sum(calc.settle_amount(f.amount, f.owner, f.paid_by, split)
                            for f in FixedCost.query.all() if calc.fixed_active(f, month)),
        "Parcelas (fatura seguinte)": sum(calc.settle_amount(calc.installment_due(i, calc.bill_month(month)), i.owner, i.paid_by, split)
                        for i in Installment.query.all()),
    }
    return {"parts": parts, "total": sum(parts.values())}


def fifty_thirty_twenty(month, person):
    s = settings()
    split = s["split_rodrigo"]
    inc = calc.income(s, person)
    groups = {g: {"Contas fixas": 0.0, "Parcelas": 0.0, "Gastos do mês": 0.0} for g in ("Necessidade", "Desejo")}
    for f in FixedCost.query.all():
        if calc.fixed_active(f, month):
            groups[f.group]["Contas fixas"] += calc.share(f.amount, f.owner, person, split)
    for i in Installment.query.all():
        groups[i.group]["Parcelas"] += calc.share(calc.installment_due(i, calc.bill_month(month)), i.owner, person, split)
    for e in month_expenses(month):
        groups[e.category.group]["Gastos do mês"] += calc.share(e.amount, e.owner, person, split)
    needs = sum(groups["Necessidade"].values())
    wants = sum(groups["Desejo"].values())
    savings = inc - needs - wants
    lines = [
        ("Necessidade", 0.5, needs, groups["Necessidade"]),
        ("Desejo", 0.3, wants, groups["Desejo"]),
        ("Poupança", 0.2, savings, {}),
    ]
    return {"income": inc, "lines": [
        {"group": g, "target_pct": t, "target": inc * t, "value": v, "pct": v / inc if inc else 0,
         "ok": (v >= inc * t) if g == "Poupança" else (v <= inc * t), "parts": parts}
        for g, t, v, parts in lines]}


def projection(start=None, end=date(2030, 12, 1)):
    s = settings()
    split = s["split_rodrigo"]
    start = start or calc.month_start(date.today())
    fixed = FixedCost.query.all()
    installments = Installment.query.all()
    daily_plan = sum(float(c.limit_rodrigo) + float(c.limit_casal) * split for c in categories())

    def monthly_costs(month):
        inflating = daily_plan + sum(calc.share(f.amount, f.owner, "Rodrigo", split)
                                     for f in fixed if f.inflates and calc.fixed_active(f, month))
        nominal = sum(calc.share(f.amount, f.owner, "Rodrigo", split)
                      for f in fixed if not f.inflates and calc.fixed_active(f, month))
        nominal += sum(calc.share(calc.installment_due(i, calc.bill_month(month)), i.owner, "Rodrigo", split) for i in installments)
        return inflating, nominal

    scenarios = {"Plano à risca": 0.0, "Realista": s["extra_realista"], "Conservador": s["extra_conservador"]}
    series = {name: calc.projection(s, monthly_costs, start, end, extra) for name, extra in scenarios.items()}
    first = next(iter(series.values()))
    checkpoints = [i for i, (m, _, _) in enumerate(first) if m.month == 12 or i == len(first) - 1]
    table = [{"month": first[i][0],
              "values": {n: series[n][i][2] for n in scenarios},
              "contrib": {n: series[n][i][1] for n in scenarios}} for i in checkpoints]
    return {"scenarios": scenarios, "table": table, "daily_plan": daily_plan, "start": start, "end": end,
            "net_salary": calc.net_salary(s)}
