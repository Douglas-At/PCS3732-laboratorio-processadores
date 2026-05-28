// =========================================
// CALCULADORA 4 BITS - ESP32-C3
// Complemento de 2 com overflow
// Operacoes:
// +  -  *  /  fatorial
// =========================================

#include <WiFi.h>

const char* ssid = "ESP32-Calc";
const char* password = "12345678";

WiFiServer server(80);

const int leds[4] = {4, 5, 6, 7};

// =========================================
// HTML
// =========================================

String pagina = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Calculadora 4 bits</title>

<style>
body{
  font-family:Arial;
  text-align:center;
  background:#101820;
  color:white;
  margin-top:40px;
}

input,select,button{
  padding:10px;
  margin:5px;
  font-size:18px;
}

.card{
  background:#1d2b36;
  width:420px;
  margin:auto;
  padding:20px;
  border-radius:12px;
}

.aviso{
  color:#ff8080;
  font-weight:bold;
}
</style>
</head>

<body>

<div class="card">

<h1>Calculadora 4 bits</h1>

<label>A</label><br>
<input type="number" id="a" min="-8" max="7" value="0"><br>

<label>B</label><br>
<input type="number" id="b" min="-8" max="7" value="0"><br>

<select id="op">
  <option value="add">A + B</option>
  <option value="sub">A - B</option>
  <option value="mul">A × B</option>
  <option value="div">A ÷ B</option>
  <option value="fat">A!</option>
</select>

<br>

<button onclick="calc()">Calcular</button>

<div id="resultado" style="margin-top:20px;"></div>

</div>

<script>

function bin4(n){
  return (n & 0x0F).toString(2).padStart(4,'0');
}

function calc(){

  let a = parseInt(document.getElementById('a').value);
  let b = parseInt(document.getElementById('b').value);
  let op = document.getElementById('op').value;

  let box = document.getElementById('resultado');

  if(isNaN(a) || isNaN(b) || a < -8 || a > 7 || b < -8 || b > 7){
    box.innerHTML = '<span class="aviso">Use valores entre -8 e 7</span>';
    return;
  }

  fetch(`/calc?a=${a}&b=${b}&op=${op}`)
  .then(r => r.json())
  .then(d => {

    if(d.erro){
      box.innerHTML = '<span class="aviso">Operacao invalida.</span>';
      return;
    }

    let simbolo = '+';

    if(op === 'sub') simbolo = '-';
    if(op === 'mul') simbolo = '×';
    if(op === 'div') simbolo = '÷';
    if(op === 'fat') simbolo = '!';

    let conta;

    if(op === 'fat'){
      conta = a + '! = ' + d.completo;
    }else{
      conta = a + ' ' + simbolo + ' ' + b + ' = ' + d.completo;
    }

    let txt =
      'Resultado assinado: ' + d.resultado +
      '<br>Bits: ' + bin4(d.bits) +
      '<br>' + conta +
      '<br>Overflow: ' + (d.overflow ? 'SIM' : 'NAO');

    box.innerHTML = txt;
  });
}

</script>

</body>
</html>
)rawliteral";

// =========================================
// Funcoes
// =========================================

void mostrarNosLeds(int valor){

  valor &= 0x0F;

  for(int i=0;i<4;i++){
    digitalWrite(leds[i], (valor >> i) & 1);
  }
}

int paraComSinal4bits(int v){

  v &= 0x0F;

  if(v & 0x08){
    return v - 16;
  }

  return v;
}

int fatorial(int n){

  if(n < 0) return 0;

  int r = 1;

  for(int i=2;i<=n;i++){
    r *= i;
  }

  return r;
}

String pegarParametro(const String &req, const String &nome){

  int inicio = req.indexOf(nome + "=");

  if(inicio < 0) return "";

  inicio += nome.length() + 1;

  int fim = req.indexOf('&', inicio);

  if(fim < 0){
    fim = req.indexOf(' ', inicio);
  }

  return req.substring(inicio, fim);
}

// =========================================
// CALCULO
// =========================================

void tratarCalc(WiFiClient &client, const String &req){

  int aU = pegarParametro(req, "a").toInt() & 0x0F;
  int bU = pegarParametro(req, "b").toInt() & 0x0F;

  String op = pegarParametro(req, "op");

  int a = paraComSinal4bits(aU);
  int b = paraComSinal4bits(bU);

  int completo = 0;
  bool erro = false;

  if(op == "add"){

    completo = a + b;

  }else if(op == "sub"){

    completo = a - b;

  }else if(op == "mul"){

    completo = a * b;

  }else if(op == "div"){

    if(b == 0){
      erro = true;
    }else{
      completo = a / b;
    }

  }else if(op == "fat"){

    if(a < 0){
      erro = true;
    }else{
      completo = fatorial(a);
    }
  }

  bool overflow = (completo < -8 || completo > 7);

  int bits = completo & 0x0F;

  int resultado = paraComSinal4bits(bits);

  mostrarNosLeds(bits);

  String json;

  if(erro){

    json = "{\"erro\":true}";

  }else{

    json = "{\"resultado\":" + String(resultado) +
           ",\"bits\":" + String(bits) +
           ",\"completo\":" + String(completo) +
           ",\"overflow\":" + String(overflow ? "true" : "false") + "}";
  }

  client.println("HTTP/1.1 200 OK");
  client.println("Content-type:application/json");
  client.println("Connection: close");
  client.println();
  client.println(json);
}

// =========================================
// Setup
// =========================================

void setup(){

  Serial.begin(115200);

  for(int i=0;i<4;i++){
    pinMode(leds[i], OUTPUT);
  }

  WiFi.softAP(ssid, password);

  Serial.println();
  Serial.println("WiFi iniciado");
  Serial.println(WiFi.softAPIP());
  server.begin();
}

// =========================================
// Loop
// =========================================

void loop(){

  WiFiClient client = server.available();

  if(!client){
    return;
  }

  String req = client.readStringUntil('\r');

  client.readStringUntil('\n');

  if(req.indexOf("GET /calc") >= 0){

    tratarCalc(client, req);

  }else{

    client.println("HTTP/1.1 200 OK");
    client.println("Content-type:text/html");
    client.println("Connection: close");
    client.println();
    client.println(pagina);
  }

  delay(1);
  client.stop();
}
