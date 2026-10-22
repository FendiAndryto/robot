//+------------------------------------------------------------------+
//|                                  TradeGearConfluenceRobot.mq5    |
//|               Copyright 2026, TradeGear Autonomous Trading Engine |
//|                                     https://tradegear.my.id      |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, TradeGear"
#property link        "https://tradegear.my.id"
#property version     "1.00"
#property description "TradeGear Standalone Confluence Trading Robot EA"
#property description "Trend: EMA 20/50 | Momentum: RSI 14 | Auto Risk Mgmt & Protection"

#include <Trade\Trade.mqh>

//--- Input Parameters
input group "--- Strategy Parameters ---"
input int             InpFastEMAPeriod     = 20;       // Fast EMA Period
input int             InpSlowEMAPeriod     = 50;       // Slow EMA Period
input int             InpRSIPeriod         = 14;       // RSI Period
input double          InpRSIOversold       = 30.0;     // RSI Oversold Level
input double          InpRSIOverbought     = 70.0;     // RSI Overbought Level
input double          InpRSIBullishMin     = 45.0;     // RSI Bullish Confirmation Min
input double          InpRSIBullishMax     = 65.0;     // RSI Bullish Confirmation Max
input double          InpRSIBearishMin     = 35.0;     // RSI Bearish Confirmation Min
input double          InpRSIBearishMax     = 55.0;     // RSI Bearish Confirmation Max

input group "--- Risk & Position Sizing ---"
input bool            InpUseDynamicRisk    = true;     // Use % Equity Risk Sizing
input double          InpRiskPercent       = 1.0;      // Risk Per Trade (% of Equity)
input double          InpFixedLot          = 0.01;     // Fixed Lot (if Dynamic Risk = false)
input double          InpStopLossPips      = 25.0;     // Default Stop Loss in Pips
input double          InpTakeProfitPips    = 50.0;     // Default Take Profit in Pips (1:2 R:R)
input double          InpMaxSpreadPoints   = 40.0;     // Max Allowable Spread in Points

input group "--- Trade Protection (BEP & Trailing) ---"
input bool            InpEnableBEP         = true;     // Enable Auto-Breakeven Protection
input int             InpBEPTriggerPips    = 18;       // Profit in Pips to Trigger BEP
input int             InpBEPBufferPips     = 2;        // Buffer Pips above Entry for BEP
input bool            InpEnableTrailing    = false;    // Enable Trailing Stop
input int             InpTrailingDistPips  = 20;       // Trailing Distance in Pips
input int             InpTrailingStepPips  = 5;        // Trailing Step in Pips

input group "--- Execution Settings ---"
input ulong           InpMagicNumber       = 778899;   // Magic Number
input ulong           InpSlippagePoints    = 10;       // Max Slippage in Points
input string          InpOrderComment      = "TG-Robot"; // Order Comment

