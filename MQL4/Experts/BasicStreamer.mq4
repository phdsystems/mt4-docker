//+------------------------------------------------------------------+
//|                                              BasicStreamer.mq4   |
//|                                         Basic Data Streamer      |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("BasicStreamer initialized");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("BasicStreamer stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    static datetime lastWrite = 0;
    
    // Write every 60 seconds
    if(TimeCurrent() - lastWrite >= 60)
    {
        lastWrite = TimeCurrent();
        
        // Open file
        int handle = FileOpen("basic_data.csv", FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
        if(handle != INVALID_HANDLE)
        {
            // Move to end of file
            FileSeek(handle, 0, SEEK_END);
            
            // Write data
            FileWrite(handle, 
                     TimeToString(TimeCurrent()),
                     Symbol(),
                     DoubleToString(Bid, Digits),
                     DoubleToString(Ask, Digits));
            
            FileClose(handle);
            Print("Data written");
        }
    }
}
//+------------------------------------------------------------------+