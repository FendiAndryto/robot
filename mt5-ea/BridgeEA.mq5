//+------------------------------------------------------------------+
//|                                                     BridgeEA.mq5 |
//|                                  Copyright 2026, Robot Trading System |
//|                                  https://github.com/FendiAndryto/robot |
//+------------------------------------------------------------------+
#property copyright "Robot Trading System"
#property link      "https://github.com/FendiAndryto/robot"
#property version   "1.10"
#property description "FastAPI Web-to-MT5 Telemetry & Execution Bridge EA"

//--- WinINet Constants & Imports (64-bit MT5 for seamless networking)
#define INTERNET_OPEN_TYPE_PRECONFIG 0
#define INTERNET_SERVICE_HTTP        3
#define INTERNET_FLAG_RELOAD         0x80000000
#define INTERNET_FLAG_SECURE         0x00800000

#import "wininet.dll"
  long InternetOpenW(string lpszAgent, uint dwAccessType, string lpszProxy, string lpszProxyBypass, uint dwFlags);
  long InternetConnectW(long hInternet, string lpszServerName, ushort nServerPort, string lpszUsername, string lpszPassword, uint dwService, uint dwFlags, long dwContext);
  long HttpOpenRequestW(long hConnect, string lpszVerb, string lpszObjectName, string lpszVersion, string lpszReferer, long lplpszAcceptTypes, uint dwFlags, long dwContext);
  bool HttpSendRequestW(long hRequest, string lpszHeaders, uint dwHeadersLength, uchar &lpOptional[], uint dwOptionalLength);
  bool InternetReadFile(long hFile, uchar &lpBuffer[], uint dwNumberOfBytesToRead, uint &lpdwNumberOfBytesRead);
  bool InternetCloseHandle(long hInternet);
#import

//--- Inputs
input group "--- Bridge Settings ---"
input string InpBackendUrl        = "http://backend:8000"; // Backend API URL (or http://host.docker.internal:8008)
input int    InpHeartbeatInterval = 1;                     // Heartbeat interval in seconds
input bool   InpVerboseLog        = false;                 // Print detailed logs to Experts tab

//--- Global Variables
datetime g_last_heartbeat = 0;
int      g_consecutive_errors = 0;
string   g_status_msg = "Initializing...";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print(">>> [BridgeEA] Initializing MT5 FastAPI Bridge EA v1.10...");
   Print(">>> [BridgeEA] Target Backend: ", InpBackendUrl);
   
   if(InpHeartbeatInterval < 1)
   {
      Print(">>> [BridgeEA] Heartbeat interval too low. Setting to 1s.");
   }
   
   // Set timer for periodic heartbeat
   EventSetTimer(MathMax(1, InpHeartbeatInterval));
   
   g_status_msg = "Started - Connecting to Backend...";
   UpdateChartHUD(g_status_msg);
   
   // Send initial heartbeat immediately
   SendHeartbeat();
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Comment("");
   Print(">>> [BridgeEA] Deinitialized. Reason code: ", reason);
}

//+------------------------------------------------------------------+
//| Timer event function                                             |
//+------------------------------------------------------------------+
void OnTimer()
{
   SendHeartbeat();
}

//+------------------------------------------------------------------+
//| Parse URL into host, port, useSSL                                |
//+------------------------------------------------------------------+
void ParseUrl(string url, string &host, ushort &port, bool &useSSL)
{
   useSSL = false;
   port = 80;
   string temp = url;
   
   if(StringFind(temp, "https://") == 0)
   {
      useSSL = true;
      port = 443;
      temp = StringSubstr(temp, 8);
   }
   else if(StringFind(temp, "http://") == 0)
   {
      useSSL = false;
      port = 80;
      temp = StringSubstr(temp, 7);
   }
   
   int slashPos = StringFind(temp, "/");
   if(slashPos >= 0)
   {
      temp = StringSubstr(temp, 0, slashPos);
   }
   
   int colonPos = StringFind(temp, ":");
   if(colonPos >= 0)
   {
      host = StringSubstr(temp, 0, colonPos);
      port = (ushort)StringToInteger(StringSubstr(temp, colonPos + 1));
   }
   else
   {
      host = temp;
   }
}

