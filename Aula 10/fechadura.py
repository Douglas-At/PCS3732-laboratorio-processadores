#!/usr/bin/env python3
# =========================================
# INTEGRADO - FECHADURA ELETRONICA
# Raspberry Pi 3 + RPi.GPIO + I2C
#
# Costura os 5 componentes isolados:
#   teclado_matricial (entrada da senha)
#   lcd_i2c           (mostra o estado)
#   buzzer_feedback   (feedback sonoro)
#   servo_fechadura   (atua o ferrolho)
#   sensor_trava      (confere a posicao do ferrolho)
#
# Maquina de estados:
#   BLOQUEADA -> DIGITANDO -> VALIDANDO -> DESTRANCADA
#                                       -> ERRO -> (3x) BLOQUEIO_TEMPORIZADO
#
# A logica (senha, tentativas, bloqueio, coerencia do
# sensor) e injetada com hardware (real ou fake), entao
# roda o auto-teste sem GPIO/I2C:  python3 fechadura.py --test
#
# Uso:  sudo python3 fechadura.py
#       python3 fechadura.py --test    (roda no PC)
# =========================================

import argparse
import time

SENHA = "1234"          # ponytail: texto no codigo e ok p/ prototipo de aula;
                        # o .md (analise de seguranca) discute o risco e mitigacoes.
MAX_TENTATIVAS = 3
BLOQUEIO_S = 30
ABERTA_S = 5            # tranca sozinha depois deste tempo destrancada


class Fechadura:
    """Nucleo logico. Nao fala com GPIO: recebe 'hw' com
    lcd/buzzer/servo/sensor (reais ou fakes)."""

    def __init__(self, hw):
        self.hw = hw
        self.buffer = ""
        self.tentativas = 0
        self.bloqueado_ate = 0.0
        self.aberta_ate = 0.0
        self.alarme = False
        self._mostrar("FECHADURA", "Digite a senha")

    def _mostrar(self, l0, l1):
        self.hw.lcd.escrever(0, l0)
        self.hw.lcd.escrever(1, l1)

    def bloqueada(self, agora):
        return agora < self.bloqueado_ate

    def tecla(self, ch, agora):
        """Processa uma tecla. Retorna o estado atual (str) p/ log/teste."""
        if self.bloqueada(agora):
            self.hw.buzzer.bip_erro()
            restante = int(self.bloqueado_ate - agora) + 1
            self._mostrar("BLOQUEADO", f"aguarde {restante}s")
            return "BLOQUEADA"

        if ch == "*":                       # limpar
            self.buffer = ""
            self._mostrar("FECHADURA", "Digite a senha")
            return "DIGITANDO"
        if ch == "#":                       # confirmar
            return self._validar(agora)

        # digito comum
        self.buffer += ch
        self.hw.buzzer.bip_tecla()
        self._mostrar("Senha:", "*" * len(self.buffer))
        return "DIGITANDO"

    def _validar(self, agora):
        certa = self.buffer == SENHA
        self.buffer = ""
        if certa:
            self.tentativas = 0
            self.hw.buzzer.bip_ok()
            self._mostrar("ACESSO", "LIBERADO")
            self.hw.servo.destrancar()
            self.aberta_ate = agora + ABERTA_S
            return "DESTRANCADA"

        self.tentativas += 1
        self.hw.buzzer.bip_erro()
        if self.tentativas >= MAX_TENTATIVAS:
            self.bloqueado_ate = agora + BLOQUEIO_S
            self.tentativas = 0
            self._mostrar("BLOQUEADO", f"aguarde {BLOQUEIO_S}s")
            return "BLOQUEADA"
        self._mostrar("SENHA", "INCORRETA")
        return "ERRO"

    def tick(self, agora):
        """Chamado periodicamente: tranca sozinha e confere o sensor."""
        if self.aberta_ate and agora >= self.aberta_ate:
            self.aberta_ate = 0.0
            self.hw.servo.trancar()
            time.sleep(0.2)
            if not self.hw.sensor.trancada():
                # Comandou trancar mas o sensor diz aberto -> alarme.
                self.alarme = True
                self.hw.buzzer.bip_erro()
                self._mostrar("ALARME", "ferrolho aberto")
                return "ALARME"
            self._mostrar("FECHADURA", "Digite a senha")
            return "TRANCADA"
        return "IDLE"


# ---------- hardware real ----------

