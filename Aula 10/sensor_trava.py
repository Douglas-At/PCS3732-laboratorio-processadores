#!/usr/bin/env python3
# =========================================
# COMPONENTE - SENSOR DE TRAVA (ultrassonico HC-SR04)
# Raspberry Pi 3 + RPi.GPIO
#
# HC-SR04: mede distancia por eco de ultrassom.
#   TRIG (saida) : pulso de 10 us dispara 8 ciclos de 40 kHz
#   ECHO (entrada): fica em ALTO por um tempo proporcional
#                   ao tempo de ida-e-volta do som
#   distancia_cm = tempo_echo * 34300 / 2
#
# Ligacao (BCM): TRIG->GPIO14, ECHO->GPIO15, VCC->5V, GND->GND.
# ATENCAO: o ECHO sai em 5V; o GPIO do RPi so tolera 3,3V.
# Usar divisor de tensao no ECHO (ex.: 1k + 2k) - o kit Freenove ja traz.
#
# Ideia da fechadura: com a porta FECHADA o batente fica perto do
# sensor (distancia pequena) -> TRANCADA; aberta, distancia grande.
# Assim o programa confere fisicamente em vez de "supor" que trancou.
#
# Uso:  sudo python3 sensor_trava.py
#       python3 sensor_trava.py --test   (roda no PC, sem hardware)
# =========================================

import argparse
import time

TRIG_PIN = 14
ECHO_PIN = 15

SOM_CM_S = 34300        # velocidade do som (~343 m/s) em cm/s

# Distancia (cm) abaixo da qual consideramos a porta TRANCADA.
# ponytail: calibrar na bancada conforme a mecanica do ferrolho/batente.
LIMIAR_TRANCADO_CM = 10.0

TIMEOUT_S = 0.02        # sem eco ate aqui -> leitura invalida (None); ~3,4 m de alcance


def distancia_cm(dt_echo_s):
    """Converte a duracao do pulso ECHO (s) em distancia (cm). Logica pura."""
    return dt_echo_s * SOM_CM_S / 2.0


def esta_trancada(dist_cm):
    """True se o batente esta perto o suficiente (porta trancada).

    dist_cm None (sem eco / nada na frente) conta como NAO trancada.
    Logica pura, separada da GPIO, para testar sem hardware.
    """
    return dist_cm is not None and dist_cm <= LIMIAR_TRANCADO_CM


class Sensor:
    def __init__(self, trig=TRIG_PIN, echo=ECHO_PIN):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.trig = trig
        self.echo = echo
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(trig, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(echo, GPIO.IN)
        time.sleep(0.05)    # sensor assenta

    def medir(self):
        """Uma medida. Retorna distancia em cm, ou None se estourar o timeout."""
        GPIO = self.GPIO
        GPIO.output(self.trig, GPIO.HIGH)
        time.sleep(0.00001)             # pulso de 10 us
        GPIO.output(self.trig, GPIO.LOW)

        t0 = time.time()
        while GPIO.input(self.echo) == GPIO.LOW:     # espera o eco subir
            if time.time() - t0 > TIMEOUT_S:
                return None
        inicio = time.time()
        while GPIO.input(self.echo) == GPIO.HIGH:    # mede a largura do pulso
            if time.time() - inicio > TIMEOUT_S:
                return None
        return distancia_cm(time.time() - inicio)

    def trancada(self):
        return esta_trancada(self.medir())

    def fechar(self):
        self.GPIO.cleanup()


def demo():
    """Auto-teste sem hardware: python3 sensor_trava.py --test"""
    # Conversao tempo->distancia (ida e volta).
    assert abs(distancia_cm(0.001) - 17.15) < 1e-6, distancia_cm(0.001)
    assert distancia_cm(0.0) == 0.0
    # Interpretacao perto/longe em torno do limiar.
    assert esta_trancada(5.0) is True, "perto = trancada"
    assert esta_trancada(30.0) is False, "longe = aberta"
    assert esta_trancada(LIMIAR_TRANCADO_CM) is True, "no limiar ainda tranca"
    assert esta_trancada(LIMIAR_TRANCADO_CM + 0.1) is False
    assert esta_trancada(None) is False, "sem eco = nao trancada"
    print(f"demo OK: distancia por eco e limiar de {LIMIAR_TRANCADO_CM:.0f} cm (perto=trancado).")


def main():
    ap = argparse.ArgumentParser(description="Sensor de trava ultrassonico HC-SR04 (RPi.GPIO)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    sensor = Sensor()
    print("\n== Sensor de trava HC-SR04 (Ctrl+C para sair) ==")
    print(f" aproxime/afaste o batente (limiar {LIMIAR_TRANCADO_CM:.0f} cm)...")
    try:
        anterior = None
        while True:
            d = sensor.medir()
            estado = esta_trancada(d)
            if estado != anterior:
                dtxt = "sem eco" if d is None else f"{d:.1f} cm"
                print(f" {'TRANCADA' if estado else 'ABERTA'}  ({dtxt})")
            anterior = estado
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        sensor.fechar()


if __name__ == "__main__":
    main()
