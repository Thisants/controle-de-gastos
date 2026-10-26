#!/usr/bin/env python3
"""Controle de gastos pessoais - registra receitas e despesas em CSV."""

import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ARQUIVO = PASTA / "gastos.csv"
ARQUIVO_METAS = PASTA / "metas.csv"
CAMPOS = ["data", "tipo", "categoria", "descricao", "valor"]
CAMPOS_METAS = ["nome", "alvo", "guardado"]
MAX_METAS = 5
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


# ---------- Metas ----------
def carregar_metas():
    if not ARQUIVO_METAS.exists():
        return []
    with ARQUIVO_METAS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def salvar_metas(metas):
    with ARQUIVO_METAS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_METAS)
        w.writeheader()
        w.writerows(metas)


def criar_meta(nome, alvo):
    metas = carregar_metas()
    if len(metas) >= MAX_METAS:
        raise ValueError(f"Limite de {MAX_METAS} metas atingido. Exclua uma para criar outra.")
    metas.append({"nome": nome, "alvo": str(alvo), "guardado": "0.00"})
    salvar_metas(metas)


def ajustar_meta(i, delta):
    """Soma (ou subtrai, se negativo) um valor ao que já foi guardado na meta."""
    metas = carregar_metas()
    novo = max(Decimal(metas[i]["guardado"]) + delta, Decimal(0))
    metas[i]["guardado"] = str(novo.quantize(Decimal("0.01")))
    salvar_metas(metas)


def excluir_meta(i):
    metas = carregar_metas()
    del metas[i]
    salvar_metas(metas)


def status_meta(m):
    """Retorna (texto, porcentagem) da meta."""
    alvo, tem = Decimal(m["alvo"]), Decimal(m["guardado"])
    falta = max(alvo - tem, Decimal(0))
    pct = min(tem / alvo * 100, Decimal(100)) if alvo else Decimal(100)
    if falta == 0:
        return "Meta atingida! 🎉", float(pct)
    return f"Você tem {fmt(tem)}, falta {fmt(falta)}", float(pct)


# ---------- Calculadora ----------
def parse_numero(txt, milhar=False):
    """Converte texto em Decimal. Com milhar=True, '.' é separador de milhar (padrão BR)."""
    txt = txt.strip().replace("R$", "").replace(" ", "")
    if milhar or "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    v = Decimal(txt)
    if not v.is_finite():
        raise InvalidOperation
    return v


def calcular(a, op, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ZeroDivisionError("Não é possível dividir por zero.")
        return a / b
    raise ValueError("Operação inválida. Use + - * /")


def fmt_num(v):
    s = f"{v:,.4f}".rstrip("0").rstrip(".")
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


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


def escolher_meta(metas):
    if not metas:
        print("Crie uma meta primeiro.")
        return None
    op = input("Número da meta: ").strip()
    if op.isdigit() and 1 <= int(op) <= len(metas):
        return int(op) - 1
    print("Meta inválida.")
    return None


def menu_metas():
    while True:
        metas = carregar_metas()
        print("\n===== METAS =====")
        if not metas:
            print("Nenhuma meta criada.")
        for i, m in enumerate(metas, 1):
            texto, pct = status_meta(m)
            print(f"{i}. {m['nome']} (alvo {fmt(Decimal(m['alvo']))})\n   {texto} [{pct:.0f}%]")
        print("\n1. Nova meta  2. Guardar dinheiro  3. Retirar  4. Excluir  0. Voltar")
        op = input("Opção: ").strip()
        if op == "0":
            return
        try:
            if op == "1":
                nome = input("Quero conseguir: ").strip()
                if not nome:
                    print("Dê um nome para a meta.")
                    continue
                criar_meta(nome, ler_valor("Quanto custa? (R$): "))
            elif op in ("2", "3", "4"):
                i = escolher_meta(metas)
                if i is None:
                    continue
                if op == "4":
                    excluir_meta(i)
                else:
                    v = ler_valor("Valor (R$): ")
                    ajustar_meta(i, v if op == "2" else -v)
            else:
                print("Opção inválida.")
        except ValueError as e:
            print(e)


def menu_calculadora():
    print("\n===== CALCULADORA =====")
    try:
        a = parse_numero(input("Primeiro número: "))
        op = input("Operação (+ - * /): ").strip()
        b = parse_numero(input("Segundo número: "))
        print(f"= {fmt_num(calcular(a, op, b))}")
    except InvalidOperation:
        print("Número inválido.")
    except (ValueError, ZeroDivisionError) as e:
        print(e)


MENU = """
===== CONTROLE DE GASTOS =====
1. Registrar receita (salário)
2. Registrar despesa
3. Resumo do mês
4. Listar lançamentos do mês
5. Metas
6. Calculadora
0. Sair
"""


def main():
    acoes = {
        "1": lambda: registrar("receita"),
        "2": lambda: registrar("despesa"),
        "3": resumo,
        "4": listar,
        "5": menu_metas,
        "6": menu_calculadora,
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