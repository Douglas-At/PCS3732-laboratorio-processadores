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
#   tecla -> clique bem curto            (confirma cada digito)
#   ok    -> 1 tom agudo curto           (acesso liberado)
#   erro  -> SIRENE DE AMBULANCIA        (senha incorreta / alarme)
#            two-tone alternando 960/770 Hz, reaproveitado da
#            Aula 09 (buzzer_ambulancia.py).
#
# Uso:  sudo python3 buzzer_feedback.py --som erro
#       sudo python3 buzzer_feedback.py --som ok
#       python3 buzzer_feedback.py --test   (roda no PC)
# =========================================

import argparse
import time

BUZZER_PIN = 4
DUTY_50 = 50

# Tons curtos (freq_Hz, duracao_ms).
BIP_TECLA = (1200, 25)
BIP_OK = (1500, 120)

# Sirene de ambulancia (Aula 09): alterna dois tons por N ciclos.
SIRENE_ALTO = 960       # Hz
SIRENE_BAIXO = 770      # Hz
SIRENE_TROCA_MS = 250   # duracao de cada tom
SIRENE_CICLOS = 3       # quantos pares alto/baixo por acionamento


class Buzzer:
    def __init__(self, pin=BUZZER_PIN):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, BIP_OK[0])
        self.pwm.start(0)

    def _tom(self, freq, ms):
        self.pwm.ChangeFrequency(freq)
        self.pwm.ChangeDutyCycle(DUTY_50)
        time.sleep(ms / 1000.0)
        self.pwm.ChangeDutyCycle(0)

    def bip_tecla(self):
        self._tom(*BIP_TECLA)

    def bip_ok(self):
        self._tom(*BIP_OK)

    def sirene(self, ciclos=SIRENE_CICLOS):
        """Som de ambulancia: alterna alto/baixo por 'ciclos' pares."""
        for _ in range(ciclos):
            self._tom(SIRENE_ALTO, SIRENE_TROCA_MS)
            self._tom(SIRENE_BAIXO, SIRENE_TROCA_MS)

    def bip_erro(self):
        self.sirene()

    def fechar(self):
        self.pwm.stop()
        self.GPIO.cleanup()


def demo():
    """Auto-teste sem hardware: python3 buzzer_feedback.py --test"""
    for freq, ms in (BIP_TECLA, BIP_OK):
        assert 100 <= freq <= 5000, f"freq {freq} fora de faixa audivel util"
        assert ms > 0
    # Sirene: dois tons distintos, ambos na faixa audivel, alto > baixo.
    assert SIRENE_ALTO != SIRENE_BAIXO, "a sirene precisa alternar dois tons"
    assert SIRENE_ALTO > SIRENE_BAIXO
    assert 100 <= SIRENE_BAIXO and SIRENE_ALTO <= 5000
    assert SIRENE_CICLOS >= 1 and SIRENE_TROCA_MS > 0
    # 'ok' agudo e 'tecla' curtinho comunicam so pelo som.
    assert BIP_OK[0] > SIRENE_BAIXO, "ok deve ser mais agudo que o tom grave da sirene"
    print("demo OK: tecla/ok curtos e sirene de ambulancia (960/770 Hz) valida.")


def main():
    ap = argparse.ArgumentParser(description="Feedback sonoro da fechadura (RPi.GPIO)")
    ap.add_argument("--som", choices=["tecla", "ok", "erro"], default="ok", help="padrao a tocar")
    ap.add_argument("--freq", type=int, help="toca um tom continuo (Hz) por --ms - so p/ teste")
    ap.add_argument("--ms", type=int, default=1000, help="duracao do tom continuo (padrao 1000)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    bz = Buzzer()
    try:
        if args.freq:                       # tom longo e obvio p/ conferir a fiacao
            print(f"Tom de teste: {args.freq} Hz por {args.ms} ms")
            bz._tom(args.freq, args.ms)
        else:
            print(f"Tocando padrao: {args.som}")
            {"tecla": bz.bip_tecla, "ok": bz.bip_ok, "erro": bz.bip_erro}[args.som]()
    finally:
        bz.fechar()


if __name__ == "__main__":
    main()
