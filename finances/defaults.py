"""Valores iniciais criados no primeiro start (banco vazio). Tudo editável no app."""

# (nome, o que entra, 50/30/20, limite casal (total), limite Rodrigo, limite Mayane)
CATEGORIES = [
    ("Mercado", "Supermercado, padaria, açougue, hortifruti", "Necessidade", 1000, 0, 0),
    ("Combustível", "Gasolina do carro", "Necessidade", 330, 0, 0),
    ("Comer fora / bar / delivery", "Restaurante, bar, iFood, lanche, marmita", "Desejo", 200, 250, 150),
    ("Transporte (Uber/estac.)", "Uber, 99, estacionamento, ônibus", "Desejo", 0, 60, 60),
    ("Assinaturas", "Streaming, apps, jogos, iCloud, Spotify", "Desejo", 25, 110, 0),
    ("Roupas / compras pessoais", "Roupas, calçados, eletrônicos, coisas pessoais", "Desejo", 0, 100, 150),
    ("Casa (itens / limpeza)", "Limpeza, utensílios, cama/mesa/banho, lavanderia", "Necessidade", 130, 0, 0),
    ("Saúde / farmácia", "Farmácia, consultas, exames", "Necessidade", 70, 0, 100),
    ("Pilates / academia", "Mensalidade de pilates ou academia", "Necessidade", 600, 0, 0),
    ("Pet", "Ração, Petz, veterinário", "Necessidade", 90, 0, 0),
    ("Lazer / passeios", "Cinema, eventos, passeios, viagens curtas", "Desejo", 100, 0, 50),
    ("Presentes", "Aniversários, Natal", "Desejo", 0, 0, 0),
    ("Carro (avulso)", "Lavagem, peças, manutenção fora das parcelas", "Necessidade", 0, 0, 0),
    ("Multas / juros", "Multa e juros de fatura atrasada — meta é zero", "Desejo", 0, 0, 0),
    ("Outros", "O que não se encaixa nas outras", "Desejo", 0, 75, 100),
]

# chave: (valor, rótulo)
SETTINGS = {
    "split_rodrigo": (0.751, "Parte do Rodrigo nos gastos do casal (0,751 = 75,1%)"),
    "salary_usd": (2184, "Salário do Rodrigo em US$"),
    "dollar": (5.00, "Dólar do dia (R$)"),
    "fx_discount": (0.04, "Deságio da cotação recebida (0,04 = 4%)"),
    "tax": (0.03, "Reserva de impostos (0,03 = 3%)"),
    "reserve": (400, "Reserva fixa mensal (R$)"),
    "mayane_salary": (2700, "Salário líquido da Mayane (R$)"),
    "mayane_voucher": (800, "Vale da Mayane (R$)"),
    "inflation": (0.045, "Projeção: inflação dos custos ao ano (0,045 = 4,5%)"),
    "yield_month": (0.008, "Projeção: rendimento do dinheiro guardado ao mês (0,008 = 0,8%)"),
    "salary_raise": (0.0, "Projeção: reajuste salarial ao ano (0,03 = 3%)"),
    "extra_realista": (840, "Projeção: cenário Realista gasta R$ X/mês além dos limites"),
    "extra_conservador": (1540, "Projeção: cenário Conservador gasta R$ X/mês além dos limites"),
}
