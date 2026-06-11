// =========================================
// CONTROLE DE INTENSIDADE DE LED - ESP32
// PWM (LEDC) com FREQUENCIA e DUTY CYCLE
// configuraveis pela interface web
//
// Mesmo modelo da Calculadora 4 bits:
//   - ESP32 como Access Point (softAP)
//   - WiFiServer na porta 80
//   - Pagina HTML em raw literal
//   - Comandos via fetch() retornando JSON
// =========================================

#include <WiFi.h>

const char* ssid     = "ESP32-PWM";
const char* password = "12345678";

WiFiServer server(80);

// -----------------------------------------
// Configuracao do PWM (LEDC)
// -----------------------------------------
const int   LED_PIN     = 4;      // pino do LED externo (com resistor de 220-330 ohm)
const int   RESOLUCAO   = 8;      // 8 bits => duty de 0 a 255
const int   DUTY_MAX     = 255;   // (2^8 - 1)

int freqAtual = 1000;             // frequencia inicial em Hz
int dutyAtual = 0;                // duty inicial (0 a 255)

// =========================================
// HTML
// =========================================

String pagina = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Controle PWM do LED</title>

<style>
body{
  font-family:Arial;
  text-align:center;
  background:#101820;
  color:white;
  margin-top:30px;
}

input,select,button{
  padding:10px;
  margin:5px;
  font-size:18px;
}

input[type=range]{
  width:90%;
}

.card{
  background:#1d2b36;
  width:440px;
  max-width:92%;
  margin:auto;
  padding:20px;
  border-radius:12px;
}

.aviso{ color:#ff8080; font-weight:bold; }
.valor{ color:#80ffd0; font-weight:bold; }

table{ margin:auto; border-collapse:collapse; min-width:380px; }
th,td{ border:1px solid #444; padding:6px 14px; }
</style>
</head>

<body>

<div class="card">

<h1>Controle PWM do LED</h1>

<p>Frequencia (Hz)</p>
<input type="number" id="freq" min="1" max="40000" value="1000" step="1">
<select id="freqPreset" onchange="aplicarPreset()">
  <option value="">-- presets --</option>
  <option value="50">50 Hz</option>
  <option value="100">100 Hz</option>
  <option value="500">500 Hz</option>
  <option value="1000">1 kHz</option>
  <option value="5000">5 kHz</option>
  <option value="10000">10 kHz</option>
</select>

<p>Intensidade (Duty Cycle)</p>
<input type="range" id="duty" min="0" max="255" value="0" oninput="mostrarDuty()">
<div>Duty: <span class="valor" id="dutyVal">0</span> / 255
  (<span class="valor" id="dutyPct">0</span>%)</div>

<br>
<button onclick="aplicar()">Aplicar</button>

<div id="resultado" style="margin-top:20px;"></div>

<div id="historico-wrap" style="margin-top:30px;display:none;">
<h2>Historico de Testes</h2>
<table id="historico">
  <thead>
    <tr>
      <th>Frequencia (Hz)</th>
      <th>Duty (0-255)</th>
      <th>Intensidade (%)</th>
      <th>Tempo (ms)</th>
    </tr>
  </thead>
  <tbody id="historico-body"></tbody>
</table>
</div>

</div>

<script>

function mostrarDuty(){
  let d = parseInt(document.getElementById('duty').value);
  document.getElementById('dutyVal').innerText = d;
  document.getElementById('dutyPct').innerText = Math.round(d/255*100);
}

function aplicarPreset(){
  let p = document.getElementById('freqPreset').value;
  if(p !== ''){
    document.getElementById('freq').value = p;
  }
}

function aplicar(){

  let freq = parseInt(document.getElementById('freq').value);
  let duty = parseInt(document.getElementById('duty').value);

  let box = document.getElementById('resultado');

  if(isNaN(freq) || freq < 1 || freq > 40000){
    box.innerHTML = '<span class="aviso">Frequencia entre 1 e 40000 Hz</span>';
    return;
  }

  if(isNaN(duty) || duty < 0 || duty > 255){
    box.innerHTML = '<span class="aviso">Duty entre 0 e 255</span>';
    return;
  }

  let t0 = Date.now();

  fetch(`/set?freq=${freq}&duty=${duty}`)
  .then(r => r.json())
  .then(d => {

    let tempo = Date.now() - t0;

    if(d.erro){
      box.innerHTML = '<span class="aviso">Configuracao invalida.</span>';
      return;
    }

    let pct = Math.round(d.duty / 255 * 100);

    box.innerHTML =
      'Frequencia aplicada: <span class="valor">' + d.freq + ' Hz</span>' +
      '<br>Duty aplicado: <span class="valor">' + d.duty + '</span> / 255' +
      '<br>Intensidade: <span class="valor">' + pct + '%</span>';

    document.getElementById('historico-wrap').style.display = 'block';
    let tbody = document.getElementById('historico-body');
    let tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + d.freq + '</td>' +
      '<td>' + d.duty + '</td>' +
      '<td>' + pct + '%</td>' +
      '<td>' + tempo + ' ms</td>';
    tbody.appendChild(tr);
  });
}

</script>

</body>
</html>
)rawliteral";

// =========================================
// Funcoes
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

// Aplica frequencia + duty no LED via LEDC.
// Reanexar o pino com ledcAttach reinicializa o canal
// com a nova frequencia mantendo a resolucao.
void aplicarPWM(int freq, int duty){

  ledcAttach(LED_PIN, freq, RESOLUCAO);
  ledcWrite(LED_PIN, duty);

  freqAtual = freq;
  dutyAtual = duty;

  Serial.print("PWM -> freq=");
  Serial.print(freq);
  Serial.print(" Hz  duty=");
  Serial.println(duty);
}

// =========================================
// HANDLER /set
// =========================================

void tratarSet(WiFiClient &client, const String &req){

  int freq = pegarParametro(req, "freq").toInt();
  int duty = pegarParametro(req, "duty").toInt();

  bool erro = false;

  if(freq < 1 || freq > 40000) erro = true;
  if(duty < 0 || duty > DUTY_MAX) erro = true;

  String json;

  if(erro){

    json = "{\"erro\":true}";

  }else{

    aplicarPWM(freq, duty);

    json = "{\"freq\":" + String(freqAtual) +
           ",\"duty\":" + String(dutyAtual) +
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

  // Inicializa o PWM com a config inicial
  aplicarPWM(freqAtual, dutyAtual);

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

  if(req.indexOf("GET /set") >= 0){

    tratarSet(client, req);

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
