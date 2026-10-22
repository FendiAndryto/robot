//+------------------------------------------------------------------+
//|                                  TradeGearConfluenceRobot.mq5    |
//|               Copyright 2026, TradeGear Autonomous Trading Engine |
//|                                     https://tradegear.my.id      |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, TradeGear"
#property link        "https://tradegear.my.id"
#property version     "1.07"
#property description "TradeGear Pure 1:2 R:R Autonomous Confluence Robot EA v1.07"
#property description "Trend: EMA 20/50 | Dynamic Swing/Engulfing Structure SL | Adaptive 1:2 R:R"

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "--- Strategy Parameters ---"
input int             InpFastEMAPeriod         = 20;       // Fast EMA Period
input int             InpSlowEMAPeriod         = 50;       // Slow EMA Period
input int             InpRSIPeriod             = 14;       // RSI Period
input double          InpRSIBullishMin         = 46.0;     // RSI Bullish Confirmation Min
input double          InpRSIBullishMax         = 62.0;     // RSI Bullish Confirmation Max
input double          InpRSIBearishMin         = 38.0;     // RSI Bearish Confirmation Min
input double          InpRSIBearishMax         = 54.0;     // RSI Bearish Confirmation Max
input bool            InpRequirePullback       = true;     // Require Candle Retest Near EMA (Anti-Chasing)

input group "--- Risk & Position Sizing ---"
input bool            InpUseDynamicRisk        = false;    // Use % Equity Risk Sizing (Default: false -> Lot 0.01)
input double          InpRiskPercent           = 1.0;      // Risk Per Trade (% of Equity)
input double          InpFixedLot              = 0.01;     // Fixed Lot Size (Default: 0.01 lot)
input bool            InpUseSwingSL            = true;     // Place SL at Recent Swing / Engulfing Structure
input int             InpSwingLookbackBars     = 3;        // Swing Lookback Bars (1 = Trigger Candle only, 3 = Recent Swing)
input double          InpSLBufferPips          = 3.0;      // Safety Buffer beyond Candle Wick (Pips)
input double          InpMinSLPips             = 20.0;     // Min SL Distance in Pips (Default: 20 pips)
input double          InpMaxSLPips             = 80.0;     // Max SL Ceiling in Pips (Default: 80 pips)
input double          InpRiskRewardRatio       = 2.0;      // Strict 1:2 R:R Ratio (TP = SL * Ratio)
input double          InpStopLossPips          = 45.0;     // Fallback SL in Pips (used if Swing SL disabled)
input double          InpTakeProfitPips        = 90.0;     // Fallback TP in Pips (used if Swing SL disabled)
input double          InpMaxSpreadPoints       = 350.0;    // Max Spread in Points (Gold: 350, FX: 45)

input group "--- Execution Settings ---"
input ulong           InpMagicNumber           = 778899;   // Magic Number
input ulong           InpSlippagePoints        = 15;       // Max Slippage in Points
input string          InpOrderComment          = "TG-Robot"; // Order Comment

//--- Global Variables
CTrade                g_trade;
int                   g_handleFastEMA          = INVALID_HANDLE;
int                   g_handleSlowEMA          = INVALID_HANDLE;
int                   g_handleRSI              = INVALID_HANDLE;
datetime              g_lastBarTime            = 0;

//+------------------------------------------------------------------+
//| Calculate Points Per Pip for symbol                              |
//+------------------------------------------------------------------+
int GetPointsPerPip(string sym)
{
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   string upper = sym;
   StringToUpper(upper);
   
   if(StringFind(upper, "XAU") >= 0 || StringFind(upper, "GOLD") >= 0)
   {
      return (digits == 3 ? 100 : 10);
   }
   if(StringFind(upper, "BTC") >= 0)
   {
      return (digits == 2 ? 100 : 1);
   }
   if(digits == 3 || digits == 5)
   {
      return 10;
   }
   return 1;
}

