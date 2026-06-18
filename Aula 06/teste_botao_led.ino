// ============================================================
// ETAPA 2 - TESTE INDEPENDENTE DE HARDWARE  (Aula 06)
//
//   Objetivo: validar a montagem do botao externo em protoboard
//   acionando um LED externo, ANTES de implementar a interrupcao.
//
//   Este teste usa POLLING simples (le o botao no loop). Serve para
//   garantir que nao ha curtos nem conexoes frouxas. Registrar os
//   resultados intermediarios no relatorio (Etapa 2).
//
//   Montagem:
//     - Botao entre BOTAO_PIN e GND, usando pull-up interno
//       (em repouso = HIGH; pressionado = LOW)
//     - LED externo no LED_PIN, em serie com resistor de 220-330 ohm,
//       outro terminal no GND
// ============================================================

const int BOTAO_PIN = 27;   // botao -> GND (com INPUT_PULLUP)
const int LED_PIN   = 5;    // LED externo + resistor limitador

void setup(){
  Serial.begin(115200);
  pinMode(BOTAO_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.println("Teste botao + LED externo (polling)");
}

void loop(){
  // Com INPUT_PULLUP, o botao pressionado leva o pino a LOW.
  bool pressionado = (digitalRead(BOTAO_PIN) == LOW);

  if(pressionado){
    digitalWrite(LED_PIN, HIGH);   // botao pressionado -> LED acende
    Serial.println("Botao PRESSIONADO -> LED ON");
  } else {
    digitalWrite(LED_PIN, LOW);    // solto -> LED apaga
  }

  delay(20);   // pequena espera p/ suavizar leitura serial
}
