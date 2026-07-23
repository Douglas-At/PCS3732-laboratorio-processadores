#!/usr/bin/env python3
# =========================================
# COMPONENTE - SENSOR DE TRAVA (botao/ferrolho)
# Raspberry Pi 3 + RPi.GPIO
#
# Botao simulando o ferrolho no GPIO27 (pull-up interno):
# em repouso o pino le 1; com o ferrolho na posicao
# TRANCADA o contato fecha e puxa o pino para 0.
# (mesmo padrao do SW do joystick - Aula 09).
#
# Assim o programa nunca "supoe" que trancou: ele confere
# fisicamente pelo sensor.
#
# Uso:  sudo python3 sensor_trava.py
#       python3 sensor_trava.py --test   (roda no PC)
# =========================================

import argparse
import time

SENSOR_PIN = 27

# Nivel logico do pino quando o ferrolho esta TRANCADO.
NIVEL_TRANCADO = 0


def esta_trancada(nivel_lido):
    """Interpreta o nivel do pino: True se o ferrolho esta trancado.

    Logica pura (separada da GPIO) para poder testar sem hardware.
    """
    return nivel_lido == NIVEL_TRANCADO


class Sensor:
    def __init__(self, pin=SENSOR_PIN):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def trancada(self):
        return esta_trancada(self.GPIO.input(self.pin))

    def fechar(self):
        self.GPIO.cleanup()


def demo():
    """Auto-teste sem hardware: python3 sensor_trava.py --test"""
    assert esta_trancada(0) is True, "pino em 0 = ferrolho trancado"
    assert esta_trancada(1) is False, "pino em 1 = ferrolho recolhido"
    print("demo OK: interpretacao do sensor (0=trancado, 1=aberto).")


def main():
    ap = argparse.ArgumentParser(description="Sensor de trava (RPi.GPIO)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    sensor = Sensor()
    print("\n== Sensor de trava (Ctrl+C para sair) ==")
    print(" mova o ferrolho/botao para ver as transicoes...")
    try:
        anterior = None
        while True:
            estado = sensor.trancada()
            if estado != anterior:
                print(" TRANCADA" if estado else " ABERTA")
            anterior = estado
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        sensor.fechar()


if __name__ == "__main__":
    main()
