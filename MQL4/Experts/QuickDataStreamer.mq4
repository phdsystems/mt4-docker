//+------------------------------------------------------------------+
//|                                           QuickDataStreamer.mq4  |
//|                                      Quick Market Data Export    |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property version   "1.00"
#property strict

// Input parameters
input int UpdateSeconds = 1;  // Update interval in seconds

// Global variables
int fileHandle = INVALID_HANDLE;
string fileName = "market_data.csv";

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
    // Create/open CSV file
    fileHandle = FileOpen(fileName, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    
    if(fileHandle == INVALID_HANDLE) {
        Print("Failed to open file: ", fileName);
        return INIT_FAILED;
    }
    
    // Write header
    FileWrite(fileHandle, "Timestamp", "Symbol", "Bid", "Ask", "Spread", "Volume");
    
    Print("QuickDataStreamer started. Writing to: ", fileName);
    
    // Set timer
    EventSetTimer(UpdateSeconds);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    EventKillTimer();
    
    if(fileHandle != INVALID_HANDLE) {
        FileClose(fileHandle);
    }
    
    Print("QuickDataStreamer stopped");
}

//+------------------------------------------------------------------+
//| Timer function                                                    |
//+------------------------------------------------------------------+
void OnTimer() {
    if(fileHandle == INVALID_HANDLE) return;
    
    // Get current symbol data
    string symbol = Symbol();
    double bid = Bid;
    double ask = Ask;
    double spread = (ask - bid) / Point;
    long volume = Volume[0];
    
    // Write to file
    FileWrite(fileHandle, 
              TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
              symbol,
              DoubleToString(bid, Digits),
              DoubleToString(ask, Digits), 
              DoubleToString(spread, 1),
              IntegerToString(volume));
    
    FileFlush(fileHandle);
    
    Print("Data written: ", symbol, " ", bid, "/", ask);
}

//+------------------------------------------------------------------+
//| Tick function                                                     |
//+------------------------------------------------------------------+
void OnTick() {
    // Can also write on every tick if needed
}