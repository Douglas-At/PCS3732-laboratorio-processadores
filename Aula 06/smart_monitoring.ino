// ============================================================
// SISTEMA DE MONITORAMENTO INTELIGENTE - ESP32  (Aula 06)
//
//   - Sensor LDR lido por ADC (12 bits, 0 a 4095)
//   - Valor disponivel em webserver local (>= 1 leitura/s)
//   - LED RGB built-in (neopixelWrite) com maquina de estados:
//       * Normal           -> LED apagado
//       * Baixa luminosidade -> pisca AMARELO a cada 2 s
//       * SOS (emergencia)   -> VERMELHO fixo por 3 s (PRIORIDADE MAX)
//   - Botao SOS tratado por INTERRUPCAO DE HARDWARE (attachInterrupt)
//     com tratamento de debounce via millis() dentro da ISR
//
//   Padrao de webserver reaproveitado da Aula 05:
//     - ESP32 como Access Point (softAP)
//     - WiFiServer na porta 80
//     - Pagina HTML em raw literal, dados via fetch() -> JSON
// ============================================================

#include <WiFi.h>

const char* ssid     = "ESP32-SOS-LDR";
const char* password = "12345678";

WiFiServer server(80);

// -----------------------------------------
// Mapa de pinos
// -----------------------------------------
// LDR no ADC1 (GPIO 32-39). ADC1 NAO conflita com o WiFi
// (o ADC2 fica indisponivel enquanto o radio esta ligado).
const int LDR_PIN = 34;          // ADC1_CH6, pino somente-entrada

// Botao de SOS: ligado entre o pino e o GND, usando pull-up interno.
// Em repouso le HIGH; ao pressionar vai para LOW => borda de descida (FALLING).
const int SOS_PIN = 27;          // pino com suporte a interrupcao

// LED RGB built-in da placa (NeoPixel). Mesmo recurso usado na Aula 02.
// Usamos neopixelWrite(LED_BUILTIN, R, G, B).

// -----------------------------------------
// Parametros de logica
// -----------------------------------------
const int  LIMIAR_ESCURO   = 1000;   // ADC abaixo disso = baixa luminosidade
const unsigned long PERIODO_PISCA_MS = 2000; // pisca amarelo a cada 2 s
const unsigned long TEMPO_SOS_MS     = 3000; // vermelho fixo por 3 s
const unsigned long DEBOUNCE_MS      = 200;  // janela de debounce do botao

// -----------------------------------------
// Estado compartilhado com a ISR (volatile!)
// -----------------------------------------
volatile bool          sosAtivo       = false; // emergencia em andamento
volatile unsigned long sosInicio      = 0;      // instante do disparo
volatile unsigned long ultimoDisparo  = 0;      // p/ debounce na ISR
volatile uint32_t      contadorSOS    = 0;      // quantas vezes acionou

// -----------------------------------------
// Estado de leitura / pisca (apenas no loop)
// -----------------------------------------
int           ultimoADC      = 0;
unsigned long ultimaLeitura  = 0;     // controla frequencia de leitura (1 Hz)
unsigned long ultimoToggle   = 0;     // controla o pisca amarelo
bool          amareloLigado  = false;

