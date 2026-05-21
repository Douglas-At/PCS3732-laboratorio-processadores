/*
  Complemento1_Serial.ino - Calculadora de 4 bits em COMPLEMENTO DE UM (ESP32)

  SEM WiFi e SEM servidor web. Toda a interacao e pelo Serial Monitor (115200 baud).
  A entrada vem do teclado do computador (conectado pela USB do ESP32),
  lida com Serial.readString().

  Complemento de um (4 bits):
    - faixa -7 a +7
    - o zero tem DUAS representacoes: 0000 (+0) e 1111 (-0)
    - negativo = inverso bit-a-bit do positivo
    - SOMA usa END-AROUND CARRY: se houver vai-um (carry out) do bit mais
      significativo, esse carry e somado de volta ao bit menos significativo.

  O resultado de 4 bits e mostrado nos LEDs dos pinos 4, 5, 6 e 7
  (pino 7 = bit mais significativo / sinal, pino 4 = bit menos significativo).

  Como usar (Serial Monitor a 115200, "Nova linha"/Newline):
    Digite a operacao no formato:  A op B
    Exemplos:
       3 + 2
       0101 - 0011      (pode digitar em binario de 4 bits)
       -2 + -3
    Operacoes aceitas: + e -
*/

#include <Arduino.h>

// ---- Pinos dos LEDs (resultado em binario de 4 bits) ----
// ledPins[0] = bit 0 (LSB) ... ledPins[3] = bit 3 (MSB / sinal)
const int ledPins[4] = {4, 5, 6, 7};

// Mostra os 4 bits baixos de "valor" nos LEDs.
void mostrarNosLeds(int valor) {
  for (int i = 0; i < 4; i++) {
    digitalWrite(ledPins[i], (valor >> i) & 0x01 ? HIGH : LOW);
  }
}

// Devolve string com os 4 bits de um padrao (0..15), ex.: "1011".
String bin4(int v) {
  String s = "";
  for (int i = 3; i >= 0; i--) {
    s += ((v >> i) & 0x01) ? '1' : '0';
  }
  return s;
}

// ---- Complemento de um (4 bits) ----

// Converte um valor com sinal (-7..7) para o padrao de 4 bits em complemento de um.
int paraComplemento1(int n) {
  if (n >= 0) {
    return n & 0x0F;            // positivo: o proprio valor
  } else {
    // negativo: inverte os bits do modulo
    return (~(-n)) & 0x0F;
  }
}

// Converte um padrao de 4 bits (0..15) em complemento de um para o valor com sinal.
int deComplemento1(int bits) {
  bits &= 0x0F;
  if (bits & 0x08) {            // bit de sinal = 1 -> negativo
    return -((~bits) & 0x0F);   // inverte os bits e poe sinal negativo
  }
  return bits;                  // positivo
}

// Soma dois padroes de 4 bits em complemento de um, COM end-around carry.
// Retorna o padrao de 4 bits do resultado.
int somaComplemento1(int x, int y) {
  x &= 0x0F;
  y &= 0x0F;
  int soma = x + y;                 // pode ter ate 5 bits
  int carryOut = (soma >> 4) & 0x01; // vai-um do bit mais significativo
  soma &= 0x0F;                      // mantem 4 bits
  if (carryOut) {                    // END-AROUND CARRY
    soma = (soma + 1) & 0x0F;        // soma o carry de volta no LSB
  }
  return soma;
}

// Em complemento de um, A - B = A + (complemento de B).
int subComplemento1(int x, int y) {
  int negY = (~y) & 0x0F;            // complemento de um de B
  return somaComplemento1(x, negY);
}

// ---- Leitura da entrada ----

