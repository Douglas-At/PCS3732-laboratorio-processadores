#!/usr/bin/env python3
# =========================================
# INTEGRADO - FECHADURA ELETRONICA
# Raspberry Pi 3 + RPi.GPIO + I2C
#
# Costura os 5 componentes isolados:
#   teclado_matricial (entrada da senha, 4x4)
#   lcd_i2c           (mostra o estado)
#   buzzer_feedback   (feedback sonoro; erro = sirene de ambulancia)
#   servo_fechadura   (atua o ferrolho)
#   sensor_trava      (confere a posicao do ferrolho)
#
# Maquina de estados:
#   BLOQUEADA -> DIGITANDO -> VALIDANDO -> DESTRANCADA
#                                       -> ERRO -> (3x) BLOQUEIO_TEMPORIZADO
#
# SEGURANCA: a senha NAO fica em texto no codigo. Guardamos apenas
# o salt e o hash PBKDF2-HMAC-SHA256 (stdlib hashlib), e a verificacao
# usa hmac.compare_digest (comparacao em tempo constante). Ver a secao
# de analise de seguranca no PLANEJAMENTO_PRE_AULA.md.
#
# A logica (senha, tentativas, bloqueio, coerencia do sensor) roda com
# hardware real OU fake, entao da p/ auto-testar no PC sem GPIO/I2C:
#   python3 fechadura.py --test
#
# Uso:  sudo python3 fechadura.py
#       python3 fechadura.py --test    (roda no PC)
# =========================================

import argparse
import hashlib
import hmac
import time

# Credencial armazenada (nunca o PIN em claro). PIN de fabrica: 1234.
# Para trocar: gere um novo hash com
#   python3 -c "import hashlib;print(hashlib.pbkdf2_hmac('sha256',b'NOVOPIN',b'fechadura-aula10-salt',100000).hex())"
SENHA_SALT = b"fechadura-aula10-salt"
SENHA_HASH = "a520aa2c53b77433c8f31239ccbd56cde6b87454f291e4bcfc75665eeac93128"
PBKDF2_ITER = 100_000

MAX_TENTATIVAS = 3
BLOQUEIO_S = 30
ABERTA_S = 5            # tranca sozinha depois deste tempo destrancada


def hash_senha(pin, salt=SENHA_SALT):
    """Deriva o hash PBKDF2-HMAC-SHA256 do PIN (str). Logica pura, testavel."""
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, PBKDF2_ITER).hex()


def senha_confere(pin):
    """True se o PIN digitado corresponde ao hash armazenado.

    compare_digest evita vazar por tempo qual prefixo estava certo.
    """
    return hmac.compare_digest(hash_senha(pin), SENHA_HASH)


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

        # digito comum (ignora A-D, que ficam livres p/ uso futuro)
        if not ch.isdigit():
            return "DIGITANDO"
        self.buffer += ch
        self.hw.buzzer.bip_tecla()
        self._mostrar("Senha:", "*" * len(self.buffer))
        return "DIGITANDO"

    def _validar(self, agora):
        certa = senha_confere(self.buffer)
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
    from teclado_matricial import novo_teclado, ler_tecla

    class HW:
        pass
    hw = HW()
    hw.lcd = LCD()
    hw.buzzer = Buzzer()
    hw.servo = Servo()
    hw.sensor = Sensor()

    # teclado pelo modulo Keypad.py da Freenove (gpiozero)
    kp = novo_teclado()
    hw.ler_tecla = lambda: ler_tecla(kp)
    hw.fechar = lambda: (hw.buzzer.fechar(), hw.servo.fechar())
    return hw


def main():
    hw = _hw_real()
    fech = Fechadura(hw)
    print("\n== Fechadura eletronica (Ctrl+C para sair) ==")
    print(" PIN de fabrica: 1234 | # confirma | * limpa")
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
    # 0) credencial: hash confere o PIN certo e rejeita os errados,
    #    e o hash armazenado NAO e o PIN em claro.
    assert senha_confere("1234")
    assert not senha_confere("0000") and not senha_confere("12345")
    assert SENHA_HASH != "1234" and len(SENHA_HASH) == 64

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

    # 5) teclas A-D sao ignoradas no meio do PIN
    f, hw = nova()
    for ch in "1":
        f.tecla(ch, 0)
    f.tecla("A", 0)                 # nao entra no buffer
    for ch in "234":
        f.tecla(ch, 0)
    assert f.tecla("#", 0) == "DESTRANCADA", "A-D nao contaminam o PIN"

    # 6) sensor incoerente ao trancar -> alarme
    f, hw = nova(sensor_ok=False)
    for ch in "1234":
        f.tecla(ch, 0)
    f.tecla("#", 0)                 # abre, aberta_ate = ABERTA_S
    assert f.tick(ABERTA_S + 1) == "ALARME"
    assert f.alarme is True

    # 7) sensor coerente ao trancar -> TRANCADA, sem alarme
    f, hw = nova(sensor_ok=True)
    for ch in "1234":
        f.tecla(ch, 0)
    f.tecla("#", 0)
    assert f.tick(ABERTA_S + 1) == "TRANCADA"
    assert f.alarme is False

    print("demo OK: hash da senha, tentativas, bloqueio, limpar, A-D e coerencia do sensor.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fechadura eletronica integrada")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()
    if args.test:
        demo()
    else:
        main()
