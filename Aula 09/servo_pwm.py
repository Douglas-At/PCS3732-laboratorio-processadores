#!/usr/bin/env python3
# =========================================
# ATIVIDADE 2 - CONTROLE DE SERVOMOTOR POR PWM
# Raspberry Pi 3 + RPi.GPIO (PWM de software)
#
# Servo no GPIO18 (sinal). Alimentacao em 5V
# (pino 2 ou 4) com GND COMUM com o Raspberry.
# Nunca alimentar o servo pelo 3,3V.
#
# Mesma convencao do servo_webserver.ino (Aula 05):
# periodo de 20 ms (50 Hz), pulso de 1,0 ms (0 graus)
# a 2,0 ms (180 graus), 1,5 ms = 90 graus.
#
# No RPi.GPIO o pulso e expresso como duty do periodo
# de 20 ms:  duty% = pulso_us / 20000 * 100.
#
# Uso:  sudo python3 servo_pwm.py
# =========================================

import argparse
import time

import RPi.GPIO as GPIO

SERVO_PIN = 18

PERIODO_US = 20_000    # 50 Hz

PULSO_MIN_US = 1000    # 0 graus
PULSO_MAX_US = 2000    # 180 graus

SEQUENCIA = [0, 45, 90, 135, 180, 90]


def angulo_para_pulso(ang):
    """Converte angulo (0-180) em largura de pulso (us)."""
    ang = max(0, min(180, ang))
    return PULSO_MIN_US + (PULSO_MAX_US - PULSO_MIN_US) * ang / 180.0


def pulso_para_duty(pulso_us):
    """Converte largura de pulso (us) no duty (%) do periodo de 20 ms."""
    return pulso_us / PERIODO_US * 100.0


def mover(pwm, ang):
    pulso = angulo_para_pulso(ang)
    pwm.ChangeDutyCycle(pulso_para_duty(pulso))
    return pulso


def main():
    ap = argparse.ArgumentParser(description="Controle de servomotor por PWM (RPi.GPIO)")
    ap.add_argument("--ang", type=int, help="posiciona em um unico angulo e sai")
    ap.add_argument("--seg", type=float, default=1.0, help="segundos por posicao")
    args = ap.parse_args()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)

    try:
        alvos = [args.ang] if args.ang is not None else SEQUENCIA

        print("\n== Posicionamento do servo (50 Hz, pulso variavel) ==")
        print(" Angulo | Pulso (us) | Duty equivalente (%)")
        print(" " + "-" * 46)
        for ang in alvos:
            pulso = mover(pwm, ang)
            print(f" {ang:>5} g | {pulso:>10.0f} | {pulso_para_duty(pulso):>19.2f}")
            time.sleep(args.seg)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        # Duty 0 desliga o trem de pulsos: sem isso o servo fica zumbindo e esquentando.
        pwm.ChangeDutyCycle(0)
        time.sleep(0.05)
        pwm.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
