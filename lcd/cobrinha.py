#!/usr/bin/env python3
# =========================================
# COBRINHA (Snake) no LCD 16x2 I2C + joystick analogico
# Raspberry Pi 3
#
# O LCD1602 e display de CARACTERES (nao grafico): a cobra e feita
# de blocos ocupando celulas numa grade de 16 colunas x 2 linhas.
#
# Ligacao:
#   LCD1602 I2C ... SDA->GPIO2  SCL->GPIO3  VCC->5V  GND->GND  (@0x27/0x3F)
#   ADC ADS7830 ... no mesmo barramento I2C (@0x48)
#   Joystick ...... VRx->canal 5  VRy->canal 6  SW->GPIO7  +5V  GND
#
# Habilitar I2C:  sudo raspi-config   |  conferir: i2cdetect -y 1
#
# Uso:  sudo python3 cobrinha.py
#       python3 cobrinha.py --test    (roda no PC, sem hardware)
# =========================================

import argparse
import random
import time

from lcd_i2c import LCD

# --- knobs de calibracao (o mundo fisico varia) ---------------------------
W, H = 16, 2               # dimensoes da grade (colunas x linhas)
SPEED = 0.3                # segundos por passo (velocidade da cobra)
LIMIAR_BAIXO = 64          # abaixo disso: eixo "para tras"/"para cima"
LIMIAR_ALTO = 192          # acima disso: eixo "para frente"/"para baixo"
INVERTER_X = False         # corrige orientacao fisica do eixo X
INVERTER_Y = False         # corrige orientacao fisica do eixo Y
WRAP = True                # atravessa as bordas (mais jogavel em 2 linhas)
# ponytail: WRAP ligado; trocar p/ morte-na-parede e 1 linha em passo().

CORPO = chr(255)           # bloco cheio (ROM do HD44780)
COMIDA = "*"
# ponytail: chars da ROM; CGRAM (createChar) so se quiser cabeca "bonita".

TAM_INICIAL = 3
CH_X, CH_Y = 5, 6          # canais do ADS7830 p/ os eixos
SW_PIN = 7                 # botao do joystick (BCM)

DIR = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}


# --- logica pura e testavel (sem I2C/GPIO) --------------------------------
def proxima_cabeca(cabeca, direcao, wrap=WRAP):
    x = cabeca[0] + direcao[0]
    y = cabeca[1] + direcao[1]
    if wrap:
        x %= W
        y %= H
    return (x, y)


def nova_direcao(atual, x, y):
    """Traduz leituras X/Y do joystick (0-255, repouso ~128) em (dx,dy).

    Zona morta no centro mantem a direcao; reversao de 180 graus e rejeitada.
    """
    if INVERTER_X:
        x = 255 - x
    if INVERTER_Y:
        y = 255 - y

    if x < LIMIAR_BAIXO:
        cand = DIR["L"]
    elif x > LIMIAR_ALTO:
        cand = DIR["R"]
    elif y < LIMIAR_BAIXO:
        cand = DIR["U"]
    elif y > LIMIAR_ALTO:
        cand = DIR["D"]
    else:
        return atual  # zona morta

    if cand == (-atual[0], -atual[1]):  # nao deixa virar sobre si mesma
        return atual
    return cand


def passo(cobra, direcao, comida, wrap=WRAP):
    """Avanca um passo. Retorna (nova_cobra, comeu, morreu)."""
    cabeca = proxima_cabeca(cobra[0], direcao, wrap)
    if not wrap and not (0 <= cabeca[0] < W and 0 <= cabeca[1] < H):
        return cobra, False, True  # bateu na parede
    comeu = cabeca == comida
    # sem comer, a cauda sai da celula neste passo -> nao conta como colisao
    corpo = cobra if comeu else cobra[:-1]
    if cabeca in corpo:
        return cobra, False, True
    nova = [cabeca] + (cobra if comeu else cobra[:-1])
    return nova, comeu, False


def sortear_comida(cobra):
    """Celula vazia aleatoria; None se a tela encheu (vitoria)."""
    livres = [(x, y) for y in range(H) for x in range(W) if (x, y) not in cobra]
    return random.choice(livres) if livres else None


