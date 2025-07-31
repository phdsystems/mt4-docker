//+------------------------------------------------------------------+
//|                                         DataExportIndicator.mq4   |
//|                                    Simple Data Export Indicator   |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict
#property indicator_chart_window

// Input parameters
input int    UpdateIntervalSeconds = 60;    // Update interval in seconds
input string FileName = "market_data.csv";  // Output filename
input bool   AppendMode = true;             // Append to existing file

// Global variables
datetime LastUpdate = 0;
int FileHandle = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
    // Set timer for periodic updates
    EventSetTimer(UpdateIntervalSeconds);
    
    // Initialize file
    InitializeFile();
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Kill timer
    EventKillTimer();
    
    // Close file if open
    if(FileHandle != INVALID_HANDLE)
    {
        FileClose(FileHandle);
    }
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
    // Export data on new bar
    if(prev_calculated == 0 || rates_total > prev_calculated)
    {
        ExportData();
    }
    
    return(rates_total);
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
    ExportData();
}

//+------------------------------------------------------------------+
//| Initialize file                                                  |
//+------------------------------------------------------------------+
void InitializeFile()
{
    int flags = FILE_CSV|FILE_ANSI;
    
    if(AppendMode)
        flags |= FILE_READ|FILE_WRITE;
    else
        flags |= FILE_WRITE;
    
    FileHandle = FileOpen(FileName, flags, ',');
    
    if(FileHandle != INVALID_HANDLE)
    {
        if(AppendMode)
        {
            // Move to end of file
            FileSeek(FileHandle, 0, SEEK_END);
        }
        else
        {
            // Write header for new file
            FileWrite(FileHandle, "Time", "Symbol", "Bid", "Ask", "Spread", "Volume");
        }
        
        Print("Data export initialized: ", FileName);
    }
    else
    {
        Print("Failed to open file: ", FileName);
    }
}

//+------------------------------------------------------------------+
//| Export current market data                                       |
//+------------------------------------------------------------------+
void ExportData()
{
    if(FileHandle == INVALID_HANDLE)
    {
        InitializeFile();
        if(FileHandle == INVALID_HANDLE)
            return;
    }
    
    // Calculate spread in points
    double spread = (Ask - Bid) / Point;
    
    // Write data
    FileWrite(FileHandle,
              TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
              Symbol(),
              DoubleToString(Bid, Digits),
              DoubleToString(Ask, Digits),
              DoubleToString(spread, 1),
              Volume[0]);
    
    // Flush to ensure data is written
    FileFlush(FileHandle);
    
    // Update last export time
    LastUpdate = TimeCurrent();
    
    // Show comment on chart
    Comment("Data Export Active\n",
            "Last Update: ", TimeToString(LastUpdate, TIME_DATE|TIME_SECONDS), "\n",
            "File: ", FileName);
}
//+------------------------------------------------------------------+