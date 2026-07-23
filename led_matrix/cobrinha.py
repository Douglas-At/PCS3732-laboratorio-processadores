#!/usr/bin/env python3
# =========================================
# COBRINHA (Snake) na matriz de LED 8x8
# Raspberry Pi 3 + RPi.GPIO
#
# Matriz 8x8 com dois 74HC595 em cascata (kit Freenove,
# exemplo 18_LEDMatrix):
#   DATA  (DS)    ... GPIO22
#   LATCH (ST_CP) ... GPIO27
#   CLOCK (SH_CP) ... GPIO17
# Multiplexacao por coluna: para cada coluna manda-se o byte
# das linhas acesas e depois a coluna ativa (ativo-baixo).
#
# 4 botoes de direcao (pull-up interno, pressionado = 0):
#   CIMA=GPIO20  BAIXO=GPIO21  ESQ=GPIO26  DIR=GPIO16
#
# A comida pisca para se distinguir da cobra (matriz de 1 cor).
# Bateu na parede (ou em si mesma) -> pisca e recomeca.
#
# Uso:  sudo python3 cobrinha.py
#       python3 cobrinha.py --test    (logica pura, sem hardware)
# =========================================

import argparse
import random
import time

# --- pinos da matriz (74HC595) ---
DATA_PIN = 22
LATCH_PIN = 27
CLOCK_PIN = 17

# --- botoes de direcao (BCM) --- pressionado = 0 (pull-up)
BTN = {20: (-1, 0), 21: (1, 0), 26: (0, -1), 16: (0, 1)}  # cima, baixo, esq, dir

N = 8
WRAP = True   # ponytail: parede atravessa (mais jogavel em 8x8). False = morre na parede.


class Cobra:
    """Estado e regras do jogo, sem nenhum acesso a hardware (testavel)."""

    def __init__(self, wrap=WRAP, rng=None):
        self.wrap = wrap
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.snake = [(4, 4), (4, 3), (4, 2)]   # cabeca primeiro, andando p/ direita
        self.dir = (0, 1)
        self.pending = (0, 1)
        self.viva = True
        self._por_comida()

    def virar(self, d):
        # Ignora reversao de 180 g (cobra nao entra em si mesma de imediato).
        if (d[0] + self.dir[0], d[1] + self.dir[1]) != (0, 0):
            self.pending = d

    def passo(self):
        if not self.viva:
            return
        self.dir = self.pending
        r, c = self.snake[0]
        nr, nc = r + self.dir[0], c + self.dir[1]
        if self.wrap:
            nr %= N
            nc %= N
        elif not (0 <= nr < N and 0 <= nc < N):
            self.viva = False
            return
        cabeca = (nr, nc)
        cresce = (cabeca == self.food)
        # A cauda vai sair do lugar, entao so colide com o corpo sem a cauda
        # (a menos que va crescer neste passo).
        corpo = self.snake if cresce else self.snake[:-1]
        if cabeca in corpo:
            self.viva = False
            return
        self.snake.insert(0, cabeca)
        if cresce:
            self._por_comida()
        else:
            self.snake.pop()

    def _por_comida(self):
        livres = [(r, c) for r in range(N) for c in range(N) if (r, c) not in self.snake]
        self.food = self.rng.choice(livres) if livres else None  # None = venceu (tabuleiro cheio)


def render(pixels):
    """Conjunto de (linha, coluna) -> lista de 8 bytes de linha, um por coluna.
    Linha 0 = bit 0x80 (topo)."""
    cols = []
    for c in range(N):
        b = 0
        for r in range(N):
            if (r, c) in pixels:
                b |= (0x80 >> r)
        cols.append(b)
    return cols


# ---------------- hardware (so roda no Raspberry) ----------------

def _shift_out(GPIO, val):
    """Empurra 8 bits MSB primeiro no 74HC595 (igual ao LEDMatrix.py do kit)."""
    for i in range(8):
        GPIO.output(CLOCK_PIN, 0)
        GPIO.output(DATA_PIN, 1 if (val << i) & 0x80 else 0)
        GPIO.output(CLOCK_PIN, 1)


def _draw(GPIO, cols):
    """Uma varredura completa das 8 colunas (multiplexacao)."""
    x = 0x80
    for c in range(N):
        GPIO.output(LATCH_PIN, 0)
        _shift_out(GPIO, cols[c])          # linhas acesas desta coluna
        _shift_out(GPIO, ~x & 0xFF)        # coluna ativa (ativo-baixo)
        GPIO.output(LATCH_PIN, 1)
        x >>= 1


