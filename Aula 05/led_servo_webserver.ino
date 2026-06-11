// =========================================
// CONTROLE DE LED (PWM) + SERVOMOTOR - ESP32
//
//   - ESP32 como Access Point (softAP)
//   - WiFiServer na porta 80
//   - Pagina HTML em raw literal
//   - Dois sliders: duty do LED e angulo do servo
//   - Comandos via fetch() retornando JSON
// =========================================

#include <WiFi.h>

const char* ssid     = "ESP32-LED-Servo";
const char* password = "12345678";

WiFiServer server(80);

// -----------------------------------------
// LED (PWM via LEDC)
// -----------------------------------------
const int LED_PIN     = 5;        // LED externo (resistor 220-330 ohm)
const int LED_FREQ    = 1000;     // 1 kHz
const int LED_RES     = 8;        // 8 bits => duty 0 a 255
const int LED_DUTY_MAX = 255;

int dutyAtual = 0;

// -----------------------------------------
// Servo (PWM via LEDC)
// -----------------------------------------
// 50 Hz, 14 bits, pulso de 1,0 ms (0 graus) a 2,0 ms (180 graus)
const int  SERVO_PIN   = 4;
const int  SERVO_FREQ  = 50;
const int  SERVO_RES   = 14;      // 14 bits => 0 a 16383
const long PERIODO_US  = 20000;   // 20 ms

const int  PULSO_MIN_US = 1000;   // 0 graus
const int  PULSO_MAX_US = 2000;   // 180 graus

int anguloAtual = 90;

// =========================================
// HTML
// =========================================

String pagina = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Controle LED + Servo</title>

<style>
body{
  font-family:Arial;
  text-align:center;
  background:#101820;
  color:white;
  margin-top:30px;
}

input,button{
  padding:10px;
  margin:5px;
  font-size:18px;
}

input[type=range]{ width:90%; }

.card{
  background:#1d2b36;
  width:440px;
  max-width:92%;
  margin:auto;
  padding:20px;
  border-radius:12px;
  margin-bottom:25px;
}

.valor{ color:#80ffd0; font-weight:bold; }

.botoes button{ width:110px; }
</style>
</head>

<body>

<!-- ===== Card do LED ===== -->
<div class="card">
  <h1>Controle do LED</h1>

  <p>Intensidade (Duty Cycle)</p>
  <input type="range" id="duty" min="0" max="255" value="0" oninput="moverLed()">
  <div>Duty: <span class="valor" id="dutyVal">0</span> / 255
    (<span class="valor" id="dutyPct">0</span>%)</div>

  <div id="resLed" style="margin-top:15px;"></div>
</div>

<!-- ===== Card do Servo ===== -->
<div class="card">
  <h1>Controle do Servomotor</h1>

  <p>Angulo (0 a 180 graus)</p>
  <input type="range" id="ang" min="0" max="180" value="90" oninput="moverServo()">
  <div>Posicao: <span class="valor" id="angVal">90</span> graus</div>

  <div class="botoes" style="margin-top:10px;">
    <button onclick="setAng(0)">0</button>
    <button onclick="setAng(90)">90</button>
    <button onclick="setAng(180)">180</button>
  </div>

  <div id="resServo" style="margin-top:15px;"></div>
</div>

<script>

let timerLed = null;
let timerServo = null;

// ---------- LED ----------
function moverLed(){
  let d = parseInt(document.getElementById('duty').value);
  document.getElementById('dutyVal').innerText = d;
  document.getElementById('dutyPct').innerText = Math.round(d/255*100);
  clearTimeout(timerLed);
  timerLed = setTimeout(aplicarLed, 60);
}

function aplicarLed(){
  let duty = parseInt(document.getElementById('duty').value);
  fetch(`/led?duty=${duty}`)
  .then(r => r.json())
  .then(d => {
    if(d.erro){ return; }
    let pct = Math.round(d.duty / 255 * 100);
    document.getElementById('resLed').innerHTML =
      'Duty aplicado: <span class="valor">' + d.duty + '</span> / 255' +
      ' (<span class="valor">' + pct + '%</span>)';
  });
}

// ---------- Servo ----------
function mostrarAng(){
  document.getElementById('angVal').innerText =
    document.getElementById('ang').value;
}

function moverServo(){
  mostrarAng();
  clearTimeout(timerServo);
  timerServo = setTimeout(aplicarServo, 60);
}

function setAng(v){
  document.getElementById('ang').value = v;
  mostrarAng();
  aplicarServo();
}

function aplicarServo(){
  let ang = parseInt(document.getElementById('ang').value);
  fetch(`/servo?ang=${ang}`)
  .then(r => r.json())
  .then(d => {
    if(d.erro){ return; }
    document.getElementById('resServo').innerHTML =
      'Angulo aplicado: <span class="valor">' + d.ang + ' graus</span>' +
      '<br>Largura de pulso: <span class="valor">' + d.pulso + ' us</span>';
  });
}

</script>

</body>
</html>
)rawliteral";

