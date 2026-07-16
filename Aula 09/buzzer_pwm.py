#!/usr/bin/env python3
# =========================================
# ATIVIDADE 3 - CONTROLE DO BUZZER (PASSIVO)
# Raspberry Pi 3 + pigpio (PWM de hardware)
#
# Buzzer passivo no GPIO13 (canal PWM1), o outro
# terminal no GND.
#
# Buzzer PASSIVO nao tem oscilador interno: a
# frequencia do PWM E a nota tocada. O duty fica
# em 50% (onda quadrada simetrica, maior volume);
# quem muda o tom e a frequencia, nao o duty.
#
# GPIO13 = PWM1, independente do GPIO18 = PWM0 do LED:
# os dois podem ter frequencias diferentes ao mesmo tempo.
#
# Requer o daemon:  sudo pigpiod
# =========================================

import argparse
import time

import pigpio

BUZZER_PIN = 4
DUTY_50 = 500_000        # 50% em milionesimos (unidade do pigpio)

ESCALA = [("La4", 440), ("Do5", 523), ("Mi5", 659), ("La5", 880)]


def tocar(pi, freq, ms):
    """Emite um tom de freq Hz por ms milissegundos."""
    pi.hardware_PWM(BUZZER_PIN, freq, DUTY_50)
    time.sleep(ms / 1000.0)
    pi.hardware_PWM(BUZZER_PIN, 0, 0)


def main():
    ap = argparse.ArgumentParser(description="Controle de buzzer passivo por PWM (pigpio)")
    ap.add_argument("--freq", type=int, help="toca um unico tom (Hz)")
    ap.add_argument("--ms", type=int, default=300, help="duracao em ms (padrao 300)")
    args = ap.parse_args()

    pi = pigpio.pi()
    if not pi.connected:
        raise SystemExit("pigpiod nao esta rodando. Execute: sudo pigpiod")

    try:
        if args.freq:
            print(f"Buzzer -> {args.freq} Hz por {args.ms} ms")
            tocar(pi, args.freq, args.ms)
            return

        print("\n== Escala no buzzer passivo (duty fixo em 50%) ==")
        print(" Nota | Freq (Hz) | Duracao (ms)")
        print(" " + "-" * 36)
        for nome, freq in ESCALA:
            print(f" {nome:>4} | {freq:>9} | {args.ms:>12}")
            tocar(pi, freq, args.ms)
            time.sleep(0.1)

        # Bipes curtos, como os usados no tick do metronomo.
        print("\n== Bipe curto (30 ms) - forma do tick do metronomo ==")
        for freq in (1_500, 1_000, 1_000, 1_000):
            print(f" bipe {freq} Hz / 30 ms")
            tocar(pi, freq, 30)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        pi.hardware_PWM(BUZZER_PIN, 0, 0)
        pi.stop()


if __name__ == "__main__":
    main()