def desenhar(cobra, comida):
    """Monta as 2 linhas de 16 chars da tela."""
    buf = [[" "] * W for _ in range(H)]
    for x, y in cobra:
        buf[y][x] = CORPO
    if comida is not None:
        buf[comida[1]][comida[0]] = COMIDA
    return ["".join(buf[0]), "".join(buf[1])]


def novo_jogo():
    cobra = [(TAM_INICIAL - 1 - i, 0) for i in range(TAM_INICIAL)]  # cabeca a dir.
    return cobra, DIR["R"], sortear_comida(cobra)


# --- I/O e loop (so no RPi) ------------------------------------------------
class ADS7830:
    """Leitura minima do ADC do kit Freenove (so o read; sem DAC/PCF8591)."""
    # ponytail: so o read do ADS7830, sem copiar o ADCDevice inteiro.
    def __init__(self, addr=0x48):
        import smbus
        self.addr = addr
        self.bus = smbus.SMBus(1)

    def analogRead(self, chn):
        cmd = 0x84 | (((chn << 2 | chn >> 1) & 0x07) << 4)
        return self.bus.read_byte_data(self.addr, cmd)


def ler_direcao(adc, atual):
    x = adc.analogRead(CH_X)
    y = adc.analogRead(CH_Y)
    return nova_direcao(atual, x, y)


def renderizar(lcd, cobra, comida):
    linhas = desenhar(cobra, comida)
    lcd.escrever(0, linhas[0])
    lcd.escrever(1, linhas[1])


def esperar_clique(GPIO):
    while GPIO.input(SW_PIN) == 0:   # solta primeiro (caso ja pressionado)
        time.sleep(0.01)
    while GPIO.input(SW_PIN) == 1:   # espera o clique
        time.sleep(0.01)
    time.sleep(0.2)


def jogar(lcd, adc, GPIO):
    while True:
        cobra, direcao, comida = novo_jogo()
        vitoria = False
        while True:
            direcao = ler_direcao(adc, direcao)
            cobra, comeu, morreu = passo(cobra, direcao, comida)
            if morreu:
                break
            if comeu:
                comida = sortear_comida(cobra)
                if comida is None:
                    vitoria = True
                    break
            renderizar(lcd, cobra, comida)
            time.sleep(SPEED)

        pontos = len(cobra) - TAM_INICIAL
        lcd.limpar()
        lcd.escrever(0, "  VOCE VENCEU!" if vitoria else "   GAME OVER")
        lcd.escrever(1, f"  Pontos: {pontos}")
        esperar_clique(GPIO)
        lcd.limpar()


def demo():
    """Auto-teste sem hardware: python3 cobrinha.py --test"""
    # comer faz a cobra crescer
    nova, comeu, morreu = passo([(1, 0)], DIR["R"], (2, 0), wrap=True)
    assert comeu and not morreu and nova == [(2, 0), (1, 0)], nova

    # colisao com o proprio corpo e detectada
    cobra = [(1, 0), (1, 1), (0, 1), (0, 0)]
    _, _, morreu = passo(cobra, DIR["D"], (5, 0), wrap=True)
    assert morreu, "colisao com o corpo deveria matar"

    # wrap: da coluna 15 volta para a 0
    assert proxima_cabeca((15, 0), DIR["R"], wrap=True) == (0, 0)

    # reversao de 180 graus e rejeitada (mantem a direcao atual)
    assert nova_direcao(DIR["R"], x=0, y=128) == DIR["R"]

    # zona morta (repouso ~128) mantem a direcao
    assert nova_direcao(DIR["R"], x=128, y=128) == DIR["R"]

    # curva valida: indo p/ direita e empurrando p/ baixo -> desce
    assert nova_direcao(DIR["R"], x=128, y=255) == DIR["D"]

    print("demo OK: crescer, colisao, wrap, reversao e zona morta corretos.")


def main():
    ap = argparse.ArgumentParser(description="Cobrinha no LCD 16x2 com joystick")
    ap.add_argument("--addr", default="0x27", help="endereco I2C do LCD (0x27/0x3f)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    lcd = LCD(addr=int(args.addr, 16))
    adc = ADS7830()
    lcd.limpar()
    lcd.escrever(0, "   COBRINHA")
    lcd.escrever(1, "  clique p/ ir")
    esperar_clique(GPIO)
    try:
        jogar(lcd, adc, GPIO)
    except KeyboardInterrupt:
        pass
    finally:
        lcd.limpar()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