// =========================================
// HTML (interface do LDR)
// =========================================
String pagina = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitoramento LDR + SOS</title>
<style>
body{ font-family:Arial; text-align:center; background:#101820; color:white; margin-top:30px; }
.card{ background:#1d2b36; width:440px; max-width:92%; margin:auto; padding:20px;
       border-radius:12px; margin-bottom:25px; }
.valor{ color:#80ffd0; font-weight:bold; font-size:26px; }
.barra{ height:22px; background:#0a0f14; border-radius:11px; overflow:hidden; margin:12px 0; }
.fill{ height:100%; width:0%; background:#80ffd0; transition:width .3s; }
.estado{ font-size:22px; font-weight:bold; padding:8px; border-radius:8px; }
.normal{ background:#1f3b2c; color:#9effc0; }
.escuro{ background:#5a4a12; color:#ffe27a; }
.sos{ background:#5a1717; color:#ff8a8a; }
</style>
</head>
<body>
  <div class="card">
    <h1>Sensor de Luminosidade (LDR)</h1>
    <p>Leitura do ADC (12 bits)</p>
    <div><span class="valor" id="adc">--</span> / 4095</div>
    <div class="barra"><div class="fill" id="fill"></div></div>
    <div>Tensao estimada: <span class="valor" id="volt" style="font-size:18px">--</span> V</div>
    <div style="margin-top:15px;" class="estado normal" id="estado">--</div>
    <p style="color:#8aa;">Atualizado a cada 1 s</p>
  </div>
<script>
function atualizar(){
  fetch('/ldr')
  .then(r => r.json())
  .then(d => {
    document.getElementById('adc').innerText  = d.adc;
    document.getElementById('volt').innerText = d.volt.toFixed(2);
    document.getElementById('fill').style.width = (d.adc/4095*100) + '%';
    let e = document.getElementById('estado');
    if(d.sos){      e.className='estado sos';    e.innerText='EMERGENCIA SOS (LED VERMELHO)'; }
    else if(d.escuro){ e.className='estado escuro'; e.innerText='BAIXA LUMINOSIDADE (PISCA AMARELO)'; }
    else {          e.className='estado normal'; e.innerText='LUMINOSIDADE NORMAL'; }
  });
}
setInterval(atualizar, 1000);   // 1 Hz -> requisito de frequencia minima
atualizar();
</script>
</body>
</html>
)rawliteral";

// =========================================
// ISR do botao de SOS  (interrupcao de HARDWARE)
//
// Mantida CURTA: apenas trata o debounce e arma o estado.
// O acendimento do LED por 3 s acontece no loop (a ISR nao deve
// bloquear com delays). IRAM_ATTR coloca a rotina na RAM interna.
// =========================================
void IRAM_ATTR isrSOS(){
  unsigned long agora = millis();
  if(agora - ultimoDisparo > DEBOUNCE_MS){   // debounce: ignora ruido de contato
    sosAtivo      = true;
    sosInicio     = agora;
    ultimoDisparo = agora;
    contadorSOS++;
  }
}

// =========================================
// Funcoes auxiliares
// =========================================
String pegarParametro(const String &req, const String &nome){
  int inicio = req.indexOf(nome + "=");
  if(inicio < 0) return "";
  inicio += nome.length() + 1;
  int fim = req.indexOf('&', inicio);
  if(fim < 0) fim = req.indexOf(' ', inicio);
  return req.substring(inicio, fim);
}

// Le o LDR respeitando a frequencia de 1 Hz (telemetria de fundo).
void lerLDR(){
  if(millis() - ultimaLeitura >= 1000){
    ultimaLeitura = millis();
    ultimoADC = analogRead(LDR_PIN);          // 0 a 4095 (12 bits)
    Serial.print("LDR ADC = ");
    Serial.println(ultimoADC);
  }
}

// Maquina de estados do LED built-in, com PRIORIDADE para o SOS.
void atualizarLED(){
  // ---- Prioridade maxima: emergencia SOS (vermelho fixo por 3 s) ----
  if(sosAtivo){
    if(millis() - sosInicio < TEMPO_SOS_MS){
      neopixelWrite(LED_BUILTIN, 120, 0, 0);  // VERMELHO
      return;                                 // ignora qualquer outra condicao
    } else {
      sosAtivo     = false;                   // expirou os 3 s
      amareloLigado = false;
      ultimoToggle  = millis();
    }
  }

  // ---- Condicao de baixa luminosidade: pisca amarelo a cada 2 s ----
  if(ultimoADC < LIMIAR_ESCURO){
    if(millis() - ultimoToggle >= PERIODO_PISCA_MS){
      ultimoToggle  = millis();
      amareloLigado = !amareloLigado;
      if(amareloLigado) neopixelWrite(LED_BUILTIN, 120, 80, 0);  // AMARELO
      else              neopixelWrite(LED_BUILTIN, 0, 0, 0);     // apagado
    }
  } else {
    // ---- Luminosidade normal: LED apagado ----
    amareloLigado = false;
    neopixelWrite(LED_BUILTIN, 0, 0, 0);
  }
}

// =========================================
// HANDLER do endpoint /ldr  -> JSON
// =========================================
void tratarLDR(WiFiClient &client){
  float volt = ultimoADC * 3.3 / 4095.0;       // tensao estimada
  bool escuro = (ultimoADC < LIMIAR_ESCURO);

  String json = "{";
  json += "\"adc\":"   + String(ultimoADC) + ",";
  json += "\"volt\":"  + String(volt, 2)   + ",";
  json += "\"escuro\":"+ String(escuro ? "true" : "false") + ",";
  json += "\"sos\":"   + String(sosAtivo ? "true" : "false") + ",";
  json += "\"nSOS\":"  + String(contadorSOS);
  json += "}";

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

  pinMode(LED_BUILTIN, OUTPUT);
  neopixelWrite(LED_BUILTIN, 0, 0, 0);

  // ADC: resolucao padrao de 12 bits (0 a 4095) e atenuacao p/ faixa ~0-3.3 V
  analogReadResolution(12);
  analogSetPinAttenuation(LDR_PIN, ADC_11db);

  // Botao de SOS com pull-up interno + interrupcao na borda de descida
  pinMode(SOS_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(SOS_PIN), isrSOS, FALLING);

  WiFi.softAP(ssid, password);
  Serial.println();
  Serial.println("WiFi iniciado (softAP)");
  Serial.print("IP: ");
  Serial.println(WiFi.softAPIP());
  server.begin();
}

// =========================================
// Loop  (polling de baixa prioridade: LDR, web e LED)
// =========================================
void loop(){
  lerLDR();          // telemetria do LDR (1 Hz)
  atualizarLED();    // maquina de estados do LED (SOS tem prioridade)

  WiFiClient client = server.available();
  if(client){
    String req = client.readStringUntil('\r');
    client.readStringUntil('\n');

    if(req.indexOf("GET /ldr") >= 0){
      tratarLDR(client);
    } else {
      client.println("HTTP/1.1 200 OK");
      client.println("Content-type:text/html");
      client.println("Connection: close");
      client.println();
      client.println(pagina);
    }
    delay(1);
    client.stop();
  }
}
