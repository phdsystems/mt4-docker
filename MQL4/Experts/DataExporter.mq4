//+------------------------------------------------------------------+
//|                                              DataExporter.mq4    |
//|                                         Market Data Exporter     |
//|                                              MT4 Docker System   |
//+------------------------------------------------------------------+
#property copyright   "MT4 Docker System"
#property link        "https://github.com/mt4-docker"

input int    UpdateInterval = 60;     // Update interval in seconds
input string FileName = "market_data.csv"; // Output file name

int FileHandle = -1;
datetime LastUpdate = 0;

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int init()
  {
   Print("DataExporter starting...");
   
   // Try to open file for append
   FileHandle = FileOpen(FileName, FILE_CSV|FILE_WRITE|FILE_READ, ',');
   
   if(FileHandle < 0)
     {
      Print("Failed to open file: ", FileName);
      return(-1);
     }
   
   // Move to end of file
   FileSeek(FileHandle, 0, SEEK_END);
   
   // Write header if file is empty
   if(FileTell(FileHandle) == 0)
     {
      FileWrite(FileHandle, "DateTime", "Symbol", "Bid", "Ask", "Spread", "Volume");
     }
   
   Print("DataExporter initialized. Writing to: ", FileName);
   return(0);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int deinit()
  {
   if(FileHandle >= 0)
     {
      FileClose(FileHandle);
     }
   Print("DataExporter stopped");
   return(0);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int start()
  {
   // Check if it's time to update
   if(TimeCurrent() - LastUpdate < UpdateInterval)
     {
      return(0);
     }
   
   LastUpdate = TimeCurrent();
   
   // Get market data
   double bid = Bid;
   double ask = Ask;
   double spread = (ask - bid) / Point;
   int volume = Volume[0];
   
   // Write to file
   if(FileHandle >= 0)
     {
      FileWrite(FileHandle,
                TimeToStr(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                Symbol(),
                DoubleToStr(bid, Digits),
                DoubleToStr(ask, Digits),
                DoubleToStr(spread, 1),
                volume);
      
      FileFlush(FileHandle);
      
      Print("Data exported: ", Symbol(), " ", bid, "/", ask);
     }
   
   return(0);
  }
//+------------------------------------------------------------------+