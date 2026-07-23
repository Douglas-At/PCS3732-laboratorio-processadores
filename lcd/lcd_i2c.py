#!/usr/bin/env python3
# =========================================
# COMPONENTE - LCD 16x2 I2C (Freenove LCD1602)
# Raspberry Pi 3 + smbus (barramento I2C-1)
#
# Copia do driver testado de "Aula 10/lcd_i2c.py" (reuso direto:
# evita import cross-folder com espaco em "Aula 10").
#
# Modulo LCD1602 com expansor PCF8574 (I2C).
# Ligacao: SDA->GPIO2, SCL->GPIO3, VCC->5V, GND->GND.
# Endereco tipico do Freenove: 0x27 (as vezes 0x3F).
#
# Mapa de bits do PCF8574 -> HD44780 (padrao dos
# modulos "I2C LCD backpack"):
#   P0=RS  P1=RW  P2=EN  P3=Backlight  P4..P7=D4..D7
# Por isso o dado vai em 2 nibbles (modo 4 bits).
#
# Habilitar I2C antes:  sudo raspi-config  (Interface > I2C)
# Conferir endereco:    i2cdetect -y 1
#
# Uso:  sudo python3 lcd_i2c.py
#       sudo python3 lcd_i2c.py --addr 0x3f
#       python3 lcd_i2c.py --test     (roda no PC, sem hardware)
# =========================================

import argparse
import time

RS = 0x01          # P0
EN = 0x04          # P2
BACKLIGHT = 0x08   # P3


def split_byte(value, rs, bl):
    """Divide um byte em (nibble alto, nibble baixo) ja com RS e backlight.

    Nibble vai nos bits P4..P7; RS em P0; backlight em P3. Logica pura,
    testavel sem hardware -> ver demo().
    """
    alto = (value & 0xF0) | rs | bl
    baixo = ((value << 4) & 0xF0) | rs | bl
    return alto, baixo


class LCD:
    def __init__(self, addr=0x27, bus_id=1, backlight=True):
        import smbus
        self.addr = addr
        self.bus = smbus.SMBus(bus_id)
        self.bl = BACKLIGHT if backlight else 0
        # Sequencia de init do HD44780 em 4 bits (datasheet).
        for cmd in (0x33, 0x32, 0x28, 0x0C, 0x06, 0x01):
            self._cmd(cmd)
        time.sleep(0.002)

    def _pulse(self, bits):
        self.bus.write_byte(self.addr, bits)
        self.bus.write_byte(self.addr, bits | EN)
        time.sleep(0.0005)
        self.bus.write_byte(self.addr, bits & ~EN)
        time.sleep(0.0001)

    def _send(self, value, rs):
        alto, baixo = split_byte(value, rs, self.bl)
        self._pulse(alto)
        self._pulse(baixo)

    def _cmd(self, c):
        self._send(c, 0)

    def limpar(self):
        self._cmd(0x01)
        time.sleep(0.002)

    def escrever(self, linha, texto):
        """Escreve 'texto' na linha 0 ou 1, preenchendo 16 colunas."""
        self._cmd(0x80 if linha == 0 else 0xC0)
        for ch in texto.ljust(16)[:16]:
            self._send(ord(ch), RS)


def demo():
    """Auto-teste sem hardware: python3 lcd_i2c.py --test"""
    # RS=0, backlight ligado: nibbles de 0x41 ('A' = 0100 0001).
    alto, baixo = split_byte(0x41, 0, BACKLIGHT)
    assert alto == (0x40 | BACKLIGHT), hex(alto)
    assert baixo == (0x10 | BACKLIGHT), hex(baixo)
    # RS=1 aparece no bit P0 dos dois nibbles.
    a, b = split_byte(0x00, RS, 0)
    assert a & RS and b & RS, "RS deve estar setado nos dois nibbles"
    # Backlight desligado nao deixa residuo no bit P3.
    a, _ = split_byte(0xFF, 0, 0)
    assert not (a & BACKLIGHT), "backlight desligado"
    print("demo OK: divisao de nibbles com RS/backlight correta.")


def main():
    ap = argparse.ArgumentParser(description="Teste do LCD 16x2 I2C (PCF8574)")
    ap.add_argument("--addr", default="0x27", help="endereco I2C (ex.: 0x27 ou 0x3f)")
    ap.add_argument("--test", action="store_true", help="auto-teste sem hardware")
    args = ap.parse_args()

    if args.test:
        demo()
        return

    lcd = LCD(addr=int(args.addr, 16))
    lcd.limpar()
    lcd.escrever(0, "FECHADURA")
    lcd.escrever(1, "LCD I2C OK")
    print(f"LCD @ {args.addr}: mensagem escrita nas 2 linhas.")


if __name__ == "__main__":
    main()
