#!/usr/bin/env python3
# =========================================
# COMPONENTE - TECLADO MATRICIAL 4x4
# Raspberry Pi 3 + RPi.GPIO
#
# 4 linhas (saidas) x 4 colunas (entradas c/ pull-up).
# Varredura: aciona uma linha em nivel BAIXO por vez e le
# as colunas; a coluna que ficar em 0 marca a tecla premida.
#
# Ligacao (BCM) - ordem dos 8 pinos do conector do teclado:
#   16, 20, 21, 26, 19, 13, 6, 5
#   Linhas (OUT) : GPIO 16, 20, 21, 26   (pinos 1..4 do modulo)
#   Colunas (IN) : GPIO 19, 13, 6, 5     (pinos 5..8, pull-up interno)
#
# Uso:  sudo python3 teclado_matricial.py
#       python3 teclado_matricial.py --test   (roda no PC)
# =========================================

import argparse
import time

# Ordem do conector do teclado: 16,20,21,26,19,13,6,5
ROWS = [16, 20, 21, 26]
COLS = [19, 13, 6, 5]

KEYS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]

DEBOUNCE_S = 0.03


def tecla_em(r, c):
    """Retorna o caractere da posicao (linha r, coluna c). Logica pura."""
    return KEYS[r][c]


def ler_tecla(GPIO):
    """Varre a matriz uma vez. Retorna o char premido ou None."""
    for r, rp in enumerate(ROWS):
        GPIO.output(rp, GPIO.LOW)
        for c, cp in enumerate(COLS):
            if GPIO.input(cp) == GPIO.LOW:
                GPIO.output(rp, GPIO.HIGH)
                return tecla_em(r, c)
        GPIO.output(rp, GPIO.HIGH)
    return None


def demo():
    """Auto-teste sem hardware: python3 teclado_matricial.py --test"""
    assert len(KEYS) == len(ROWS), "uma lista de teclas por linha"
    assert all(len(linha) == len(COLS) for linha in KEYS), "uma tecla por coluna"
    assert tecla_em(0, 0) == "1" and tecla_em(3, 2) == "#"
    assert tecla_em(3, 0) == "*" and tecla_em(3, 1) == "0"
    assert tecla_em(0, 3) == "A" and tecla_em(3, 3) == "D"
    # Todas as teclas sao unicas (nenhuma posicao repetida).
    todas = [k for linha in KEYS for k in linha]
    assert len(set(todas)) == len(todas), "teclas duplicadas na matriz"
    assert len(todas) == 16, "teclado 4x4 tem 16 teclas"
    print("demo OK: mapa 4x4 consistente (0-9, *, #, A-D).")


def main():
    ap = argparse.ArgumentParser(description="Teste do teclado matricial 4x4")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for rp in ROWS:
        GPIO.setup(rp, GPIO.OUT, initial=GPIO.HIGH)
    for cp in COLS:
        GPIO.setup(cp, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print("\n== Teclado 4x4 (Ctrl+C para sair) ==")
    print(" pressione teclas...")
    try:
        anterior = None
        while True:
            tecla = ler_tecla(GPIO)
            if tecla and tecla != anterior:
                print(f" tecla: {tecla}")
                time.sleep(DEBOUNCE_S)
            anterior = tecla
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
