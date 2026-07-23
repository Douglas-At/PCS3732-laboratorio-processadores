#!/usr/bin/env python3
# =========================================
# COMPONENTE - TECLADO MATRICIAL 4x4
# Raspberry Pi 3 - usa o modulo Keypad.py da Freenove (gpiozero)
#
# Baseado no exemplo oficial 21_MatrixKeypad da Freenove:
# a varredura (aciona colunas, le linhas) fica no Keypad.py;
# aqui so definimos o mapa de teclas e os pinos.
#
# Ligacao (BCM):
#   Linhas (rowsPins) : GPIO 16, 20, 21, 26
#   Colunas (colsPins): GPIO 19, 13, 6, 5
#
# Uso:  sudo python3 teclado_matricial.py
#       python3 teclado_matricial.py --test   (roda no PC, so o mapa)
# =========================================

import argparse
import time

ROWS = [16, 20, 21, 26]   # rowsPins
COLS = [19, 13, 6, 5]      # colsPins

# Mapa achatado (linha a linha), como o Keypad.py da Freenove espera.
KEYS = [
    "1", "2", "3", "A",
    "4", "5", "6", "B",
    "7", "8", "9", "C",
    "*", "0", "#", "D",
]


def tecla_em(r, c):
    """Caractere na linha r, coluna c. Logica pura (testavel no PC)."""
    return KEYS[r * len(COLS) + c]


def novo_teclado():
    """Cria o objeto Keypad da Freenove ja configurado. Import tardio (so no RPi)."""
    import Keypad
    kp = Keypad.Keypad(KEYS, ROWS, COLS, len(ROWS), len(COLS))
    kp.setDebounceTime(50)
    return kp


def ler_tecla(kp):
    """Retorna o char premido ou None (compat. com a integracao da fechadura)."""
    k = kp.getKey()
    return None if k == kp.NULL else k


def demo():
    """Auto-teste sem hardware: python3 teclado_matricial.py --test"""
    assert len(KEYS) == len(ROWS) * len(COLS) == 16, "teclado 4x4 tem 16 teclas"
    assert tecla_em(0, 0) == "1" and tecla_em(0, 3) == "A"
    assert tecla_em(2, 0) == "7" and tecla_em(3, 0) == "*"
    assert tecla_em(3, 2) == "#" and tecla_em(3, 3) == "D"
    assert len(set(KEYS)) == len(KEYS), "teclas duplicadas na matriz"
    print("demo OK: mapa 4x4 consistente (0-9, *, #, A-D).")


def main():
    ap = argparse.ArgumentParser(description="Teste do teclado matricial 4x4 (Freenove Keypad)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    kp = novo_teclado()
    print("\n== Teclado 4x4 (Ctrl+C para sair) ==")
    print(" pressione teclas...")
    try:
        while True:
            tecla = ler_tecla(kp)
            if tecla:
                print(f" tecla: {tecla}")
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nInterrompido.")


if __name__ == "__main__":
    main()
