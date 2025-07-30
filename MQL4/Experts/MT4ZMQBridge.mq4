//+------------------------------------------------------------------+
//|                                                 MT4ZMQBridge.mq4 |
//|                     Production MT4 to ZeroMQ Bridge via DLL      |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "2.00"
#property strict
#property description "High-performance market data streaming to ZeroMQ via native DLL"

// Import DLL functions
#import "mt4zmq.dll"
    int    zmq_init();
    void   zmq_term();
    int    zmq_create_publisher(string address);
    int    zmq_send_message(int handle, string topic, string message);
    int    zmq_close(int handle);
    void   zmq_get_last_error(string &error, int len);
#import

//--- Input parameters
input string  InpPublishAddress = "tcp://*:5556";              // ZeroMQ publish address
input string  InpSymbols = "";                                 // Symbols to stream (empty = all)
input int     InpTickInterval = 100;                           // Tick publish interval (ms)
input bool    InpPublishTicks = true;                          // Publish tick data
input bool    InpPublishBars = true;                           // Publish bar data
input ENUM_TIMEFRAMES InpBarTimeframe = PERIOD_M1;            // Bar timeframe
input bool    InpPublishDepth = false;                         // Publish market depth
input int     InpStatsInterval = 10000;                        // Statistics update interval (ms)
input bool    InpVerboseLogging = false;                       // Verbose logging

