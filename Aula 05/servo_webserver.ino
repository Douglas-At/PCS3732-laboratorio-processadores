// =========================================
// CONTROLE DE POSICAO DE SERVOMOTOR - ESP32
// PWM (LEDC) ~50 Hz, largura de pulso variavel
// Posicao (angulo) configuravel pela interface web
//
//   - ESP32 como Access Point (softAP)
//   - WiFiServer na porta 80
//   - Pagina HTML em raw literal
//   - Comandos via fetch() retornando JSON
// =========================================

#include <WiFi.h>

const char* ssid     = "ESP32-Servo";
const char* password = "12345678";

WiFiServer server(80);

// -----------------------------------------
// Configuracao do PWM para o servo (LEDC)
// -----------------------------------------
// Servos hobby: periodo de 20 ms (50 Hz),
// pulso de 1,0 ms (0 graus) a 2,0 ms (180 graus),
// sendo 1,5 ms = 90 graus (posicao central).
//
// Resolucao de 14 bits (0 a 16383): combinacao
// aceita pelo core a 50 Hz. O valor de duty e
// calculado a partir da largura de pulso (us).
const int   SERVO_PIN  = 4;       // pino de sinal do servo
const int   FREQ_SERVO = 50;      // 50 Hz
const int   RESOLUCAO  = 14;      // 14 bits => 0 a 16383
const long  PERIODO_US = 20000;   // 20 ms em microssegundos

const int   PULSO_MIN_US = 1000;  // 0 graus   (1,0 ms)
const int   PULSO_MAX_US = 2000;  // 180 graus (2,0 ms)

int anguloAtual = 90;             // posicao inicial

// =========================================
// HTML
// =========================================

String pagina = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Controle do Servomotor</title>

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

input[type=range]{ width:90%; }

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

.botoes button{ width:110px; }
</style>
</head>

<body>

<div class="card">

<h1>Controle do Servomotor</h1>

<p>Angulo (0 a 180 graus)</p>
<input type="range" id="ang" min="0" max="180" value="90" oninput="moverSlider()">
<div>Posicao: <span class="valor" id="angVal">90</span> graus</div>

<div class="botoes" style="margin-top:10px;">
  <button onclick="setAng(0)">0</button>
  <button onclick="setAng(90)">90</button>
  <button onclick="setAng(180)">180</button>
</div>

<div id="resultado" style="margin-top:20px;"></div>

<div id="historico-wrap" style="margin-top:30px;display:none;">
<h2>Historico de Posicoes</h2>
<table id="historico">
  <thead>
    <tr>
      <th>Angulo (graus)</th>
      <th>Pulso (us)</th>
      <th>Tempo (ms)</th>
    </tr>
  </thead>
  <tbody id="historico-body"></tbody>
</table>
</div>

</div>

<script>

let debounceTimer = null;

function mostrarAng(){
  document.getElementById('angVal').innerText =
    document.getElementById('ang').value;
}

// Chamado enquanto o slider e arrastado.
// Atualiza o numero na hora e agenda o envio
// (debounce de 60 ms) para nao inundar o ESP32.
function moverSlider(){
  mostrarAng();
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(aplicar, 60);
}

function setAng(v){
  document.getElementById('ang').value = v;
  mostrarAng();
  aplicar();
}

function aplicar(){

  let ang = parseInt(document.getElementById('ang').value);
  let box = document.getElementById('resultado');

  if(isNaN(ang) || ang < 0 || ang > 180){
    box.innerHTML = '<span class="aviso">Angulo entre 0 e 180 graus</span>';
    return;
  }

  let t0 = Date.now();

  fetch(`/servo?ang=${ang}`)
  .then(r => r.json())
  .then(d => {

    let tempo = Date.now() - t0;

    if(d.erro){
      box.innerHTML = '<span class="aviso">Posicao invalida.</span>';
      return;
    }

    box.innerHTML =
      'Angulo aplicado: <span class="valor">' + d.ang + ' graus</span>' +
      '<br>Largura de pulso: <span class="valor">' + d.pulso + ' us</span>';

    document.getElementById('historico-wrap').style.display = 'block';
    let tbody = document.getElementById('historico-body');
    let tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + d.ang + '</td>' +
      '<td>' + d.pulso + '</td>' +
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

// Converte um angulo (0-180) em largura de pulso (us)
long anguloParaPulso(int ang){
  return map(ang, 0, 180, PULSO_MIN_US, PULSO_MAX_US);
}

// Converte largura de pulso (us) em valor de duty.
// O duty maximo e derivado da resolucao (2^RESOLUCAO - 1),
// entao a conta continua certa se a resolucao mudar.
int pulsoParaDuty(long pulsoUs){
  long maxDuty = (1L << RESOLUCAO) - 1;     // 14 bits => 16383
  return (int)((pulsoUs * maxDuty) / PERIODO_US);
}

// Aplica a posicao no servo
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
// HANDLER /servo
// =========================================

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

  // Inicializa o canal LEDC para o servo (50 Hz, 14 bits).
  // Conferir o retorno: se vier FALHOU, a combinacao
  // freq/resolucao nao foi aceita e o servo nao se move.
  bool ok = ledcAttach(SERVO_PIN, FREQ_SERVO, RESOLUCAO);
  Serial.print("ledcAttach: ");
  Serial.println(ok ? "OK" : "FALHOU");

  // Posiciona o servo na posicao inicial
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

  if(req.indexOf("GET /servo") >= 0){

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
