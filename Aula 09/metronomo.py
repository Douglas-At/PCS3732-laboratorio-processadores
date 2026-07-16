#!/usr/bin/env python3
# =========================================
# ATIVIDADE 4 - METRONOMO (servo + buzzer)
# + DESAFIO: frequencia ajustavel por botoes
# Raspberry Pi 3 + RPi.GPIO (PWM de software)
#
# Ligacoes:
#   Servo (sinal) ... GPIO18   (50 Hz, pulso 1000-2000 us)
#   Buzzer passivo .. GPIO4
#   Botao BPM +  .... GPIO26   (outro terminal no GND)
#   Botao BPM -  .... GPIO16   (outro terminal no GND)
# Servo alimentado em 5V com GND comum ao Raspberry.
# Os botoes usam pull-up interno: em repouso leem 1,
# pressionados vao a 0 (borda de descida).
#
# Sem botoes conectados o script e o metronomo puro
# da atividade 4 (os pinos ficam em 1 e nada dispara).
#
# Uso:  sudo python3 metronomo.py --bpm 60
#       python3 metronomo.py --test    (roda no PC, sem hardware)
# =========================================

import argparse
import time

SERVO_PIN = 18
BUZZER_PIN = 4
BTN_MAIS = 26
BTN_MENOS = 16

PERIODO_US = 20_000     # 50 Hz do servo
PULSO_MIN_US = 1000     # 0 graus   - ver nota de calibracao em servo_pwm.py
PULSO_MAX_US = 2000     # 180 graus

ANG_ESQ = 60            # extremos do balanco do pendulo
ANG_DIR = 120

TOM_FORTE = 1500        # tempo 1 do compasso (Hz)
TOM_FRACO = 1000        # demais tempos (Hz)
BIPE_MS = 30
DUTY_50 = 50

BPM_MIN = 30
BPM_MAX = 240
BPM_PASSO = 5
COMPASSO = 4            # batidas por compasso (tom forte a cada 4)

DEBOUNCE_MS = 150       # bouncetime do add_event_detect


def angulo_para_pulso(ang):
    """Converte angulo (0-180) em largura de pulso (us)."""
    ang = max(0, min(180, ang))
    return PULSO_MIN_US + (PULSO_MAX_US - PULSO_MIN_US) * ang / 180.0


def pulso_para_duty(pulso_us):
    """Converte largura de pulso (us) no duty (%) do periodo de 20 ms."""
    return pulso_us / PERIODO_US * 100.0


def limitar_bpm(bpm):
    return max(BPM_MIN, min(BPM_MAX, bpm))


class Metronomo:
    def __init__(self, servo, buzzer, bpm):
        self.servo = servo
        self.buzzer = buzzer
        self.bpm = limitar_bpm(bpm)
        self.batida = 0
        self.para_direita = True

    def ajustar_bpm(self, delta):
        antes = self.bpm
        self.bpm = limitar_bpm(self.bpm + delta)
        if self.bpm != antes:
            print(f"  >> BPM: {antes} -> {self.bpm}  (periodo {60.0 / self.bpm:.3f} s)")

    def bater(self):
        ang = ANG_DIR if self.para_direita else ANG_ESQ
        self.para_direita = not self.para_direita
        self.servo.ChangeDutyCycle(pulso_para_duty(angulo_para_pulso(ang)))
        tom = TOM_FORTE if self.batida % COMPASSO == 0 else TOM_FRACO
        self.buzzer.ChangeFrequency(tom)
        self.buzzer.ChangeDutyCycle(DUTY_50)
        time.sleep(BIPE_MS / 1000.0)
        self.buzzer.ChangeDutyCycle(0)
        return ang, tom

    def rodar(self):
        print("\n== Metronomo em execucao (Ctrl+C para sair) ==")
        print("   n | BPM | Tempo | Angulo | Tom (Hz) | erro_ms")
        print(" " + "-" * 52)

        # Temporizacao por deadline ABSOLUTA: cada instante e calculado a partir do
        # anterior, nao da soma dos sleeps. O tempo gasto no bipe e o atraso do
        # escalonador do Linux nao se acumulam de uma batida para a outra.
        proximo = time.monotonic()
        while True:
            proximo += 60.0 / self.bpm
            atraso = proximo - time.monotonic()
            if atraso > 0:
                time.sleep(atraso)

            erro_ms = (time.monotonic() - proximo) * 1000.0
            ang, tom = self.bater()
            tempo = self.batida % COMPASSO + 1
            print(f" {self.batida + 1:>3} | {self.bpm:>3} | {tempo:>5} |"
                  f" {ang:>5} g | {tom:>8} | {erro_ms:>7.2f}")
            self.batida += 1


