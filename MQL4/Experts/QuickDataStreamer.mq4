//+------------------------------------------------------------------+
//|                                           QuickDataStreamer.mq4  |
//|                                      Quick Market Data Export    |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property version   "1.00"
#property strict
#property description "Streams market data to CSV file"

// Input parameters
input int UpdateSeconds = 1;  // Update interval in seconds
input bool WriteHeader = true; // Write CSV header

// Global variables
int fileHandle = INVALID_HANDLE;
string fileName = "market_data.csv";
datetime lastUpdate = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
    // Create/open CSV file with proper flags
    fileHandle = FileOpen(fileName, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
    
    if(fileHandle == INVALID_HANDLE) {
        int error = GetLastError();
        Print("ERROR: Failed to open file: ", fileName, " Error: ", error);
        return(INIT_FAILED);
    }
    
    // Write header if requested
    if(WriteHeader) {
        FileWrite(fileHandle, "Timestamp", "Symbol", "Bid", "Ask", "Spread", "Volume");
        FileFlush(fileHandle);
    }
    
    Print("QuickDataStreamer v1.00 started successfully");
    Print("Writing to: ", fileName);
    Print("Update interval: ", UpdateSeconds, " seconds");
    
    // Set timer for periodic updates
    if(!EventSetTimer(UpdateSeconds)) {
        Print("ERROR: Failed to set timer");
        FileClose(fileHandle);
        return(INIT_FAILED);
    }
    
    // Write initial data
    WriteMarketData();
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    // Kill timer
    EventKillTimer();
    
    // Close file if open
    if(fileHandle != INVALID_HANDLE) {
        FileClose(fileHandle);
        fileHandle = INVALID_HANDLE;
    }
    
    // Log shutdown reason
    string reasonText = "";
    switch(reason) {
        case REASON_REMOVE:      reasonText = "EA removed"; break;
        case REASON_RECOMPILE:   reasonText = "EA recompiled"; break;
        case REASON_CHARTCHANGE: reasonText = "Chart changed"; break;
        case REASON_CHARTCLOSE:  reasonText = "Chart closed"; break;
        case REASON_PARAMETERS:  reasonText = "Parameters changed"; break;
        case REASON_ACCOUNT:     reasonText = "Account changed"; break;
        default:                 reasonText = "Other reason";
    }
    
    Print("QuickDataStreamer stopped. Reason: ", reasonText);
}

//+------------------------------------------------------------------+
//| Timer event handler                                               |
//+------------------------------------------------------------------+
void OnTimer() {
    WriteMarketData();
}

//+------------------------------------------------------------------+
//| Tick event handler                                                |
//+------------------------------------------------------------------+
void OnTick() {
    // Update on tick if enough time has passed
    if(TimeCurrent() - lastUpdate >= UpdateSeconds) {
        WriteMarketData();
    }
}

//+------------------------------------------------------------------+
//| Write market data to file                                         |
//+------------------------------------------------------------------+
void WriteMarketData() {
    if(fileHandle == INVALID_HANDLE) return;
    
    // Update last write time
    lastUpdate = TimeCurrent();
    
    // Get current market data
    string symbol = Symbol();
    double bid = MarketInfo(symbol, MODE_BID);
    double ask = MarketInfo(symbol, MODE_ASK);
    double point = MarketInfo(symbol, MODE_POINT);
    int digits = (int)MarketInfo(symbol, MODE_DIGITS);
    double spread = 0;
    
    // Calculate spread in points
    if(point > 0) {
        spread = (ask - bid) / point;
    }
    
    // Get volume (current bar volume)
    long volume = iVolume(symbol, 0, 0);
    
    // Format timestamp
    string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
    
    // Write data to file
    if(FileWrite(fileHandle, 
                 timestamp,
                 symbol,
                 DoubleToString(bid, digits),
                 DoubleToString(ask, digits), 
                 DoubleToString(spread, 1),
                 IntegerToString(volume)) < 0) {
        Print("ERROR: Failed to write to file");
        return;
    }
    
    // Flush to ensure data is written
    FileFlush(fileHandle);
    
    // Log successful write (reduce logging frequency in production)
    static int writeCount = 0;
    writeCount++;
    if(writeCount % 10 == 1) {  // Log every 10th write
        Print("Data written: ", symbol, " Bid:", bid, " Ask:", ask, " Spread:", spread);
    }
}

//+------------------------------------------------------------------+