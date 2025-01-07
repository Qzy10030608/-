#include <M5Unified.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPAsyncWebServer.h>

#define SERIAL_BAUD 115200

// Wi-Fi 配置
const char *ssid = "TP-Link_8C53";
const char *password = "08072224932";

// HTTP 服务器
AsyncWebServer server(80);

bool isActivated = false;  // 是否已被激活

// 激活 M5 的处理函数
void activateHandler(AsyncWebServerRequest *request) {
  isActivated = true;  // 激活拍摄功能

  // 更新屏幕显示
  M5.Lcd.fillScreen(GREEN);
  M5.Lcd.setCursor(10, 30);
  M5.Lcd.setTextColor(BLUE);
  M5.Lcd.setTextSize(3);
  M5.Lcd.println("Press A to Take Photo");

  Serial.println("M5 被激活");
  request->send(200, "M5 Activated");
}

// 初始化
void setup() {
  M5.begin();
  M5.Lcd.setRotation(3);  // 横屏
  M5.Lcd.fillScreen(RED); // 初始状态为未连接
  M5.Lcd.setCursor(10, 30);
  M5.Lcd.setTextColor(BLACK);
  M5.Lcd.setTextSize(3);
  M5.Lcd.println("Not Activated");

  // 串口初始化
  Serial.begin(SERIAL_BAUD);

  // Wi-Fi 连接
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  M5.Lcd.fillScreen(RED);
  M5.Lcd.setCursor(10, 30);
  M5.Lcd.setTextColor(BLACK);
  M5.Lcd.setTextSize(3);
  M5.Lcd.println(WiFi.localIP().toString());

  Serial.println("\nWiFi Connected!");
  Serial.print("M5StickC Plus IP: ");
  Serial.println(WiFi.localIP());

  // 激活端点
  server.on("/activate", HTTP_GET, activateHandler);
  server.begin();
}

void loop() {
  M5.update();

  // 如果未激活
  if (!isActivated) {
    delay(1000);
    return;
  }

  // 如果按下 A 按钮
  if (M5.BtnA.wasPressed()) {
    Serial.println("按下 A 按钮，发送拍照请求");

    HTTPClient http;
    http.begin("http://192.168.0.174:5000/take_photo");  // 替换为 Flask 的地址
    int httpCode = http.GET();

    if (httpCode > 0) {
      Serial.print("HTTP 请求成功，状态码: ");
      Serial.println(httpCode);
    } else {
      Serial.print("HTTP 请求失败，错误: ");
      Serial.println(http.errorToString(httpCode).c_str());
    }
    http.end();
  }
}



