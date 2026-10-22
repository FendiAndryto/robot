//+------------------------------------------------------------------+
//|                                  TradeGearConfluenceRobot.mq5    |
//|               Copyright 2026, TradeGear Autonomous Trading Engine |
//|                                     https://tradegear.my.id      |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, TradeGear"
#property link        "https://tradegear.my.id"
#property version     "1.05"
#property description "TradeGear Autonomous Confluence Trading Robot EA v1.05"
#property description "Trend: EMA 20/50 | Pullback Retest Filter | Anti-Choke Golden Profit Lock & BEP | 1:2 R:R"

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
input double          InpStopLossPips          = 40.0;     // Stop Loss in Pips (Default: 40 pips, Gold: 45 pips)
input double          InpTakeProfitPips        = 80.0;     // Take Profit in Pips (1:2 Ratio -> 80 pips)
input double          InpMaxSpreadPoints       = 350.0;    // Max Spread in Points (Gold: 350, FX: 45)

input group "--- Advanced Trade Protection (Anti-Choke & Profit Lock) ---"
input bool            InpEnableBEP             = true;     // Enable Auto-Breakeven Protection (BEP)
input int             InpBEPTriggerPips        = 35;       // Profit in Pips to Trigger BEP (e.g. 35 pips)
input int             InpBEPBufferPips         = 4;        // Buffer Pips above Entry for BEP (4 pips safe buffer)
input bool            InpEnableProfitLock      = true;     // Enable Golden Profit Lock (Locks profit when near TP)
input int             InpProfitLockTriggerPips = 60;       // Profit in Pips to Lock Gain (60 pips = ~75% to TP)
input int             InpProfitLockGainPips    = 30;       // Pips Locked In (Guarantees +30 pips if price reverses)
input bool            InpEnableTrailing        = true;     // Enable Dynamic Trailing Stop
input int             InpTrailingDistPips      = 25;       // Trailing Distance in Pips
input int             InpTrailingStepPips      = 5;        // Trailing Step in Pips

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
//| Get Adaptive Stop Loss Pips for symbol (Anti-Choke minimums)     |
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
   return GetAdaptiveSLPips(sym) * 2.0; // Strictly 1:2 R:R (e.g. 40 pip SL -> 80 pip TP)
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
//| Manage Position Protections (BEP, Golden Profit Lock, Trailing)  |
//+------------------------------------------------------------------+
void ManagePositionsProtection()
{
   int total = PositionsTotal();
   string sym = _Symbol;
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   int pointsPerPip = GetPointsPerPip(sym);

   double bepTriggerPts      = InpBEPTriggerPips * pointsPerPip;
   double bepBufferPts       = InpBEPBufferPips * pointsPerPip;
   double profitLockTrigPts  = InpProfitLockTriggerPips * pointsPerPip;
   double profitLockGainPts  = InpProfitLockGainPips * pointsPerPip;
   double trailingDistPts    = InpTrailingDistPips * pointsPerPip;
   double trailingStepPts    = InpTrailingStepPips * pointsPerPip;

   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;

      if(PositionGetString(POSITION_SYMBOL) != sym || PositionGetInteger(POSITION_MAGIC) != (long)InpMagicNumber)
         continue;

      long posType = PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      double currentPrice = PositionGetDouble(POSITION_PRICE_CURRENT);

      if(posType == POSITION_TYPE_BUY)
      {
         double profitPts = (currentPrice - openPrice) / point;

         // Tier 2: Golden Profit Lock (e.g. at 60 pips profit, lock in 30 pips)
         if(InpEnableProfitLock && profitPts >= profitLockTrigPts)
         {
            double lockSL = NormalizeDouble(openPrice + (profitLockGainPts * point), digits);
            if(lockSL > currentSL + (point * 0.5) || currentSL == 0.0)
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, lockSL, currentTP))
                  PrintFormat("[TG-Robot] Tier-2 Profit Lock BUY #%I64u: SL locked at %.5f (+%d pips profit secured!)",
                              ticket, lockSL, InpProfitLockGainPips);
            }
         }
         // Tier 1: Auto-BEP (e.g. at 35 pips profit, move SL to entry + 4 pips buffer)
         else if(InpEnableBEP && profitPts >= bepTriggerPts)
         {
            double newSL = NormalizeDouble(openPrice + (bepBufferPts * point), digits);
            if(currentSL < newSL - (point * 0.5) || currentSL == 0.0)
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, newSL, currentTP))
                  PrintFormat("[TG-Robot] Auto-BEP BUY #%I64u: SL moved to %.5f (Zero-Risk Active)", ticket, newSL);
            }
         }

         // Tier 3: Dynamic Trailing Stop (Rides the move when deep in profit)
         if(InpEnableTrailing && profitPts >= trailingDistPts)
         {
            double proposedSL = NormalizeDouble(currentPrice - (trailingDistPts * point), digits);
            if(proposedSL > currentSL + (trailingStepPts * point))
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, proposedSL, currentTP))
                  PrintFormat("[TG-Robot] Trailing BUY #%I64u: SL trailed to %.5f", ticket, proposedSL);
            }
         }
      }
      else if(posType == POSITION_TYPE_SELL)
      {
         double profitPts = (openPrice - currentPrice) / point;

         // Tier 2: Golden Profit Lock (e.g. at 60 pips profit, lock in 30 pips)
         if(InpEnableProfitLock && profitPts >= profitLockTrigPts)
         {
            double lockSL = NormalizeDouble(openPrice - (profitLockGainPts * point), digits);
            if(currentSL == 0.0 || lockSL < currentSL - (point * 0.5))
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, lockSL, currentTP))
                  PrintFormat("[TG-Robot] Tier-2 Profit Lock SELL #%I64u: SL locked at %.5f (+%d pips profit secured!)",
                              ticket, lockSL, InpProfitLockGainPips);
            }
         }
         // Tier 1: Auto-BEP (e.g. at 35 pips profit, move SL to entry - 4 pips buffer)
         else if(InpEnableBEP && profitPts >= bepTriggerPts)
         {
            double newSL = NormalizeDouble(openPrice - (bepBufferPts * point), digits);
            if(currentSL > newSL + (point * 0.5) || currentSL == 0.0)
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, newSL, currentTP))
                  PrintFormat("[TG-Robot] Auto-BEP SELL #%I64u: SL moved to %.5f (Zero-Risk Active)", ticket, newSL);
            }
         }

         // Tier 3: Dynamic Trailing Stop (Rides the move when deep in profit)
         if(InpEnableTrailing && profitPts >= trailingDistPts)
         {
            double proposedSL = NormalizeDouble(currentPrice + (trailingDistPts * point), digits);
            if(currentSL == 0.0 || proposedSL < currentSL - (trailingStepPts * point))
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, proposedSL, currentTP))
                  PrintFormat("[TG-Robot] Trailing SELL #%I64u: SL trailed to %.5f", ticket, proposedSL);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Update On-Chart Information HUD                                  |