// =========================================
// Funcoes auxiliares
// =========================================

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

// ---------- LED ----------
void aplicarLed(int duty){
  ledcWrite(LED_PIN, duty);
  dutyAtual = duty;

  Serial.print("LED -> duty=");
  Serial.println(duty);
}

// ---------- Servo ----------
long anguloParaPulso(int ang){
  return map(ang, 0, 180, PULSO_MIN_US, PULSO_MAX_US);
}

int pulsoParaDuty(long pulsoUs){
  long maxDuty = (1L << SERVO_RES) - 1;     // 14 bits => 16383
  return (int)((pulsoUs * maxDuty) / PERIODO_US);
}

long aplicarServo(int ang){
  long pulso = anguloParaPulso(ang);
  int  duty  = pulsoParaDuty(pulso);

  ledcWrite(SERVO_PIN, duty);
  anguloAtual = ang;

  Serial.print("Servo -> ang=");
  Serial.print(ang);
  Serial.print(" graus  pulso=");
  Serial.print(pulso);
  Serial.print(" us  duty=");
  Serial.println(duty);

  return pulso;
}

// =========================================
// HANDLERS
// =========================================

void tratarLed(WiFiClient &client, const String &req){

  int duty = pegarParametro(req, "duty").toInt();

  bool erro = (duty < 0 || duty > LED_DUTY_MAX);

  String json;

  if(erro){
    json = "{\"erro\":true}";
  }else{
    aplicarLed(duty);
    json = "{\"duty\":" + String(dutyAtual) + ",\"erro\":false}";
  }

  client.println("HTTP/1.1 200 OK");
  client.println("Content-type:application/json");
  client.println("Connection: close");
  client.println();
  client.println(json);
}

void tratarServo(WiFiClient &client, const String &req){

  int ang = pegarParametro(req, "ang").toInt();

  bool erro = (ang < 0 || ang > 180);

  String json;

  if(erro){
    json = "{\"erro\":true}";
  }else{
    long pulso = aplicarServo(ang);
    json = "{\"ang\":" + String(anguloAtual) +
           ",\"pulso\":" + String(pulso) +
           ",\"erro\":false}";
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

  // Canal LEDC do LED (1 kHz, 8 bits)
  bool okLed = ledcAttach(LED_PIN, LED_FREQ, LED_RES);
  Serial.print("ledcAttach LED: ");
  Serial.println(okLed ? "OK" : "FALHOU");
  aplicarLed(dutyAtual);

  // Canal LEDC do servo (50 Hz, 14 bits)
  bool okServo = ledcAttach(SERVO_PIN, SERVO_FREQ, SERVO_RES);
  Serial.print("ledcAttach Servo: ");
  Serial.println(okServo ? "OK" : "FALHOU");
  aplicarServo(anguloAtual);

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

  if(req.indexOf("GET /led") >= 0){

    tratarLed(client, req);

  }else if(req.indexOf("GET /servo") >= 0){

    tratarServo(client, req);

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
