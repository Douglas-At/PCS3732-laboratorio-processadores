/*
  WiFiAccessPoint.ino - Calculadora de 4 bits COM SINAL via interface web (ESP32)

  Os operandos sao inteiros de 4 bits em complemento de dois: -8 a +7.
  Operacoes: soma e subtracao.
  O resultado e mostrado em binario (4 bits) nos LEDs dos pinos 4, 5, 6 e 7
  (pino 7 = bit mais significativo / bit de sinal, pino 4 = bit menos significativo)
  e tambem exibido na pagina web (em decimal com sinal e em binario).

  Indica OVERFLOW aritmetico de complemento de dois (quando o resultado
  verdadeiro nao cabe na faixa -8..+7).

  Na pagina da para digitar cada operando em DECIMAL (-8 a 7) ou em BINARIO (4 bits).

  Como usar:
    1. Conecte-se ao ponto de acesso "yourAP" (senha "yourPassword")
    2. Abra http://192.168.4.1/ no navegador

  Baseado no exemplo WiFiAccessPoint do arduino-esp32.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <NetworkClient.h>
#include <WiFiAP.h>

// ---- Pinos dos LEDs (resultado em binario de 4 bits) ----
// ledPins[0] = bit 0 (LSB) ... ledPins[3] = bit 3 (MSB / sinal)
const int ledPins[4] = {4, 5, 6, 7};

// Credenciais do ponto de acesso.
const char *ssid = "yourAP";
const char *password = "yourPassword";

NetworkServer server(80);

// Mostra os 4 bits baixos de "valor" nos LEDs.
void mostrarNosLeds(int valor) {
  for (int i = 0; i < 4; i++) {
    digitalWrite(ledPins[i], (valor >> i) & 0x01 ? HIGH : LOW);
  }
}

// Converte um valor de 4 bits (0..15) interpretado em complemento de dois para -8..+7
int paraComSinal4bits(int v) {
  v &= 0x0F;
  if (v & 0x08) {       // bit de sinal ligado
    return v - 16;      // valor negativo
  }
  return v;
}

// ---- Pagina HTML com JavaScript embutido ----
const char PAGINA_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Calculadora 4 bits com sinal - ESP32</title>
  <style>
    body { font-family: sans-serif; max-width: 440px; margin: 24px auto; padding: 0 16px; }
    h1 { font-size: 1.3rem; }
    fieldset { margin-top: 14px; border: 1px solid #ccc; border-radius: 6px; }
    legend { font-weight: bold; }
    label { display:block; margin-top: 8px; }
    input, select, button { font-size: 1rem; padding: 6px; margin-top: 4px; box-sizing: border-box; }
    input[type=number], input[type=text], select { width: 100%; }
    button { margin-top: 18px; cursor: pointer; width: 100%; }
    .modo { display:flex; gap: 12px; align-items:center; }
    .modo label { display:inline; margin-top:0; font-weight:normal; }
    #resultado { margin-top: 18px; padding: 12px; border: 1px solid #ccc; border-radius: 6px; min-height: 1.4em; }
    .aviso { color: #b00; font-weight: bold; }
    small { color:#555; }
  </style>
</head>
<body>
  <h1>Calculadora de 4 bits (com sinal -8 a +7)</h1>

  <fieldset>
    <legend>Operando A</legend>
    <div class="modo">
      <label><input type="radio" name="modoA" value="dec" checked onchange="trocaModo('A')"> Decimal</label>
      <label><input type="radio" name="modoA" value="bin" onchange="trocaModo('A')"> Binario</label>
    </div>
    <input type="number" id="aDec" min="-8" max="7" value="0">
    <input type="text" id="aBin" maxlength="4" placeholder="ex.: 0101" style="display:none">
    <small>Decimal: -8 a 7 &nbsp;|&nbsp; Binario: 4 bits (1000 = -8)</small>
  </fieldset>

  <label for="op" style="font-weight:bold; margin-top:14px;">Operacao</label>
  <select id="op">
    <option value="add">A + B (soma)</option>
    <option value="sub">A - B (subtracao)</option>
  </select>

  <fieldset>
    <legend>Operando B</legend>
    <div class="modo">
      <label><input type="radio" name="modoB" value="dec" checked onchange="trocaModo('B')"> Decimal</label>
      <label><input type="radio" name="modoB" value="bin" onchange="trocaModo('B')"> Binario</label>
    </div>
    <input type="number" id="bDec" min="-8" max="7" value="0">
    <input type="text" id="bBin" maxlength="4" placeholder="ex.: 1110" style="display:none">
    <small>Decimal: -8 a 7 &nbsp;|&nbsp; Binario: 4 bits (1000 = -8)</small>
  </fieldset>

  <button id="calcular">Calcular</button>

  <div id="resultado">Informe os valores e clique em Calcular.</div>

<script>
// alterna entre os campos decimal e binario
function trocaModo(qual) {
  let modo = document.querySelector('input[name=modo' + qual + ']:checked').value;
  document.getElementById(qual.toLowerCase() + 'Dec').style.display = (modo === 'dec') ? '' : 'none';
  document.getElementById(qual.toLowerCase() + 'Bin').style.display = (modo === 'bin') ? '' : 'none';
}

// representacao binaria de 4 bits em complemento de dois para um valor -8..7
function bin4comSinal(n) {
  return ((n & 0x0F) >>> 0).toString(2).padStart(4, '0');
}

// le um operando (A ou B) e devolve o valor decimal com sinal, ou null se invalido
function lerOperando(qual) {
  let modo = document.querySelector('input[name=modo' + qual + ']:checked').value;
  if (modo === 'dec') {
    let v = parseInt(document.getElementById(qual.toLowerCase() + 'Dec').value, 10);
    if (isNaN(v) || v < -8 || v > 7) return null;
    return v;
  } else {
    let s = document.getElementById(qual.toLowerCase() + 'Bin').value.trim();
    if (!/^[01]{1,4}$/.test(s)) return null;     // so 0 e 1, ate 4 digitos
    let u = parseInt(s.padStart(4, '0'), 2);     // 0..15
    return (u & 0x08) ? u - 16 : u;              // complemento de dois -> -8..7
  }
}

document.getElementById('calcular').addEventListener('click', function () {
  const box = document.getElementById('resultado');
  let a = lerOperando('A');
  let b = lerOperando('B');
  let op = document.getElementById('op').value;

  if (a === null || b === null) {
    box.innerHTML = '<span class="aviso">Valores invalidos. Decimal: -8 a 7. Binario: ate 4 bits (0/1).</span>';
    return;
  }

  box.textContent = 'Calculando...';

  // envia em complemento de dois (0..15) para o ESP32
  let aU = a & 0x0F;
  let bU = b & 0x0F;

  fetch('/calc?a=' + aU + '&b=' + bU + '&op=' + op)
    .then(r => r.json())
    .then(d => {
      // d.resultado = valor com sinal (-8..7), d.bits = padrao de 4 bits (0..15)
      let txt = 'Resultado: ' + d.resultado +
                '<br>Em binario (4 bits): ' + bin4comSinal(d.bits) +
                '<br>Conta: ' + a + (op === 'add' ? ' + ' : ' - ') + b + ' = ' + d.completo;
      if (d.overflow) {
        txt += '<br><span class="aviso">OVERFLOW! O resultado verdadeiro (' + d.completo +
               ') nao cabe na faixa -8 a +7. Os LEDs mostram os 4 bits truncados.</span>';
      }
      box.innerHTML = txt;
    })
    .catch(() => {
      box.innerHTML = '<span class="aviso">Falha ao comunicar com o ESP32.</span>';
    });
});
</script>
</body>
</html>
)HTML";

// Extrai o valor de um parametro (ex.: "a") da linha de request HTTP.
String pegarParametro(const String &req, const String &nome) {
  String chave = nome + "=";
  int ini = req.indexOf(chave);
  if (ini < 0) return "";
  ini += chave.length();
  int fim = ini;
  while (fim < (int)req.length()) {
    char c = req[fim];
    if (c == '&' || c == ' ' || c == '\r' || c == '\n') break;
    fim++;
  }
  return req.substring(ini, fim);
}

// Faz a conta com sinal, acende os LEDs e devolve JSON.
void tratarCalc(NetworkClient &client, const String &req) {
  // recebe os operandos ja em complemento de dois (0..15)
  int aU = pegarParametro(req, "a").toInt() & 0x0F;
  int bU = pegarParametro(req, "b").toInt() & 0x0F;
  String op = pegarParametro(req, "op");

  // converte para valores com sinal -8..7
  int a = paraComSinal4bits(aU);
  int b = paraComSinal4bits(bU);

  int completo = 0;       // resultado verdadeiro (sem truncar)
  if (op == "add") {
    completo = a + b;
  } else if (op == "sub") {
    completo = a - b;
  }

  // overflow de complemento de dois: resultado verdadeiro fora de -8..+7
  bool overflow = (completo < -8 || completo > 7);

  int bits = completo & 0x0F;             // padrao de 4 bits que vai aos LEDs
  int resultado = paraComSinal4bits(bits); // valor com sinal apos truncar (o que os 4 bits representam)

  mostrarNosLeds(bits);

  String json = "{\"resultado\":" + String(resultado) +
                ",\"bits\":" + String(bits) +
                ",\"completo\":" + String(completo) +
                ",\"overflow\":" + String(overflow ? "true" : "false") + "}";

  client.println("HTTP/1.1 200 OK");
  client.println("Content-type:application/json");
  client.println("Connection: close");
  client.println();
  client.println(json);
}

// Envia a pagina HTML principal.
void enviarPagina(NetworkClient &client) {
  client.println("HTTP/1.1 200 OK");
  client.println("Content-type:text/html");
  client.println("Connection: close");
  client.println();
  client.print(PAGINA_HTML);
  client.println();
}

void setup() {
  for (int i = 0; i < 4; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  Serial.begin(115200);
  Serial.println();
  Serial.println("Configurando ponto de acesso...");

  if (!WiFi.softAP(ssid, password)) {
    log_e("Falha ao criar o Soft AP.");
    while (1);
  }
  IPAddress myIP = WiFi.softAPIP();
  Serial.print("IP do AP: ");
  Serial.println(myIP);
  server.begin();

  Serial.println("Servidor iniciado");
}

void loop() {
  NetworkClient client = server.accept();

  if (client) {
    Serial.println("Novo cliente.");
    String currentLine = "";
    String requestLine = "";

    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        Serial.write(c);
        if (c == '\n') {
          if (currentLine.length() == 0) {
            if (requestLine.indexOf("GET /calc") >= 0) {
              tratarCalc(client, requestLine);
            } else {
              enviarPagina(client);
            }
            break;
          } else {
            if (requestLine.length() == 0) {
              requestLine = currentLine;
            }
            currentLine = "";
          }
        } else if (c != '\r') {
          currentLine += c;
        }
      }
    }
    client.stop();
    Serial.println("Cliente desconectado.");
  }
}