// Interpreta um token como numero: decimal (-7..7) ou binario de 4 bits.
// Devolve o padrao de 4 bits em complemento de um. *ok indica se foi valido.
int lerNumero(String t, bool *ok) {
  t.trim();
  *ok = false;
  if (t.length() == 0) return 0;

  // binario: exatamente ate 4 caracteres, so 0 e 1, com 2+ digitos para nao confundir com decimal
  bool soBin = true;
  for (unsigned int i = 0; i < t.length(); i++) {
    if (t[i] != '0' && t[i] != '1') { soBin = false; break; }
  }
  if (soBin && t.length() >= 2 && t.length() <= 4) {
    int u = 0;
    for (unsigned int i = 0; i < t.length(); i++) {
      u = (u << 1) | (t[i] - '0');
    }
    *ok = true;
    return u & 0x0F;               // ja e padrao de 4 bits
  }

  // decimal com sinal
  int val = t.toInt();
  // toInt() devolve 0 para texto invalido; valida basico
  if (val == 0 && t != "0" && t != "-0" && t != "+0") {
    return 0;                      // invalido, *ok continua false
  }
  if (val < -7 || val > 7) {
    return 0;                      // fora da faixa
  }
  *ok = true;
  return paraComplemento1(val);
}

void setup() {
  for (int i = 0; i < 4; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("=== Calculadora 4 bits - Complemento de Um ===");
  Serial.println("Faixa: -7 a +7  |  zero tem duas formas: 0000 (+0) e 1111 (-0)");
  Serial.println("Soma usa end-around carry.");
  Serial.println("Digite no formato:  A op B   (op = + ou -)");
  Serial.println("Exemplos:  3 + 2   |   0101 - 0011   |   -2 + -3");
  Serial.println("-----------------------------------------------");
}

void loop() {
  if (Serial.available()) {
    String linha = Serial.readString();
    linha.trim();
    if (linha.length() == 0) return;

    // descobre o operador. Procuramos + ou - que seja o operador (nao o sinal do 1o numero).
    char op = 0;
    int posOp = -1;
    // comeca a busca a partir do indice 1 para nao pegar um sinal negativo inicial
    for (unsigned int i = 1; i < linha.length(); i++) {
      char c = linha[i];
      if (c == '+' || c == '-') {
        // so e operador se vier depois de um espaco ou de um digito/letra (e nao logo apos outro sinal)
        char ant = linha[i - 1];
        if (ant == ' ' || (ant >= '0' && ant <= '9') || ant == '1' || ant == '0') {
          // garante que o proximo caractere faz parte de um numero
          op = c;
          posOp = i;
          break;
        }
      }
    }

    if (posOp < 0) {
      Serial.println("Formato invalido. Use:  A op B   (ex.: 3 + 2)");
      return;
    }

    String sa = linha.substring(0, posOp);
    String sb = linha.substring(posOp + 1);

    bool okA, okB;
    int aBits = lerNumero(sa, &okA);
    int bBits = lerNumero(sb, &okB);

    if (!okA || !okB) {
      Serial.println("Numero invalido. Decimal: -7 a 7. Binario: 2 a 4 bits (0/1).");
      return;
    }

    int aVal = deComplemento1(aBits);
    int bVal = deComplemento1(bBits);

    int resBits;
    if (op == '+') {
      resBits = somaComplemento1(aBits, bBits);
    } else {
      resBits = subComplemento1(aBits, bBits);
    }

    int resVal = deComplemento1(resBits);

    mostrarNosLeds(resBits);

    // imprime tudo no Serial Monitor
    Serial.print("A = "); Serial.print(aVal);
    Serial.print(" ("); Serial.print(bin4(aBits)); Serial.print(")   ");
    Serial.print(op);
    Serial.print("   B = "); Serial.print(bVal);
    Serial.print(" ("); Serial.print(bin4(bBits)); Serial.println(")");

    Serial.print("Resultado = "); Serial.print(resVal);
    Serial.print("  ->  bits nos LEDs: "); Serial.print(bin4(resBits));
    if (resBits == 0x0F || resBits == 0x00) {
      Serial.print("  (zero: ");
      Serial.print(resBits == 0x00 ? "+0 / 0000" : "-0 / 1111");
      Serial.print(")");
    }
    Serial.println();
    Serial.println("-----------------------------------------------");
  }
}
