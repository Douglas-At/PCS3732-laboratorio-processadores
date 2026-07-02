#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =========================================================
# CALCULADORA 4 BITS - Raspberry Pi 3 (Python 3)
# Complemento de dois com deteccao de overflow
# Operacoes: +  -  *  fatorial
#
# Entrada: teclado conectado ao Raspberry Pi 3
# Saida:   monitor via adaptador HDMI-VGA (terminal / stdout)
#
# Inclui modo BENCHMARK: roda N testes de uma operacao e
# imprime uma tabela com o tempo de execucao (us) de cada teste.
#
# Porta em Python da calculadora feita no ESP32
# (Aula 03/04 - .ino com complemento de 2 e overflow).
# =========================================================

import time


# ---------------------------------------------------------
# Funcoes de baixo nivel (equivalentes as do ESP32)
# ---------------------------------------------------------

def para_com_sinal_4bits(v):
    """Interpreta os 4 bits baixos (0..15) em complemento de dois -> -8..+7."""
    v &= 0x0F
    if v & 0x08:          # bit de sinal (MSB) ligado
        return v - 16
    return v


def bin4(n):
    """Padrao de 4 bits (string) do valor n, truncado em complemento de dois."""
    return format(n & 0x0F, "04b")


def fatorial(n):
    """Fatorial de n (n >= 0). Retorna None se n for negativo."""
    if n < 0:
        return None
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r


def bin_para_valor(s):
    """Converte uma string binaria (ate 4 bits) para valor com sinal -8..+7."""
    u = int(s, 2) & 0x0F
    return para_com_sinal_4bits(u)


# Casos de teste (binarios) para o benchmark de multiplicacao.
# Cada tupla (A, B) e interpretada em complemento de dois de 4 bits.
CASOS_MULT = [
    ("1000", "1000"),
    ("1000", "111"),
    ("111",  "111"),
    ("1100", "1100"),
    ("101",  "11"),
    ("1101", "110"),
    ("10",   "1011"),
    ("1",    "111"),
    ("1010", "1110"),
    ("100",  "100"),
]


def calcular(op, a, b):
    """Executa a operacao e devolve (completo, bits, resultado, overflow).
       Para 'fat' usa apenas 'a'. Levanta ValueError para casos indefinidos."""
    if op == "add":
        completo = a + b
    elif op == "sub":
        completo = a - b
    elif op == "mul":
        completo = a * b
    elif op == "div":
        # DIVISAO POR ZERO: verificacao explicita ANTES de dividir.
        # Sem este teste, a / 0 lancaria ZeroDivisionError e travaria o programa.
        if b == 0:
            raise ValueError("divisao por zero")
        # divisao inteira truncando em direcao a zero (igual ao 'a / b' do C no ESP32).
        # Ex.: -7 / 2 = -3 (e nao -4, que seria o arredondamento p/ baixo do // do Python).
        q = abs(a) // abs(b)
        completo = -q if (a < 0) != (b < 0) else q
    elif op == "fat":
        completo = fatorial(a)
        if completo is None:
            raise ValueError("fatorial nao definido para numero negativo")
    else:
        raise ValueError("operacao desconhecida")

    overflow = (completo < -8 or completo > 7)
    bits = completo & 0x0F
    resultado = para_com_sinal_4bits(bits)
    return completo, bits, resultado, overflow


# ---------------------------------------------------------
# Leitura de operandos pelo teclado (decimal ou binario)
# ---------------------------------------------------------

def ler_operando(nome):
    """Le um operando -8..+7 pelo teclado, aceitando decimal ou binario de 4 bits.
       Repete ate a entrada ser valida."""
    while True:
        entrada = input(f"  Operando {nome} (decimal -8..7  ou  binario 4 bits, ex.: 1010): ").strip()

        if entrada == "":
            print("  >> Entrada vazia. Tente novamente.")
            continue

        # Modo binario: exatamente 4 caracteres 0/1
        if all(c in "01" for c in entrada) and len(entrada) == 4:
            u = int(entrada, 2)                 # 0..15
            valor = para_com_sinal_4bits(u)     # -8..7
            print(f"  >> {nome} = {entrada}b = {valor} (decimal)")
            return valor

        # Modo decimal (aceita negativos)
        try:
            valor = int(entrada, 10)
        except ValueError:
            print("  >> Formato invalido. Use um decimal (-8..7) ou 4 bits (0/1).")
            continue

        if valor < -8 or valor > 7:
            print("  >> Fora da faixa. Em 4 bits com sinal so cabe -8 a +7.")
            continue

        print(f"  >> {nome} = {valor} = {bin4(valor)}b")
        return valor


