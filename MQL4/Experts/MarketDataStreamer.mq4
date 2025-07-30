//+------------------------------------------------------------------+
//|                                          MarketDataStreamer.mq4  |
//|                                    Market Data Streaming Service |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict
#property description "Streams real-time market data via multiple protocols"

#include <Files\FilePipe.mqh>

// Streaming modes
enum STREAM_MODE {
    STREAM_FILE = 0,      // File-based streaming (CSV)
    STREAM_PIPE = 1,      // Named pipe streaming
    STREAM_SOCKET = 2,    // TCP socket (via DLL)
    STREAM_ALL = 3        // All methods
};

// Input parameters
input STREAM_MODE InpStreamMode = STREAM_ALL;                // Streaming mode
input string InpSymbols = "EURUSD,GBPUSD,USDJPY,AUDUSD";    // Symbols to stream (comma separated)
input int InpUpdateIntervalMs = 100;                         // Update interval (ms)
input bool InpStreamTicks = true;                            // Stream tick data
input bool InpStreamBars = true;                             // Stream bar data
input bool InpStreamDepth = false;                           // Stream market depth
input string InpPipeName = "MT4_MarketData";                 // Pipe name
input string InpFileName = "market_data.csv";                // Output filename
input int InpTcpPort = 5555;                                 // TCP port for socket streaming

// Global variables
string g_symbols[];
int g_symbolCount;
CFilePipe g_pipe;
int g_fileHandle = INVALID_HANDLE;
datetime g_lastUpdate;
int g_tickCount = 0;

// Tick data structure
struct TickData {
    string symbol;
    datetime time;
    double bid;
    double ask;
    double spread;
    int volume;
};

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
    // Parse symbols
    g_symbolCount = ParseSymbols(InpSymbols, g_symbols);
    if (g_symbolCount == 0) {
        Print("No valid symbols specified");
        return INIT_FAILED;
    }
    
    // Initialize streaming methods
    if (InpStreamMode == STREAM_FILE || InpStreamMode == STREAM_ALL) {
        if (!InitFileStream()) {
            Print("Failed to initialize file streaming");
            return INIT_FAILED;
        }
    }
    
    if (InpStreamMode == STREAM_PIPE || InpStreamMode == STREAM_ALL) {
        if (!InitPipeStream()) {
            Print("Failed to initialize pipe streaming");
            // Don't fail, pipe might connect later
        }
    }
    
    // Set timer for updates
    EventSetMillisecondTimer(InpUpdateIntervalMs);
    
    Print("Market Data Streamer initialized");
    Print("Streaming ", g_symbolCount, " symbols");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    EventKillTimer();
    
    // Close file
    if (g_fileHandle != INVALID_HANDLE) {
        FileClose(g_fileHandle);
    }
    
    // Close pipe
    if (g_pipe.Handle() != INVALID_HANDLE) {
        g_pipe.Close();
    }
    
    Print("Market Data Streamer stopped. Streamed ", g_tickCount, " ticks");
}

//+------------------------------------------------------------------+
//| Timer function                                                    |
//+------------------------------------------------------------------+
void OnTimer() {
    // Stream current market data
    StreamMarketData();
}

//+------------------------------------------------------------------+
//| Tick function                                                     |
//+------------------------------------------------------------------+
void OnTick() {
    if (InpStreamTicks) {
        // Stream tick data immediately
        StreamTickData(Symbol());
    }
}

//+------------------------------------------------------------------+
//| Parse comma-separated symbols                                     |
//+------------------------------------------------------------------+
int ParseSymbols(string symbolList, string &symbols[]) {
    StringTrimLeft(symbolList);
    StringTrimRight(symbolList);
    
    if (symbolList == "") {
        ArrayResize(symbols, 1);
        symbols[0] = Symbol();
        return 1;
    }
    
    int count = StringSplit(symbolList, ',', symbols);
    
    // Validate symbols
    for (int i = 0; i < count; i++) {
        StringTrimLeft(symbols[i]);
        StringTrimRight(symbols[i]);
        
        if (MarketInfo(symbols[i], MODE_BID) == 0) {
            Print("Warning: Invalid symbol ", symbols[i]);
        }
    }
    
    return count;
}

//+------------------------------------------------------------------+
//| Initialize file streaming                                         |
//+------------------------------------------------------------------+
bool InitFileStream() {
    g_fileHandle = FileOpen(InpFileName, FILE_WRITE|FILE_CSV);
    if (g_fileHandle == INVALID_HANDLE) {
        return false;
    }
    
    // Write header
    string header = "Timestamp,Symbol,Bid,Ask,Spread,Volume";
    if (InpStreamBars) {
        header += ",Open,High,Low,Close,BarVolume";
    }
    FileWriteString(g_fileHandle, header + "\n");
    
    return true;
}

