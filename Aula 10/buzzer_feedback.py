#!/usr/bin/env python3
# =========================================
# COMPONENTE - FEEDBACK SONORO (buzzer passivo)
# Raspberry Pi 3 + RPi.GPIO (PWM de software)
#
# Buzzer passivo no GPIO4, outro terminal no GND.
# Buzzer PASSIVO: a frequencia do PWM E a nota; duty 50%.
# (mesma base validada na Aula 09 - buzzer_pwm.py).
#
# Padroes de feedback da fechadura:
#   ok    -> 1 tom agudo curto  (acesso liberado)
#   erro  -> 2 tons graves      (senha incorreta)
#   tecla -> clique bem curto   (confirma cada digito)
#
# Uso:  sudo python3 buzzer_feedback.py --som ok
#       python3 buzzer_feedback.py --test   (roda no PC)
# =========================================

import argparse
import time

BUZZER_PIN = 4
DUTY_50 = 50

# Cada padrao e uma lista de (frequencia_Hz, duracao_ms).
SONS = {
    "ok":    [(1500, 120)],
    "erro":  [(400, 180), (300, 180)],
    "tecla": [(1200, 25)],
}


class Buzzer:
    def __init__(self, pin=BUZZER_PIN):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, SONS["ok"][0][0])
        self.pwm.start(0)

    def tocar(self, nome):
        for freq, ms in SONS[nome]:
            self.pwm.ChangeFrequency(freq)
            self.pwm.ChangeDutyCycle(DUTY_50)
            time.sleep(ms / 1000.0)
            self.pwm.ChangeDutyCycle(0)
            time.sleep(0.03)

    def bip_ok(self):
        self.tocar("ok")

    def bip_erro(self):
        self.tocar("erro")

    def bip_tecla(self):
        self.tocar("tecla")

    def fechar(self):
        self.pwm.stop()
        self.GPIO.cleanup()


def demo():
    """Auto-teste sem hardware: python3 buzzer_feedback.py --test"""
    for nome in ("ok", "erro", "tecla"):
        assert nome in SONS and SONS[nome], f"padrao {nome} vazio"
        for freq, ms in SONS[nome]:
            assert 100 <= freq <= 5000, f"freq {freq} fora de faixa audivel util"
            assert ms > 0
    # 'ok' agudo, 'erro' grave: comunica o resultado so pelo som.
    assert SONS["ok"][0][0] > SONS["erro"][0][0], "ok deve ser mais agudo que erro"
    print("demo OK: padroes ok/erro/tecla dentro de faixa e distinguiveis.")


def main():
    ap = argparse.ArgumentParser(description="Feedback sonoro da fechadura (RPi.GPIO)")
    ap.add_argument("--som", choices=list(SONS), default="ok", help="padrao a tocar")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    bz = Buzzer()
    try:
        print(f"Tocando padrao: {args.som}")
        bz.tocar(args.som)
    finally:
        bz.fechar()


if __name__ == "__main__":
    main()