def _mostrar(GPIO, pixels, seg):
    """Mantem 'pixels' aceso por 'seg' segundos, remultiplexando."""
    cols = render(pixels)
    fim = time.time() + seg
    while time.time() < fim:
        _draw(GPIO, cols)


def _tick(n_corpo):
    """Passo do jogo acelera um pouco conforme a cobra cresce."""
    return max(0.15, 0.4 - 0.02 * (n_corpo - 3))


def main():
    ap = argparse.ArgumentParser(description="Cobrinha na matriz de LED 8x8")
    ap.add_argument("--test", action="store_true", help="testa a logica sem hardware")
    args = ap.parse_args()
    if args.test:
        demo()
        return

    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for p in (DATA_PIN, LATCH_PIN, CLOCK_PIN):
        GPIO.setup(p, GPIO.OUT)
    for p in BTN:
        GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    jogo = Cobra()
    proximo = time.time() + _tick(len(jogo.snake))
    pisca = time.time() + 0.15
    comida_on = True
    print("\n== Cobrinha (Ctrl+C para sair) ==")
    try:
        while True:
            agora = time.time()

            for pino, d in BTN.items():
                if GPIO.input(pino) == 0:
                    jogo.virar(d)

            if agora >= pisca:
                comida_on = not comida_on
                pisca = agora + 0.15

            if agora >= proximo:
                jogo.passo()
                if not jogo.viva:
                    for _ in range(3):
                        _mostrar(GPIO, set(jogo.snake), 0.2)
                        _mostrar(GPIO, set(), 0.2)
                    jogo.reset()
                elif jogo.food is None:      # tabuleiro cheio = venceu
                    _mostrar(GPIO, set(jogo.snake), 1.5)
                    jogo.reset()
                proximo = agora + _tick(len(jogo.snake))

            pixels = set(jogo.snake)
            if comida_on and jogo.food is not None:
                pixels.add(jogo.food)
            _draw(GPIO, render(pixels))
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        _mostrar(GPIO, set(), 0.02)   # apaga
        GPIO.cleanup()


def demo():
    """Auto-teste da logica: python3 cobrinha.py --test"""
    # render: um pixel aceso no topo-esquerda -> coluna 0, bit 0x80.
    assert render({(0, 0)})[0] == 0x80
    assert render({(7, 0)})[0] == 0x01
    assert render(set()) == [0] * 8

    g = Cobra(wrap=False, rng=random.Random(1))
    assert len(g.snake) == 3
    cab = g.snake[0]
    g.passo()                                   # anda p/ direita
    assert g.snake[0] == (cab[0], cab[1] + 1)
    assert len(g.snake) == 3                     # nao cresceu

    # Reversao ignorada: andando p/ direita, mandar esquerda nao inverte.
    antes = g.snake[0]
    g.virar((0, -1))
    g.passo()
    assert g.snake[0] == (antes[0], antes[1] + 1)

    # Comer cresce e nao remove a cauda.
    g2 = Cobra(wrap=True, rng=random.Random(2))
    g2.food = (g2.snake[0][0], g2.snake[0][1] + 1)
    n0 = len(g2.snake)
    g2.passo()
    assert len(g2.snake) == n0 + 1

    # Parede mata quando WRAP=False.
    g3 = Cobra(wrap=False, rng=random.Random(3))
    g3.snake = [(0, 4), (1, 4), (2, 4)]
    g3.dir = g3.pending = (-1, 0)                # sobe direto pra fora
    g3.passo()
    assert not g3.viva

    # WRAP=True atravessa a parede, continua viva.
    g4 = Cobra(wrap=True, rng=random.Random(4))
    g4.snake = [(0, 4), (1, 4), (2, 4)]
    g4.dir = g4.pending = (-1, 0)
    g4.passo()
    assert g4.viva and g4.snake[0] == (7, 4)

    # Colisao com o proprio corpo mata: cabeca (4,4) vai p/ (4,5), que e corpo do meio
    # (nao a cauda, que essa seria uma casa livre no mesmo passo).
    g5 = Cobra(wrap=True, rng=random.Random(5))
    g5.snake = [(4, 4), (3, 4), (3, 5), (4, 5), (5, 5)]
    g5.dir = g5.pending = (0, 1)
    g5.food = (0, 0)
    g5.passo()
    assert not g5.viva

    print("demo OK: render, movimento, reversao, comer, parede e auto-colisao")


if __name__ == "__main__":
    main()
