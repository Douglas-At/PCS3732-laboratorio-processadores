
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  neopixelWrite(LED_BUILTIN, 100,0,0);  
  delay(4000);                     
  neopixelWrite(LED_BUILTIN, 120,80,0);   
  delay(1000);                     
  neopixelWrite(LED_BUILTIN, 0,100,0);
  delay(3000);                   
}
