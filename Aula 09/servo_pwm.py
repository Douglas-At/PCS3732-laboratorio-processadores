#!/usr/bin/env python3
# =========================================
# ATIVIDADE 2 - CONTROLE DE SERVOMOTOR POR PWM
# Raspberry Pi 3 + pigpio
#
# Servo no GPIO12 (sinal). Alimentacao em 5V
# (pino 2 ou 4) com GND COMUM com o Raspberry.
# Nunca alimentar o servo pelo 3,3V.
#
# Mesma convencao do servo_webserver.ino (Aula 05):
# periodo de 20 ms (50 Hz), pulso de 1,0 ms (0 graus)
# a 2,0 ms (180 graus), 1,5 ms = 90 graus.
#
# set_servo_pulsewidth usa waveform por DMA: funciona
# em qualquer GPIO e nao disputa os canais PWM0/PWM1
# com o LED e o buzzer.
#
# Requer o daemon:  sudo pigpiod
# =========================================

import argparse
import time

import pigpio

SERVO_PIN = 18

# ponytail: 1000/2000 us e o valor nominal da folha de dados; o servo real da bancada
# costuma precisar de ~500-2400 us para o curso completo. Se 0/180 nao chegarem ao
# batente (ou forcarem contra ele), calibrar AQUI antes de mexer em qualquer outra coisa.
PULSO_MIN_US = 1000    # 0 graus
PULSO_MAX_US = 2000    # 180 graus

SEQUENCIA = [0, 45, 90, 135, 180, 90]


def angulo_para_pulso(ang):
    """Converte angulo (0-180) em largura de pulso (us)."""
    ang = max(0, min(180, ang))
    return PULSO_MIN_US + (PULSO_MAX_US - PULSO_MIN_US) * ang / 180.0


def mover(pi, ang):
    pulso = angulo_para_pulso(ang)
    pi.set_servo_pulsewidth(SERVO_PIN, pulso)
    return pulso


def main():
    ap = argparse.ArgumentParser(description="Controle de servomotor por PWM (pigpio)")
    ap.add_argument("--ang", type=int, help="posiciona em um unico angulo e sai")
    ap.add_argument("--seg", type=float, default=1.0, help="segundos por posicao")
    args = ap.parse_args()

    pi = pigpio.pi()
    if not pi.connected:
        raise SystemExit("pigpiod nao esta rodando. Execute: sudo pigpiod")

    try:
        alvos = [args.ang] if args.ang is not None else SEQUENCIA

        print("\n== Posicionamento do servo (50 Hz, pulso variavel) ==")
        print(" Angulo | Pulso (us) | Duty equivalente (%)")
        print(" " + "-" * 46)
        for ang in alvos:
            pulso = mover(pi, ang)
            print(f" {ang:>5} g | {pulso:>10.0f} | {pulso / 20000 * 100:>19.2f}")
            time.sleep(args.seg)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        # 0 desliga o trem de pulsos: sem isso o servo fica zumbindo e esquentando.
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()


if __name__ == "__main__":
    main()