//--- Global variables
int           g_publisher = -1;                                 // Publisher handle
string        g_symbols[];                                      // Array of symbols
int           g_symbolCount = 0;                                // Number of symbols
datetime      g_lastBar[];                                      // Last bar time for each symbol
ulong         g_tickCount = 0;                                  // Total ticks sent
ulong         g_barCount = 0;                                   // Total bars sent
ulong         g_errorCount = 0;                                // Total errors
ulong         g_startTime = 0;                                  // Start timestamp
datetime      g_lastStatsTime = 0;                             // Last stats update time

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("========================================");
    Print("MT4 ZeroMQ Bridge v2.0 Starting...");
    Print("========================================");
    
    // Initialize ZeroMQ context
    if (zmq_init() != 0)
    {
        Alert("Failed to initialize ZeroMQ context!");
        return INIT_FAILED;
    }
    
    // Create publisher socket
    g_publisher = zmq_create_publisher(InpPublishAddress);
    if (g_publisher <= 0)
    {
        string error = StringInit(256, ' ');
        zmq_get_last_error(error, 256);
        Alert("Failed to create ZeroMQ publisher: ", StringTrimRight(error));
        zmq_term();
        return INIT_FAILED;
    }
    
    Print("✓ ZeroMQ publisher created on ", InpPublishAddress);
    
    // Parse symbols
    if (InpSymbols == "")
    {
        // Use all available symbols
        int total = SymbolsTotal(true);
        ArrayResize(g_symbols, total);
        g_symbolCount = 0;
        
        for (int i = 0; i < total; i++)
        {
            string symbol = SymbolName(i, true);
            if (SymbolSelect(symbol, true))
            {
                g_symbols[g_symbolCount++] = symbol;
            }
        }
        ArrayResize(g_symbols, g_symbolCount);
    }
    else
    {
        // Parse user-specified symbols
        g_symbolCount = StringSplit(InpSymbols, ',', g_symbols);
    }
    
    // Initialize last bar tracking
    ArrayResize(g_lastBar, g_symbolCount);
    ArrayInitialize(g_lastBar, 0);
    
    Print("✓ Streaming ", g_symbolCount, " symbols");
    
    // Send startup message
    SendStatusMessage("startup", "Bridge initialized");
    
    // Set timers
    EventSetMillisecondTimer(InpTickInterval);
    g_startTime = GetMicrosecondCount();
    g_lastStatsTime = TimeCurrent();
    
    // Initial display
    UpdateDisplay();
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Kill timer
    EventKillTimer();
    
    // Send shutdown message
    string reasonStr = GetUninitReasonText(reason);
    SendStatusMessage("shutdown", reasonStr);
    
    // Show final statistics
    PrintStatistics();
    
    // Close publisher
    if (g_publisher > 0)
    {
        zmq_close(g_publisher);
        g_publisher = -1;
    }
    
    // Cleanup ZeroMQ
    zmq_term();
    
    Comment("");
    Print("MT4 ZeroMQ Bridge stopped");
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
    // Process all symbols
    for (int i = 0; i < g_symbolCount; i++)
    {
        string symbol = g_symbols[i];
        
        // Publish tick data
        if (InpPublishTicks)
        {
            PublishTick(symbol);
        }
        
        // Check for new bars
        if (InpPublishBars)
        {
            CheckAndPublishBar(symbol, i);
        }
        
        // Publish market depth
        if (InpPublishDepth && i < 5) // Limit depth to first 5 symbols
        {
            PublishDepth(symbol);
        }
    }
    
    // Update statistics periodically
    if (TimeCurrent() - g_lastStatsTime >= InpStatsInterval / 1000)
    {
        PublishStatistics();
        UpdateDisplay();
        g_lastStatsTime = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Publish tick data                                               |
//+------------------------------------------------------------------+
void PublishTick(string symbol)
{
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    
    if (bid <= 0 || ask <= 0) return;
    
    // Build JSON message
    string json = StringFormat(
        "{\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.1f,\"time\":%d,\"ms\":%d}",
        symbol, bid, ask,
        (ask - bid) / SymbolInfoDouble(symbol, SYMBOL_POINT),
        (int)TimeCurrent(),
        (int)(GetMicrosecondCount() % 1000)
    );
    
    string topic = "tick." + symbol;
    
    if (zmq_send_message(g_publisher, topic, json) == 0)
    {
        g_tickCount++;
        if (InpVerboseLogging && g_tickCount % 100 == 0)
        {
            Print("Sent tick #", g_tickCount, ": ", symbol, " ", DoubleToString(bid, 5));
        }
    }
    else
    {
        g_errorCount++;
        if (g_errorCount % 10 == 0)
        {
            Print("Error sending tick data, total errors: ", g_errorCount);
        }
    }
}

//+------------------------------------------------------------------+
//| Check and publish new bars                                      |
//+------------------------------------------------------------------+
void CheckAndPublishBar(string symbol, int index)
{
    datetime currentBar = iTime(symbol, InpBarTimeframe, 0);
    
    if (currentBar > g_lastBar[index] && g_lastBar[index] > 0)
    {
        // New bar formed, publish the completed bar (shift 1)
        string json = StringFormat(
            "{\"symbol\":\"%s\",\"timeframe\":\"%s\",\"time\":%d,\"open\":%.5f,\"high\":%.5f,\"low\":%.5f,\"close\":%.5f,\"volume\":%d}",
            symbol,
            PeriodToString(InpBarTimeframe),
            (int)iTime(symbol, InpBarTimeframe, 1),
            iOpen(symbol, InpBarTimeframe, 1),
            iHigh(symbol, InpBarTimeframe, 1),
            iLow(symbol, InpBarTimeframe, 1),
            iClose(symbol, InpBarTimeframe, 1),
            (int)iVolume(symbol, InpBarTimeframe, 1)
        );
        
        string topic = StringFormat("bar.%s.%s", symbol, PeriodToString(InpBarTimeframe));
        
        if (zmq_send_message(g_publisher, topic, json) == 0)
        {
            g_barCount++;
            if (InpVerboseLogging)
            {
                Print("New bar: ", symbol, " ", PeriodToString(InpBarTimeframe));
            }
        }
        else
        {
            g_errorCount++;
        }
    }
    
    g_lastBar[index] = currentBar;
}

//+------------------------------------------------------------------+
//| Publish market depth                                            |
//+------------------------------------------------------------------+
void PublishDepth(string symbol)
{
    // Note: MT4 doesn't have native market depth, this is a placeholder
    // In MT5, you would use MarketBookGet() here
    
    string json = StringFormat(
        "{\"symbol\":\"%s\",\"type\":\"depth\",\"bids\":[],\"asks\":[],\"time\":%d}",
        symbol, (int)TimeCurrent()
    );
    
    string topic = "depth." + symbol;
    zmq_send_message(g_publisher, topic, json);
}

//+------------------------------------------------------------------+
//| Send status message                                             |
//+------------------------------------------------------------------+
void SendStatusMessage(string event, string description)
{
    string json = StringFormat(
        "{\"event\":\"%s\",\"description\":\"%s\",\"account\":%d,\"time\":%d}",
        event, description, AccountNumber(), (int)TimeCurrent()
    );
    
    zmq_send_message(g_publisher, "status", json);
}

//+------------------------------------------------------------------+
//| Publish statistics                                              |
//+------------------------------------------------------------------+
void PublishStatistics()
{
    double elapsedSeconds = (GetMicrosecondCount() - g_startTime) / 1000000.0;
    double ticksPerSecond = elapsedSeconds > 0 ? g_tickCount / elapsedSeconds : 0;
    
    string json = StringFormat(
        "{\"ticks_sent\":%d,\"bars_sent\":%d,\"errors\":%d,\"uptime\":%.1f,\"tps\":%.1f}",
        g_tickCount, g_barCount, g_errorCount, elapsedSeconds, ticksPerSecond
    );
    
    zmq_send_message(g_publisher, "stats", json);
}

//+------------------------------------------------------------------+
//| Update display                                                  |
//+------------------------------------------------------------------+
void UpdateDisplay()
{
    double elapsedSeconds = (GetMicrosecondCount() - g_startTime) / 1000000.0;
    double ticksPerSecond = elapsedSeconds > 0 ? g_tickCount / elapsedSeconds : 0;
    
    string display = StringFormat(
        "MT4 ZeroMQ Bridge (DLL)\n" +
        "Address: %s\n" +
        "Symbols: %d\n" +
        "Ticks sent: %d\n" +
        "Bars sent: %d\n" +
        "Errors: %d\n" +
        "Rate: %.1f ticks/sec\n" +
        "Uptime: %s",
        InpPublishAddress,
        g_symbolCount,
        g_tickCount,
        g_barCount,
        g_errorCount,
        ticksPerSecond,
        TimeToString(elapsedSeconds, TIME_SECONDS)
    );
    
    Comment(display);
}

//+------------------------------------------------------------------+
//| Print final statistics                                          |
//+------------------------------------------------------------------+
void PrintStatistics()
{
    double elapsedSeconds = (GetMicrosecondCount() - g_startTime) / 1000000.0;
    
    Print("========================================");
    Print("Final Statistics:");
    Print("  Total ticks sent: ", g_tickCount);
    Print("  Total bars sent: ", g_barCount);
    Print("  Total errors: ", g_errorCount);
    Print("  Runtime: ", TimeToString(elapsedSeconds, TIME_SECONDS));
    Print("  Average rate: ", DoubleToString(g_tickCount / elapsedSeconds, 1), " ticks/sec");
    Print("========================================");
}

//+------------------------------------------------------------------+
//| Helper: Period to string                                        |
//+------------------------------------------------------------------+
string PeriodToString(ENUM_TIMEFRAMES period)
{
    switch(period)
    {
        case PERIOD_M1:  return "M1";
        case PERIOD_M5:  return "M5";
        case PERIOD_M15: return "M15";
        case PERIOD_M30: return "M30";
        case PERIOD_H1:  return "H1";
        case PERIOD_H4:  return "H4";
        case PERIOD_D1:  return "D1";
        case PERIOD_W1:  return "W1";
        case PERIOD_MN1: return "MN1";
        default:         return "Unknown";
    }
}

//+------------------------------------------------------------------+
//| Helper: String initialization                                   |
//+------------------------------------------------------------------+
string StringInit(int size, ushort character)
{
    string result;
    StringInit(result, size, character);
    return result;
}