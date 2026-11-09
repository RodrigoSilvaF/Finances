"""Comandos de terminal: flask --app finances <comando>."""
from datetime import date, datetime

import click

from .models import Category, Expense, FixedCost, Installment, db

# categoria da planilha Orçamento -> categoria do app
CATEGORY_MAP = {
    "Mercado": "Mercado",
    "Combustível": "Combustível",
    "Comer fora / bar / delivery": "Comer fora / bar / delivery",
    "Transporte (Uber/estac.)": "Transporte (Uber/estac.)",
    "Assinaturas": "Assinaturas",
    "Pet": "Pet",
    "Multas / juros": "Multas / juros",
    "Outros": "Outros",
}
SHARED_FIXED = {"Aluguel", "Condominio", "Internet"}


def app_category(sheet_category, description, owner):
    if sheet_category in CATEGORY_MAP:
        name = CATEGORY_MAP[sheet_category]
    elif sheet_category.startswith("Compras"):
        name = "Casa (itens / limpeza)" if owner == "Casal" else "Roupas / compras pessoais"
    elif sheet_category.startswith("Saúde"):
        name = "Pilates / academia" if "pilates" in description.lower() else "Saúde / farmácia"
    else:
        name = "Outros"
    return Category.query.filter_by(name=name).one()


def as_date(v):
    return v.date() if isinstance(v, datetime) else v


def register_cli(app):
    @app.cli.command("import-planilha")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    @click.option("--replace", is_flag=True, help="Apaga fixas, parcelas e gastos já importados antes.")
    def import_planilha(path, replace):
        """Importa Fixos, Parcelas e Lançamentos Out da planilha 'Orcamento Rodrigo v4.xlsx'."""
        from openpyxl import load_workbook
        wb = load_workbook(path, data_only=True)

        if replace:
            Expense.query.filter(Expense.notes.like("Importado%")).delete(synchronize_session=False)
            FixedCost.query.delete()
            Installment.query.delete()

        fixed = 0
        for row in wb["Fixos"].iter_rows(min_row=5, values_only=True):
            name, what, group, _how, value = row[:5]
            if not name or name == "Total" or value is None:
                continue
            fc = FixedCost(name=name, description=what or "", amount=value, group=group or "Necessidade",
                           owner="Casal" if name in SHARED_FIXED else "Rodrigo", paid_by="Rodrigo",
                           inflates=name != "Parcela Carro",
                           end_month=date(2028, 10, 1) if name == "Parcela Carro" else None)
            db.session.add(fc)
            fixed += 1

        inst = 0
        for row in wb["Parcelas"].iter_rows(min_row=5, values_only=True):
            card, name, what, owner, group, value, number, total, ref = row[:9]
            if not name or value is None or ref is None:
                continue
            ref = as_date(ref).replace(day=1)
            month = ref.month - 1 - (int(number) - 1)
            first = date(ref.year + month // 12, month % 12 + 1, 1)
            db.session.add(Installment(card=card or "", name=name, description=what or "", amount=value,
                                       total=int(total), first_month=first, owner=owner, paid_by="Rodrigo",
                                       group=group or "Desejo"))
            inst += 1

        exp = 0
        for row in wb["Lançamentos Out"].iter_rows(min_row=5, values_only=True):
            card, when, desc, value, owner, kind, category = row[:7]
            if not desc or value is None or kind != "À vista" or owner not in ("Casal", "Rodrigo", "Mayane"):
                continue
            if float(value) <= 0:  # estornos ficam de fora
                continue
            db.session.add(Expense(date=as_date(when), description=str(desc)[:120], amount=value,
                                   category=app_category(category, str(desc), owner), owner=owner,
                                   paid_by="Rodrigo", method=f"Cartão {card}", notes="Importado da planilha",
                                   created_by="import"))
            exp += 1

        db.session.commit()
        click.echo(f"Importado: {fixed} contas fixas, {inst} parcelas, {exp} gastos de outubro.")