//+------------------------------------------------------------------+
//| Get Adaptive Max Spread Limit for symbol                         |
//+------------------------------------------------------------------+
double GetMaxSpreadLimit(string sym)
{
   string upper = sym;
   StringToUpper(upper);
   if(StringFind(upper, "XAU") >= 0 || StringFind(upper, "GOLD") >= 0)
   {
      // Gold default max spread threshold (35 pips = 350 points)
      return (InpMaxSpreadPoints > 40.0 ? InpMaxSpreadPoints : 350.0);
   }
   if(StringFind(upper, "BTC") >= 0)
   {
      return (InpMaxSpreadPoints > 100.0 ? InpMaxSpreadPoints : 3000.0);
   }
   return InpMaxSpreadPoints;
}

//+------------------------------------------------------------------+
//| Get Adaptive Stop Loss Pips for symbol (Clean breathing room)    |
//+------------------------------------------------------------------+
double GetAdaptiveSLPips(string sym)
{
   string upper = sym;
   StringToUpper(upper);
   if(StringFind(upper, "XAU") >= 0 || StringFind(upper, "GOLD") >= 0)
   {
      // Gold safe default SL: min 45 pips ($4.50)
      return (InpStopLossPips >= 40.0 ? InpStopLossPips : 45.0);
   }
   if(StringFind(upper, "BTC") >= 0)
   {
      return (InpStopLossPips >= 100.0 ? InpStopLossPips : 200.0);
   }
   return (InpStopLossPips >= 30.0 ? InpStopLossPips : 35.0);
}

//+------------------------------------------------------------------+
//| Get Adaptive Take Profit Pips for symbol (Strict 1:2 R:R Ratio)  |
//+------------------------------------------------------------------+
double GetAdaptiveTPPips(string sym)
{
   return GetAdaptiveSLPips(sym) * InpRiskRewardRatio; // Strictly 1:2 R:R
}

//+------------------------------------------------------------------+
//| Calculate Dynamic Lot Size based on % Risk and Stop Loss Pips    |
//+------------------------------------------------------------------+
double CalculateLotSize(string sym, double slPips, double riskPct)
{
   if(!InpUseDynamicRisk)
   {
      return InpFixedLot;
   }

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0) equity = AccountInfoDouble(ACCOUNT_BALANCE);
   if(equity <= 0.0) return InpFixedLot;

   double riskAmount = equity * (riskPct / 100.0);
   double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   int pointsPerPip = GetPointsPerPip(sym);

   if(point <= 0.0 || tickSize <= 0.0 || tickValue <= 0.0)
      return InpFixedLot;

   double slPoints = slPips * (double)pointsPerPip;
   double lossPerLot = (slPoints * point / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return InpFixedLot;

   double calculatedLot = riskAmount / lossPerLot;

   double minLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);

   if(stepLot > 0.0)
      calculatedLot = MathFloor(calculatedLot / stepLot) * stepLot;

   if(calculatedLot < minLot) calculatedLot = minLot;
   if(calculatedLot > maxLot) calculatedLot = maxLot;

   return NormalizeDouble(calculatedLot, 2);
}

//+------------------------------------------------------------------+
//| Set Safe Execution Filling Type for Broker                       |
//+------------------------------------------------------------------+
void SetSafeFillingType(string sym)
{
   uint filling = (uint)SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_FOK) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((filling & SYMBOL_FILLING_IOC) != 0)
      g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      g_trade.SetTypeFilling(ORDER_FILLING_RETURN);
}