def ler_inteiro(msg, minimo=None, maximo=None):
    """Le um inteiro do teclado com faixa opcional [minimo, maximo]."""
    while True:
        try:
            v = int(input(msg).strip())
        except ValueError:
            print("  >> Digite um numero inteiro.")
            continue
        if minimo is not None and v < minimo:
            print(f"  >> Valor minimo: {minimo}.")
            continue
        if maximo is not None and v > maximo:
            print(f"  >> Valor maximo: {maximo}.")
            continue
        return v


# ---------------------------------------------------------
# Execucao de uma operacao e impressao do resultado
# ---------------------------------------------------------

NOMES_OP = {"add": "A + B", "sub": "A - B", "mul": "A * B", "div": "A / B", "fat": "A!"}


def executar(op):
    """op in {'add','sub','mul','fat'}. Le operandos, calcula e imprime resultado."""
    print()
    a = ler_operando("A")
    b = None if op == "fat" else ler_operando("B")

    try:
        completo, bits, resultado, overflow = calcular(op, a, b)
    except ValueError as e:
        print(f"\n  ERRO: {e}.\n")
        return

    if op == "fat":
        conta = f"{a}! = {completo}"
    else:
        simbolo = {"add": "+", "sub": "-", "mul": "*", "div": "/"}[op]
        conta = f"{a} {simbolo} {b} = {completo}"

    print("\n  --------- RESULTADO ---------")
    print(f"  Conta (valor real) : {conta}")
    print(f"  Bits (4 bits)      : {bin4(bits)}   [MSB=sinal ... LSB]")
    print(f"  Valor com sinal    : {resultado}")
    print(f"  Overflow           : {'SIM  (nao cabe em -8..+7)' if overflow else 'NAO'}")
    print("  -----------------------------\n")


# ---------------------------------------------------------
# BENCHMARK: mede o tempo de execucao de N testes
# ---------------------------------------------------------

def _medir_us(op, a, b):
    """Executa a operacao uma vez e devolve (completo, tempo_em_us)."""
    inicio = time.perf_counter_ns()
    completo, _bits, _res, _ovf = calcular(op, a, b)
    fim = time.perf_counter_ns()
    return completo, (fim - inicio) / 1000.0   # ns -> us


def tabela_tempos(op, a, b, n_testes):
    """Roda n_testes da operacao e imprime a tabela de tempos no terminal.
       Coluna 'N' = operando de referencia (a para fatorial; a para as demais)."""
    print(f"\n  Operacao: {NOMES_OP[op]}", end="")
    if op == "fat":
        print(f"   (N = {a})")
        n_ref = a
    else:
        print(f"   (A = {a}, B = {b})")
        n_ref = a

    print(f"  {n_testes} testes | tempo de execucao por teste\n")

    # Protecao: se a operacao for invalida (ex.: divisao por zero), avisa e sai
    # sem tentar cronometrar (evita ZeroDivisionError/ValueError no meio da tabela).
    try:
        calcular(op, a, b)
    except ValueError as e:
        print(f"  Operacao invalida: {e}.\n")
        return

    # Cabecalho no formato pedido
    print(f"  {'N':>3}  {'N Teste':>7}  {'Resultado':>10}  {'Tempo (us)':>11}")
    print("  " + "-" * 37)

    tempos = []
    resultado = None
    for i in range(1, n_testes + 1):
        resultado, t_us = _medir_us(op, a, b)
        tempos.append(t_us)
        print(f"  {n_ref:>3}  {i:>7}  {resultado:>10}  {t_us:>11.3f}")

    # Estatisticas
    media = sum(tempos) / len(tempos)
    print("  " + "-" * 37)
    print(f"  Resultado (valor real): {resultado}")
    print(f"  Tempo (us) -> min: {min(tempos):.3f}   "
          f"medio: {media:.3f}   max: {max(tempos):.3f}\n")


