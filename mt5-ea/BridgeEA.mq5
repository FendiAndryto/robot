//+------------------------------------------------------------------+
//|                                                     BridgeEA.mq5 |
//|                                  Copyright 2026, Robot Trading System |
//|                                  https://github.com/FendiAndryto/robot |
//+------------------------------------------------------------------+
#property copyright "Robot Trading System"
#property link      "https://github.com/FendiAndryto/robot"
#property version   "1.80"
#property description "FastAPI Web-to-MT5 Telemetry & Adaptive SL/TP Protection EA v1.80 (Pure WebRequest, MQL5 VPS Ready)"

//--- Standard MT5 Trade Library
#include <Trade\Trade.mqh>

//--- Inputs
input group "--- Bridge Settings ---"
input string InpBackendUrl        = "https://staging-trade-gear.homever.my.id"; // Backend API URL
input string InpMonitoredSymbols  = "XAUUSD,EURUSD,GBPUSD,USDJPY,BTCUSD";      // Watchlist symbols (comma-separated)
input int    InpHistoryDays       = 30;                                        // History lookback days
input int    InpHeartbeatInterval = 1;                                         // Heartbeat interval in seconds
input bool   InpVerboseLog        = false;                                     // Print detailed logs to Experts tab

input group "--- SL / TP Protection Settings ---"
input bool   InpEnforceMinSL      = true;                  // Enforce minimum safe SL distance (prevents noise hit)
input int    InpMinSLPipsForex    = 30;                    // Minimum safe SL for Forex (30 pips)
input int    InpMinSLPipsGold     = 45;                    // Minimum safe SL for Gold (45 pips = $4.50 on Gold)
input int    InpMinSLPipsCrypto   = 150;                   // Minimum safe SL for Crypto / BTC (pips)
input double InpDefaultRRRatio    = 1.8;                   // Default Risk-Reward Ratio (TP = SL * RR)

input group "--- Scalping Protection Settings ---"
input bool   InpEnableBEP         = false;                 // Enable Auto-Breakeven (Default: false to allow full TP runs)
input int    InpBEPTriggerPips    = 35;                    // Profit pips to move SL to BEP (35 pips = $3.50 on Gold)
input int    InpBEPBufferPips     = 4;                     // Lock-in pips above open price (4 pips = $0.40 on Gold)
input bool   InpEnableTrailing    = false;                 // Enable Trailing Stop (Default: false)
input int    InpTrailingDistPips  = 40;                    // Trailing Stop distance in pips (40 pips)
input int    InpTrailingStepPips  = 10;                    // Trailing Stop step in pips (10 pips)

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
void ManagePositionsProtection();
void SetSafeFillingType(string sym);
string FindBrokerSymbol(string baseSym);
int GetPointsPerPip(string sym);
int GetMinSLPipsForSymbol(string sym);
void GetDealPositionOpenDetails(ulong posId, double &openPrice, long &openTime);

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print(">>> [BridgeEA] Initializing MT5 FastAPI Bridge EA v1.80 (Adaptive SL/TP Protection, MQL5 VPS Ready)...");
   Print(">>> [BridgeEA] Target Backend: ", InpBackendUrl);
   PrintFormat(">>> [BridgeEA] Magic Number: %I64u, Deviation: %I64u pts", InpMagicNumber, InpDeviationPoints);
   PrintFormat(">>> [BridgeEA] Safe SL Barrier: Forex=%d pips | Gold=%d pips ($%.2f) | Crypto=%d pts | MinEnforce=%s",
               InpMinSLPipsForex, InpMinSLPipsGold, (InpMinSLPipsGold * 0.10), InpMinSLPipsCrypto, (InpEnforceMinSL ? "YES" : "NO"));
   PrintFormat(">>> [BridgeEA] Protection: BEP=%s (Trig=%d pips, Buf=%d pips) | Trailing=%s (Dist=%d pips, Step=%d pips)",
               (InpEnableBEP ? "ON" : "OFF"), InpBEPTriggerPips, InpBEPBufferPips,
               (InpEnableTrailing ? "ON" : "OFF"), InpTrailingDistPips, InpTrailingStepPips);
   
   // Configure trade executor
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(InpDeviationPoints);
   SetSafeFillingType(_Symbol);
   
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
   ManagePositionsProtection();
   SendHeartbeat();
}

