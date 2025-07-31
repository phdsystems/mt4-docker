//+------------------------------------------------------------------+
//|                                            DataExportScript.mq4   |
//|                                    Simple Data Export Script      |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
    string filename = "market_data.csv";
    int file_handle = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
    
    if(file_handle != INVALID_HANDLE)
    {
        // Write header
        FileWrite(file_handle, "Time", "Symbol", "Bid", "Ask", "Spread", "Volume");
        
        // Write current data
        FileWrite(file_handle,
                  TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                  Symbol(),
                  DoubleToString(Bid, Digits),
                  DoubleToString(Ask, Digits),
                  DoubleToString((Ask - Bid) / Point, 1),
                  Volume[0]);
        
        FileClose(file_handle);
        Print("Data exported to ", filename);
    }
    else
    {
        Print("Failed to create file ", filename);
    }
}
//+------------------------------------------------------------------+
