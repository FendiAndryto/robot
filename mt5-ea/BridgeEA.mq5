//+------------------------------------------------------------------+
//|                                                     BridgeEA.mq5 |
//|                                  Copyright 2026, Robot Trading System |
//|                                  https://github.com/FendiAndryto/robot |
//+------------------------------------------------------------------+
#property copyright "Robot Trading System"
#property link      "https://github.com/FendiAndryto/robot"
#property version   "1.30"
#property description "FastAPI Web-to-MT5 Telemetry & Execution Bridge EA v1.30"

//--- Standard MT5 Trade Library
#include <Trade\Trade.mqh>

//--- WinINet Constants & Imports (64-bit MT5 for seamless networking)
#define INTERNET_OPEN_TYPE_PRECONFIG 0
#define INTERNET_SERVICE_HTTP        3
#define INTERNET_FLAG_RELOAD         0x80000000
#define INTERNET_FLAG_SECURE         0x00800000
#define INTERNET_OPTION_CONNECT_TIMEOUT 2
#define INTERNET_OPTION_RECEIVE_TIMEOUT 6
#define INTERNET_OPTION_SEND_TIMEOUT    5
#define HTTP_QUERY_STATUS_CODE          19
#define HTTP_QUERY_FLAG_NUMBER          0x20000000

#import "wininet.dll"
  long InternetOpenW(string lpszAgent, uint dwAccessType, string lpszProxy, string lpszProxyBypass, uint dwFlags);
  long InternetConnectW(long hInternet, string lpszServerName, ushort nServerPort, string lpszUsername, string lpszPassword, uint dwService, uint dwFlags, long dwContext);
  long HttpOpenRequestW(long hConnect, string lpszVerb, string lpszObjectName, string lpszVersion, string lpszReferer, long lplpszAcceptTypes, uint dwFlags, long dwContext);
  bool HttpSendRequestW(long hRequest, string lpszHeaders, uint dwHeadersLength, uchar &lpOptional[], uint dwOptionalLength);
  bool HttpQueryInfoW(long hRequest, uint dwInfoLevel, uchar &lpBuffer[], uint &lpdwBufferLength, uint &lpdwIndex);
  bool InternetReadFile(long hFile, uchar &lpBuffer[], uint dwNumberOfBytesToRead, uint &lpdwNumberOfBytesRead);
  bool InternetSetOptionW(long hInternet, uint dwOption, uint &lpBuffer, uint dwBufferLength);
  bool InternetCloseHandle(long hInternet);
#import

//--- Inputs
input group "--- Bridge Settings ---"
input string InpBackendUrl        = "https://staging-trade-gear.homever.my.id"; // Backend API URL
input string InpMonitoredSymbols  = "XAUUSD,EURUSD,GBPUSD,USDJPY,BTCUSD";      // Watchlist symbols (comma-separated)
input int    InpHistoryDays       = 30;                                        // History lookback days
input int    InpHeartbeatInterval = 1;                                         // Heartbeat interval in seconds
input bool   InpVerboseLog        = false;                                     // Print detailed logs to Experts tab

input group "--- Trade Settings ---"
input ulong  InpMagicNumber       = 778899;                // Magic Number for orders
input ulong  InpDeviationPoints   = 20;                    // Maximum slippage in points

//--- Global Objects & Variables
CTrade   g_trade;
datetime g_last_heartbeat = 0;
int      g_consecutive_errors = 0;
string   g_status_msg = "Initializing...";

