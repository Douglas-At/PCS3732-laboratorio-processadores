// =========================================
// CALCULADORA 4 BITS - ESP32-C3
// Complemento de 2 com overflow
// Operacoes: + - * / fatorial
// + Benchmark multiplicacao: 2, 4, 8 bits
// =========================================

#include <WiFi.h>

const char* ssid     = "ESP32-Calc";
const char* password = "12345678";

WiFiServer server(80);

const int leds[4] = {4, 5, 6, 7};

#define N_REP 10000UL

struct Caso { int a; int b; };

// 2 bits com sinal: faixa -2 a 1
const Caso casos2[10] = {
  {-2,-2},{-2,-1},{-2,0},{-2,1},
  {-1,-1},{-1,0},{-1,1},
  {0,0},{0,1},{1,1}
};

// 4 bits com sinal: faixa -8 a 7
const Caso casos4[10] = {
  {-8,-8},{-8,7},{7,7},{-4,-4},
  {5,3},{-3,6},{2,-5},{1,7},
  {-6,-2},{4,4}
};

// 8 bits com sinal: faixa -128 a 127
const Caso casos8[10] = {
  {-128,-128},{-128,127},{127,127},{-64,64},
  {100,100},{-99,99},{33,-33},{15,15},
  {-50,50},{-1,-1}
};

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
body{font-family:Arial;text-align:center;background:#101820;color:white;margin-top:40px;padding-bottom:40px;}
input,select,button{padding:10px;margin:5px;font-size:18px;}
.card{background:#1d2b36;width:420px;margin:auto;padding:20px;border-radius:12px;margin-bottom:20px;}
.aviso{color:#ff8080;font-weight:bold;}
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
  <option value="mul">A &times; B</option>
  <option value="div">A &divide; B</option>
  <option value="fat">A!</option>
</select>
<br>
<button onclick="calc()">Calcular</button>
<div id="resultado" style="margin-top:20px;"></div>
</div>
<script>
function bin4(n){return(n&0x0F).toString(2).padStart(4,'0');}
function calc(){
  let a=parseInt(document.getElementById('a').value);
  let b=parseInt(document.getElementById('b').value);
  let op=document.getElementById('op').value;
  let box=document.getElementById('resultado');
  if(isNaN(a)||isNaN(b)||a<-8||a>7||b<-8||b>7){box.innerHTML='<span class="aviso">Use valores entre -8 e 7</span>';return;}
  fetch(`/calc?a=${a}&b=${b}&op=${op}`).then(r=>r.json()).then(d=>{
    if(d.erro){box.innerHTML='<span class="aviso">Operacao invalida.</span>';return;}
    let s='+';
    if(op==='sub')s='-';if(op==='mul')s='&times;';if(op==='div')s='&divide;';if(op==='fat')s='!';
    let conta=op==='fat'?a+'! = '+d.completo:a+' '+s+' '+b+' = '+d.completo;
    box.innerHTML='Resultado: '+d.resultado+'<br>Bits: '+bin4(d.bits)+'<br>'+conta+'<br>Overflow: '+(d.overflow?'SIM':'NAO');
  });
}
</script>
</body>
</html>
)rawliteral";

// =========================================
// Funcoes auxiliares — calculadora
// =========================================

void mostrarNosLeds(int valor){
  valor &= 0x0F;
  for(int i=0;i<4;i++) digitalWrite(leds[i],(valor>>i)&1);
}

int paraComSinal4bits(int v){
  v &= 0x0F;
  if(v & 0x08) return v-16;
  return v;
}

int fatorial(int n){
  if(n<0) return 0;
  int r=1;
  for(int i=2;i<=n;i++) r*=i;
  return r;
}

String pegarParametro(const String &req, const String &nome){
  int inicio=req.indexOf(nome+"=");
  if(inicio<0) return "";
  inicio+=nome.length()+1;
  int fim=req.indexOf('&',inicio);
  if(fim<0) fim=req.indexOf(' ',inicio);
  return req.substring(inicio,fim);
}

// =========================================
// CALCULO CALCULADORA
// =========================================

void tratarCalc(WiFiClient &client, const String &req){
  int aU=pegarParametro(req,"a").toInt()&0x0F;
  int bU=pegarParametro(req,"b").toInt()&0x0F;
  String op=pegarParametro(req,"op");
  int a=paraComSinal4bits(aU);
  int b=paraComSinal4bits(bU);
  int completo=0;
  bool erro=false;

  if(op=="add")      completo=a+b;
  else if(op=="sub") completo=a-b;
  else if(op=="mul") completo=a*b;
  else if(op=="div"){ if(b==0) erro=true; else completo=a/b; }
  else if(op=="fat"){ if(a<0)  erro=true; else completo=fatorial(a); }

  bool overflow=(completo<-8||completo>7);
  int bits=completo&0x0F;
  int resultado=paraComSinal4bits(bits);
  mostrarNosLeds(bits);

  String json;
  if(erro){
    json="{\"erro\":true}";
  }else{
    json="{\"resultado\":"+String(resultado)+
         ",\"bits\":"+String(bits)+
         ",\"completo\":"+String(completo)+
         ",\"overflow\":"+String(overflow?"true":"false")+"}";
  }

  client.println("HTTP/1.1 200 OK");
  client.println("Content-type:application/json");
  client.println("Connection: close");
  client.println();
  client.println(json);
}

// =========================================
// BENCHMARK — funcoes de tempo e impressao
// =========================================

// Retorna representacao binaria de v com 'bits' digitos (complemento de 2)
String toBin(int v, int bits){
  int mask = (1 << bits) - 1;
  v &= mask;
  String s = "";
  for(int i = bits-1; i >= 0; i--) s += String((v >> i) & 1);
  return s;
}

// Executa a*b N_REP vezes e retorna o tempo total em microsegundos
unsigned long medirTotalUs(int a, int b){
  volatile int32_t r;
  int32_t va=a, vb=b;
  unsigned long t0=micros();
  for(unsigned long i=0;i<N_REP;i++){
    r=va*vb;
  }
  return micros()-t0;
}

// Tempo medio por operacao em nanosegundos (usado pela interface web)
unsigned long medirNs(int a, int b){
  return medirTotalUs(a,b) * 1000UL / N_REP;
}

// Imprime tabela do benchmark no Serial Monitor
void printBenchmarkSerial(){
  const Caso* arrs[3]    = {casos2,   casos4,  casos8};
  const int   bitsV[3]   = {2,        4,        8};
  const int   minVals[3] = {-2,      -8,      -128};
  const int   maxVals[3] = { 1,       7,       127};

  Serial.println();
  Serial.println("=========================================");
  Serial.println("  BENCHMARK DE MULTIPLICACAO");
  Serial.print  ("  N_REP = "); Serial.print(N_REP); Serial.println(" repeticoes por caso");
  Serial.println("=========================================");

  for(int g = 0; g < 3; g++){
    int bits   = bitsV[g];
    int minVal = minVals[g];
    int maxVal = maxVals[g];
    int mask   = (1 << bits) - 1;

    Serial.println();
    Serial.print("--- "); Serial.print(bits);
    Serial.print(" bits  (faixa: "); Serial.print(minVal);
    Serial.print(" a "); Serial.print(maxVal); Serial.println(") ---");

    // Cabecalho da tabela
    Serial.println("Caso | A          | B          | Tempo(us) | Overflow");
    Serial.println("-----|------------|------------|-----------|--------");

    for(int i = 0; i < 10; i++){
      int a = arrs[g][i].a;
      int b = arrs[g][i].b;
      long res  = (long)a * (long)b;
      bool ov   = (res < minVal || res > maxVal);
      unsigned long t = medirTotalUs(a, b);

      String binA = toBin(a, bits);
      String binB = toBin(b, bits);

      // Imprime linha alinhada
      char buf[80];
      snprintf(buf, sizeof(buf), " %3d | %-10s | %-10s | %9lu | %s",
               i+1, binA.c_str(), binB.c_str(), t, ov ? "SIM" : "nao");
      Serial.println(buf);
    }
  }

  Serial.println();
  Serial.println("=========================================");
  Serial.println("  Benchmark concluido.");
  Serial.println("=========================================");
}

// =========================================
// Setup
// =========================================

void setup(){
  Serial.begin(115200);
  delay(500);

  for(int i=0;i<4;i++) pinMode(leds[i],OUTPUT);

  // Roda benchmark e imprime no Serial antes de iniciar o WiFi
  printBenchmarkSerial();

  WiFi.softAP(ssid,password);
  Serial.println();
  Serial.println("WiFi iniciado");
  Serial.println(WiFi.softAPIP());
  server.begin();
}

// =========================================
// Loop
// =========================================

void loop(){
  WiFiClient client=server.available();
  if(!client) return;

  String req=client.readStringUntil('\r');
  client.readStringUntil('\n');

  if(req.indexOf("GET /calc")>=0){
    tratarCalc(client,req);
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
