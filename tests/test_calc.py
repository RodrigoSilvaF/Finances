from datetime import date
from types import SimpleNamespace

import pytest

from finances import calc

SPLIT = 0.751


def test_share_split():
    assert calc.share(100, "Casal", "Rodrigo", SPLIT) == pytest.approx(75.1)
    assert calc.share(100, "Casal", "Mayane", SPLIT) == pytest.approx(24.9)
    assert calc.share(100, "Mayane", "Rodrigo", SPLIT) == 0
    assert calc.share(100, "Rodrigo", "Rodrigo", SPLIT) == 100


def test_settle_matches_october_case():
    # Nubank de outubro: casal 3.845,16 + só da Mayane 444,61, tudo pago pelo Rodrigo
    owed = (calc.settle_amount(3845.16, "Casal", "Rodrigo", SPLIT)
            + calc.settle_amount(444.61, "Mayane", "Rodrigo", SPLIT))
    assert owed == pytest.approx(1402.05, abs=0.01)


def test_settle_when_mayane_pays():
    # Mayane paga 200 de mercado do casal com o vale: Rodrigo deve a parte dele
    assert calc.settle_amount(200, "Casal", "Mayane", SPLIT) == pytest.approx(-150.2)


def test_installment_schedule():
    pneus = SimpleNamespace(amount=665, total=4, first_month=date(2026, 12, 1))
    assert calc.installment_due(pneus, date(2026, 11, 1)) == 0
    assert calc.installment_due(pneus, date(2026, 12, 1)) == 665
    assert calc.installment_due(pneus, date(2027, 3, 1)) == 665
    assert calc.installment_due(pneus, date(2027, 4, 1)) == 0
    assert calc.installment_remaining(pneus, date(2027, 2, 1)) == 2


def test_net_salary_at_5_reais():
    s = {"salary_usd": 2184, "dollar": 5.0, "fx_discount": 0.04, "tax": 0.03, "reserve": 400}
    assert calc.net_salary(s) == pytest.approx(9768.70, abs=0.01)


def test_days_left():
    nov = date(2026, 11, 1)
    assert calc.days_left(nov, date(2026, 11, 9)) == 22
    assert calc.days_left(nov, date(2026, 10, 1)) == 30
    assert calc.days_left(nov, date(2026, 12, 1)) == 0


def test_projection_accumulates_with_yield():
    s = {"salary_usd": 1000, "dollar": 1, "fx_discount": 0, "tax": 0, "reserve": 0,
         "inflation": 0, "salary_raise": 0, "yield_month": 0.01}
    rows = calc.projection(s, lambda m: (0, 900), date(2026, 1, 1), date(2026, 3, 1))
    assert [round(r[2], 2) for r in rows] == [100, 201, 303.01]