//--- Global Variables
CTrade                g_trade;
int                   g_handleFastEMA      = INVALID_HANDLE;
int                   g_handleSlowEMA      = INVALID_HANDLE;
int                   g_handleRSI          = INVALID_HANDLE;
datetime              g_lastBarTime        = 0;

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
   if(equity <= 0.0) return 0.01;

   double riskAmount = equity * (riskPct / 100.0);
   double tickSize = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   int pointsPerPip = GetPointsPerPip(sym);

   if(point <= 0.0 || tickSize <= 0.0 || tickValue <= 0.0)
      return 0.01;

   double slPoints = slPips * (double)pointsPerPip;
   double lossPerLot = (slPoints * point / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.01;

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
//| Count Active Positions for this EA on Current Symbol             |
//+------------------------------------------------------------------+
int CountOpenPositions(string sym, ulong magic)
{
   int count = 0;
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0)
      {
         if(PositionGetString(POSITION_SYMBOL) == sym && PositionGetInteger(POSITION_MAGIC) == (long)magic)
            count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Position Protection: Auto-Breakeven (BEP) & Trailing Stop        |
//+------------------------------------------------------------------+
void ManagePositionsProtection()
{
   if(!InpEnableBEP && !InpEnableTrailing) return;

   string sym = _Symbol;
   int total = PositionsTotal();
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   int pointsPerPip = GetPointsPerPip(sym);

   double bepTriggerPts = InpBEPTriggerPips * pointsPerPip;
   double bepBufferPts = InpBEPBufferPips * pointsPerPip;
   double trailingDistPts = InpTrailingDistPips * pointsPerPip;
   double trailingStepPts = InpTrailingStepPips * pointsPerPip;

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

         // Auto-Breakeven
         if(InpEnableBEP && profitPts >= bepTriggerPts)
         {
            double newSL = NormalizeDouble(openPrice + (bepBufferPts * point), digits);
            if(currentSL < newSL - (point * 0.5) || currentSL == 0.0)
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, newSL, currentTP))
                  PrintFormat("[TG-Robot] Auto-BEP BUY #%I64u: SL moved to %.5f", ticket, newSL);
            }
         }

         // Trailing Stop
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

         // Auto-Breakeven
         if(InpEnableBEP && profitPts >= bepTriggerPts)
         {
            double newSL = NormalizeDouble(openPrice - (bepBufferPts * point), digits);
            if(currentSL > newSL + (point * 0.5) || currentSL == 0.0)
            {
               ResetLastError();
               if(g_trade.PositionModify(ticket, newSL, currentTP))
                  PrintFormat("[TG-Robot] Auto-BEP SELL #%I64u: SL moved to %.5f", ticket, newSL);
            }
         }

         // Trailing Stop
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
   string hud = "=================================================\n";
   hud += "  TRADEGEAR CONFLUENCE ROBOT (AUTONOMOUS EA)    \n";
   hud += "=================================================\n";
   hud += StringFormat(" Symbol: %s | Timeframe: %s | Magic: %I64u\n", _Symbol, EnumToString(_Period), InpMagicNumber);
   hud += StringFormat(" Fast EMA (%d): %.5f | Slow EMA (%d): %.5f\n", InpFastEMAPeriod, fastEMA, InpSlowEMAPeriod, slowEMA);
   hud += StringFormat(" RSI (%d): %.2f | Bias: %s\n", InpRSIPeriod, rsi, (fastEMA > slowEMA ? "BULLISH" : "BEARISH"));
   hud += StringFormat(" Spread: %d pts (Max: %d) | Open Pos: %d\n", (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD), (int)InpMaxSpreadPoints, CountOpenPositions(_Symbol, InpMagicNumber));
   hud += StringFormat(" Risk Setting: %.1f%% | Status: %s\n", InpRiskPercent, signalStatus);
   hud += "=================================================\n";
   hud += " Note: Run TradeGearMonitor.ex5 on any chart to\n";
   hud += " stream telemetry & track journal in TradeGear SaaS.\n";
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

   Print("[TG-Robot] TradeGear Confluence Robot initialized successfully on ", _Symbol);
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
   // 1. Manage active position protections on every tick
   ManagePositionsProtection();

   // 2. Spread Guard: Do not open trades if spread is wide
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > (long)InpMaxSpreadPoints)
   {
      UpdateChartHUD(0, 0, 0, "BLOCKED: Spread too wide");
      return;
   }

   // 3. New Bar Check: Evaluate signals once per bar close
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == g_lastBarTime)
   {
      return; // Wait for new candle
   }

   // Read indicator buffers for previous completed candle (index 1)
   double fastEMABuffer[2], slowEMABuffer[2], rsiBuffer[2];
   if(CopyBuffer(g_handleFastEMA, 0, 1, 2, fastEMABuffer) < 2) return;
   if(CopyBuffer(g_handleSlowEMA, 0, 1, 2, slowEMABuffer) < 2) return;
   if(CopyBuffer(g_handleRSI, 0, 1, 2, rsiBuffer) < 2) return;

   double fastEMA = fastEMABuffer[1];
   double slowEMA = slowEMABuffer[1];
   double rsi = rsiBuffer[1];
   double closePrice = iClose(_Symbol, _Period, 1);

   // Check if we already have an active trade for this symbol & magic
   int openCount = CountOpenPositions(_Symbol, InpMagicNumber);

   string signalStatus = "SCANNING...";

   if(openCount == 0)
   {
      double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      int pointsPerPip = GetPointsPerPip(_Symbol);

      // --- BULLISH CONFLUENCE ---
      // Fast EMA > Slow EMA, Candle Close > Fast EMA, RSI in healthy bullish expansion
      if(fastEMA > slowEMA && closePrice > fastEMA && rsi >= InpRSIBullishMin && rsi <= InpRSIBullishMax)
      {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double sl = NormalizeDouble(ask - (InpStopLossPips * pointsPerPip * point), digits);
         double tp = NormalizeDouble(ask + (InpTakeProfitPips * pointsPerPip * point), digits);
         double lot = CalculateLotSize(_Symbol, InpStopLossPips, InpRiskPercent);

         ResetLastError();
         if(g_trade.Buy(lot, _Symbol, ask, sl, tp, InpOrderComment))
         {
            PrintFormat("[TG-Robot] BUY executed! Lot: %.2f | Ask: %.5f | SL: %.5f | TP: %.5f", lot, ask, sl, tp);
            g_lastBarTime = currentBarTime;
            signalStatus = "BUY EXECUTED";
         }
         else
         {
            PrintFormat("[TG-Robot] BUY order failed! Error: %d", GetLastError());
            signalStatus = "ORDER ERROR";
         }
      }
      // --- BEARISH CONFLUENCE ---
      // Fast EMA < Slow EMA, Candle Close < Fast EMA, RSI in healthy bearish expansion
      else if(fastEMA < slowEMA && closePrice < fastEMA && rsi >= InpRSIBearishMin && rsi <= InpRSIBearishMax)
      {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double sl = NormalizeDouble(bid + (InpStopLossPips * pointsPerPip * point), digits);
         double tp = NormalizeDouble(bid - (InpTakeProfitPips * pointsPerPip * point), digits);
         double lot = CalculateLotSize(_Symbol, InpStopLossPips, InpRiskPercent);

         ResetLastError();
         if(g_trade.Sell(lot, _Symbol, bid, sl, tp, InpOrderComment))
         {
            PrintFormat("[TG-Robot] SELL executed! Lot: %.2f | Bid: %.5f | SL: %.5f | TP: %.5f", lot, bid, sl, tp);
            g_lastBarTime = currentBarTime;
            signalStatus = "SELL EXECUTED";
         }
         else
         {
            PrintFormat("[TG-Robot] SELL order failed! Error: %d", GetLastError());
            signalStatus = "ORDER ERROR";
         }
      }
   }
   else
   {
      signalStatus = "POSITION ACTIVE (MANAGING PROTECTION)";
   }

   UpdateChartHUD(fastEMA, slowEMA, rsi, signalStatus);
}
//+------------------------------------------------------------------+
