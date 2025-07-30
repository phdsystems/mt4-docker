//+------------------------------------------------------------------+
//|                                            ZeroMQStreamer.mq4    |
//|                           High-Performance Market Data Streamer  |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict
#property description "Streams market data via ZeroMQ for high-performance distribution"

// Note: Since we don't have the actual DLL, we'll use named pipes as fallback
// This EA demonstrates the architecture and can be extended with actual ZeroMQ DLL

//--- Input parameters
input string InpSymbols = "EURUSD,GBPUSD,USDJPY,AUDUSD";    // Symbols to stream
input int    InpTickInterval = 100;                           // Tick update interval (ms)
input int    InpBarInterval = 1000;                          // Bar update interval (ms)
input bool   InpStreamTicks = true;                          // Stream tick data
input bool   InpStreamBars = true;                           // Stream bar data
input string InpPipeName = "MT4_ZMQ_Bridge";                 // Named pipe for bridge

//--- Global variables
string g_symbols[];
int    g_symbolCount;
int    g_pipeHandle = INVALID_HANDLE;
int    g_ticksSent = 0;
int    g_barsSent = 0;
datetime g_lastBarTime[];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Parse symbols
    g_symbolCount = StringSplit(InpSymbols, ',', g_symbols);
    if(g_symbolCount == 0)
    {
        Print("No symbols specified");
        return INIT_FAILED;
    }
    
    // Initialize last bar times
    ArrayResize(g_lastBarTime, g_symbolCount);
    for(int i = 0; i < g_symbolCount; i++)
    {
        g_lastBarTime[i] = 0;
    }
    
    // Open named pipe for communication with ZeroMQ bridge
    string pipePath = "\\\\.\\pipe\\" + InpPipeName;
    g_pipeHandle = FileOpen(pipePath, FILE_WRITE|FILE_BIN|FILE_ANSI);
    
    if(g_pipeHandle == INVALID_HANDLE)
    {
        // Fallback to file mode
        Print("Named pipe not available, using file mode");
        g_pipeHandle = FileOpen("zmq_bridge_data.json", FILE_WRITE|FILE_SHARE_READ|FILE_ANSI);
        
        if(g_pipeHandle == INVALID_HANDLE)
        {
            Print("Failed to open output stream");
            return INIT_FAILED;
        }
    }
    
    // Set timers
    if(InpStreamTicks)
        EventSetMillisecondTimer(InpTickInterval);
    else
        EventSetTimer(InpBarInterval / 1000);
    
    Print("ZeroMQ Streamer initialized");
    Print("Streaming ", g_symbolCount, " symbols");
    Print("Tick streaming: ", InpStreamTicks ? "ON" : "OFF");
    Print("Bar streaming: ", InpStreamBars ? "ON" : "OFF");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    
    if(g_pipeHandle != INVALID_HANDLE)
    {
        FileClose(g_pipeHandle);
    }
    
    Print("ZeroMQ Streamer stopped");
    Print("Ticks sent: ", g_ticksSent);
    Print("Bars sent: ", g_barsSent);
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
    if(InpStreamBars)
        StreamBars();
}

//+------------------------------------------------------------------+
//| Millisecond timer function                                       |
//+------------------------------------------------------------------+
void OnMillisecondTimer()
{
    if(InpStreamTicks)
        StreamTicks();
        
    // Check for new bars
    if(InpStreamBars && MathMod(GetTickCount(), InpBarInterval) < InpTickInterval)
        StreamBars();
}

//+------------------------------------------------------------------+
//| Stream tick data                                                |
//+------------------------------------------------------------------+
void StreamTicks()
{
    for(int i = 0; i < g_symbolCount; i++)
    {
        string symbol = g_symbols[i];
        
        double bid = MarketInfo(symbol, MODE_BID);
        double ask = MarketInfo(symbol, MODE_ASK);
        
        if(bid > 0 && ask > 0)
        {
            double spread = (ask - bid) / MarketInfo(symbol, MODE_POINT);
            int volume = (int)MarketInfo(symbol, MODE_VOLUME);
            
            // Create JSON message
            string json = StringFormat(
                "{\"type\":\"tick\",\"symbol\":\"%s\",\"bid\":%f,\"ask\":%f,\"spread\":%.1f,\"volume\":%d}\n",
                symbol, bid, ask, spread, volume
            );
            
            // Write to pipe/file
            if(FileWriteString(g_pipeHandle, json) > 0)
            {
                g_ticksSent++;
                FileFlush(g_pipeHandle);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Stream bar data                                                  |
//+------------------------------------------------------------------+
void StreamBars()
{
    for(int i = 0; i < g_symbolCount; i++)
    {
        string symbol = g_symbols[i];
        datetime currentBarTime = iTime(symbol, PERIOD_M1, 0);
        
        // Check if new bar
        if(currentBarTime > g_lastBarTime[i])
        {
            g_lastBarTime[i] = currentBarTime;
            
            // Get completed bar data (shift = 1)
            double open = iOpen(symbol, PERIOD_M1, 1);
            double high = iHigh(symbol, PERIOD_M1, 1);
            double low = iLow(symbol, PERIOD_M1, 1);
            double close = iClose(symbol, PERIOD_M1, 1);
            long volume = iVolume(symbol, PERIOD_M1, 1);
            datetime time = iTime(symbol, PERIOD_M1, 1);
            
            // Create JSON message
            string json = StringFormat(
                "{\"type\":\"bar\",\"symbol\":\"%s\",\"timeframe\":\"M1\",\"time\":%d,\"open\":%f,\"high\":%f,\"low\":%f,\"close\":%f,\"volume\":%d}\n",
                symbol, (int)time, open, high, low, close, (int)volume
            );
            
            // Write to pipe/file
            if(FileWriteString(g_pipeHandle, json) > 0)
            {
                g_barsSent++;
                FileFlush(g_pipeHandle);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Tick function                                                    |
//+------------------------------------------------------------------+
void OnTick()
{
    // Can be used for immediate tick streaming on actual price changes
    // Currently using timer-based approach for consistent performance
}