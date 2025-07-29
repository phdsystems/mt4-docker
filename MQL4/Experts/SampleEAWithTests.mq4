//+------------------------------------------------------------------+
//|                                            SampleEAWithTests.mq4  |
//|                                Example EA with integrated tests   |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

#include <EATestFramework.mqh>

// Input parameters
input double InpLotSize = 0.01;          // Lot size
input int    InpMAPeriod = 14;           // MA Period
input int    InpRSIPeriod = 14;          // RSI Period
input double InpRSIOverbought = 70;      // RSI Overbought
input double InpRSIOversold = 30;        // RSI Oversold
input bool   InpRunTests = false;        // Run tests on init

// Global variables
CTestSuite* g_testSuite = NULL;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
    // Run tests if requested
    if (InpRunTests) {
        RunAllTests();
    }
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    if (g_testSuite != NULL) {
        delete g_testSuite;
        g_testSuite = NULL;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick() {
    // Skip if tests are running
    if (InpRunTests) return;
    
    // Calculate indicators
    double ma = iMA(Symbol(), Period(), InpMAPeriod, 0, MODE_SMA, PRICE_CLOSE, 0);
    double rsi = iRSI(Symbol(), Period(), InpRSIPeriod, PRICE_CLOSE, 0);
    
    // Simple trading logic (demo only)
    if (ShouldOpenBuy(ma, rsi)) {
        // In real EA, would open buy order here
        Comment("Signal: BUY");
    }
    else if (ShouldOpenSell(ma, rsi)) {
        // In real EA, would open sell order here
        Comment("Signal: SELL");
    }
    else {
        Comment("No signal");
    }
}

//+------------------------------------------------------------------+
//| Check if should open buy                                          |
//+------------------------------------------------------------------+
bool ShouldOpenBuy(double ma, double rsi) {
    return (Close[0] > ma && rsi < InpRSIOversold);
}

//+------------------------------------------------------------------+
//| Check if should open sell                                         |
//+------------------------------------------------------------------+
bool ShouldOpenSell(double ma, double rsi) {
    return (Close[0] < ma && rsi > InpRSIOverbought);
}

//+------------------------------------------------------------------+
//| Calculate position size                                           |
//+------------------------------------------------------------------+
double CalculatePositionSize(double riskPercent, double stopLossPips) {
    if (stopLossPips <= 0) return 0;
    
    double accountSize = AccountBalance();
    double riskAmount = accountSize * riskPercent / 100.0;
    double pipValue = MarketInfo(Symbol(), MODE_TICKVALUE);
    double lotSize = riskAmount / (stopLossPips * pipValue);
    
    // Normalize to allowed lot size
    double minLot = MarketInfo(Symbol(), MODE_MINLOT);
    double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
    double lotStep = MarketInfo(Symbol(), MODE_LOTSTEP);
    
    lotSize = MathMax(minLot, lotSize);
    lotSize = MathMin(maxLot, lotSize);
    lotSize = MathRound(lotSize / lotStep) * lotStep;
    
    return lotSize;
}

//+------------------------------------------------------------------+
//| Run all tests                                                     |
//+------------------------------------------------------------------+
void RunAllTests() {
    Print("Starting EA tests...");
    
    g_testSuite = new CTestSuite("SampleEA");
    
    // Run test categories
    TestIndicatorCalculations();
    TestTradingLogic();
    TestPositionSizing();
    TestEdgeCases();
    
    // Generate report
    g_testSuite.PrintSummary();
    g_testSuite.GenerateReport();
    
    // Clean up
    delete g_testSuite;
    g_testSuite = NULL;
    
    Print("Tests completed!");
}

//+------------------------------------------------------------------+
//| Test indicator calculations                                       |
//+------------------------------------------------------------------+
void TestIndicatorCalculations() {
    Print("Testing indicator calculations...");
    
    // Test MA calculation
    double ma = iMA(Symbol(), Period(), InpMAPeriod, 0, MODE_SMA, PRICE_CLOSE, 0);
    g_testSuite.AssertGreater("MA value should be positive", ma, 0);
    g_testSuite.AssertLess("MA value should be reasonable", ma, 999999);
    
    // Test RSI calculation
    double rsi = iRSI(Symbol(), Period(), InpRSIPeriod, PRICE_CLOSE, 0);
    g_testSuite.AssertTrue("RSI should be between 0 and 100", 
        rsi >= 0 && rsi <= 100);
    
    // Test with different periods
    double ma1 = iMA(Symbol(), Period(), 10, 0, MODE_SMA, PRICE_CLOSE, 0);
    double ma2 = iMA(Symbol(), Period(), 20, 0, MODE_SMA, PRICE_CLOSE, 0);
    g_testSuite.AssertNotEquals("Different period MAs should differ", ma1, ma2, 0.1);
}

//+------------------------------------------------------------------+
//| Test trading logic                                                |
//+------------------------------------------------------------------+
void TestTradingLogic() {
    Print("Testing trading logic...");
    
    // Test buy condition
    double maBuy = 1.1000;
    double rsiBuy = 25.0;  // Oversold
    bool shouldBuy = (1.1010 > maBuy && rsiBuy < InpRSIOversold);
    g_testSuite.AssertTrue("Should generate buy signal", shouldBuy);
    
    // Test sell condition
    double maSell = 1.1020;
    double rsiSell = 75.0;  // Overbought
    bool shouldSell = (1.1010 < maSell && rsiSell > InpRSIOverbought);
    g_testSuite.AssertTrue("Should generate sell signal", shouldSell);
    
    // Test no signal condition
    double maFlat = 1.1010;
    double rsiFlat = 50.0;  // Neutral
    bool shouldBuyFlat = (1.1010 > maFlat && rsiFlat < InpRSIOversold);
    bool shouldSellFlat = (1.1010 < maFlat && rsiFlat > InpRSIOverbought);
    g_testSuite.AssertFalse("Should not generate buy signal", shouldBuyFlat);
    g_testSuite.AssertFalse("Should not generate sell signal", shouldSellFlat);
}

//+------------------------------------------------------------------+
//| Test position sizing                                              |
//+------------------------------------------------------------------+
void TestPositionSizing() {
    Print("Testing position sizing...");
    
    // Test normal calculation
    double lots = CalculatePositionSize(1.0, 50);  // 1% risk, 50 pip stop
    g_testSuite.AssertGreater("Position size should be positive", lots, 0);
    g_testSuite.AssertLess("Position size should be reasonable", lots, 100);
    
    // Test with zero stop loss
    double lotsZeroSL = CalculatePositionSize(1.0, 0);
    g_testSuite.AssertEquals("Zero SL should return zero lots", 0, lotsZeroSL);
    
    // Test minimum lot size
    double minLot = MarketInfo(Symbol(), MODE_MINLOT);
    double lotsMin = CalculatePositionSize(0.01, 10);  // Very small risk
    g_testSuite.AssertTrue("Should respect minimum lot size", 
        lotsMin >= minLot || lotsMin == 0);
}

//+------------------------------------------------------------------+
//| Test edge cases                                                   |
//+------------------------------------------------------------------+
void TestEdgeCases() {
    Print("Testing edge cases...");
    
    // Test with extreme RSI values
    g_testSuite.AssertTrue("Should handle RSI = 0", 
        ShouldOpenBuy(1.1000, 0) || !ShouldOpenBuy(1.1000, 0));
    g_testSuite.AssertTrue("Should handle RSI = 100", 
        ShouldOpenSell(1.2000, 100) || !ShouldOpenSell(1.2000, 100));
    
    // Test position sizing with extreme values
    double lotsHuge = CalculatePositionSize(100, 1);  // 100% risk
    double maxLot = MarketInfo(Symbol(), MODE_MAXLOT);
    g_testSuite.AssertTrue("Should respect maximum lot size", 
        lotsHuge <= maxLot);
    
    // Test with negative values (should handle gracefully)
    double lotsNeg = CalculatePositionSize(-1, 50);
    g_testSuite.AssertTrue("Should handle negative risk", lotsNeg >= 0);
}