//+------------------------------------------------------------------+
//| Send HTTP POST via WinINet DLL (bypasses MT5 whitelist dialog)   |
//+------------------------------------------------------------------+
bool SendWinInetPost(string host, ushort port, bool useSSL, string path, string jsonPayload, string &responseStr)
{
   long hSession = InternetOpenW("RobotBridgeEA", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
   if(hSession == 0)
   {
      Print(">>> [BridgeEA] WinINet InternetOpen failed. Error: ", GetLastError());
      return false;
   }
   
   long hConnect = InternetConnectW(hSession, host, port, NULL, NULL, INTERNET_SERVICE_HTTP, 0, 0);
   if(hConnect == 0)
   {
      Print(">>> [BridgeEA] WinINet InternetConnect failed. Host: ", host, ", Port: ", port, ", Error: ", GetLastError());
      InternetCloseHandle(hSession);
      return false;
   }
   
   uint flags = INTERNET_FLAG_RELOAD;
   if(useSSL) flags |= INTERNET_FLAG_SECURE;
   
   long hRequest = HttpOpenRequestW(hConnect, "POST", path, NULL, NULL, 0, flags, 0);
   if(hRequest == 0)
   {
      Print(">>> [BridgeEA] WinINet HttpOpenRequest failed. Error: ", GetLastError());
      InternetCloseHandle(hConnect);
      InternetCloseHandle(hSession);
      return false;
   }
   
   string headers = "Content-Type: application/json\r\nAccept: application/json\r\n";
   uchar postDataBytes[];
   StringToCharArray(jsonPayload, postDataBytes, 0, StringLen(jsonPayload), CP_UTF8);
   uint postLen = (uint)ArraySize(postDataBytes);
   if(postLen > 0 && postDataBytes[postLen - 1] == 0) postLen--;
   
   bool sent = HttpSendRequestW(hRequest, headers, (uint)StringLen(headers), postDataBytes, postLen);
   if(!sent)
   {
      Print(">>> [BridgeEA] WinINet HttpSendRequest failed. Error: ", GetLastError());
      InternetCloseHandle(hRequest);
      InternetCloseHandle(hConnect);
      InternetCloseHandle(hSession);
      return false;
   }
   
   responseStr = "";
   uchar readBuf[1024];
   uint bytesRead = 0;
   
   while(true)
   {
      ArrayInitialize(readBuf, 0);
      if(!InternetReadFile(hRequest, readBuf, 1023, bytesRead) || bytesRead == 0)
         break;
      responseStr += CharArrayToString(readBuf, 0, bytesRead, CP_UTF8);
   }
   
   InternetCloseHandle(hRequest);
   InternetCloseHandle(hConnect);
   InternetCloseHandle(hSession);
   return true;
}

//+------------------------------------------------------------------+
//| Build JSON telemetry payload from native MT5 account functions   |
//+------------------------------------------------------------------+
string BuildHeartbeatJson()
{
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   string server = AccountInfoString(ACCOUNT_SERVER);
   string currency = AccountInfoString(ACCOUNT_CURRENCY);
   if(currency == "") currency = "USD";
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   double profit = AccountInfoDouble(ACCOUNT_PROFIT);
   bool connected = (bool)TerminalInfoInteger(TERMINAL_CONNECTED);
   int positions = PositionsTotal();
   long timestamp = (long)TimeCurrent();
   
   // Escape double quotes in server name if present
   StringReplace(server, "\"", "\\\"");

   string json = StringFormat(
      "{\"account_number\":%I64d,\"server\":\"%s\",\"currency\":\"%s\",\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"free_margin\":%.2f,\"margin_level\":%.2f,\"floating_pnl\":%.2f,\"terminal_connected\":%s,\"open_positions\":%d,\"timestamp\":%I64d}",
      login,
      server,
      currency,
      balance,
      equity,
      margin,
      free_margin,
      margin_level,
      profit,
      connected ? "true" : "false",
      positions,
      timestamp
   );
   
   return json;
}

//+------------------------------------------------------------------+
//| Send HTTP POST heartbeat to FastAPI backend                      |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
   string endpoint = InpBackendUrl + "/api/v1/bridge/heartbeat";
   string json = BuildHeartbeatJson();
   
   char postData[];
   char resultData[];
   string resultHeaders;
   
   StringToCharArray(json, postData, 0, WHOLE_ARRAY, CP_UTF8);
   int postLen = ArraySize(postData);
   if(postLen > 0 && postData[postLen - 1] == 0)
   {
      ArrayResize(postData, postLen - 1);
   }
   
   string headers = "Content-Type: application/json\r\n";
   ResetLastError();
   
   // 1. Try native WebRequest first
   int res = WebRequest("POST", endpoint, headers, 3000, postData, resultData, resultHeaders);
   
   if(res == 200)
   {
      g_last_heartbeat = TimeCurrent();
      g_consecutive_errors = 0;
      g_status_msg = "Connected (Heartbeat OK - 200)";
      
      if(InpVerboseLog)
      {
         string responseStr = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
         Print(">>> [BridgeEA] Heartbeat OK. Response: ", responseStr);
      }
      UpdateChartHUD(g_status_msg);
      return;
   }
   
   // 2. Fallback to WinINet if WebRequest is blocked by MT5 sandbox (Error 4014)
   string host;
   ushort port;
   bool useSSL;
   ParseUrl(InpBackendUrl, host, port, useSSL);
   
   string wininetResp;
   if(SendWinInetPost(host, port, useSSL, "/api/v1/bridge/heartbeat", json, wininetResp))
   {
      g_last_heartbeat = TimeCurrent();
      g_consecutive_errors = 0;
      g_status_msg = "Connected (WinINet Heartbeat OK)";
      
      if(InpVerboseLog)
      {
         Print(">>> [BridgeEA] WinINet Heartbeat OK: ", wininetResp);
      }
      UpdateChartHUD(g_status_msg);
      return;
   }
   
   // 3. Both failed
   int err = GetLastError();
   g_consecutive_errors++;
   g_status_msg = StringFormat("Connection Failed (Failures: %d)", g_consecutive_errors);
   if(g_consecutive_errors % 10 == 1)
   {
      Print(">>> [BridgeEA] Heartbeat failed. WebRequest Err: ", err, " URL: ", endpoint);
   }
   UpdateChartHUD(g_status_msg);
}

//+------------------------------------------------------------------+
//| Update onscreen HUD commentary                                   |
//+------------------------------------------------------------------+
void UpdateChartHUD(string status_text)
{
   string hud = "========================================\n"
              + "   ROBOT TRADING - MT5 FASTAPI BRIDGE   \n"
              + "========================================\n"
              + "Backend URL    : " + InpBackendUrl + "\n"
              + "Bridge Status  : " + status_text + "\n"
              + "Last Telemetry : " + (g_last_heartbeat > 0 ? TimeToString(g_last_heartbeat, TIME_DATE|TIME_SECONDS) : "None") + "\n"
              + "Server Name    : " + AccountInfoString(ACCOUNT_SERVER) + "\n"
              + "Account Login  : " + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + " (" + AccountInfoString(ACCOUNT_CURRENCY) + ")\n"
              + "Balance        : " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "\n"
              + "Equity         : " + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "\n"
              + "Floating PnL   : " + DoubleToString(AccountInfoDouble(ACCOUNT_PROFIT), 2) + "\n"
              + "Open Positions : " + IntegerToString(PositionsTotal()) + "\n"
              + "========================================";
   Comment(hud);
}
//+------------------------------------------------------------------+
