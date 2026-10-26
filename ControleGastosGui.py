#!/usr/bin/env python3
"""Interface gráfica do Controle de Gastos.

Usa o mesmo gastos.csv e as mesmas funções do controleGastos.py,
então os dois programas podem ser usados em conjunto.
Deixe os dois arquivos na mesma pasta.
"""

import tkinter as tk
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

try:
    from Controlegastos import (CATEGORIAS, MAX_METAS, ajustar_meta, calcular,
                               carregar, carregar_metas, criar_meta, do_mes,
                               excluir_meta, fmt, fmt_num, parse_numero, salvar,
                               status_meta)
except ModuleNotFoundError:
    from Controlegastos import (CATEGORIAS, MAX_METAS, ajustar_meta, calcular,
                               carregar, carregar_metas, criar_meta, do_mes,
                               excluir_meta, fmt, fmt_num, parse_numero, salvar,
                               status_meta)

VERDE, VERMELHO, AZUL = "#1a7f37", "#c62828", "#1565c0"


def parse_valor(txt):
    txt = txt.strip().replace("R$", "").replace(".", "").replace(",", ".")
    v = Decimal(txt)  # levanta InvalidOperation se inválido
    if v <= 0:
        raise InvalidOperation
    return v.quantize(Decimal("0.01"))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Controle de Gastos")
        self.geometry("860x680")
        self.minsize(760, 600)

        hoje = date.today()
        self.mes = tk.IntVar(value=hoje.month)
        self.ano = tk.IntVar(value=hoje.year)
        self.tipo = tk.StringVar(value="despesa")
        self.cat = tk.StringVar(value=CATEGORIAS[0])
        self.desc = tk.StringVar()
        self.valor = tk.StringVar()
        self.data = tk.StringVar(value=hoje.strftime("%d/%m/%Y"))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.aba_gastos = ttk.Frame(self.nb)
        self.aba_metas = ttk.Frame(self.nb)
        self.aba_calc = ttk.Frame(self.nb)
        self.nb.add(self.aba_gastos, text="Gastos")
        self.nb.add(self.aba_metas, text="Metas")
        self.nb.add(self.aba_calc, text="Calculadora")

        self.montar()
        self.montar_metas()
        self.montar_calc()
        self.atualizar()
        self.atualizar_metas()

    # ---------- Layout ----------
    def montar(self):
        pad = {"padx": 10, "pady": 6}

        # Período
        topo = ttk.Frame(self.aba_gastos)
        topo.pack(fill="x", **pad)
        ttk.Label(topo, text="Mês:").pack(side="left")
        sp_mes = ttk.Spinbox(topo, from_=1, to=12, width=4, textvariable=self.mes,
                             command=self.atualizar)
        sp_mes.pack(side="left", padx=(4, 12))
        ttk.Label(topo, text="Ano:").pack(side="left")
        sp_ano = ttk.Spinbox(topo, from_=2000, to=2100, width=6, textvariable=self.ano,
                             command=self.atualizar)
        sp_ano.pack(side="left", padx=4)
        for sp in (sp_mes, sp_ano):
            sp.bind("<Return>", lambda e: self.atualizar())

        # Cartões de resumo
        cards = ttk.Frame(self.aba_gastos)
        cards.pack(fill="x", **pad)
        self.lbl = {}
        for chave, titulo, cor in (("rec", "Receitas", VERDE),
                                   ("gas", "Total gasto", VERMELHO),
                                   ("sob", "Sobrou", AZUL)):
            box = ttk.LabelFrame(cards, text=titulo)
            box.pack(side="left", expand=True, fill="x", padx=4)
            self.lbl[chave] = tk.Label(box, text="R$ 0,00", fg=cor,
                                       font=("TkDefaultFont", 16, "bold"))
            self.lbl[chave].pack(padx=8, pady=6)
        self.lbl_pct = ttk.Label(self.aba_gastos, text="")
        self.lbl_pct.pack(anchor="w", padx=14)

        # Formulário
        form = ttk.LabelFrame(self.aba_gastos, text="Novo lançamento")
        form.pack(fill="x", **pad)

        linha1 = ttk.Frame(form)
        linha1.pack(fill="x", padx=8, pady=4)
        for texto, valor in (("Despesa", "despesa"), ("Receita", "receita")):
            ttk.Radiobutton(linha1, text=texto, value=valor, variable=self.tipo,
                            command=self.trocar_tipo).pack(side="left", padx=(0, 12))

        linha2 = ttk.Frame(form)
        linha2.pack(fill="x", padx=8, pady=4)
        ttk.Label(linha2, text="Categoria").grid(row=0, column=0, sticky="w")
        ttk.Label(linha2, text="Descrição").grid(row=0, column=1, sticky="w")
        ttk.Label(linha2, text="Valor (R$)").grid(row=0, column=2, sticky="w")
        ttk.Label(linha2, text="Data").grid(row=0, column=3, sticky="w")
        self.cb_cat = ttk.Combobox(linha2, textvariable=self.cat, values=CATEGORIAS, width=16)
        self.cb_cat.grid(row=1, column=0, padx=(0, 8), sticky="we")
        ttk.Entry(linha2, textvariable=self.desc, width=28).grid(row=1, column=1, padx=(0, 8), sticky="we")
        ent_valor = ttk.Entry(linha2, textvariable=self.valor, width=12)
        ent_valor.grid(row=1, column=2, padx=(0, 8))
        ttk.Entry(linha2, textvariable=self.data, width=12).grid(row=1, column=3, padx=(0, 8))
        ttk.Button(linha2, text="Adicionar", command=self.adicionar).grid(row=1, column=4)
        linha2.columnconfigure(1, weight=1)
        ent_valor.bind("<Return>", lambda e: self.adicionar())

        # Gastos por categoria
        cat_frame = ttk.LabelFrame(self.aba_gastos, text="Gastos por categoria")
        cat_frame.pack(fill="x", **pad)
        self.tv_cat = ttk.Treeview(cat_frame, columns=("cat", "total", "pct"),
                                   show="headings", height=4)
        for col, titulo, larg in (("cat", "Categoria", 200), ("total", "Total", 120), ("pct", "%", 60)):
            self.tv_cat.heading(col, text=titulo)
            self.tv_cat.column(col, width=larg, anchor="w" if col == "cat" else "e")
        self.tv_cat.pack(fill="x", padx=6, pady=6)

        # Lançamentos
        lanc = ttk.LabelFrame(self.aba_gastos, text="Lançamentos do mês")
        lanc.pack(fill="both", expand=True, **pad)
        cols = ("data", "categoria", "descricao", "valor")
        self.tv = ttk.Treeview(lanc, columns=cols, show="headings")
        for col, titulo, larg in (("data", "Data", 80), ("categoria", "Categoria", 140),
                                  ("descricao", "Descrição", 300), ("valor", "Valor", 120)):
            self.tv.heading(col, text=titulo)
            self.tv.column(col, width=larg, anchor="e" if col == "valor" else "w")
        self.tv.tag_configure("receita", foreground=VERDE)
        self.tv.tag_configure("despesa", foreground=VERMELHO)
        sb = ttk.Scrollbar(lanc, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb.pack(side="right", fill="y", pady=6, padx=(0, 6))

    # ---------- Lógica ----------
    def trocar_tipo(self):
        if self.tipo.get() == "receita":
            self.cat.set("Salário/Receita")
            self.cb_cat.state(["disabled"])
        else:
            self.cat.set(CATEGORIAS[0])
            self.cb_cat.state(["!disabled"])

    def adicionar(self):
        try:
            valor = parse_valor(self.valor.get())
        except InvalidOperation:
            messagebox.showerror("Valor inválido", "Digite um valor maior que zero. Ex.: 49,90")
            return
        try:
            data = datetime.strptime(self.data.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror("Data inválida", "Use o formato DD/MM/AAAA.")
            return
        categoria = self.cat.get().strip().title() if self.tipo.get() == "despesa" else "Salário/Receita"
        salvar({
            "data": data.isoformat(),
            "tipo": self.tipo.get(),
            "categoria": categoria or "Outros",
            "descricao": self.desc.get().strip(),
            "valor": str(valor),
        })
        self.desc.set("")
        self.valor.set("")
        self.mes.set(data.month)
        self.ano.set(data.year)
        self.atualizar()

    def atualizar(self):
        try:
            ano, mes = self.ano.get(), self.mes.get()
        except tk.TclError:
            return
        regs = sorted(do_mes(carregar(), ano, mes), key=lambda r: r["data"])

        rec = sum((Decimal(r["valor"]) for r in regs if r["tipo"] == "receita"), Decimal(0))
        gas = sum((Decimal(r["valor"]) for r in regs if r["tipo"] == "despesa"), Decimal(0))
        sob = rec - gas
        self.lbl["rec"].config(text=fmt(rec))
        self.lbl["gas"].config(text=fmt(gas))
        self.lbl["sob"].config(text=fmt(sob), fg=AZUL if sob >= 0 else VERMELHO)
        self.lbl_pct.config(text=f"Você guardou {sob / rec * 100:.1f}% da sua renda." if rec > 0 else "")

        self.tv.delete(*self.tv.get_children())
        for r in regs:
            sinal = "+" if r["tipo"] == "receita" else "-"
            self.tv.insert("", "end", tags=(r["tipo"],), values=(
                date.fromisoformat(r["data"]).strftime("%d/%m/%Y"),
                r["categoria"], r["descricao"], f"{sinal} {fmt(Decimal(r['valor']))}"))

        por_cat = defaultdict(Decimal)
        for r in regs:
            if r["tipo"] == "despesa":
                por_cat[r["categoria"]] += Decimal(r["valor"])
        self.tv_cat.delete(*self.tv_cat.get_children())
        for cat, v in sorted(por_cat.items(), key=lambda x: -x[1]):
            pct = (v / gas * 100) if gas else Decimal(0)
            self.tv_cat.insert("", "end", values=(cat, fmt(v), f"{pct:.0f}%"))

    # ---------- Metas ----------
    def montar_metas(self):
        p = self.aba_metas
        self.meta_nome, self.meta_alvo = tk.StringVar(), tk.StringVar()
        novo = ttk.LabelFrame(p, text=f"Nova meta (máximo {MAX_METAS})")
        novo.pack(fill="x", padx=10, pady=8)
        ttk.Label(novo, text="Quero conseguir:").grid(row=0, column=0, sticky="w", padx=8)
        ttk.Label(novo, text="Quanto custa? (R$)").grid(row=0, column=1, sticky="w")
        ttk.Entry(novo, textvariable=self.meta_nome, width=32).grid(row=1, column=0, padx=8, pady=6)
        ent = ttk.Entry(novo, textvariable=self.meta_alvo, width=14)
        ent.grid(row=1, column=1)
        ent.bind("<Return>", lambda e: self.nova_meta())
        ttk.Button(novo, text="Criar meta", command=self.nova_meta).grid(row=1, column=2, padx=8)
        self.lista_metas = ttk.Frame(p)
        self.lista_metas.pack(fill="both", expand=True, padx=10)

    def nova_meta(self):
        nome = self.meta_nome.get().strip()
        if not nome:
            messagebox.showerror("Meta", "Dê um nome para a meta. Ex.: Viagem")
            return
        try:
            alvo = parse_valor(self.meta_alvo.get())
            criar_meta(nome, alvo)
        except InvalidOperation:
            messagebox.showerror("Valor inválido", "Digite um valor maior que zero. Ex.: 5000,00")
            return
        except ValueError as e:
            messagebox.showwarning("Limite de metas", str(e))
            return
        self.meta_nome.set("")
        self.meta_alvo.set("")
        self.atualizar_metas()

    def mover_meta(self, i, var, sinal):
        try:
            valor = parse_valor(var.get())
        except InvalidOperation:
            messagebox.showerror("Valor inválido", "Digite um valor maior que zero.")
            return
        ajustar_meta(i, valor * sinal)
        self.atualizar_metas()

    def apagar_meta(self, i):
        if messagebox.askyesno("Excluir meta", "Excluir esta meta?"):
            excluir_meta(i)
            self.atualizar_metas()

    def atualizar_metas(self):
        for w in self.lista_metas.winfo_children():
            w.destroy()
        metas = carregar_metas()
        if not metas:
            ttk.Label(self.lista_metas, text="Nenhuma meta ainda. Crie a primeira acima!").pack(pady=20)
        for i, m in enumerate(metas):
            texto, pct = status_meta(m)
            box = ttk.LabelFrame(self.lista_metas, text=f"{m['nome']} — alvo {fmt(Decimal(m['alvo']))}")
            box.pack(fill="x", pady=4)
            tk.Label(box, text=texto, fg=VERDE if pct >= 100 else AZUL,
                     font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
            ttk.Progressbar(box, value=pct, maximum=100).pack(fill="x", padx=8)
            linha = ttk.Frame(box)
            linha.pack(fill="x", padx=8, pady=6)
            v = tk.StringVar()
            ttk.Entry(linha, textvariable=v, width=14).pack(side="left")
            ttk.Button(linha, text="Guardar",
                       command=lambda i=i, v=v: self.mover_meta(i, v, 1)).pack(side="left", padx=4)
            ttk.Button(linha, text="Retirar",
                       command=lambda i=i, v=v: self.mover_meta(i, v, -1)).pack(side="left")
            ttk.Button(linha, text="Excluir",
                       command=lambda i=i: self.apagar_meta(i)).pack(side="right")

    # ---------- Calculadora ----------
    def montar_calc(self):
        self.n1, self.n2 = tk.StringVar(), tk.StringVar()
        self.res = tk.StringVar(value="—")
        q = ttk.Frame(self.aba_calc)
        q.pack(pady=30)
        ttk.Label(q, text="Primeiro número").pack()
        ttk.Entry(q, textvariable=self.n1, width=22, justify="right").pack(pady=4)
        ttk.Label(q, text="Segundo número").pack()
        ttk.Entry(q, textvariable=self.n2, width=22, justify="right").pack(pady=4)
        botoes = ttk.Frame(q)
        botoes.pack(pady=10)
        for simbolo, op in (("+", "+"), ("−", "-"), ("×", "*"), ("÷", "/")):
            ttk.Button(botoes, text=simbolo, width=4,
                       command=lambda op=op: self.operar(op)).pack(side="left", padx=3)
        tk.Label(q, textvariable=self.res, fg=AZUL, font=("TkDefaultFont", 20, "bold")).pack(pady=10)

    def operar(self, op):
        try:
            r = calcular(parse_numero(self.n1.get()), op, parse_numero(self.n2.get()))
            self.res.set(f"= {fmt_num(r)}")
        except InvalidOperation:
            self.res.set("Número inválido")
        except ZeroDivisionError:
            self.res.set("Divisão por zero")


if __name__ == "__main__":
    App().mainloop()