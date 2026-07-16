#!/usr/bin/env python3
# =========================================
# ATIVIDADE 1 - CONTROLE DE LED POR PWM
# Raspberry Pi 3 + pigpio (PWM de hardware)
#
# LED no GPIO18 (canal PWM0 do BCM2837) com
# resistor de 220-330 ohm em serie para o GND.
#
# Requer o daemon:  sudo pigpiod
# =========================================

import argparse
import time

import pigpio

LED_PIN = 18                 # GPIO12/18 = PWM0 ; GPIO13/19 = PWM1

# Duty no pigpio e dado em milionesimos (0 a 1_000_000).
DUTY_MAX = 1_000_000

# Varredura da atividade: mesma intensidade (50%), frequencias diferentes.
FREQUENCIAS = [1, 5, 50, 100, 500, 1_000, 10_000]


def duty_de_pct(pct):
    return int(pct / 100.0 * DUTY_MAX)


def aplicar(pi, freq, pct):
    """Aplica frequencia (Hz) e duty (%) no LED. Retorna a freq real."""
    real = pi.hardware_PWM(LED_PIN, freq, duty_de_pct(pct))
    if real != 0:
        raise RuntimeError(f"hardware_PWM falhou (codigo {real}) - pigpiod rodando?")
    return pi.get_PWM_frequency(LED_PIN)


def varrer_frequencias(pi, segundos):
    print("\n== Varredura de frequencia (duty fixo em 50%) ==")
    print(" Freq pedida | Freq real | Duty (%) | Duty (ppm) | Observacao visual")
    print(" " + "-" * 74)
    for f in FREQUENCIAS:
        real = aplicar(pi, f, 50)
        nota = "pisca visivel" if f <= 20 else "aparenta brilho continuo"
        print(f" {f:>10} Hz | {real:>6} Hz |       50 | {duty_de_pct(50):>10} | {nota}")
        time.sleep(segundos)


def varrer_duty(pi, freq):
    print(f"\n== Varredura de intensidade (fade) a {freq} Hz ==")
    print(" Duty (%) | Duty (ppm)")
    print(" " + "-" * 22)
    for pct in range(0, 101, 10):
        aplicar(pi, freq, pct)
        print(f" {pct:>8} | {duty_de_pct(pct):>10}")
        time.sleep(0.3)
    for pct in range(100, -1, -10):
        aplicar(pi, freq, pct)
        time.sleep(0.3)


def main():
    ap = argparse.ArgumentParser(description="Controle de LED por PWM (pigpio)")
    ap.add_argument("--freq", type=int, help="testa uma unica frequencia (Hz)")
    ap.add_argument("--duty", type=float, default=50, help="duty em %% (padrao 50)")
    ap.add_argument("--seg", type=float, default=3, help="segundos por frequencia na varredura")
    args = ap.parse_args()

    pi = pigpio.pi()
    if not pi.connected:
        raise SystemExit("pigpiod nao esta rodando. Execute: sudo pigpiod")

    try:
        if args.freq:
            real = aplicar(pi, args.freq, args.duty)
            print(f"LED -> freq={real} Hz  duty={args.duty}% ({duty_de_pct(args.duty)} ppm)")
            print("Ctrl+C para sair.")
            while True:
                time.sleep(1)
        else:
            varrer_frequencias(pi, args.seg)
            varrer_duty(pi, 1_000)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        pi.hardware_PWM(LED_PIN, 0, 0)   # desliga o canal antes de sair
        pi.stop()


if __name__ == "__main__":
    main()
