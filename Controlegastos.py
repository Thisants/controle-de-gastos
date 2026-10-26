#!/usr/bin/env python3
"""Controle de gastos pessoais - registra receitas e despesas em CSV."""

import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ARQUIVO = Path("gastos.csv")
CAMPOS = ["data", "tipo", "categoria", "descricao", "valor"]
CATEGORIAS = [
    "Moradia", "Alimentação", "Transporte", "Saúde",
    "Lazer", "Educação", "Contas", "Outros",
]


# ---------- Persistência ----------
def carregar():
    if not ARQUIVO.exists():
        return []
    with ARQUIVO.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def salvar(registro):
    novo = not ARQUIVO.exists()
    with ARQUIVO.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerow(registro)


# ---------- Entrada de dados ----------
def ler_valor(msg):
    while True:
        txt = input(msg).strip().replace("R$", "").replace(".", "").replace(",", ".")
        try:
            v = Decimal(txt)
            if v > 0:
                return v.quantize(Decimal("0.01"))
        except InvalidOperation:
            pass
        print("  Valor inválido. Exemplo: 49,90")


def ler_data():
    while True:
        txt = input("Data (DD/MM/AAAA, Enter = hoje): ").strip()
        if not txt:
            return date.today()
        try:
            return datetime.strptime(txt, "%d/%m/%Y").date()
        except ValueError:
            print("  Data inválida.")


def escolher_categoria():
    print("\nCategorias:")
    for i, c in enumerate(CATEGORIAS, 1):
        print(f"  {i}. {c}")
    while True:
        op = input("Escolha o número (ou digite uma nova): ").strip()
        if op.isdigit() and 1 <= int(op) <= len(CATEGORIAS):
            return CATEGORIAS[int(op) - 1]
        if op and not op.isdigit():
            return op.title()
        print("  Opção inválida.")


def ler_mes():
    txt = input("Mês (MM/AAAA, Enter = atual): ").strip()
    if not txt:
        hoje = date.today()
        return hoje.year, hoje.month
    try:
        d = datetime.strptime(txt, "%m/%Y")
        return d.year, d.month
    except ValueError:
        print("  Formato inválido, usando o mês atual.")
        hoje = date.today()
        return hoje.year, hoje.month


# ---------- Funcionalidades ----------
def registrar(tipo):
    print(f"\n--- Nova {tipo} ---")
    categoria = "Salário/Receita" if tipo == "receita" else escolher_categoria()
    descricao = input("Descrição: ").strip()
    valor = ler_valor("Valor (R$): ")
    data = ler_data()
    salvar({
        "data": data.isoformat(),
        "tipo": tipo,
        "categoria": categoria,
        "descricao": descricao,
        "valor": str(valor),
    })
    print(f"✔ {tipo.capitalize()} de {fmt(valor)} registrada.")


def do_mes(registros, ano, mes):
    return [
        r for r in registros
        if (d := date.fromisoformat(r["data"])).year == ano and d.month == mes
    ]


def fmt(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def resumo():
    ano, mes = ler_mes()
    regs = do_mes(carregar(), ano, mes)
    receitas = sum((Decimal(r["valor"]) for r in regs if r["tipo"] == "receita"), Decimal(0))
    despesas = sum((Decimal(r["valor"]) for r in regs if r["tipo"] == "despesa"), Decimal(0))
    saldo = receitas - despesas

    print(f"\n===== RESUMO {mes:02d}/{ano} =====")
    print(f"Receitas:       {fmt(receitas)}")
    print(f"Total gasto:    {fmt(despesas)}")
    print(f"Sobrou/guardou: {fmt(saldo)}")
    if receitas > 0:
        print(f"Você guardou {saldo / receitas * 100:.1f}% da sua renda.")

    por_cat = defaultdict(Decimal)
    for r in regs:
        if r["tipo"] == "despesa":
            por_cat[r["categoria"]] += Decimal(r["valor"])
    if por_cat:
        print("\nGastos por categoria:")
        for cat, v in sorted(por_cat.items(), key=lambda x: -x[1]):
            print(f"  {cat:<15} {fmt(v):>14}  ({v / despesas * 100:.0f}%)")


def listar():
    ano, mes = ler_mes()
    regs = sorted(do_mes(carregar(), ano, mes), key=lambda r: r["data"])
    if not regs:
        print("\nNenhum lançamento nesse mês.")
        return
    print(f"\n===== LANÇAMENTOS {mes:02d}/{ano} =====")
    for r in regs:
        d = date.fromisoformat(r["data"]).strftime("%d/%m")
        sinal = "+" if r["tipo"] == "receita" else "-"
        print(f"{d}  {sinal} {fmt(Decimal(r['valor'])):>12}  {r['categoria']:<15} {r['descricao']}")


MENU = """
===== CONTROLE DE GASTOS =====
1. Registrar receita (salário)
2. Registrar despesa
3. Resumo do mês
4. Listar lançamentos do mês
0. Sair
"""


def main():
    acoes = {
        "1": lambda: registrar("receita"),
        "2": lambda: registrar("despesa"),
        "3": resumo,
        "4": listar,
    }
    while True:
        print(MENU)
        op = input("Opção: ").strip()
        if op == "0":
            print("Até logo!")
            break
        acao = acoes.get(op)
        if acao:
            acao()
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nAté logo!")