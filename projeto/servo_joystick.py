#!/usr/bin/env python3
# =========================================
# CONTROLE DE SERVO PELO JOYSTICK (incremental)
# Raspberry Pi 3 + RPi.GPIO (PWM de software) + ADS7830 (I2C)
#
# O eixo X do joystick e ANALOGICO; o Raspberry nao tem ADC,
# entao o valor (0-255) vem do ADS7830 do kit Freenove
# (I2C, 0x48, canal 5 = X, igual ao exemplo Joystick.py do kit).
#
# Mapeamento INCREMENTAL: joystick no centro segura a posicao;
# empurrar p/ um lado aumenta o angulo, p/ o outro diminui,
# proporcional a quao longe do centro. Clicar o joystick (SW,
# GPIO7) recentra em 90 g. Faixa util do atuador: 20-160 g.
#
# Servo no GPIO18. Alimentacao 5V com GND COMUM ao RPi.
# Nunca alimentar o servo pelo 3,3V.
#
# Uso:  sudo python3 servo_joystick.py
#       python3 servo_joystick.py --test    (roda no PC, sem hardware)
# =========================================

import argparse
import time

SERVO_PIN = 18
SW_PIN = 7
ADC_ADDR = 0x48
ADC_CH_X = 5           # canal do eixo X no ADS7830 (igual ao kit Freenove)

PERIODO_US = 20_000
PULSO_MIN_US = 1000    # 0 graus
PULSO_MAX_US = 2000    # 180 graus

ANG_MIN = 20
ANG_MAX = 160
ANG_CENTRO = 90
TAXA = 90              # graus/s com o joystick no talo
ZONA_MORTA = 0.12      # ignora tremor perto do centro
DT = 0.02              # periodo do laco (s)


def angulo_para_pulso(ang):
    """Converte angulo (0-180) em largura de pulso (us)."""
    ang = max(0, min(180, ang))
    return PULSO_MIN_US + (PULSO_MAX_US - PULSO_MIN_US) * ang / 180.0


def pulso_para_duty(pulso_us):
    """Converte largura de pulso (us) no duty (%) do periodo de 20 ms."""
    return pulso_us / PERIODO_US * 100.0


def normaliza(bruto):
    """ADC 0-255 -> [-1,1] com centro em 128 e zona morta."""
    norm = (bruto - 128) / 127.0
    return 0.0 if abs(norm) < ZONA_MORTA else norm


def proximo_angulo(ang, norm, dt=DT):
    """Integra o deslocamento do joystick e trava na faixa util."""
    ang += norm * TAXA * dt
    return max(ANG_MIN, min(ANG_MAX, ang))


def ler_x(bus):
    """Le o canal X do ADS7830 (0-255). Formula do ADCDevice.py do kit."""
    chn = ADC_CH_X
    return bus.read_byte_data(ADC_ADDR, 0x84 | (((chn << 2 | chn >> 1) & 0x07) << 4))


def demo():
    """Auto-teste sem hardware: python3 servo_joystick.py --test"""
    assert angulo_para_pulso(0) == 1000
    assert angulo_para_pulso(180) == 2000
    assert angulo_para_pulso(90) == 1500
    # Zona morta: joystick quase centrado nao move.
    assert normaliza(128) == 0.0
    assert normaliza(135) == 0.0
    assert normaliza(255) > ZONA_MORTA
    # Empurrado no talo por varios passos trava em 20/160, nao estoura.
    ang = ANG_CENTRO
    for _ in range(1000):
        ang = proximo_angulo(ang, 1.0)
    assert ang == ANG_MAX
    for _ in range(1000):
        ang = proximo_angulo(ang, -1.0)
    assert ang == ANG_MIN
    print("demo OK: faixa 20-160 g, zona morta e travas respeitadas")


def main():
    ap = argparse.ArgumentParser(description="Controle de servo pelo joystick (incremental)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    import RPi.GPIO as GPIO
    import smbus

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)
    bus = smbus.SMBus(1)

    ang = ANG_CENTRO
    ultimo = None
    print("\n== Servo pelo joystick (Ctrl+C para sair) ==")
    print(" empurre X p/ mover, centro segura, clique recentra em 90 g")
    try:
        while True:
            norm = normaliza(ler_x(bus))
            ang = ANG_CENTRO if GPIO.input(SW_PIN) == 0 else proximo_angulo(ang, norm)
            # So refresca o PWM quando o angulo muda de fato.
            if ultimo is None or abs(ang - ultimo) > 0.1:
                pwm.ChangeDutyCycle(pulso_para_duty(angulo_para_pulso(ang)))
                ultimo = ang
                print(f" angulo: {ang:6.1f} g   pulso: {angulo_para_pulso(ang):4.0f} us", end="\r")
            # ponytail: mantem o trem de pulsos ativo (servo pode zumbir parado).
            # Se incomodar, soltar duty=0 apos ~0,3 s sem movimento.
            time.sleep(DT)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        pwm.ChangeDutyCycle(0)
        time.sleep(0.05)
        pwm.stop()
        GPIO.cleanup()
        bus.close()


if __name__ == "__main__":
    main()
