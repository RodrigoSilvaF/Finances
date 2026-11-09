# Finanças — Rodrigo & Mayane

App web (Flask + Postgres) para lançar gastos do dia a dia e acompanhar limites por categoria,
a divisão do casal (75,1% / 24,9%), o acerto do mês, a regra 50/30/20, parcelas, contas fixas
e a projeção até 2030.

## Telas
| Aba | O que faz |
|---|---|
| Painel | Quanto cada um (Casal, Rodrigo, Mayane) já gastou no mês, quanto ainda pode e quanto por dia; acerto do mês |
| + Lançar gasto | Formulário rápido (funciona bem no celular) |
| Gastos | Lista do mês, com filtro por dono; toque para editar ou apagar |
| 50/30/20 | Necessidades, desejos e poupança do mês para Rodrigo ou Mayane |
| Parcelas | Compras parceladas, quantas faltam e quando terminam |
| Fixas | Aluguel, condomínio, carro... e quem paga |
| Limites | Verba por categoria (Casal / Rodrigo / Mayane) e classificação 50/30/20 |
| Projeção | Saldo guardado até dez/2030 em 3 cenários |
| Config | Salário, dólar, divisão do casal e premissas da projeção |

**Meses:** gastos contam no mês da compra; contas fixas no mês em que são pagas; a parcela de um mês
é a que vem na fatura paga no mês seguinte.

## Rodar no computador
```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt pytest
cp .env.example .env        # e escolha as senhas
.venv/Scripts/python run_dev.py   # http://localhost:5000
.venv/Scripts/python -m pytest
```

## Publicar no Render
1. Crie um repositório **privado** no GitHub e envie este projeto (o `.gitignore` já deixa de fora `.env`, banco local e planilhas).
2. No Render: **New → Blueprint**, escolha o repositório. O `render.yaml` cria o app `financas` e o banco `financas-db`.
3. O Render pede `RODRIGO_PASSWORD` e `MAYANE_PASSWORD`: são as senhas de login de cada um.
4. Abra a URL `https://financas-xxxx.onrender.com` e entre.

### Importar os dados da planilha para o banco do Render
No Render, abra o banco `financas-db` → **Connect → External Database URL** e copie a URL. No computador:
```bash
DATABASE_URL="<url externa>" .venv/Scripts/flask --app finances import-planilha "caminho/Orcamento Rodrigo v4.xlsx"
```
Importa contas fixas, parcelas e os gastos à vista de outubro. `--replace` apaga o que foi importado antes.

### Plano gratuito
- O app "dorme" sem uso; a primeira abertura depois disso leva ~1 minuto.
- O Postgres gratuito expira depois de um período (veja os termos atuais no Render). Para guardar os dados de vez, mude o banco para um plano pago antes de expirar.
- Para trocar uma senha: altere a variável no Render, adicione `RESET_PASSWORDS=1`, faça um deploy e depois remova essa variável.