// Forward Declarations
void SendHeartbeat();
void ProcessBackendCommands(string responseJson);
void UpdateChartHUD(string status_text);

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print(">>> [BridgeEA] Initializing MT5 FastAPI Bridge EA v1.30 (Telemetry v2)...");
   Print(">>> [BridgeEA] Target Backend: ", InpBackendUrl);
   PrintFormat(">>> [BridgeEA] Magic Number: %I64u, Deviation: %I64u pts", InpMagicNumber, InpDeviationPoints);
   
   // Configure trade executor
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   
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
   
   // Set WinINet timeouts (2s) to prevent blocking the EA thread if backend is unreachable
   uint timeoutMs = 2000;
   InternetSetOptionW(hSession, INTERNET_OPTION_CONNECT_TIMEOUT, timeoutMs, 4);
   InternetSetOptionW(hSession, INTERNET_OPTION_RECEIVE_TIMEOUT, timeoutMs, 4);
   InternetSetOptionW(hSession, INTERNET_OPTION_SEND_TIMEOUT, timeoutMs, 4);
   
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
   
   // Verify HTTP status code (must be 200 OK)
   uint statusCode = 0;
   uint statusLen = 4;
   uint index = 0;
   uchar statusBuf[4];
   if(HttpQueryInfoW(hRequest, HTTP_QUERY_STATUS_CODE | HTTP_QUERY_FLAG_NUMBER, statusBuf, statusLen, index))
   {
      statusCode = (uint)(statusBuf[0] | (statusBuf[1] << 8) | (statusBuf[2] << 16) | (statusBuf[3] << 24));
   }
   if(statusCode != 200 && statusCode != 0)
   {
      PrintFormat(">>> [BridgeEA] WinINet HTTP response rejected with code %u", statusCode);
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
//| Escape special characters for strict JSON compliance             |
//+------------------------------------------------------------------+
string EscapeJsonString(string src)
{
   string res = src;
   StringReplace(res, "\\", "\\\\");
   StringReplace(res, "\"", "\\\"");
   StringReplace(res, "\r", "\\r");
   StringReplace(res, "\n", "\\n");
   StringReplace(res, "\t", "\\t");
   return res;
}

//+------------------------------------------------------------------+
//| Simple string extract helper for JSON key-value                  |
//+------------------------------------------------------------------+
string ExtractJsonValue(string jsonBlock, string key)
{
   string search = "\"" + key + "\":";
   int pos = StringFind(jsonBlock, search);
   if(pos < 0) return "";
   
   pos += StringLen(search);
   
   // Skip whitespace
   while(pos < StringLen(jsonBlock) && (StringGetCharacter(jsonBlock, pos) == ' ' || StringGetCharacter(jsonBlock, pos) == '\t'))
      pos++;
      
   if(pos >= StringLen(jsonBlock)) return "";
   
   // String value
   if(StringGetCharacter(jsonBlock, pos) == '\"')
   {
      pos++;
      int endPos = StringFind(jsonBlock, "\"", pos);
      if(endPos < 0) return "";
      return StringSubstr(jsonBlock, pos, endPos - pos);
   }
   
   // Number, boolean, or null
   int endPos = pos;
   while(endPos < StringLen(jsonBlock))
   {
      ushort ch = StringGetCharacter(jsonBlock, endPos);
      if(ch == ',' || ch == '}' || ch == ']' || ch == ' ' || ch == '\r' || ch == '\n')
         break;
      endPos++;
   }
   
   string val = StringSubstr(jsonBlock, pos, endPos - pos);
   if(val == "null") return "";
   return val;
}

//+------------------------------------------------------------------+
//| Auto-resolve symbol with broker suffix (e.g. XAUUSD -> XAUUSDm)   |
//+------------------------------------------------------------------+
string FindBrokerSymbol(string baseSym)
{
   if(SymbolSelect(baseSym, true)) return baseSym;
   
   // 1. Try chart symbol suffix
   string currentSym = _Symbol;
   int curLen = StringLen(currentSym);
   if(curLen > 6)
   {
      string suffix = StringSubstr(currentSym, 6);
      string candidate = baseSym + suffix;
      if(SymbolSelect(candidate, true)) return candidate;
   }
   
   // 2. Try common broker suffixes (Exness 'm', Raw 'c', Pro 'pro', etc.)
   string commonSuffixes[8] = {"m", "c", "r", "pro", "raw", ".", "_i", "+"};
   for(int i = 0; i < 8; i++)
   {
      string candidate = baseSym + commonSuffixes[i];
      if(SymbolSelect(candidate, true)) return candidate;
   }
   
   return baseSym;
}

//+------------------------------------------------------------------+
//| Process and execute trade commands from backend response         |
//+------------------------------------------------------------------+
void ProcessBackendCommands(string responseJson)
{
   int cmdPos = StringFind(responseJson, "\"commands\":");
   if(cmdPos < 0) return;
   
   int arrayStart = StringFind(responseJson, "[", cmdPos);
   if(arrayStart < 0) return;
   
   int arrayEnd = StringFind(responseJson, "]", arrayStart);
   if(arrayEnd <= arrayStart + 1) return; // empty array "[]"
   
   string commandsArray = StringSubstr(responseJson, arrayStart + 1, arrayEnd - arrayStart - 1);
   
   int curPos = 0;
   while(curPos < StringLen(commandsArray))
   {
      int objStart = StringFind(commandsArray, "{", curPos);
      if(objStart < 0) break;
      int objEnd = StringFind(commandsArray, "}", objStart);
      if(objEnd < 0) break;
      
      string cmdItem = StringSubstr(commandsArray, objStart, objEnd - objStart + 1);
      curPos = objEnd + 1;
      
      string cmdId = ExtractJsonValue(cmdItem, "command_id");
      string action = ExtractJsonValue(cmdItem, "action");
      string symbol = ExtractJsonValue(cmdItem, "symbol");
      if(symbol == "") symbol = _Symbol;
      else symbol = FindBrokerSymbol(symbol);
      
      double volume = StringToDouble(ExtractJsonValue(cmdItem, "volume"));
      if(volume <= 0.0) volume = 0.01;
      
      string slStr = ExtractJsonValue(cmdItem, "sl");
      double sl = (slStr != "" ? StringToDouble(slStr) : 0.0);
      
      string tpStr = ExtractJsonValue(cmdItem, "tp");
      double tp = (tpStr != "" ? StringToDouble(tpStr) : 0.0);
      
      string ticketStr = ExtractJsonValue(cmdItem, "ticket");
      ulong ticket = (ticketStr != "" ? (ulong)StringToInteger(ticketStr) : 0);
      
      PrintFormat(">>> [BridgeEA] Received Command [%s]: Action=%s Symbol=%s Vol=%.2f Ticket=%I64u",
                  cmdId, action, symbol, volume, ticket);
                  
      // Normalize SL/TP to instrument digits
      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      if(digits > 0)
      {
         if(sl > 0.0) sl = NormalizeDouble(sl, digits);
         if(tp > 0.0) tp = NormalizeDouble(tp, digits);
      }
      
      // Dynamically configure filling mode for target symbol
      g_trade.SetTypeFillingBySymbol(symbol);
                  
      if(action == "BUY")
      {
         ResetLastError();
         if(g_trade.Buy(volume, symbol, 0, sl, tp, "Web Buy #" + cmdId))
         {
            PrintFormat(">>> [BridgeEA] BUY SUCCESS: Ticket #%I64u Price=%.5f", g_trade.ResultOrder(), g_trade.ResultPrice());
         }
         else
         {
            PrintFormat(">>> [BridgeEA] BUY FAILED: Retcode=%u Error=%d", g_trade.ResultRetcode(), GetLastError());
         }
      }
      else if(action == "SELL")
      {
         ResetLastError();
         if(g_trade.Sell(volume, symbol, 0, sl, tp, "Web Sell #" + cmdId))
         {
            PrintFormat(">>> [BridgeEA] SELL SUCCESS: Ticket #%I64u Price=%.5f", g_trade.ResultOrder(), g_trade.ResultPrice());
         }
         else
         {
            PrintFormat(">>> [BridgeEA] SELL FAILED: Retcode=%u Error=%d", g_trade.ResultRetcode(), GetLastError());
         }
      }
      else if(action == "CLOSE")
      {
         if(ticket > 0)
         {
            ResetLastError();
            if(g_trade.PositionClose(ticket))
            {
               PrintFormat(">>> [BridgeEA] CLOSE SUCCESS: Ticket #%I64u", ticket);
            }
            else
            {
               PrintFormat(">>> [BridgeEA] CLOSE FAILED: Ticket #%I64u Retcode=%u Error=%d", ticket, g_trade.ResultRetcode(), GetLastError());
            }
         }
      }
      else if(action == "CLOSE_ALL")
      {
         Print(">>> [BridgeEA] Executing CLOSE_ALL positions...");
         int total = PositionsTotal();
         for(int i = total - 1; i >= 0; i--)
         {
            ulong posTicket = PositionGetTicket(i);
            if(posTicket > 0)
            {
               g_trade.PositionClose(posTicket);
            }
         }
         Print(">>> [BridgeEA] CLOSE_ALL completed.");
      }
   }
}

//+------------------------------------------------------------------+
//| Build JSON array of live quotes for monitored symbols           |
//+------------------------------------------------------------------+
string BuildMarketQuotesJson()
{
   string symbols[];
   int totalSym = StringSplit(InpMonitoredSymbols, ',', symbols);
   string json = "[";
   int count = 0;
   
   for(int i = 0; i < totalSym; i++)
   {
      string baseSym = symbols[i];
      StringTrimLeft(baseSym);
      StringTrimRight(baseSym);
      if(baseSym == "") continue;
      
      string actualSym = FindBrokerSymbol(baseSym);
      SymbolSelect(actualSym, true);
      
      double bid = SymbolInfoDouble(actualSym, SYMBOL_BID);
      double ask = SymbolInfoDouble(actualSym, SYMBOL_ASK);
      if(bid <= 0.0) continue;
      
      int digits = (int)SymbolInfoInteger(actualSym, SYMBOL_DIGITS);
      int spread = (int)SymbolInfoInteger(actualSym, SYMBOL_SPREAD);
      
      double changePct = 0.0;
      double high = bid;
      double low = bid;
      
      MqlRates d1Rates[];
      ArraySetAsSeries(d1Rates, true);
      if(CopyRates(actualSym, PERIOD_D1, 0, 1, d1Rates) > 0)
      {
         if(d1Rates[0].open > 0.0)
         {
            changePct = ((bid - d1Rates[0].open) / d1Rates[0].open) * 100.0;
         }
         high = d1Rates[0].high;
         low = d1Rates[0].low;
      }
      
      if(count > 0) json += ",";
      json += StringFormat(
         "{\"symbol\":\"%s\",\"bid\":%.*f,\"ask\":%.*f,\"spread\":%d,\"digits\":%d,\"daily_change_pct\":%.2f,\"high\":%.*f,\"low\":%.*f}",
         EscapeJsonString(baseSym),
         digits, bid,
         digits, ask,
         spread,
         digits,
         changePct,
         digits, high,
         digits, low
      );
      count++;
   }
   json += "]";
   return json;
}

//+------------------------------------------------------------------+
//| Build JSON array of closed trade history from MT5 deals          |
//+------------------------------------------------------------------+
string BuildClosedTradesJson()
{
   datetime fromTime = TimeCurrent() - InpHistoryDays * 86400;
   HistorySelect(fromTime, TimeCurrent());
   int totalDeals = HistoryDealsTotal();
   
   string json = "[";
   int count = 0;
   int maxRecords = 50;
   
   for(int i = totalDeals - 1; i >= 0 && count < maxRecords; i--)
   {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket <= 0) continue;
      
      long entryType = HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
      if(entryType != DEAL_ENTRY_OUT) continue;
      
      string dealSymbol = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
      long dealType = HistoryDealGetInteger(dealTicket, DEAL_TYPE);
      double dealVol = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
      double dealPrice = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
      double dealProfit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT) + 
                          HistoryDealGetDouble(dealTicket, DEAL_SWAP) + 
                          HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);
      long dealTime = HistoryDealGetInteger(dealTicket, DEAL_TIME);
      long dealMagic = HistoryDealGetInteger(dealTicket, DEAL_MAGIC);
      
      string origType = (dealType == DEAL_TYPE_SELL ? "BUY" : "SELL");
      
      if(count > 0) json += ",";
      json += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.2f,\"open_price\":%.5f,\"close_price\":%.5f,\"profit\":%.2f,\"open_time\":%I64d,\"close_time\":%I64d,\"magic\":%I64d}",
         dealTicket,
         EscapeJsonString(dealSymbol),
         origType,
         dealVol,
         dealPrice,
         dealPrice,
         dealProfit,
         dealTime,
         dealTime,
         dealMagic
      );
      count++;
   }
   json += "]";
   return json;
}

