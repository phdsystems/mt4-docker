//+------------------------------------------------------------------+
//|                                              ExportDataNow.mq4   |
//|                    Simple script to export data immediately      |
//+------------------------------------------------------------------+
#property copyright "Export Data Script"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict
#property show_inputs

// Input parameters
input string   Symbols = "EURUSD,GBPUSD,EURJPY";  // Symbols to export
input int      BarsCount = 100;                   // Number of bars
input bool     ExportToConsole = true;            // Also print to console

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
    Print("=== Starting Data Export ===");
    
    // Get current symbol if none specified
    string symbols_to_export = Symbols;
    if(symbols_to_export == "") symbols_to_export = Symbol();
    
    // Split symbols
    string symbol_array[];
    int count = StringSplit(symbols_to_export, ',', symbol_array);
    
    // Create main JSON file
    string filename = "export_" + TimeToString(TimeCurrent(), TIME_DATE) + ".json";
    StringReplace(filename, " ", "_");
    StringReplace(filename, ":", "");
    
    int handle = FileOpen(filename, FILE_WRITE|FILE_TXT);
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot create file ", filename);
        return;
    }
    
    // Start JSON
    FileWriteString(handle, "{\n");
    FileWriteString(handle, "  \"export_time\": \"" + TimeToString(TimeCurrent()) + "\",\n");
    FileWriteString(handle, "  \"data\": {\n");
    
    // Export each symbol
    for(int i = 0; i < count; i++)
    {
        string sym = symbol_array[i];
        StringTrimLeft(sym);
        StringTrimRight(sym);
        
        Print("Exporting ", sym, "...");
        
        FileWriteString(handle, "    \"" + sym + "\": [\n");
        
        int bars = MathMin(BarsCount, iBars(sym, Period()));
        
        for(int j = bars-1; j >= 0; j--)
        {
            datetime time = iTime(sym, Period(), j);
            double o = iOpen(sym, Period(), j);
            double h = iHigh(sym, Period(), j);
            double l = iLow(sym, Period(), j);
            double c = iClose(sym, Period(), j);
            long v = iVolume(sym, Period(), j);
            
            string bar = "      {";
            bar += "\"t\":\"" + TimeToString(time) + "\",";
            bar += "\"o\":" + DoubleToString(o, 5) + ",";
            bar += "\"h\":" + DoubleToString(h, 5) + ",";
            bar += "\"l\":" + DoubleToString(l, 5) + ",";
            bar += "\"c\":" + DoubleToString(c, 5) + ",";
            bar += "\"v\":" + IntegerToString(v) + "}";
            
            if(j > 0) bar += ",";
            FileWriteString(handle, bar + "\n");
            
            if(ExportToConsole && j < 3)
            {
                Print(sym, " ", TimeToString(time), " O:", o, " H:", h, " L:", l, " C:", c);
            }
        }
        
        FileWriteString(handle, "    ]");
        if(i < count-1) FileWriteString(handle, ",");
        FileWriteString(handle, "\n");
        
        Print("Exported ", bars, " bars for ", sym);
    }
    
    FileWriteString(handle, "  }\n}\n");
    FileClose(handle);
    
    string full_path = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL4\\Files\\" + filename;
    Print("=== Export Complete ===");
    Print("File saved to: ", filename);
    Print("Full path: ", full_path);
    
    // Also create a simple CSV
    string csv_file = "export_" + Symbol() + ".csv";
    int csv_handle = FileOpen(csv_file, FILE_WRITE|FILE_CSV);
    if(csv_handle != INVALID_HANDLE)
    {
        FileWrite(csv_handle, "Time", "Open", "High", "Low", "Close", "Volume");
        
        for(int i = BarsCount-1; i >= 0; i--)
        {
            FileWrite(csv_handle,
                TimeToString(iTime(Symbol(), Period(), i)),
                iOpen(Symbol(), Period(), i),
                iHigh(Symbol(), Period(), i),
                iLow(Symbol(), Period(), i),
                iClose(Symbol(), Period(), i),
                iVolume(Symbol(), Period(), i)
            );
        }
        FileClose(csv_handle);
        Print("CSV saved to: ", csv_file);
    }
}