//+------------------------------------------------------------------+
void UpdateChartHUD(double fastEMA, double slowEMA, double rsi, string signalStatus)
{
   double maxSpreadAllowed = GetMaxSpreadLimit(_Symbol);
   int curSpread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double slPips = GetAdaptiveSLPips(_Symbol);
   double tpPips = GetAdaptiveTPPips(_Symbol);
   double lot = InpUseDynamicRisk ? CalculateLotSize(_Symbol, slPips, InpRiskPercent) : InpFixedLot;

   bool termTrade = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED);
   bool eaTrade   = (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
   bool acctTrade = (bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);

   string bias = "NEUTRAL";
   if(fastEMA > slowEMA && fastEMA > 0) bias = "BULLISH (UPTREND)";
   else if(fastEMA < slowEMA && slowEMA > 0) bias = "BEARISH (DOWNTREND)";

   string hud = "=================================================\n";
   hud += "  TRADEGEAR CONFLUENCE ROBOT (AUTONOMOUS EA) v1.05\n";
   hud += "=================================================\n";
   hud += StringFormat(" Symbol: %s | Timeframe: %s | Magic: %I64u\n", _Symbol, EnumToString(_Period), InpMagicNumber);
   hud += StringFormat(" Fast EMA (%d): %.5f | Slow EMA (%d): %.5f\n", InpFastEMAPeriod, fastEMA, InpSlowEMAPeriod, slowEMA);
   hud += StringFormat(" RSI (%d): %.2f | Market Bias: %s\n", InpRSIPeriod, rsi, bias);
   hud += StringFormat(" Spread: %d pts (Limit: %d pts) | Open Pos: %d\n", curSpread, (int)maxSpreadAllowed, CountOpenPositions(_Symbol, InpMagicNumber));
   hud += StringFormat(" Strategy Targets: SL %.0f pips | TP %.0f pips (1:2 R:R)\n", slPips, tpPips);
   hud += StringFormat(" Protection: BEP @ +%dp | Profit Lock @ +%dp (+%dp)\n", InpBEPTriggerPips, InpProfitLockTriggerPips, InpProfitLockGainPips);
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
   double tpPips = GetAdaptiveTPPips(_Symbol);
   PrintFormat("[TG-Robot] Initialized v1.05 on %s | SL: %.0fp | TP: %.0fp (1:2 RR) | Lot: %.2f | Spread Limit: %d pts",
               _Symbol, slPips, tpPips, InpFixedLot, (int)GetMaxSpreadLimit(_Symbol));
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
   // 1. Manage active position protections on every tick (BEP, Golden Profit Lock, Trailing)
   ManagePositionsProtection();

   // 2. Read indicator buffers for previous completed candle (index 1)
   double fastEMABuffer[2], slowEMABuffer[2], rsiBuffer[2];
   double fastEMA = 0.0, slowEMA = 0.0, rsi = 0.0;
   if(CopyBuffer(g_handleFastEMA, 0, 1, 2, fastEMABuffer) >= 2) fastEMA = fastEMABuffer[1];
   if(CopyBuffer(g_handleSlowEMA, 0, 1, 2, slowEMABuffer) >= 2) slowEMA = slowEMABuffer[1];
   if(CopyBuffer(g_handleRSI, 0, 1, 2, rsiBuffer) >= 2) rsi = rsiBuffer[1];

   // 3. Spread Guard Check
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double maxSpreadAllowed = GetMaxSpreadLimit(_Symbol);
   if(spread > (long)maxSpreadAllowed)
   {
      UpdateChartHUD(fastEMA, slowEMA, rsi, StringFormat("BLOCKED: Spread too wide (%d > %d pts)", (int)spread, (int)maxSpreadAllowed));
      return;
   }

   int openCount = CountOpenPositions(_Symbol, InpMagicNumber);

   // 4. New Bar Check: Evaluate signals once per bar close
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_lastBarTime)
   {
      string idleStatus = (openCount > 0) ? "POSITION ACTIVE (MANAGING PROTECTION)" : "WAITING FOR CANDLE CLOSE...";
      UpdateChartHUD(fastEMA, slowEMA, rsi, idleStatus);
      return;
   }

   string signalStatus = "SCANNING...";

   if(openCount == 0)
   {
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      int pointsPerPip = GetPointsPerPip(_Symbol);

      double slPips = GetAdaptiveSLPips(_Symbol);
      double tpPips = GetAdaptiveTPPips(_Symbol);
      double lot = InpUseDynamicRisk ? CalculateLotSize(_Symbol, slPips, InpRiskPercent) : InpFixedLot;

      double open1  = iOpen(_Symbol, _Period, 1);
      double high1  = iHigh(_Symbol, _Period, 1);
      double low1   = iLow(_Symbol, _Period, 1);
      double close1 = iClose(_Symbol, _Period, 1);

      // Maximum allowable distance from Fast EMA to avoid buying/selling at exhausted extremes:
      double maxDistFromEMA = slPips * 0.70 * pointsPerPip * point;

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
            double sl = NormalizeDouble(ask - (slPips * pointsPerPip * point), digits);
            double tp = NormalizeDouble(ask + (tpPips * pointsPerPip * point), digits);

            ResetLastError();
            if(g_trade.Buy(lot, _Symbol, ask, sl, tp, InpOrderComment))
            {
               PrintFormat("[TG-Robot] BUY executed! Lot: %.2f | Ask: %.5f | SL: %.5f (-%.0fp) | TP: %.5f (+%.0fp) [1:2 RR]",
                           lot, ask, sl, slPips, tp, tpPips);
               g_lastBarTime = currentBarTime;
               signalStatus = "BUY EXECUTED (1:2 RR)";
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
            double sl = NormalizeDouble(bid + (slPips * pointsPerPip * point), digits);
            double tp = NormalizeDouble(bid - (tpPips * pointsPerPip * point), digits);

            ResetLastError();
            if(g_trade.Sell(lot, _Symbol, bid, sl, tp, InpOrderComment))
            {
               PrintFormat("[TG-Robot] SELL executed! Lot: %.2f | Bid: %.5f | SL: %.5f (+%.0fp) | TP: %.5f (-%.0fp) [1:2 RR]",
                           lot, bid, sl, slPips, tp, tpPips);
               g_lastBarTime = currentBarTime;
               signalStatus = "SELL EXECUTED (1:2 RR)";
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
      signalStatus = "POSITION ACTIVE (MANAGING PROTECTION)";
   }

   UpdateChartHUD(fastEMA, slowEMA, rsi, signalStatus);
}
//+------------------------------------------------------------------+