def tabela_casos_mult(repeticoes=1):
    """Roda os casos de teste fixos de multiplicacao (CASOS_MULT) e imprime a tabela
       com o tempo de execucao de cada teste. Se repeticoes>1, cronometra a media."""
    print("\n  Operacao: A * B  (multiplicacao) | casos de teste em binario (4 bits)")
    if repeticoes > 1:
        print(f"  {len(CASOS_MULT)} casos | tempo = media de {repeticoes} execucoes por caso\n")
    else:
        print(f"  {len(CASOS_MULT)} casos | 1 execucao por caso\n")

    cab = (f"  {'#':>2}  {'A(bin)':>6}  {'B(bin)':>6}  {'A':>3}  {'B':>3}  "
           f"{'Real':>5}  {'Bits':>5}  {'Result':>6}  {'OVF':>3}  {'Tempo(us)':>9}")
    print(cab)
    print("  " + "-" * (len(cab) - 2))

    tempos = []
    for i, (sa, sb) in enumerate(CASOS_MULT, start=1):
        a = bin_para_valor(sa)
        b = bin_para_valor(sb)

        # cronometra a multiplicacao (media de 'repeticoes' execucoes)
        inicio = time.perf_counter_ns()
        for _ in range(repeticoes):
            completo, bits, resultado, overflow = calcular("mul", a, b)
        fim = time.perf_counter_ns()
        t_us = (fim - inicio) / 1000.0 / repeticoes
        tempos.append(t_us)

        print(f"  {i:>2}  {sa:>6}  {sb:>6}  {a:>3}  {b:>3}  "
              f"{completo:>5}  {bin4(bits):>5}  {resultado:>6}  "
              f"{'SIM' if overflow else 'NAO':>3}  {t_us:>9.3f}")

    media = sum(tempos) / len(tempos)
    print("  " + "-" * (len(cab) - 2))
    print(f"  Tempo (us) -> min: {min(tempos):.3f}   "
          f"medio: {media:.3f}   max: {max(tempos):.3f}\n")


def benchmark():
    """Menu do modo benchmark: escolhe operacao, operandos, nº de testes e imprime tabela."""
    print("\n  === BENCHMARK (tempo de execucao) ===")
    print("  Escolha a operacao a cronometrar:")
    print("    1 - Soma (A+B)")
    print("    2 - Subtracao (A-B)")
    print("    3 - Multiplicacao (A*B)")
    print("    4 - Divisao (A/B)")
    print("    5 - Fatorial (A!)")
    print("    6 - TODAS (uma tabela por operacao)")
    print("    7 - Multiplicacao com a TABELA DE CASOS (binarios pre-definidos)")
    escolha = input("  Opcao: ").strip()

    mapa = {"1": "add", "2": "sub", "3": "mul", "4": "div", "5": "fat"}

    if escolha == "7":
        # Cada linha de CASOS_MULT e um caso de teste. Pergunta quantas execucoes
        # cronometrar por caso (para reduzir ruido; 1 = mede uma unica execucao).
        rep = ler_inteiro("  Execucoes por caso p/ media (1 = medir 1x): ",
                           minimo=1, maximo=100000)
        tabela_casos_mult(rep)
        return

    n_testes = ler_inteiro("  Numero de testes (ex.: 10): ", minimo=1, maximo=100000)

    if escolha == "5":
        # Fatorial: N pode passar de 7 (benchmark de tempo, sem trava de 4 bits)
        a = ler_inteiro("  N para o fatorial (0..12): ", minimo=0, maximo=12)
        tabela_tempos("fat", a, None, n_testes)

    elif escolha in ("1", "2", "3", "4"):
        print()
        a = ler_operando("A")
        b = ler_operando("B")
        tabela_tempos(mapa[escolha], a, b, n_testes)  # div por zero e tratada dentro

    elif escolha == "6":
        print()
        a = ler_operando("A")
        b = ler_operando("B")
        for op in ("add", "sub", "mul", "div"):
            tabela_tempos(op, a, b, n_testes)         # div: se B=0, avisa e pula
        # Para o fatorial usa A (se A<0, avisa e pula)
        if a < 0:
            print("  (Fatorial pulado: A negativo.)\n")
        else:
            tabela_tempos("fat", a, None, n_testes)
    else:
        print("  >> Opcao invalida.\n")


# ---------------------------------------------------------
# Menu principal (exibido no monitor via HDMI-VGA)
# ---------------------------------------------------------

def menu():
    print("=" * 45)
    print("   CALCULADORA 4 BITS - Raspberry Pi 3")
    print("   Complemento de dois (-8 a +7)")
    print("=" * 45)

    opcoes = {
        "1": ("add", "A + B  (soma)"),
        "2": ("sub", "A - B  (subtracao)"),
        "3": ("mul", "A * B  (multiplicacao)"),
        "4": ("div", "A / B  (divisao inteira)"),
        "5": ("fat", "A!     (fatorial)"),
    }

    while True:
        print("Escolha a operacao:")
        for k, (_, desc) in opcoes.items():
            print(f"  {k} - {desc}")
        print("  6 - Benchmark (tabela de tempos de execucao)")
        print("  0 - Sair")

        escolha = input("Opcao: ").strip()

        if escolha == "0":
            print("Encerrando. Ate a proxima!")
            break
        elif escolha == "6":
            benchmark()
        elif escolha in opcoes:
            executar(opcoes[escolha][0])
        else:
            print(">> Opcao invalida.\n")


if __name__ == "__main__":
    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado pelo usuario.")
