#!/usr/bin/env python3
# =========================================
# COMPONENTE - SERVO DA FECHADURA (ferrolho)
# Raspberry Pi 3 + RPi.GPIO (PWM de software)
#
# Mesma convencao validada na Aula 09 (servo_pwm.py):
# periodo 20 ms (50 Hz), pulso 1000 us (0 g) a 2000 us
# (180 g). Faixa util do atuador nesta bancada: 20-160 g.
# Ferrolho: TRANCADO = 20 g, DESTRANCADO = 160 g.
#
# Servo no GPIO18. Alimentacao 5V com GND COMUM ao RPi.
# Nunca alimentar o servo pelo 3,3V.
#
# Uso:  sudo python3 servo_fechadura.py --pos abrir
#       sudo python3 servo_fechadura.py --pos fechar
#       python3 servo_fechadura.py --test    (roda no PC)
# =========================================

import argparse
import time

SERVO_PIN = 18
PERIODO_US = 20_000
PULSO_MIN_US = 1000    # 0 graus
PULSO_MAX_US = 2000    # 180 graus

ANG_TRANCADO = 20
ANG_DESTRANCADO = 160
# ponytail: se o ferrolho nao encaixar, ajustar estes dois angulos
# (calibracao mecanica) - o mapa us<->graus abaixo nao muda.


def angulo_para_pulso(ang):
    """Converte angulo (0-180) em largura de pulso (us)."""
    ang = max(0, min(180, ang))
    return PULSO_MIN_US + (PULSO_MAX_US - PULSO_MIN_US) * ang / 180.0


def pulso_para_duty(pulso_us):
    """Converte largura de pulso (us) no duty (%) do periodo de 20 ms."""
    return pulso_us / PERIODO_US * 100.0


class Servo:
    def __init__(self, pin=SERVO_PIN):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, 50)
        self.pwm.start(0)

    def _ir(self, ang):
        self.pwm.ChangeDutyCycle(pulso_para_duty(angulo_para_pulso(ang)))
        time.sleep(0.5)
        # Duty 0 solta o trem de pulsos: sem isso o servo fica zumbindo.
        self.pwm.ChangeDutyCycle(0)

    def trancar(self):
        self._ir(ANG_TRANCADO)

    def destrancar(self):
        self._ir(ANG_DESTRANCADO)

    def fechar(self):
        self.pwm.ChangeDutyCycle(0)
        self.pwm.stop()
        self.GPIO.cleanup()


def demo():
    """Auto-teste sem hardware: python3 servo_fechadura.py --test"""
    assert angulo_para_pulso(0) == 1000
    assert angulo_para_pulso(180) == 2000
    assert angulo_para_pulso(90) == 1500
    # As posicoes da trava respeitam a faixa util 20-160 g e o pulso 1000-2000 us.
    for ang in (ANG_TRANCADO, ANG_DESTRANCADO):
        assert 20 <= ang <= 160, f"angulo {ang} fora da faixa util"
        assert 1000 <= angulo_para_pulso(ang) <= 2000
    assert ANG_TRANCADO != ANG_DESTRANCADO, "trancado e destrancado distintos"
    print(f"demo OK: trancar={angulo_para_pulso(ANG_TRANCADO):.0f}us "
          f"destrancar={angulo_para_pulso(ANG_DESTRANCADO):.0f}us")


def main():
    ap = argparse.ArgumentParser(description="Servo da fechadura (RPi.GPIO)")
    ap.add_argument("--pos", choices=["abrir", "fechar"], help="destranca ou tranca")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    servo = Servo()
    try:
        if args.pos == "abrir":
            print(f"Destrancando ({ANG_DESTRANCADO} g)...")
            servo.destrancar()
        else:
            print(f"Trancando ({ANG_TRANCADO} g)...")
            servo.trancar()
    finally:
        servo.fechar()


if __name__ == "__main__":
    main()
