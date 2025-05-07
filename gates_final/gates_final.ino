#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266HTTPClient.h>

// RFID Reader Pins
#define SS_Reader1 D2
#define SS_Reader2 D3
#define RST_PIN D4
#define BUZZER_PIN D8

// Shared SPI Pins
#define SCK_PIN D5
#define MOSI_PIN D7
#define MISO_PIN D6

const char* ssid = "P";
const char* password = "stranger";
const char* serverUrl = "https://librarymanagement-93wn.onrender.com/exit_rfid_scan";

MFRC522 mfrc522_1(SS_Reader1, RST_PIN);
MFRC522 mfrc522_2(SS_Reader2, RST_PIN);

// Secure WiFi client
WiFiClientSecure secureClient;

void setup() {
    Serial.begin(115200);

    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);

    // Start SPI
    SPI.begin();

    // Initialize RFID readers
    mfrc522_1.PCD_Init();
    mfrc522_2.PCD_Init();

    // Connect to WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi...");
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected!");

    // Disable SSL certificate validation for testing (use setFingerprint() in production)
    secureClient.setInsecure();
}

void loop() {
    checkReader(mfrc522_1);
    checkReader(mfrc522_2);
}

void checkReader(MFRC522 &reader) {
    if (!reader.PICC_IsNewCardPresent() || !reader.PICC_ReadCardSerial()) {
        return;
    }

    String rfidTag = "";
    for (byte i = 0; i < reader.uid.size; i++) {
        rfidTag += String(reader.uid.uidByte[i], HEX);
    }

    Serial.println("Scanned RFID: " + rfidTag);
    sendToServer(rfidTag);
    reader.PICC_HaltA();
}

void sendToServer(String rfidTag) {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(secureClient, serverUrl);
        http.addHeader("Content-Type", "application/json");

        String payload = "{\"rfid\":\"" + rfidTag + "\"}";
        Serial.println("Sending: " + payload);

        int httpCode = http.POST(payload);
        String response = http.getString();

        if (httpCode == 403) {
            Serial.println("🚨 ALERT: Unissued book detected at exit!");
            activateAlarm();
        } else {
            Serial.println("✅ Book exit verified.");
        }

        Serial.println("HTTP Code: " + String(httpCode));
        Serial.println("Server Response: " + response);

        http.end();
    } else {
        Serial.println("WiFi not connected.");
    }
}

void activateAlarm() {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(5000);
    digitalWrite(BUZZER_PIN, LOW);
}
