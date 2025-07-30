//+------------------------------------------------------------------+
//|                                           ZMQDirectPublisher.mq4 |
//|                      Direct ZeroMQ Publishing from MT4 via DLL   |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

#include <MT4ZMQ.mqh>

//--- Input parameters
input string InpBindAddress = "tcp://*:5556";             // ZeroMQ bind address
input string InpSymbols = "EURUSD,GBPUSD,USDJPY,AUDUSD"; // Symbols to publish
input int    InpTickInterval = 100;                       // Tick interval (ms)
input bool   InpPublishBars = true;                       // Publish bar data
input bool   InpShowStats = true;                         // Show statistics

//--- Global variables
CZMQPublisher g_publisher;
string        g_symbols[];
int           g_symbolCount;
int           g_ticksSent = 0;
int           g_barsSent = 0;
datetime      g_lastBar[];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Show ZeroMQ version
    Print("Initializing Direct ZeroMQ Publisher");
    Print("ZeroMQ Library: ", GetZMQVersion());
    
    // Parse symbols
    g_symbolCount = StringSplit(InpSymbols, ',', g_symbols);
    if (g_symbolCount == 0)
    {
        Alert("No symbols specified!");
        return INIT_FAILED;
    }
    
    // Initialize last bar times
    ArrayResize(g_lastBar, g_symbolCount);
    for (int i = 0; i < g_symbolCount; i++)
    {
        g_lastBar[i] = 0;
    }
    
    // Create ZeroMQ publisher
    if (!g_publisher.Create(InpBindAddress))
    {
        Alert("Failed to create ZeroMQ publisher!");
        return INIT_FAILED;
    }
    
    // Start publishing
    EventSetMillisecondTimer(InpTickInterval);
    
    Comment("ZeroMQ Direct Publisher Active\n",
            "Address: ", InpBindAddress, "\n",
            "Symbols: ", g_symbolCount, "\n",
            "Ticks sent: 0");
    
    // Send initial configuration message
    string config = StringFormat(
        "{\"type\":\"config\",\"publisher\":\"MT4_DIRECT\",\"address\":\"%s\",\"symbols\":%d,\"dll\":true}",
        InpBindAddress, g_symbolCount
    );
    g_publisher.SendMessage("config", config);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    
    // Send shutdown message
    g_publisher.SendMessage("control", "{\"type\":\"shutdown\",\"reason\":\"" + GetDeInitReason(reason) + "\"}");
    
    // Close publisher
    g_publisher.Close();
    
    Print("ZeroMQ Publisher stopped. Ticks sent: ", g_ticksSent, ", Bars sent: ", g_barsSent);
    Comment("");
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnMillisecondTimer()
{
    // Publish tick data for all symbols
    for (int i = 0; i < g_symbolCount; i++)
    {
        string symbol = g_symbols[i];
        
        double bid = MarketInfo(symbol, MODE_BID);
        double ask = MarketInfo(symbol, MODE_ASK);
        
        if (bid > 0 && ask > 0)
        {
            if (g_publisher.SendTick(symbol, bid, ask))
            {
                g_ticksSent++;
            }
            
            // Check for new bar
            if (InpPublishBars)
            {
                datetime currentBar = iTime(symbol, PERIOD_M1, 0);
                if (currentBar > g_lastBar[i])
                {
                    g_lastBar[i] = currentBar;
                    
                    // Publish completed bar (shift = 1)
                    if (g_publisher.SendBar(symbol, PERIOD_M1, 1))
                    {
                        g_barsSent++;
                    }
                }
            }
        }
    }
    
    // Update display
    if (InpShowStats && g_ticksSent % 10 == 0)
    {
        UpdateDisplay();
    }
}

//+------------------------------------------------------------------+
//| Update display                                                   |
//+------------------------------------------------------------------+
void UpdateDisplay()
{
    double elapsed = (GetTickCount() - g_startTime) / 1000.0;
    double tickRate = elapsed > 0 ? g_ticksSent / elapsed : 0;
    
    Comment("ZeroMQ Direct Publisher Active\n",
            "Address: ", InpBindAddress, "\n",
            "Symbols: ", g_symbolCount, "\n",
            "Ticks sent: ", g_ticksSent, "\n",
            "Bars sent: ", g_barsSent, "\n",
            "Rate: ", DoubleToString(tickRate, 1), " ticks/sec\n",
            "Uptime: ", FormatTime(elapsed));
}

//+------------------------------------------------------------------+
//| Helper functions                                                 |
//+------------------------------------------------------------------+
string GetDeInitReason(int reason)
{
    switch(reason)
    {
        case REASON_PROGRAM:     return "EA stopped";
        case REASON_REMOVE:      return "EA removed";
        case REASON_RECOMPILE:   return "EA recompiled";
        case REASON_CHARTCHANGE: return "Chart changed";
        case REASON_CHARTCLOSE:  return "Chart closed";
        case REASON_PARAMETERS:  return "Parameters changed";
        case REASON_ACCOUNT:     return "Account changed";
        default:                 return "Unknown";
    }
}

string FormatTime(double seconds)
{
    int hours = (int)(seconds / 3600);
    int minutes = (int)((seconds - hours * 3600) / 60);
    int secs = (int)(seconds - hours * 3600 - minutes * 60);
    
    return StringFormat("%02d:%02d:%02d", hours, minutes, secs);
}

static datetime g_startTime = GetTickCount();