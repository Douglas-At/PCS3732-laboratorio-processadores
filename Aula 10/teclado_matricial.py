#!/usr/bin/env python3
# =========================================
# COMPONENTE - TECLADO MATRICIAL 4x3
# Raspberry Pi 3 + RPi.GPIO
#
# 4 linhas (saidas) x 3 colunas (entradas c/ pull-up).
# Varredura: aciona uma linha em nivel BAIXO por vez e le
# as colunas; a coluna que ficar em 0 marca a tecla premida.
#
# Ligacao (BCM):
#   Linhas (OUT) : GPIO 5, 6, 13, 19
#   Colunas (IN) : GPIO 12, 16, 20   (pull-up interno)
#
# Uso:  sudo python3 teclado_matricial.py
#       python3 teclado_matricial.py --test   (roda no PC)
# =========================================

import argparse
import time

ROWS = [5, 6, 13, 19]
COLS = [12, 16, 20]

# ponytail: 4x3 conforme pedido. Para 4x4 basta acrescentar a coluna
# extra em COLS e a coluna de teclas ('A','B','C','D') em KEYS.
KEYS = [
    ["1", "2", "3"],
    ["4", "5", "6"],
    ["7", "8", "9"],
    ["*", "0", "#"],
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
    # Todas as teclas sao unicas (nenhuma posicao repetida).
    todas = [k for linha in KEYS for k in linha]
    assert len(set(todas)) == len(todas), "teclas duplicadas na matriz"
    print("demo OK: mapa 4x3 consistente (0-9, *, #).")


def main():
    ap = argparse.ArgumentParser(description="Teste do teclado matricial 4x3")
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

    print("\n== Teclado 4x3 (Ctrl+C para sair) ==")
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
