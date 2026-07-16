#!/usr/bin/env python3
# =========================================
# ATIVIDADE 3 - CONTROLE DO BUZZER (PASSIVO)
# Raspberry Pi 3 + RPi.GPIO (PWM de software)
#
# Buzzer passivo no GPIO4, o outro terminal no GND.
#
# Buzzer PASSIVO nao tem oscilador interno: a
# frequencia do PWM E a nota tocada. O duty fica
# em 50% (onda quadrada simetrica, maior volume);
# quem muda o tom e a frequencia, nao o duty.
#
# Uso:  sudo python3 buzzer_pwm.py
# =========================================

import argparse
import time

import RPi.GPIO as GPIO

BUZZER_PIN = 4
DUTY_50 = 50             # 50% (unidade do RPi.GPIO e porcento)

ESCALA = [("La4", 440), ("Do5", 523), ("Mi5", 659), ("La5", 880)]


def tocar(pwm, freq, ms):
    """Emite um tom de freq Hz por ms milissegundos."""
    pwm.ChangeFrequency(freq)
    pwm.ChangeDutyCycle(DUTY_50)
    time.sleep(ms / 1000.0)
    pwm.ChangeDutyCycle(0)


def main():
    ap = argparse.ArgumentParser(description="Controle de buzzer passivo por PWM (RPi.GPIO)")
    ap.add_argument("--freq", type=int, help="toca um unico tom (Hz)")
    ap.add_argument("--ms", type=int, default=300, help="duracao em ms (padrao 300)")
    args = ap.parse_args()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)

    pwm = GPIO.PWM(BUZZER_PIN, ESCALA[0][1])
    pwm.start(0)

    try:
        if args.freq:
            print(f"Buzzer -> {args.freq} Hz por {args.ms} ms")
            tocar(pwm, args.freq, args.ms)
            return

        print("\n== Escala no buzzer passivo (duty fixo em 50%) ==")
        print(" Nota | Freq (Hz) | Duracao (ms)")
        print(" " + "-" * 36)
        for nome, freq in ESCALA:
            print(f" {nome:>4} | {freq:>9} | {args.ms:>12}")
            tocar(pwm, freq, args.ms)
            time.sleep(0.1)

        # Bipes curtos, como os usados no tick do metronomo.
        print("\n== Bipe curto (30 ms) - forma do tick do metronomo ==")
        for freq in (1_500, 1_000, 1_000, 1_000):
            print(f" bipe {freq} Hz / 30 ms")
            tocar(pwm, freq, 30)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        pwm.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
