"""Regras de cálculo, sem acesso ao banco: fáceis de testar."""
import calendar
from datetime import date


def month_start(d):
    return date(d.year, d.month, 1)


def add_months(d, n):
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def months_between(a, b):
    """Quantos meses de a até b (ambos 1º dia do mês)."""
    return (b.year - a.year) * 12 + b.month - a.month


def month_end(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def share(amount, owner, person, split_rodrigo):
    """Parte de `person` num valor cujo dono é `owner`."""
    amount = float(amount)
    if owner == person:
        return amount
    if owner == "Casal":
        return amount * (split_rodrigo if person == "Rodrigo" else 1 - split_rodrigo)
    return 0.0


def settle_amount(amount, owner, paid_by, split_rodrigo):
    """Quanto a Mayane deve ao Rodrigo por este item (negativo = Rodrigo deve à Mayane)."""
    if paid_by == "Rodrigo":
        return share(amount, owner, "Mayane", split_rodrigo)
    if paid_by == "Mayane":
        return -share(amount, owner, "Rodrigo", split_rodrigo)
    return 0.0


def bill_month(month):
    """Gastos contam no mês da compra; a parcela desse mês vem na fatura paga no mês seguinte."""
    return add_months(month, 1)


def installment_number(first_month, month):
    """Número da parcela que vence em `month` (pode ser <1 ou >total)."""
    return months_between(first_month, month) + 1


def installment_due(inst, month):
    k = installment_number(inst.first_month, month)
    return float(inst.amount) if 1 <= k <= inst.total else 0.0


def installment_remaining(inst, month):
    """Parcelas que faltam pagar contando a de `month`."""
    k = installment_number(inst.first_month, month)
    return max(0, min(inst.total, inst.total - k + 1))


def fixed_active(fc, month):
    return fc.end_month is None or month <= fc.end_month


def net_salary(s, dollar=None):
    """Salário líquido do Rodrigo em R$ a partir das configurações."""
    dollar = s["dollar"] if dollar is None else dollar
    gross = s["salary_usd"] * dollar * (1 - s["fx_discount"])
    return gross * (1 - s["tax"]) - s["reserve"]


def income(s, person):
    return net_salary(s) if person == "Rodrigo" else s["mayane_salary"] + s["mayane_voucher"]


def days_left(month, today):
    if today < month:
        return calendar.monthrange(month.year, month.month)[1]
    if today > month_end(month):
        return 0
    return (month_end(month) - today).days + 1


def projection(s, monthly_costs, start, end, extra=0.0):
    """Saldo acumulado mês a mês.

    monthly_costs(month) -> (custos que reajustam, custos fixos em R$ nominais).
    Os custos que reajustam sobem `inflation` a cada janeiro; o salário sobe `salary_raise`.
    Retorna lista de (mês, aporte, saldo).
    """
    rows, balance, month = [], 0.0, start
    while month <= end:
        years = month.year - start.year
        infl = (1 + s["inflation"]) ** years
        inc = net_salary(s) * (1 + s["salary_raise"]) ** years
        inflating, nominal = monthly_costs(month)
        contribution = inc - (inflating + extra) * infl - nominal
        balance = balance * (1 + s["yield_month"]) + contribution
        rows.append((month, contribution, balance))
        month = add_months(month, 1)
    return rows