def _hw_real():
    """Monta os componentes reais. Import tardio: so no RPi."""
    from lcd_i2c import LCD
    from buzzer_feedback import Buzzer
    from servo_fechadura import Servo
    from sensor_trava import Sensor
    from teclado_matricial import ROWS, COLS, ler_tecla
    import RPi.GPIO as GPIO

    class HW:
        pass
    hw = HW()
    hw.lcd = LCD()
    hw.buzzer = Buzzer()
    hw.servo = Servo()
    hw.sensor = Sensor()

    # o teclado compartilha o mesmo GPIO ja em BCM
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for rp in ROWS:
        GPIO.setup(rp, GPIO.OUT, initial=GPIO.HIGH)
    for cp in COLS:
        GPIO.setup(cp, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    hw.GPIO = GPIO
    hw.ler_tecla = lambda: ler_tecla(GPIO)
    hw.fechar = lambda: (hw.buzzer.fechar(), hw.servo.fechar(), GPIO.cleanup())
    return hw


def main():
    hw = _hw_real()
    fech = Fechadura(hw)
    print("\n== Fechadura eletronica (Ctrl+C para sair) ==")
    print(f" senha atual: {SENHA} | # confirma | * limpa")
    try:
        anterior = None
        while True:
            agora = time.time()
            fech.tick(agora)
            tecla = hw.ler_tecla()
            if tecla and tecla != anterior:
                estado = fech.tecla(tecla, agora)
                print(f" [{tecla}] -> {estado}")
                time.sleep(0.15)
            anterior = tecla
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        hw.fechar()


# ---------- auto-teste (fakes) ----------

class _FakeDev:
    def __init__(self):
        self.log = []
    def __getattr__(self, nome):
        return lambda *a: self.log.append((nome,) + a)


class _FakeSensor:
    def __init__(self, trancada=True):
        self._t = trancada
    def trancada(self):
        return self._t


def demo():
    """Auto-teste sem hardware: python3 fechadura.py --test"""
    def nova(sensor_ok=True):
        class HW:
            pass
        hw = HW()
        hw.lcd = _FakeDev()
        hw.buzzer = _FakeDev()
        hw.servo = _FakeDev()
        hw.sensor = _FakeSensor(sensor_ok)
        return Fechadura(hw), hw

    # 1) senha certa destranca
    f, hw = nova()
    for ch in "1234":
        f.tecla(ch, 0)
    assert f.tecla("#", 0) == "DESTRANCADA"
    assert ("destrancar",) in hw.servo.log

    # 2) senha errada conta tentativa (nao bloqueia na 1a)
    f, hw = nova()
    for ch in "0000":
        f.tecla(ch, 0)
    assert f.tecla("#", 0) == "ERRO"
    assert f.tentativas == 1

    # 3) 3 erros -> bloqueio temporizado; teclas ignoradas durante o bloqueio
    f, hw = nova()
    for _ in range(3):
        for ch in "9999":
            f.tecla(ch, 0)
        estado = f.tecla("#", 0)
    assert estado == "BLOQUEADA"
    assert f.bloqueada(1) and not f.bloqueada(BLOQUEIO_S + 1)
    assert f.tecla("1", 1) == "BLOQUEADA", "durante bloqueio ignora digito"

    # 4) '*' limpa o buffer (senha parcial nao valida)
    f, hw = nova()
    for ch in "12":
        f.tecla(ch, 0)
    f.tecla("*", 0)
    for ch in "1234":
        f.tecla(ch, 0)
    assert f.tecla("#", 0) == "DESTRANCADA", "apos limpar, senha correta abre"

    # 5) sensor incoerente ao trancar -> alarme
    f, hw = nova(sensor_ok=False)
    for ch in "1234":
        f.tecla(ch, 0)
    f.tecla("#", 0)                 # abre, aberta_ate = ABERTA_S
    assert f.tick(ABERTA_S + 1) == "ALARME"
    assert f.alarme is True

    # 6) sensor coerente ao trancar -> TRANCADA, sem alarme
    f, hw = nova(sensor_ok=True)
    for ch in "1234":
        f.tecla(ch, 0)
    f.tecla("#", 0)
    assert f.tick(ABERTA_S + 1) == "TRANCADA"
    assert f.alarme is False

    print("demo OK: senha, tentativas, bloqueio, limpar e coerencia do sensor.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fechadura eletronica integrada")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()
    if args.test:
        demo()
    else:
        main()