//+------------------------------------------------------------------+
//| Initialize pipe streaming                                         |
//+------------------------------------------------------------------+
bool InitPipeStream() {
    string pipeName = "\\\\.\\pipe\\" + InpPipeName;
    
    // Try to create pipe server
    if (g_pipe.Open(pipeName, FILE_WRITE|FILE_READ|FILE_BIN) == INVALID_HANDLE) {
        Print("Pipe not connected. Will retry...");
        return false;
    }
    
    Print("Pipe connected: ", pipeName);
    
    // Send header
    string header = "{\"type\":\"header\",\"version\":\"1.0\",\"symbols\":[";
    for (int i = 0; i < g_symbolCount; i++) {
        if (i > 0) header += ",";
        header += "\"" + g_symbols[i] + "\"";
    }
    header += "]}";
    
    g_pipe.WriteString(header);
    
    return true;
}

//+------------------------------------------------------------------+
//| Stream market data for all symbols                                |
//+------------------------------------------------------------------+
void StreamMarketData() {
    for (int i = 0; i < g_symbolCount; i++) {
        StreamSymbolData(g_symbols[i]);
    }
}

//+------------------------------------------------------------------+
//| Stream data for a specific symbol                                 |
//+------------------------------------------------------------------+
void StreamSymbolData(string symbol) {
    double bid = MarketInfo(symbol, MODE_BID);
    double ask = MarketInfo(symbol, MODE_ASK);
    double spread = (ask - bid) / MarketInfo(symbol, MODE_POINT);
    int volume = (int)MarketInfo(symbol, MODE_VOLUME);
    
    if (bid == 0 || ask == 0) return;
    
    datetime now = TimeCurrent();
    
    // File streaming
    if (g_fileHandle != INVALID_HANDLE) {
        string line = TimeToString(now, TIME_DATE|TIME_SECONDS) + "," +
                     symbol + "," +
                     DoubleToString(bid, (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
                     DoubleToString(ask, (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
                     DoubleToString(spread, 1) + "," +
                     IntegerToString(volume);
        
        if (InpStreamBars) {
            line += "," + DoubleToString(iOpen(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) +
                   "," + DoubleToString(iHigh(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) +
                   "," + DoubleToString(iLow(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) +
                   "," + DoubleToString(iClose(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) +
                   "," + IntegerToString(iVolume(symbol, Period(), 0));
        }
        
        FileWriteString(g_fileHandle, line + "\n");
        FileFlush(g_fileHandle);
    }
    
    // Pipe streaming (JSON format)
    if (g_pipe.Handle() != INVALID_HANDLE) {
        string json = "{" +
            "\"type\":\"quote\"," +
            "\"symbol\":\"" + symbol + "\"," +
            "\"timestamp\":" + IntegerToString(now) + "," +
            "\"bid\":" + DoubleToString(bid, (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
            "\"ask\":" + DoubleToString(ask, (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
            "\"spread\":" + DoubleToString(spread, 1) + "," +
            "\"volume\":" + IntegerToString(volume);
        
        if (InpStreamBars) {
            json += ",\"bar\":{" +
                "\"open\":" + DoubleToString(iOpen(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
                "\"high\":" + DoubleToString(iHigh(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
                "\"low\":" + DoubleToString(iLow(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
                "\"close\":" + DoubleToString(iClose(symbol, Period(), 0), (int)MarketInfo(symbol, MODE_DIGITS)) + "," +
                "\"volume\":" + IntegerToString(iVolume(symbol, Period(), 0)) + "}";
        }
        
        json += "}";
        
        if (!g_pipe.WriteString(json + "\n")) {
            // Pipe disconnected, try to reconnect
            g_pipe.Close();
            InitPipeStream();
        }
    }
    
    g_tickCount++;
}

//+------------------------------------------------------------------+
//| Stream tick data                                                  |
//+------------------------------------------------------------------+
void StreamTickData(string symbol) {
    if (!InpStreamTicks) return;
    
    double bid = Bid;
    double ask = Ask;
    datetime now = TimeCurrent();
    int ms = GetTickCount() % 1000;
    
    // Pipe streaming for ticks
    if (g_pipe.Handle() != INVALID_HANDLE) {
        string json = "{" +
            "\"type\":\"tick\"," +
            "\"symbol\":\"" + symbol + "\"," +
            "\"timestamp\":" + IntegerToString(now) + "," +
            "\"ms\":" + IntegerToString(ms) + "," +
            "\"bid\":" + DoubleToString(bid, Digits) + "," +
            "\"ask\":" + DoubleToString(ask, Digits) + "}";
        
        g_pipe.WriteString(json + "\n");
    }
}

//+------------------------------------------------------------------+
//| Get current milliseconds                                          |
//+------------------------------------------------------------------+
int GetMilliseconds() {
    return GetTickCount() % 1000;
}