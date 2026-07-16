#!/usr/bin/env python3
# =========================================
# ATIVIDADE 1 - CONTROLE DE LED POR PWM
# Raspberry Pi 3 + RPi.GPIO (PWM de software)
#
# LED no GPIO17 com resistor de 220-330 ohm
# em serie para o GND.
#
# Uso:  sudo python3 led_pwm.py
# =========================================

import argparse
import time

import RPi.GPIO as GPIO

LED_PIN = 17

# Varredura da atividade: mesma intensidade (50%), frequencias diferentes.
FREQUENCIAS = [1, 5, 50, 100, 500, 1_000, 10_000]


def aplicar(pwm, freq, pct):
    """Aplica frequencia (Hz) e duty (%) no LED."""
    if freq > 0:
        pwm.ChangeFrequency(freq)
    pwm.ChangeDutyCycle(pct)


def varrer_frequencias(pwm, segundos):
    print("\n== Varredura de frequencia (duty fixo em 50%) ==")
    print(" Frequencia | Duty (%) | Observacao visual")
    print(" " + "-" * 52)
    for f in FREQUENCIAS:
        aplicar(pwm, f, 50)
        nota = "pisca visivel" if f <= 20 else "aparenta brilho continuo"
        print(f" {f:>7} Hz |       50 | {nota}")
        time.sleep(segundos)


def varrer_duty(pwm, freq):
    print(f"\n== Varredura de intensidade (fade) a {freq} Hz ==")
    print(" Duty (%)")
    print(" " + "-" * 9)
    for pct in range(0, 101, 10):
        aplicar(pwm, freq, pct)
        print(f" {pct:>8}")
        time.sleep(0.3)
    for pct in range(100, -1, -10):
        aplicar(pwm, freq, pct)
        time.sleep(0.3)


def main():
    ap = argparse.ArgumentParser(description="Controle de LED por PWM (RPi.GPIO)")
    ap.add_argument("--freq", type=int, help="testa uma unica frequencia (Hz)")
    ap.add_argument("--duty", type=float, default=50, help="duty em %% (padrao 50)")
    ap.add_argument("--seg", type=float, default=3, help="segundos por frequencia na varredura")
    args = ap.parse_args()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(LED_PIN, GPIO.OUT)

    pwm = GPIO.PWM(LED_PIN, FREQUENCIAS[0])
    pwm.start(0)

    try:
        if args.freq:
            aplicar(pwm, args.freq, args.duty)
            print(f"LED -> freq={args.freq} Hz  duty={args.duty}%")
            print("Ctrl+C para sair.")
            while True:
                time.sleep(1)
        else:
            varrer_frequencias(pwm, args.seg)
            varrer_duty(pwm, 1_000)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        pwm.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