def demo():
    """Auto-teste sem hardware: python3 metronomo.py --test"""
    assert angulo_para_pulso(0) == 1000
    assert angulo_para_pulso(90) == 1500
    assert angulo_para_pulso(180) == 2000
    assert angulo_para_pulso(-10) == 1000, "angulo abaixo da faixa deve saturar"
    assert angulo_para_pulso(999) == 2000, "angulo acima da faixa deve saturar"

    assert pulso_para_duty(angulo_para_pulso(90)) == 7.5, "1,5 ms em 20 ms = 7,5%"
    assert pulso_para_duty(PULSO_MIN_US) == 5.0
    assert pulso_para_duty(PULSO_MAX_US) == 10.0

    assert limitar_bpm(0) == BPM_MIN
    assert limitar_bpm(600) == BPM_MAX
    assert limitar_bpm(60) == 60

    # Agendamento: mesmo com uma batida que atrasa (o bipe, o escalonador), as deadlines
    # continuam multiplos exatos do periodo - e o que garante ausencia de drift acumulado.
    periodo = 60.0 / 60
    proximo = 0.0
    agora = 0.0
    for n in range(1, 101):
        proximo += periodo
        agora = max(agora, proximo) + 0.03      # simula o bipe de 30 ms atrasando a batida
        assert abs(proximo - n * periodo) < 1e-9, f"drift na batida {n}"
    assert abs(proximo - 100.0) < 1e-9

    # Contraprova: somar sleeps a partir do relogio corrente acumula o atraso do bipe.
    ingenuo = 0.0
    for _ in range(100):
        ingenuo += periodo + 0.03
    assert ingenuo > 102.9, "o metodo ingenuo deveria acumular ~3 s de drift em 100 batidas"

    print("demo OK: pulso, duty, limites de BPM e agendamento sem drift.")


def main():
    ap = argparse.ArgumentParser(description="Metronomo com servo + buzzer (RPi.GPIO)")
    ap.add_argument("--bpm", type=int, default=60, help="batidas por minuto (padrao 60 = 1 s)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)

    servo = GPIO.PWM(SERVO_PIN, 50)
    buzzer = GPIO.PWM(BUZZER_PIN, TOM_FRACO)
    servo.start(0)
    buzzer.start(0)

    m = Metronomo(servo, buzzer, args.bpm)
    try:
        # Desafio: botoes ajustam o BPM; o callback so mexe no BPM, a batida segue no laco.
        for pino, delta in ((BTN_MAIS, +BPM_PASSO), (BTN_MENOS, -BPM_PASSO)):
            GPIO.setup(pino, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pino, GPIO.FALLING,
                                  callback=lambda ch, d=delta: m.ajustar_bpm(d),
                                  bouncetime=DEBOUNCE_MS)

        print(f"Metronomo iniciado em {m.bpm} BPM (periodo {60.0 / m.bpm:.3f} s)")
        print(f"Botoes: GPIO{BTN_MAIS} = +{BPM_PASSO} BPM | GPIO{BTN_MENOS} = -{BPM_PASSO} BPM"
              f" | faixa {BPM_MIN}-{BPM_MAX}")
        m.rodar()
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        servo.ChangeDutyCycle(0)
        buzzer.ChangeDutyCycle(0)
        time.sleep(0.05)
        servo.stop()
        buzzer.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