//+------------------------------------------------------------------+
//| Count Open Positions for this EA on this Symbol                  |
//+------------------------------------------------------------------+
int CountOpenPositions(string sym, ulong magic)
{
   int count = 0;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == sym && PositionGetInteger(POSITION_MAGIC) == (long)magic)
      {
         count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Calculate Dynamic Swing / Structure SL & 1:2 TP                 |
//+------------------------------------------------------------------+
void CalculateDynamicSLTP(bool isBuy, double entryPrice, double &outSLPrice, double &outTPPrice, double &outSLPips, double &outTPPips)
{
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   int pointsPerPip = GetPointsPerPip(_Symbol);
   double pipUnit = (double)pointsPerPip * point;

   if(!InpUseSwingSL)
   {
      outSLPips = GetAdaptiveSLPips(_Symbol);
      outTPPips = outSLPips * InpRiskRewardRatio;
      if(isBuy)
      {
         outSLPrice = NormalizeDouble(entryPrice - (outSLPips * pipUnit), digits);
         outTPPrice = NormalizeDouble(entryPrice + (outTPPips * pipUnit), digits);
      }
      else
      {
         outSLPrice = NormalizeDouble(entryPrice + (outSLPips * pipUnit), digits);
         outTPPrice = NormalizeDouble(entryPrice - (outTPPips * pipUnit), digits);
      }
      return;
   }

   int lookback = (InpSwingLookbackBars > 0) ? InpSwingLookbackBars : 1;
   double bufferDistance = InpSLBufferPips * pipUnit;

   if(isBuy)
   {
      double lowestLow = iLow(_Symbol, _Period, 1);
      for(int i = 2; i <= lookback; i++)
      {
         double lowVal = iLow(_Symbol, _Period, i);
         if(lowVal < lowestLow) lowestLow = lowVal;
      }

      double rawSL = lowestLow - bufferDistance;
      double slDist = entryPrice - rawSL;
      double slPips = (pipUnit > 0.0) ? (slDist / pipUnit) : InpStopLossPips;

      if(slPips < InpMinSLPips) slPips = InpMinSLPips;
      if(slPips > InpMaxSLPips) slPips = InpMaxSLPips;

      outSLPips = slPips;
      outTPPips = slPips * InpRiskRewardRatio;
      outSLPrice = NormalizeDouble(entryPrice - (outSLPips * pipUnit), digits);
      outTPPrice = NormalizeDouble(entryPrice + (outTPPips * pipUnit), digits);
   }
   else
   {
      double highestHigh = iHigh(_Symbol, _Period, 1);
      for(int i = 2; i <= lookback; i++)
      {
         double highVal = iHigh(_Symbol, _Period, i);
         if(highVal > highestHigh) highestHigh = highVal;
      }

      double rawSL = highestHigh + bufferDistance;
      double slDist = rawSL - entryPrice;
      double slPips = (pipUnit > 0.0) ? (slDist / pipUnit) : InpStopLossPips;

      if(slPips < InpMinSLPips) slPips = InpMinSLPips;
      if(slPips > InpMaxSLPips) slPips = InpMaxSLPips;

      outSLPips = slPips;
      outTPPips = slPips * InpRiskRewardRatio;
      outSLPrice = NormalizeDouble(entryPrice + (outSLPips * pipUnit), digits);
      outTPPrice = NormalizeDouble(entryPrice - (outTPPips * pipUnit), digits);
   }
}

//+------------------------------------------------------------------+
//| Update On-Chart Information HUD                                  |
//+------------------------------------------------------------------+
void UpdateChartHUD(double fastEMA, double slowEMA, double rsi, string signalStatus)
{
   double maxSpreadAllowed = GetMaxSpreadLimit(_Symbol);
   int curSpread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double defaultSLPips = GetAdaptiveSLPips(_Symbol);
   double defaultTPPips = defaultSLPips * InpRiskRewardRatio;
   double lot = InpUseDynamicRisk ? CalculateLotSize(_Symbol, defaultSLPips, InpRiskPercent) : InpFixedLot;

   bool termTrade = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   bool eaTrade   = (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
   bool acctTrade = (bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);

   string bias = "NEUTRAL";
   if(fastEMA > slowEMA && fastEMA > 0) bias = "BULLISH (UPTREND)";
   else if(fastEMA < slowEMA && slowEMA > 0) bias = "BEARISH (DOWNTREND)";

   string hud = "=================================================\n";
   hud += "  TRADEGEAR CONFLUENCE ROBOT (AUTONOMOUS EA) v1.07\n";
   hud += "=================================================\n";
   hud += StringFormat(" Symbol: %s | Timeframe: %s | Magic: %I64u\n", _Symbol, EnumToString(_Period), InpMagicNumber);
   hud += StringFormat(" Fast EMA (%d): %.5f | Slow EMA (%d): %.5f\n", InpFastEMAPeriod, fastEMA, InpSlowEMAPeriod, slowEMA);
   hud += StringFormat(" RSI (%d): %.2f | Market Bias: %s\n", InpRSIPeriod, rsi, bias);
   hud += StringFormat(" Spread: %d pts (Limit: %d pts) | Open Pos: %d\n", curSpread, (int)maxSpreadAllowed, CountOpenPositions(_Symbol, InpMagicNumber));
   if(InpUseSwingSL)
   {
      hud += StringFormat(" SL/TP Mode : DYNAMIC SWING (Lookback %d bars | +%.1fp buf)\n", InpSwingLookbackBars, InpSLBufferPips);
      hud += StringFormat(" Target R:R : Strict 1:%.1f (Min %.0fp, Max %.0fp)\n", InpRiskRewardRatio, InpMinSLPips, InpMaxSLPips);
   }
   else
   {
      hud += StringFormat(" SL/TP Mode : FIXED (SL %.0fp | TP %.0fp - 1:%.1f R:R)\n", defaultSLPips, defaultTPPips, InpRiskRewardRatio);
   }
   hud += " Protection Model: Pure Dynamic SL/TP (BEP Disabled)\n";
   hud += StringFormat(" Order Execution Lot : %.2f %s\n", lot, InpUseDynamicRisk ? "(Dynamic)" : "(Fixed 0.01)");
   hud += "---------------- PERMISSIONS --------------------\n";
   hud += StringFormat(" Toolbar Algo Trading : %s\n", termTrade ? "ON [GREEN OK]" : "OFF! [CLICK TOOLBAR ALGO TRADING]");
   hud += StringFormat(" Chart EA Permission  : %s\n", eaTrade ? "ALLOWED [OK]" : "BLOCKED! [F7 -> Common -> Allow Algo Trading]");
   hud += StringFormat(" Account Trade Mode   : %s\n", acctTrade ? "TRADING ACTIVE [OK]" : "READ-ONLY (INVESTOR PASSWORD!)");
   hud += "-------------------------------------------------\n";
   hud += StringFormat(" Status: %s\n", signalStatus);
   hud += "=================================================\n";
   hud += " Note: Run TradeGearMonitor.ex5 on another chart\n";
   hud += " to stream telemetry & journal in TradeGear SaaS.\n";
   hud += "=================================================";

   Comment(hud);
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints(InpSlippagePoints);
   SetSafeFillingType(_Symbol);

   // Initialize Indicator Handles
   g_handleFastEMA = iMA(_Symbol, _Period, InpFastEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_handleSlowEMA = iMA(_Symbol, _Period, InpSlowEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_handleRSI = iRSI(_Symbol, _Period, InpRSIPeriod, PRICE_CLOSE);

   if(g_handleFastEMA == INVALID_HANDLE || g_handleSlowEMA == INVALID_HANDLE || g_handleRSI == INVALID_HANDLE)
   {
      Print("[TG-Robot] Error creating technical indicator handles!");
      return INIT_FAILED;
   }

   double slPips = GetAdaptiveSLPips(_Symbol);
   double tpPips = slPips * InpRiskRewardRatio;
   PrintFormat("[TG-Robot] Initialized v1.07 on %s | Swing SL: %s (Lookback %d, Buffer %.1fp) | 1:%.1f RR | Default SL/TP: %.0fp/%.0fp | Lot: %.2f",
               _Symbol, InpUseSwingSL ? "ENABLED" : "DISABLED", InpSwingLookbackBars, InpSLBufferPips, InpRiskRewardRatio, slPips, tpPips, InpFixedLot);
   PrintFormat("[TG-Robot] Pre-flight Check: TerminalTradeAllowed=%s | EATradeAllowed=%s | AcctTradeAllowed=%s",
               TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) ? "YES" : "NO",
               MQLInfoInteger(MQL_TRADE_ALLOWED) ? "YES" : "NO",
               AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) ? "YES" : "NO");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Comment("");
   IndicatorRelease(g_handleFastEMA);
   IndicatorRelease(g_handleSlowEMA);
   IndicatorRelease(g_handleRSI);
   Print("[TG-Robot] Deinitialized. Reason code: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Read indicator buffers for previous completed candle (index 1)
   double fastEMABuffer[2], slowEMABuffer[2], rsiBuffer[2];
   double fastEMA = 0.0, slowEMA = 0.0, rsi = 0.0;
   if(CopyBuffer(g_handleFastEMA, 0, 1, 2, fastEMABuffer) >= 2) fastEMA = fastEMABuffer[1];
   if(CopyBuffer(g_handleSlowEMA, 0, 1, 2, slowEMABuffer) >= 2) slowEMA = slowEMABuffer[1];
   if(CopyBuffer(g_handleRSI, 0, 1, 2, rsiBuffer) >= 2) rsi = rsiBuffer[1];

   // 2. Spread Guard Check
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double maxSpreadAllowed = GetMaxSpreadLimit(_Symbol);
   if(spread > (long)maxSpreadAllowed)
   {
      UpdateChartHUD(fastEMA, slowEMA, rsi, StringFormat("BLOCKED: Spread too wide (%d > %d pts)", (int)spread, (int)maxSpreadAllowed));
      return;
   }

   int openCount = CountOpenPositions(_Symbol, InpMagicNumber);

   // 3. New Bar Check: Evaluate signals once per bar close
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_lastBarTime)
   {
      string idleStatus = (openCount > 0) ? "POSITION RUNNING (RIDING TO FULL 1:2 TP)" : "WAITING FOR CANDLE CLOSE...";
      UpdateChartHUD(fastEMA, slowEMA, rsi, idleStatus);
      return;
   }

   string signalStatus = "SCANNING...";

   if(openCount == 0)
   {
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      int pointsPerPip = GetPointsPerPip(_Symbol);

      double defaultSLPips = GetAdaptiveSLPips(_Symbol);

      double open1  = iOpen(_Symbol, _Period, 1);
      double high1  = iHigh(_Symbol, _Period, 1);
      double low1   = iLow(_Symbol, _Period, 1);
      double close1 = iClose(_Symbol, _Period, 1);

      // Maximum allowable distance from Fast EMA to avoid buying/selling at exhausted extremes:
      double maxDistFromEMA = defaultSLPips * 0.70 * pointsPerPip * point;

      // BULLISH CONFLUENCE:
      // 1. Fast EMA > Slow EMA (Uptrend bias)
      // 2. Candle 1 closed above Fast EMA
      // 3. Candle 1 closed bullish or with lower wick testing EMA (pullback confirmation)
      // 4. Price not overextended beyond maxDistFromEMA
      // 5. RSI in healthy bullish expansion zone (46 to 62)
      bool pullbackBuy = (!InpRequirePullback || low1 <= fastEMA || (close1 - fastEMA) <= maxDistFromEMA);
      bool isBullish = (fastEMA > slowEMA &&
                        close1 > fastEMA &&
                        close1 >= open1 &&
                        pullbackBuy &&
                        rsi >= InpRSIBullishMin && rsi <= InpRSIBullishMax);

      // BEARISH CONFLUENCE:
      // 1. Fast EMA < Slow EMA (Downtrend bias)
      // 2. Candle 1 closed below Fast EMA
      // 3. Candle 1 closed bearish or with upper wick testing EMA (pullback confirmation)
      // 4. Price not overextended beyond maxDistFromEMA
      // 5. RSI in healthy bearish expansion zone (38 to 54 - NOT oversold < 38)
      bool pullbackSell = (!InpRequirePullback || high1 >= fastEMA || (fastEMA - close1) <= maxDistFromEMA);
      bool isBearish = (fastEMA < slowEMA &&
                        close1 < fastEMA &&
                        close1 <= open1 &&
                        pullbackSell &&
                        rsi >= InpRSIBearishMin && rsi <= InpRSIBearishMax);

      if(isBullish || isBearish)
      {
         bool termTrade = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
         bool eaTrade   = (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
         bool acctTrade = (bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);

         if(!termTrade)
         {
            signalStatus = "BLOCKED: Toolbar 'Algo Trading' is OFF!";
            UpdateChartHUD(fastEMA, slowEMA, rsi, signalStatus);
            static datetime lastPrintTerm = 0;
            if(TimeCurrent() - lastPrintTerm > 5)
            {
               Print("[TG-Robot] Order blocked! 'Algo Trading' button in MT5 toolbar is turned OFF. Click it so it turns GREEN.");
               lastPrintTerm = TimeCurrent();
            }
            return;
         }

         if(!eaTrade)
         {
            signalStatus = "BLOCKED: Press F7 -> Common -> Check 'Allow Algo Trading'";
            UpdateChartHUD(fastEMA, slowEMA, rsi, signalStatus);
            static datetime lastPrintEA = 0;
            if(TimeCurrent() - lastPrintEA > 5)
            {
               Print("[TG-Robot] Order blocked! EA permission is disabled on chart. Press F7 -> Tab Common -> Check 'Allow Algo Trading' -> Click OK.");
               lastPrintEA = TimeCurrent();
            }
            return;
         }

         if(!acctTrade)
         {
            signalStatus = "BLOCKED: Account is Read-Only (Investor Password)";
            UpdateChartHUD(fastEMA, slowEMA, rsi, signalStatus);
            return;
         }

         // --- BULLISH EXECUTION ---
         if(isBullish)
         {
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double slPrice = 0.0, tpPrice = 0.0, dynamicSLPips = 0.0, dynamicTPPips = 0.0;
            CalculateDynamicSLTP(true, ask, slPrice, tpPrice, dynamicSLPips, dynamicTPPips);
            double lot = InpUseDynamicRisk ? CalculateLotSize(_Symbol, dynamicSLPips, InpRiskPercent) : InpFixedLot;

            ResetLastError();
            if(g_trade.Buy(lot, _Symbol, ask, slPrice, tpPrice, InpOrderComment))
            {
               PrintFormat("[TG-Robot] BUY executed! Lot: %.2f | Ask: %.5f | SL: %.5f (-%.1fp) | TP: %.5f (+%.1fp) [Swing SL - Strict 1:%.1f RR]",
                           lot, ask, slPrice, dynamicSLPips, tpPrice, dynamicTPPips, InpRiskRewardRatio);
               g_lastBarTime = currentBarTime;
               signalStatus = StringFormat("BUY EXECUTED (SL %.1fp | TP %.1fp)", dynamicSLPips, dynamicTPPips);
            }
            else
            {
               PrintFormat("[TG-Robot] BUY order failed! Error: %d", GetLastError());
               signalStatus = StringFormat("BUY ERROR (%d)", GetLastError());
            }
         }
         // --- BEARISH EXECUTION ---
         else if(isBearish)
         {
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double slPrice = 0.0, tpPrice = 0.0, dynamicSLPips = 0.0, dynamicTPPips = 0.0;
            CalculateDynamicSLTP(false, bid, slPrice, tpPrice, dynamicSLPips, dynamicTPPips);
            double lot = InpUseDynamicRisk ? CalculateLotSize(_Symbol, dynamicSLPips, InpRiskPercent) : InpFixedLot;

            ResetLastError();
            if(g_trade.Sell(lot, _Symbol, bid, slPrice, tpPrice, InpOrderComment))
            {
               PrintFormat("[TG-Robot] SELL executed! Lot: %.2f | Bid: %.5f | SL: %.5f (+%.1fp) | TP: %.5f (-%.1fp) [Swing SL - Strict 1:%.1f RR]",
                           lot, bid, slPrice, dynamicSLPips, tpPrice, dynamicTPPips, InpRiskRewardRatio);
               g_lastBarTime = currentBarTime;
               signalStatus = StringFormat("SELL EXECUTED (SL %.1fp | TP %.1fp)", dynamicSLPips, dynamicTPPips);
            }
            else
            {
               PrintFormat("[TG-Robot] SELL order failed! Error: %d", GetLastError());
               signalStatus = StringFormat("SELL ERROR (%d)", GetLastError());
            }
         }
      }
      else
      {
         signalStatus = "NO SIGNAL CONFLUENCE";
      }
   }
   else
   {
      signalStatus = "POSITION RUNNING (RIDING TO FULL 1:2 TP)";
   }

   UpdateChartHUD(fastEMA, slowEMA, rsi, signalStatus);
}
//+------------------------------------------------------------------+

