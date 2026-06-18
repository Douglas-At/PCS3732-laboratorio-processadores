// ============================================================
// DESAFIO - SEMAFORO INTELIGENTE  (Aula 06)
//
//   Evolucao do semaforo da Aula 02, agora com:
//     1) MODO NOTURNO automatico: ao detectar baixa luminosidade
//        pelo LDR (ADC), o semaforo entra em alerta piscando
//        AMARELO a cada 1 s (1 Hz).
//     2) BOTAO DE PEDESTRE por INTERRUPCAO DE HARDWARE: ao solicitar
//        travessia durante o dia, o semaforo interrompe o fluxo de
//        transito com seguranca (fecha em vermelho) e depois retoma.
//
//   O semaforo veicular e representado no LED RGB built-in
//   (neopixelWrite), no mesmo estilo da Aula 02.
//   Maquina de estados NAO bloqueante (millis), para que o LDR e a
//   interrupcao continuem responsivos.
// ============================================================

// -----------------------------------------
// Pinos
// -----------------------------------------
const int LDR_PIN  = 4;    // mesmo pino do smart_monitoring (sua montagem real)
const int PED_PIN  = 5;    // botao de pedestre -> GND (INPUT_PULLUP), interrupcao
// Semaforo veicular = LED RGB built-in (neopixelWrite)

// -----------------------------------------
// Parametros
// -----------------------------------------
const int  LIMIAR_ESCURO = 1000;     // ADC abaixo disso = modo noturno
const unsigned long DEBOUNCE_MS = 250;

// Tempos de cada fase do semaforo veicular (modo diurno)
const unsigned long T_VERDE    = 4000;
const unsigned long T_AMARELO  = 1500;
const unsigned long T_VERMELHO = 4000;  // tambem usado p/ travessia de pedestre

// -----------------------------------------
// Estados
// -----------------------------------------
enum Fase { VERDE, AMARELO, VERMELHO };
Fase fase = VERDE;

unsigned long inicioFase   = 0;
unsigned long ultimaLeitura = 0;
int  ultimoADC = 0;

// Pisca do modo noturno (1 Hz)
unsigned long ultimoBlink = 0;
bool amareloOn = false;

// Compartilhado com a ISR
volatile bool          pedidoPedestre = false;
volatile unsigned long ultimoDisparo  = 0;

// =========================================
// ISR do botao de pedestre (interrupcao de HARDWARE)
// Curta: apenas registra o pedido, com debounce.
// =========================================
void IRAM_ATTR isrPedestre(){
  unsigned long agora = millis();
  if(agora - ultimoDisparo > DEBOUNCE_MS){
    pedidoPedestre = true;
    ultimoDisparo  = agora;
  }
}

// =========================================
// Cores do semaforo veicular
// =========================================
void luzVerde()    { neopixelWrite(LED_BUILTIN, 0, 100, 0); }
void luzAmarela()  { neopixelWrite(LED_BUILTIN, 120, 80, 0); }
void luzVermelha() { neopixelWrite(LED_BUILTIN, 120, 0, 0); }
void luzApagada()  { neopixelWrite(LED_BUILTIN, 0, 0, 0); }

void trocarFase(Fase nova){
  fase = nova;
  inicioFase = millis();
  if(nova == VERDE)         luzVerde();
  else if(nova == AMARELO)  luzAmarela();
  else                      luzVermelha();
}

// =========================================
// Leitura do LDR (telemetria a 1 Hz)
// =========================================
void lerLDR(){
  if(millis() - ultimaLeitura >= 1000){
    ultimaLeitura = millis();
    ultimoADC = 4095 - analogRead(LDR_PIN);   // inverte: escuro = valor baixo
    Serial.print("LDR ADC = ");
    Serial.println(ultimoADC);
  }
}

// =========================================
// Setup
// =========================================
void setup(){
  Serial.begin(115200);

  pinMode(LED_BUILTIN, OUTPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(LDR_PIN, ADC_11db);

  pinMode(PED_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PED_PIN), isrPedestre, FALLING);

  trocarFase(VERDE);
  Serial.println("Semaforo inteligente iniciado");
}

// =========================================
// Loop
// =========================================
void loop(){
  lerLDR();

  // ---------- MODO NOTURNO: baixa luminosidade -> pisca amarelo 1 Hz ----------
  // Montagem real: MAIS luz -> MAIOR tensao -> ADC ALTO. Logo ADC baixo = escuro.
  if(ultimoADC < LIMIAR_ESCURO){
    if(millis() - ultimoBlink >= 500){   // meio periodo de 1 Hz (ON/OFF a cada 0,5 s)
      ultimoBlink = millis();
      amareloOn = !amareloOn;
      if(amareloOn) luzAmarela();
      else          luzApagada();
    }
    pedidoPedestre = false;  // de noite o ciclo normal fica suspenso
    return;
  }

  // ---------- MODO DIURNO: ciclo normal verde -> amarelo -> vermelho ----------
  unsigned long decorrido = millis() - inicioFase;

  switch(fase){
    case VERDE:
      // Se houver pedido de pedestre, encurta o verde indo p/ amarelo.
      if(pedidoPedestre || decorrido >= T_VERDE){
        if(pedidoPedestre) Serial.println("Pedido de travessia -> fechando para pedestre");
        trocarFase(AMARELO);
      }
      break;

    case AMARELO:
      if(decorrido >= T_AMARELO){
        trocarFase(VERMELHO);
      }
      break;

    case VERMELHO:
      // Vermelho mantem transito parado (travessia segura do pedestre).
      if(decorrido >= T_VERMELHO){
        pedidoPedestre = false;   // pedido atendido
        trocarFase(VERDE);
      }
      break;
  }
}
