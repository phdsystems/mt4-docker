//+------------------------------------------------------------------+
//|                                            DataExporterZMQ.mq4   |
//|                           Real ZeroMQ Data Export                |
//+------------------------------------------------------------------+
#property copyright "PHD Systems"
#property version   "1.00"
#property strict

// Include the PHD Quants ZMQ service
#include <phd-quants/service/ZmqService.mqh>

// Input parameters
input int    PUB_PORT = 5555;          // Publisher port
input int    UpdateInterval = 1000;    // Update interval in milliseconds
input string Symbols = "EURUSD,GBPUSD,USDJPY"; // Symbols to export

// Global variables
string symbolArray[];
int symbolCount;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Parse symbols
    symbolCount = StringSplit(Symbols, ',', symbolArray);
    
    // Bind publisher socket
    ZmqService::bindPublisherSocket(PUB_PORT);
    
    Print("DataExporterZMQ initialized on port ", PUB_PORT);
    Print("Publishing data for ", symbolCount, " symbols");
    
    // Set timer for updates
    EventSetMillisecondTimer(UpdateInterval);
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Clean shutdown
    ZmqService::unbindPublisherSocket(PUB_PORT);
    ZmqService::shutDownContext();
    
    EventKillTimer();
    Print("DataExporterZMQ stopped");
}

//+------------------------------------------------------------------+
//| Timer function - publish market data                             |
//+------------------------------------------------------------------+
void OnTimer()
{
    // Publish market data for each symbol
    for(int i = 0; i < symbolCount; i++)
    {
        string symbol = symbolArray[i];
        
        // Get market data
        double bid = MarketInfo(symbol, MODE_BID);
        double ask = MarketInfo(symbol, MODE_ASK);
        double spread = (ask - bid) / MarketInfo(symbol, MODE_POINT);
        long volume = iVolume(symbol, PERIOD_M1, 0);
        
        // Create JSON message
        string message = StringFormat(
            "{\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.1f,\"volume\":%d,\"timestamp\":\"%s\"}",
            symbol, bid, ask, spread, volume,
            TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
        );
        
        // Publish with topic
        string topic = "TICK." + symbol;
        ZmqService::publish(topic + " " + message);
    }
    
    // Also publish account info periodically
    static datetime lastAccountUpdate = 0;
    if(TimeCurrent() - lastAccountUpdate >= 60) // Every minute
    {
        string accountInfo = StringFormat(
            "{\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"free_margin\":%.2f,\"timestamp\":\"%s\"}",
            AccountBalance(), AccountEquity(), AccountMargin(), AccountFreeMargin(),
            TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
        );
        
        ZmqService::publish("ACCOUNT " + accountInfo);
        lastAccountUpdate = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Tick function - capture important events                         |
//+------------------------------------------------------------------+
void OnTick()
{
    // For high-frequency data, you could publish here instead of timer
    // But be careful not to overwhelm subscribers
}