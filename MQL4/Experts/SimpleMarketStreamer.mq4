//+------------------------------------------------------------------+
//|                                        SimpleMarketStreamer.mq4  |
//|                                    Simple Market Data CSV Export |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict
#property description "Streams market data to CSV file"

// Input parameters
input string InpSymbols = "";                                // Symbols (empty = current)
input int InpUpdateIntervalMs = 1000;                        // Update interval (ms)
input string InpFileName = "market_data.csv";                // Output filename

// Global variables
string g_symbols[];
int g_symbolCount;
int g_fileHandle = INVALID_HANDLE;
int g_tickCount = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
    // Parse symbols
    if (InpSymbols == "") {
        g_symbolCount = 1;
        ArrayResize(g_symbols, 1);
        g_symbols[0] = Symbol();
    } else {
        g_symbolCount = StringSplit(InpSymbols, ',', g_symbols);
    }
    
    // Open file
    g_fileHandle = FileOpen(InpFileName, FILE_WRITE|FILE_CSV|FILE_SHARE_READ);
    if (g_fileHandle == INVALID_HANDLE) {
        Print("Failed to open file: ", InpFileName);
        return INIT_FAILED;
    }
    
    // Write header
    FileWrite(g_fileHandle, "Timestamp", "Symbol", "Bid", "Ask", "Spread", "Volume");
    FileFlush(g_fileHandle);
    
    // Set timer
    EventSetMillisecondTimer(InpUpdateIntervalMs);
    
    Print("Simple Market Streamer started. Streaming ", g_symbolCount, " symbols to ", InpFileName);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    EventKillTimer();
    
    if (g_fileHandle != INVALID_HANDLE) {
        FileClose(g_fileHandle);
    }
    
    Print("Simple Market Streamer stopped. Streamed ", g_tickCount, " records");
}

//+------------------------------------------------------------------+
//| Timer function                                                    |
//+------------------------------------------------------------------+
void OnTimer() {
    for (int i = 0; i < g_symbolCount; i++) {
        string symbol = g_symbols[i];
        
        double bid = MarketInfo(symbol, MODE_BID);
        double ask = MarketInfo(symbol, MODE_ASK);
        
        if (bid > 0 && ask > 0) {
            double spread = (ask - bid) / MarketInfo(symbol, MODE_POINT);
            int volume = (int)MarketInfo(symbol, MODE_VOLUME);
            
            FileWrite(g_fileHandle, 
                TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                symbol,
                DoubleToString(bid, (int)MarketInfo(symbol, MODE_DIGITS)),
                DoubleToString(ask, (int)MarketInfo(symbol, MODE_DIGITS)),
                DoubleToString(spread, 1),
                IntegerToString(volume)
            );
            
            g_tickCount++;
        }
    }
    
    FileFlush(g_fileHandle);
    
    if (g_tickCount % 10 == 0) {
        Print("Streamed ", g_tickCount, " records");
    }
}