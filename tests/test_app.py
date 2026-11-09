from datetime import date

import pytest

from finances import create_app
from finances.models import Category, Expense, FixedCost, db


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("RODRIGO_PASSWORD", "teste-rodrigo")
    monkeypatch.setenv("MAYANE_PASSWORD", "teste-mayane")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    with app.test_client() as c:
        with app.app_context():
            yield c


def login(c, who="rodrigo"):
    return c.post("/login", data={"username": who, "password": f"teste-{who}"}, follow_redirects=True)


def test_requires_login(client):
    assert client.get("/").status_code == 302
    assert client.post("/login", data={"username": "rodrigo", "password": "errada"}).status_code == 200


def test_all_pages_render(client):
    login(client)
    for url in ["/", "/gastos", "/gastos/novo", "/50-30-20", "/50-30-20?p=Mayane", "/parcelas", "/parcelas/nova",
                "/fixas", "/fixas/nova", "/limites", "/projecao", "/config"]:
        assert client.get(url).status_code == 200, url


def test_add_expense_updates_dashboard_and_settle(client):
    login(client)
    cat = Category.query.filter_by(name="Mercado").one()
    r = client.post("/gastos/novo", data={"date": "2026-11-03", "description": "Giassi", "amount": "400,00",
                                          "category_id": cat.id, "owner": "Casal", "paid_by": "Rodrigo",
                                          "method": "Cartão Nubank"}, follow_redirects=True)
    assert r.status_code == 200
    e = Expense.query.one()
    assert float(e.amount) == 400 and e.created_by == "Rodrigo"
    page = client.get("/?m=2026-11").get_data(as_text=True)
    assert "Mayane transfere R$ 99,60 para o Rodrigo" in page


def test_fixed_casal_enters_settle(client):
    login(client)
    db.session.add(FixedCost(name="Aluguel", amount=2068, owner="Casal", paid_by="Rodrigo"))
    db.session.commit()
    page = client.get("/?m=2026-11").get_data(as_text=True)
    assert "R$ 514,93" in page  # 24,9% de 2.068


def test_invalid_amount_rejected(client):
    login(client)
    cat = Category.query.first()
    r = client.post("/gastos/novo", data={"date": "2026-11-03", "description": "x", "amount": "abc",
                                          "category_id": cat.id, "owner": "Casal", "paid_by": "Rodrigo"})
    assert r.status_code == 400
    assert Expense.query.count() == 0
