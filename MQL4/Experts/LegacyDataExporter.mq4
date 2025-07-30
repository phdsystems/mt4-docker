//+------------------------------------------------------------------+
//|                                          LegacyDataExporter.mq4  |
//|                                   Legacy Compatible Data Export  |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property version   "1.00"

// Input parameters
extern int UpdateSeconds = 1;  // Update interval in seconds

// Global variables
int fileHandle = -1;
string fileName = "market_data.csv";

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int init() {
    // Create/open CSV file
    fileHandle = FileOpen(fileName, FILE_CSV|FILE_WRITE, ',');
    
    if(fileHandle < 0) {
        Print("Failed to open file: ", fileName);
        return(-1);
    }
    
    // Write header
    FileWrite(fileHandle, "Timestamp", "Symbol", "Bid", "Ask", "Spread", "Volume");
    
    Print("LegacyDataExporter started. Writing to: ", fileName);
    
    return(0);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
int deinit() {
    if(fileHandle > 0) {
        FileClose(fileHandle);
    }
    
    Print("LegacyDataExporter stopped");
    return(0);
}

//+------------------------------------------------------------------+
//| Expert start function                                             |
//+------------------------------------------------------------------+
int start() {
    static datetime lastUpdate = 0;
    
    // Update every N seconds
    if(TimeCurrent() - lastUpdate >= UpdateSeconds) {
        lastUpdate = TimeCurrent();
        
        if(fileHandle > 0) {
            // Get current data
            double spread = (Ask - Bid) / Point;
            
            // Write to file
            FileWrite(fileHandle, 
                      TimeToStr(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                      Symbol(),
                      DoubleToStr(Bid, Digits),
                      DoubleToStr(Ask, Digits), 
                      DoubleToStr(spread, 1),
                      Volume[0]);
            
            FileFlush(fileHandle);
            
            Print("Data exported: ", Symbol(), " ", Bid, "/", Ask);
        }
    }
    
    return(0);
}
//+------------------------------------------------------------------+