//+------------------------------------------------------------------+
//| Tick event function (ultra-fast trailing stop & BEP execution)   |
//+------------------------------------------------------------------+
void OnTick()
{
   ManagePositionsProtection();
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
//| Configure safe trade filling mode supported by broker             |
//+------------------------------------------------------------------+
void SetSafeFillingType(string sym)
{
   uint filling = (uint)SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_IOC) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else if((filling & SYMBOL_FILLING_FOK) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else
      g_trade.SetTypeFilling(ORDER_FILLING_RETURN);
}

//+------------------------------------------------------------------+
//| Find real broker symbol matching base symbol (handles suffixes)  |
//+------------------------------------------------------------------+
string FindBrokerSymbol(string baseSym)
{
   if(SymbolSelect(baseSym, true)) return baseSym;
   
   string upperTarget = baseSym;
   StringToUpper(upperTarget);
   
   // Extract root 6-character currency/commodity if longer (e.g. XAUUSDM -> XAUUSD)
   string coreSym = upperTarget;
   if(StringLen(coreSym) > 6)
   {
      string s6 = StringSubstr(coreSym, 0, 6);
      if(s6 == "XAUUSD" || s6 == "EURUSD" || s6 == "GBPUSD" || s6 == "USDJPY" || s6 == "BTCUSD" || s6 == "ETHUSD")
      {
         coreSym = s6;
      }
   }
   
   // 1. Direct case-insensitive match against all available symbols
   int total = SymbolsTotal(false);
   for(int i = 0; i < total; i++)
   {
      string sName = SymbolName(i, false);
      string upperS = sName;
      StringToUpper(upperS);
      if(upperS == upperTarget)
      {
         SymbolSelect(sName, true);
         return sName;
      }
   }
   
   // 2. Prefix match for broker with custom suffix (e.g. XAUUSDm, EURUSDm)
   for(int i = 0; i < total; i++)
   {
      string sName = SymbolName(i, false);
      string upperS = sName;
      StringToUpper(upperS);
      if(StringFind(upperS, coreSym) == 0 && StringLen(upperS) <= StringLen(coreSym) + 4)
      {
         SymbolSelect(sName, true);
         return sName;
      }
   }
   
   // 3. Fallback to chart symbol if compatible
   string chartUpper = _Symbol;
   StringToUpper(chartUpper);
   if(StringFind(chartUpper, coreSym) >= 0)
   {
      return _Symbol;
   }
   
   return _Symbol;
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
                  
      // Normalize SL/TP to instrument digits & enforce safe minimum distance
      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      int pointsPerPip = GetPointsPerPip(symbol);
      double pipDistInPrice = (double)pointsPerPip * point;
      int minSLPips = GetMinSLPipsForSymbol(symbol);
      double minSLDist = (double)minSLPips * pipDistInPrice;

      if(action == "BUY")
      {
         double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
         if(ask <= 0.0) ask = SymbolInfoDouble(symbol, SYMBOL_LAST);
         if(ask <= 0.0) ask = SymbolInfoDouble(symbol, SYMBOL_BID);

         if(sl <= 0.0)
         {
            sl = ask - minSLDist;
            PrintFormat(">>> [BridgeEA] Auto-applied safe default BUY SL for %s: %.5f (-%d pips)", symbol, sl, minSLPips);
         }
         else if(InpEnforceMinSL && (ask - sl) < (minSLDist - (point * 0.5)))
         {
            double oldSL = sl;
            sl = ask - minSLDist;
            PrintFormat(">>> [BridgeEA] Widened narrow BUY SL for %s from %.5f to safe %.5f (-%d pips buffer to avoid noise hit)",
                        symbol, oldSL, sl, minSLPips);
         }

         if(tp <= 0.0)
         {
            tp = ask + (minSLDist * InpDefaultRRRatio);
            PrintFormat(">>> [BridgeEA] Auto-applied safe default BUY TP for %s: %.5f (1:%.1f RR)", symbol, tp, InpDefaultRRRatio);
         }
         else if(InpEnforceMinSL && (tp - ask) < (minSLDist * 1.0))
         {
            tp = ask + ((ask - sl) * InpDefaultRRRatio);
            PrintFormat(">>> [BridgeEA] Adjusted BUY TP for %s to %.5f to maintain 1:%.1f RR", symbol, tp, InpDefaultRRRatio);
         }
      }
      else if(action == "SELL")
      {
         double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
         if(bid <= 0.0) bid = SymbolInfoDouble(symbol, SYMBOL_LAST);
         if(bid <= 0.0) bid = SymbolInfoDouble(symbol, SYMBOL_ASK);

         if(sl <= 0.0)
         {
            sl = bid + minSLDist;
            PrintFormat(">>> [BridgeEA] Auto-applied safe default SELL SL for %s: %.5f (+%d pips)", symbol, sl, minSLPips);
         }
         else if(InpEnforceMinSL && (sl - bid) < (minSLDist - (point * 0.5)))
         {
            double oldSL = sl;
            sl = bid + minSLDist;
            PrintFormat(">>> [BridgeEA] Widened narrow SELL SL for %s from %.5f to safe %.5f (+%d pips buffer to avoid noise hit)",
                        symbol, oldSL, sl, minSLPips);
         }

         if(tp <= 0.0)
         {
            tp = bid - (minSLDist * InpDefaultRRRatio);
            PrintFormat(">>> [BridgeEA] Auto-applied safe default SELL TP for %s: %.5f (1:%.1f RR)", symbol, tp, InpDefaultRRRatio);
         }
         else if(InpEnforceMinSL && (bid - tp) < (minSLDist * 1.0))
         {
            tp = bid - ((sl - bid) * InpDefaultRRRatio);
            PrintFormat(">>> [BridgeEA] Adjusted SELL TP for %s to %.5f to maintain 1:%.1f RR", symbol, tp, InpDefaultRRRatio);
         }
      }

      if(digits > 0)
      {
         if(sl > 0.0) sl = NormalizeDouble(sl, digits);
         if(tp > 0.0) tp = NormalizeDouble(tp, digits);
      }
      
      // Dynamically configure safe filling mode for target symbol
      SetSafeFillingType(symbol);
                  
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
//| Calculate Points Per Pip for symbol (Forex, Metals, Crypto)      |
//+------------------------------------------------------------------+
int GetPointsPerPip(string sym)
{
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   string upper = sym;
   StringToUpper(upper);
   
   if(StringFind(upper, "XAU") >= 0 || StringFind(upper, "GOLD") >= 0)
   {
      // Gold 1 pip = $0.10. 
      // In 3-digit broker (point = 0.001): 1 pip = 100 points ($0.10)
      // In 2-digit broker (point = 0.01): 1 pip = 10 points ($0.10)
      return (digits == 3 ? 100 : 10);
   }
   if(StringFind(upper, "BTC") >= 0)
   {
      // BTC 1 pip = $1.00. 
      // In 2-digit broker (point = 0.01): 1 pip = 100 points ($1.00)
      return (digits == 2 ? 100 : 1);
   }
   if(digits == 3 || digits == 5)
   {
      // 3 or 5 digit Forex pairs: 1 pip = 10 points
      return 10;
   }
   return 1;
}

//+------------------------------------------------------------------+
//| Get minimum safe SL pips based on asset class                     |
//+------------------------------------------------------------------+
int GetMinSLPipsForSymbol(string sym)
{
   string upper = sym;
   StringToUpper(upper);
   if(StringFind(upper, "XAU") >= 0 || StringFind(upper, "GOLD") >= 0)
      return InpMinSLPipsGold;
   if(StringFind(upper, "BTC") >= 0)
      return InpMinSLPipsCrypto;
   return InpMinSLPipsForex;
}

//+------------------------------------------------------------------+
//| Get Entry Price and Entry Time for a closed position's deals     |
//+------------------------------------------------------------------+
void GetDealPositionOpenDetails(ulong posId, double &openPrice, long &openTime)
{
   if(posId <= 0) return;
   
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong t = HistoryDealGetTicket(i);
      if(t > 0 && (ulong)HistoryDealGetInteger(t, DEAL_POSITION_ID) == posId)
      {
         long entry = HistoryDealGetInteger(t, DEAL_ENTRY);
         if(entry == DEAL_ENTRY_IN)
         {
            openPrice = HistoryDealGetDouble(t, DEAL_PRICE);
            openTime = HistoryDealGetInteger(t, DEAL_TIME);
            return;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Get Initial Deposit from MT5 balance deals history               |
//+------------------------------------------------------------------+
double GetAccountInitialDeposit()
{
   HistorySelect(0, TimeCurrent());
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong t = HistoryDealGetTicket(i);
      if(t > 0)
      {
         long type = HistoryDealGetInteger(t, DEAL_TYPE);
         if(type == DEAL_TYPE_BALANCE)
         {
            double p = HistoryDealGetDouble(t, DEAL_PROFIT);
            if(p > 0.0) return p;
         }
      }
   }
   return 0.0;
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
      
      ulong posId = (ulong)HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
      double openPrice = dealPrice;
      long openTime = dealTime;
      if(posId > 0)
      {
         GetDealPositionOpenDetails(posId, openPrice, openTime);
      }
      
      string origType = (dealType == DEAL_TYPE_SELL ? "BUY" : "SELL");
      
      if(count > 0) json += ",";
      json += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.2f,\"open_price\":%.5f,\"close_price\":%.5f,\"profit\":%.2f,\"open_time\":%I64d,\"close_time\":%I64d,\"magic\":%I64d}",
         dealTicket,
         EscapeJsonString(dealSymbol),
         origType,
         dealVol,
         openPrice,
         dealPrice,
         dealProfit,
         openTime,
         dealTime,
         dealMagic
      );
      count++;
   }
   json += "]";
   return json;
}

//+------------------------------------------------------------------+
//| Auto-Breakeven & Dynamic Trailing Stop for Open Positions        |
//+------------------------------------------------------------------+
void ManagePositionsProtection()
{
   if(!InpEnableBEP && !InpEnableTrailing) return;

   int total = PositionsTotal();
   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      long posMagic = PositionGetInteger(POSITION_MAGIC);
      if(InpMagicNumber != 0 && posMagic != 0 && posMagic != (long)InpMagicNumber) continue;
      
      string posSymbol = PositionGetString(POSITION_SYMBOL);
      long posType = PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      double currentPrice = PositionGetDouble(POSITION_PRICE_CURRENT);
      
      double point = SymbolInfoDouble(posSymbol, SYMBOL_POINT);
      int digits = (int)SymbolInfoInteger(posSymbol, SYMBOL_DIGITS);
      if(point <= 0.0) continue;

      int pointsPerPip = GetPointsPerPip(posSymbol);
      double bepTriggerPts = InpBEPTriggerPips * pointsPerPip;
      double bepBufferPts = InpBEPBufferPips * pointsPerPip;
      double trailingDistPts = InpTrailingDistPips * pointsPerPip;
      double trailingStepPts = InpTrailingStepPips * pointsPerPip;

      if(posType == POSITION_TYPE_BUY)
      {
         double profitPoints = (currentPrice - openPrice) / point;
         
         // 1. Auto-Breakeven check
         if(InpEnableBEP && profitPoints >= bepTriggerPts)
         {
            double newSL = NormalizeDouble(openPrice + (bepBufferPts * point), digits);
            if(currentSL < newSL - (point * 0.5) || currentSL == 0.0)
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, newSL, currentTP))
               {
                  PrintFormat(">>> [BridgeEA] Auto-BEP BUY #%I64u: SL moved to %.5f (+%d pts)",
                              ticket, newSL, (int)bepBufferPts);
                  currentSL = newSL;
               }
            }
         }
         
         // 2. Trailing Stop check
         if(InpEnableTrailing && profitPoints >= trailingDistPts)
         {
            double proposedSL = NormalizeDouble(currentPrice - (trailingDistPts * point), digits);
            if(proposedSL > currentSL + (trailingStepPts * point))
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, proposedSL, currentTP))
               {
                  PrintFormat(">>> [BridgeEA] Trailing Stop BUY #%I64u: SL trailed to %.5f",
                              ticket, proposedSL);
               }
            }
         }
      }
      else if(posType == POSITION_TYPE_SELL)
      {
         double profitPoints = (openPrice - currentPrice) / point;
         
         // 1. Auto-Breakeven check
         if(InpEnableBEP && profitPoints >= bepTriggerPts)
         {
            double newSL = NormalizeDouble(openPrice - (bepBufferPts * point), digits);
            if(currentSL > newSL + (point * 0.5) || currentSL == 0.0)
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, newSL, currentTP))
               {
                  PrintFormat(">>> [BridgeEA] Auto-BEP SELL #%I64u: SL moved to %.5f (+%d pts)",
                              ticket, newSL, (int)bepBufferPts);
                  currentSL = newSL;
               }
            }
         }
         
         // 2. Trailing Stop check
         if(InpEnableTrailing && profitPoints >= trailingDistPts)
         {
            double proposedSL = NormalizeDouble(currentPrice + (trailingDistPts * point), digits);
            if(currentSL == 0.0 || proposedSL < currentSL - (trailingStepPts * point))
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, proposedSL, currentTP))
               {
                  PrintFormat(">>> [BridgeEA] Trailing Stop SELL #%I64u: SL trailed to %.5f",
                              ticket, proposedSL);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Build JSON array of recent candles for specified timeframe       |
//+------------------------------------------------------------------+
string BuildCandlesJson(ENUM_TIMEFRAMES tf = PERIOD_M15)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, tf, 0, 35, rates);
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
   
   double initial_deposit = GetAccountInitialDeposit();
   if(!MathIsValidNumber(initial_deposit)) initial_deposit = 0.0;
   
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
   string candlesM15Json = BuildCandlesJson(PERIOD_M15);
   string candlesM5Json = BuildCandlesJson(PERIOD_M5);

   string json = "{"
      + StringFormat("\"account_number\":%I64d,", login)
      + "\"server\":\"" + server + "\","
      + "\"currency\":\"" + currency + "\","
      + StringFormat("\"balance\":%.2f,", balance)
      + StringFormat("\"equity\":%.2f,", equity)
      + StringFormat("\"initial_deposit\":%.2f,", initial_deposit)
      + StringFormat("\"margin\":%.2f,", margin)
      + StringFormat("\"free_margin\":%.2f,", free_margin)
      + StringFormat("\"margin_level\":%.2f,", margin_level)
      + StringFormat("\"floating_pnl\":%.2f,", profit)
      + "\"terminal_connected\":" + (connected ? "true," : "false,")
      + StringFormat("\"open_positions\":%d,", positions)
      + "\"positions\":" + positionsJson + ","
      + "\"market_quotes\":" + quotesJson + ","
      + "\"closed_trades\":" + closedTradesJson + ","
      + "\"candles\":" + candlesM15Json + ","
      + "\"candles_m5\":" + candlesM5Json + ","
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
   
   // 2. Native WebRequest failed
   int err = GetLastError();
   g_consecutive_errors++;
   g_status_msg = StringFormat("Connection Failed (HTTP %d, Err %d)", res, err);
   if(g_consecutive_errors % 10 == 1)
   {
      if(err == 4014)
      {
         Print(">>> [BridgeEA] ERROR 4014: URL not allowed! Please add '", InpBackendUrl, "' to Tools -> Options -> Expert Advisors -> Allow WebRequest for listed URL.");
      }
      else
      {
         Print(">>> [BridgeEA] Heartbeat failed. HTTP: ", res, ", WebRequest Err: ", err, " URL: ", endpoint);
      }
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
