#!/usr/bin/env python3
# =========================================
# EXTRA - SIRENE DE AMBULANCIA
# Raspberry Pi 3 + RPi.GPIO (PWM de software)
#
# Buzzer passivo no GPIO4, o outro terminal no GND.
#
# Dois modos:
#   two-tone (padrao) .. alterna 2 tons fixos (sirene europeia)
#   wail (--wail) ...... varre a frequencia de subida e descida
#
# Uso:  sudo python3 buzzer_ambulancia.py
#       sudo python3 buzzer_ambulancia.py --wail
#       python3 buzzer_ambulancia.py --test    (roda no PC, sem hardware)
# =========================================

import argparse
import time

BUZZER_PIN = 4
DUTY_50 = 50

TOM_ALTO = 960          # Hz
TOM_BAIXO = 770
TROCA_S = 0.6           # duracao de cada tom no two-tone

WAIL_MIN = 600          # Hz
WAIL_MAX = 1400
WAIL_PASSOS = 40        # degraus por subida ou descida
WAIL_PERIODO_S = 2.0    # ciclo completo (sobe + desce)


def freq_wail(passo):
    """Frequencia (Hz) do degrau n da sirene wail: sobe e desce em rampa triangular."""
    n = passo % (2 * WAIL_PASSOS)
    if n >= WAIL_PASSOS:                     # segunda metade: desce
        n = 2 * WAIL_PASSOS - n
    return WAIL_MIN + (WAIL_MAX - WAIL_MIN) * n / WAIL_PASSOS


def two_tone(pwm):
    print("\n== Sirene two-tone (Ctrl+C para sair) ==")
    print(f" alterna {TOM_ALTO} Hz / {TOM_BAIXO} Hz a cada {TROCA_S} s")
    pwm.ChangeDutyCycle(DUTY_50)
    while True:
        for tom in (TOM_ALTO, TOM_BAIXO):
            pwm.ChangeFrequency(tom)
            time.sleep(TROCA_S)


def wail(pwm):
    print("\n== Sirene wail (Ctrl+C para sair) ==")
    print(f" varre {WAIL_MIN}-{WAIL_MAX} Hz em {WAIL_PERIODO_S} s por ciclo")
    pwm.ChangeDutyCycle(DUTY_50)
    espera = WAIL_PERIODO_S / (2 * WAIL_PASSOS)
    passo = 0
    while True:
        pwm.ChangeFrequency(freq_wail(passo))
        time.sleep(espera)
        passo += 1


def demo():
    """Auto-teste sem hardware: python3 buzzer_ambulancia.py --test"""
    assert freq_wail(0) == WAIL_MIN
    assert freq_wail(WAIL_PASSOS) == WAIL_MAX, "topo da rampa"
    assert freq_wail(2 * WAIL_PASSOS) == WAIL_MIN, "fim do ciclo volta ao inicio"
    assert freq_wail(2 * WAIL_PASSOS + 1) == freq_wail(1), "rampa e periodica"

    # A rampa nunca sai da faixa e e simetrica em torno do topo.
    for n in range(4 * WAIL_PASSOS):
        assert WAIL_MIN <= freq_wail(n) <= WAIL_MAX, f"passo {n} fora da faixa"
        assert freq_wail(WAIL_PASSOS - 1) == freq_wail(WAIL_PASSOS + 1)

    print("demo OK: rampa da sirene periodica, simetrica e dentro da faixa.")


def main():
    ap = argparse.ArgumentParser(description="Sirene de ambulancia no buzzer (RPi.GPIO)")
    ap.add_argument("--wail", action="store_true", help="modo varredura em vez de dois tons")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)

    pwm = GPIO.PWM(BUZZER_PIN, TOM_BAIXO)
    pwm.start(0)

    try:
        wail(pwm) if args.wail else two_tone(pwm)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        pwm.ChangeDutyCycle(0)
        pwm.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
