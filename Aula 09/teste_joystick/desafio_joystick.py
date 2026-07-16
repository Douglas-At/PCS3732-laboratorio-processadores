#!/usr/bin/env python3
# =========================================
# DESAFIO - TESTE DO JOYSTICK (botao SW)
# Raspberry Pi 3 + RPi.GPIO
#
# Joystick Freenove:
#   SW  ... GPIO7   (clique do eixo - DIGITAL)
#   GND ... GND
#   +5V ... 5V
#   VRx / VRy ... NAO conectados aqui (ver nota abaixo)
#
# O SW e um botao comum: pull-up interno deixa o pino
# em 1 em repouso e o clique puxa para 0.
#
# Os eixos VRx/VRy sao ANALOGICOS e o Raspberry Pi nao
# tem ADC: precisam do ADS7830 (I2C) do kit Freenove.
# Este script cobre so o que a GPIO7 sozinha permite.
#
# Uso:  sudo python3 desafio_joystick.py
#       sudo python3 desafio_joystick.py --polling
# =========================================

import argparse
import time

SW_PIN = 7
DEBOUNCE_MS = 200


def por_evento(GPIO):
    """Callback na borda de descida: o clique avisa, o laco so espera."""
    cliques = [0]

    def clicou(canal):
        cliques[0] += 1
        print(f" clique #{cliques[0]}  (GPIO{canal} -> 0)")

    GPIO.add_event_detect(SW_PIN, GPIO.FALLING, callback=clicou, bouncetime=DEBOUNCE_MS)
    print("\n== Joystick por evento (Ctrl+C para sair) ==")
    print(" clique o joystick para baixo...")
    while True:
        time.sleep(1)


def por_polling(GPIO):
    """Le o pino em laco: mostra o estado bruto, util para ver o pull-up agindo."""
    print("\n== Joystick por polling (Ctrl+C para sair) ==")
    print(" Estado | Leitura")
    print(" " + "-" * 26)
    anterior = None
    while True:
        nivel = GPIO.input(SW_PIN)
        if nivel != anterior:
            estado = "solto     " if nivel else "PRESSIONADO"
            print(f" {estado} | GPIO{SW_PIN} = {nivel}")
            anterior = nivel
            time.sleep(DEBOUNCE_MS / 1000.0)
        time.sleep(0.01)


def main():
    ap = argparse.ArgumentParser(description="Teste do botao do joystick (RPi.GPIO)")
    ap.add_argument("--polling", action="store_true", help="le em laco em vez de usar callback")
    args = ap.parse_args()

    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    try:
        por_polling(GPIO) if args.polling else por_evento(GPIO)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
