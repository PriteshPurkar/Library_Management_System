#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <ESP8266HTTPClient.h>

// **RFID Module SPI Pins**
#define SS_PIN D2    
#define RST_PIN D4   
#define SCK_PIN D5   
#define MOSI_PIN D7  
#define MISO_PIN D6  

MFRC522 rfid(SS_PIN, RST_PIN);

// **WiFi Credentials**
const char* ssid = "P";
const char* password = "stranger";

// **Server URL**
const char* server_url = "https://librarymanagement-93wn.onrender.com/receive_rfid";  

// **Secure Client**
WiFiClientSecure secureClient;

void setup() {
    Serial.begin(115200);
    SPI.begin();  
    rfid.PCD_Init();

    // Connect to WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi...");
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected!");

    // Insecure SSL (okay for testing)
    secureClient.setInsecure();  
}

void loop() {
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
        String rfidTag = "";
        for (byte i = 0; i < rfid.uid.size; i++) {
            rfidTag += String(rfid.uid.uidByte[i], HEX);
        }

        Serial.println("RFID Detected: " + rfidTag);
        sendToServer(rfidTag);
        rfid.PICC_HaltA();
    }
    delay(500);
}

// **Send RFID to HTTPS Flask Server**
void sendToServer(String rfid) {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(secureClient, server_url);
        http.addHeader("Content-Type", "application/json");

        String payload = "{\"rfid\":\"" + rfid + "\"}";
        Serial.println("Sending to Server: " + payload);

        int httpResponseCode = http.POST(payload);
        String response = http.getString();

        Serial.println("Response Code: " + String(httpResponseCode));
        Serial.println("Response: " + response);

        http.end();
    } else {
        Serial.println("WiFi not connected!");
    }
}