//+------------------------------------------------------------------+
//| Build JSON array of recent M15 candles for chart symbol         |
//+------------------------------------------------------------------+
string BuildCandlesJson()
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_M15, 0, 35, rates);
   if(copied <= 0) return "[]";
   
   string json = "[";
   int count = 0;
   for(int i = copied - 1; i >= 0; i--)
   {
      if(count > 0) json += ",";
      json += StringFormat(
         "{\"time\":%I64d,\"open\":%.5f,\"high\":%.5f,\"low\":%.5f,\"close\":%.5f,\"volume\":%.1f}",
         (long)rates[i].time,
         rates[i].open,
         rates[i].high,
         rates[i].low,
         rates[i].close,
         (double)rates[i].tick_volume
      );
      count++;
   }
   json += "]";
   return json;
}

//+------------------------------------------------------------------+
//| Build JSON telemetry payload with live positions list            |
//+------------------------------------------------------------------+
string BuildHeartbeatJson()
{
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   string server = EscapeJsonString(AccountInfoString(ACCOUNT_SERVER));
   string currency = EscapeJsonString(AccountInfoString(ACCOUNT_CURRENCY));
   if(currency == "") currency = "USD";
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(!MathIsValidNumber(balance)) balance = 0.0;
   
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(equity)) equity = balance;
   
   double margin = AccountInfoDouble(ACCOUNT_MARGIN);
   if(!MathIsValidNumber(margin) || margin < 0.0) margin = 0.0;
   
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(!MathIsValidNumber(free_margin)) free_margin = equity;
   
   double margin_level = 0.0;
   if(margin > 0.0001)
   {
      margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
      if(!MathIsValidNumber(margin_level)) margin_level = 0.0;
   }
   
   double profit = AccountInfoDouble(ACCOUNT_PROFIT);
   if(!MathIsValidNumber(profit)) profit = 0.0;
   
   bool connected = (bool)TerminalInfoInteger(TERMINAL_CONNECTED);
   int positions = PositionsTotal();
   long timestamp = (long)TimeLocal();

   // Build Open Positions Array
   string positionsJson = "[";
   int count = 0;
   
   for(int i = 0; i < positions; i++)
   {
      ulong posTicket = PositionGetTicket(i);
      if(posTicket > 0)
      {
         string posSymbol = PositionGetString(POSITION_SYMBOL);
         long posType = PositionGetInteger(POSITION_TYPE);
         double posVol = PositionGetDouble(POSITION_VOLUME);
         double posOpenPrice = PositionGetDouble(POSITION_PRICE_OPEN);
         double posCurrentPrice = PositionGetDouble(POSITION_PRICE_CURRENT);
         double posSL = PositionGetDouble(POSITION_SL);
         double posTP = PositionGetDouble(POSITION_TP);
         double posProfit = PositionGetDouble(POSITION_PROFIT);
         long posTime = PositionGetInteger(POSITION_TIME);
         long posMagic = PositionGetInteger(POSITION_MAGIC);
         
         if(count > 0) positionsJson += ",";
         
         positionsJson += StringFormat(
            "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.2f,\"open_price\":%.5f,\"current_price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"pnl\":%.2f,\"open_time\":%I64d,\"magic\":%I64d}",
            posTicket,
            EscapeJsonString(posSymbol),
            (posType == POSITION_TYPE_BUY ? "BUY" : "SELL"),
            posVol,
            posOpenPrice,
            posCurrentPrice,
            posSL,
            posTP,
            posProfit,
            posTime,
            posMagic
         );
         count++;
      }
   }
   positionsJson += "]";

   string quotesJson = BuildMarketQuotesJson();
   string closedTradesJson = BuildClosedTradesJson();
   string candlesJson = BuildCandlesJson();

   string json = "{"
      + StringFormat("\"account_number\":%I64d,", login)
      + "\"server\":\"" + server + "\","
      + "\"currency\":\"" + currency + "\","
      + StringFormat("\"balance\":%.2f,", balance)
      + StringFormat("\"equity\":%.2f,", equity)
      + StringFormat("\"margin\":%.2f,", margin)
      + StringFormat("\"free_margin\":%.2f,", free_margin)
      + StringFormat("\"margin_level\":%.2f,", margin_level)
      + StringFormat("\"floating_pnl\":%.2f,", profit)
      + "\"terminal_connected\":" + (connected ? "true," : "false,")
      + StringFormat("\"open_positions\":%d,", positions)
      + "\"positions\":" + positionsJson + ","
      + "\"market_quotes\":" + quotesJson + ","
      + "\"closed_trades\":" + closedTradesJson + ","
      + "\"candles\":" + candlesJson + ","
      + "\"chart_symbol\":\"" + EscapeJsonString(_Symbol) + "\","
      + StringFormat("\"timestamp\":%I64d", timestamp)
      + "}";
   
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
      g_last_heartbeat = TimeLocal();
      g_consecutive_errors = 0;
      g_status_msg = "Connected (Heartbeat OK - 200)";
      
      string responseStr = CharArrayToString(resultData, 0, WHOLE_ARRAY, CP_UTF8);
      ProcessBackendCommands(responseStr);
      
      if(InpVerboseLog)
      {
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
      g_last_heartbeat = TimeLocal();
      g_consecutive_errors = 0;
      g_status_msg = "Connected (WinINet Heartbeat OK)";
      
      ProcessBackendCommands(wininetResp);
      
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
