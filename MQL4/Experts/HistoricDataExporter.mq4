//+------------------------------------------------------------------+
//|                                          HistoricDataExporter.mq4 |
//|                                     Export historic data to JSON |
//+------------------------------------------------------------------+
#property copyright "Historic Data Exporter"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

// Input parameters
input string   Symbol_List = "EURUSD,GBPUSD,USDJPY,EURJPY";  // Comma-separated symbols
input int      Bars_To_Export = 1000;                        // Number of bars to export
input ENUM_TIMEFRAMES Export_Timeframe = PERIOD_H1;          // Timeframe
input string   Export_Path = "historic_data.json";           // Output filename

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("Historic Data Exporter initialized");
    Print("Will export ", Bars_To_Export, " bars for timeframe ", PeriodToString(Export_Timeframe));
    
    // Export data immediately on init
    ExportHistoricData();
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("Historic Data Exporter stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Can be triggered on each tick if needed
    // ExportHistoricData();
}

//+------------------------------------------------------------------+
//| Convert period to string                                        |
//+------------------------------------------------------------------+
string PeriodToString(int period)
{
    switch(period)
    {
        case PERIOD_M1:  return "M1";
        case PERIOD_M5:  return "M5";
        case PERIOD_M15: return "M15";
        case PERIOD_M30: return "M30";
        case PERIOD_H1:  return "H1";
        case PERIOD_H4:  return "H4";
        case PERIOD_D1:  return "D1";
        case PERIOD_W1:  return "W1";
        case PERIOD_MN1: return "MN1";
        default: return "H1";
    }
}

//+------------------------------------------------------------------+
//| Export historic data to JSON                                     |
//+------------------------------------------------------------------+
void ExportHistoricData()
{
    // Parse symbol list
    string symbols[];
    int symbol_count = StringSplit(Symbol_List, ',', symbols);
    
    if(symbol_count == 0)
    {
        Print("No symbols to export");
        return;
    }
    
    // Open file for writing
    string full_path = TerminalInfoString(TERMINAL_DATA_PATH) + "\\MQL4\\Files\\" + Export_Path;
    int file_handle = FileOpen(Export_Path, FILE_WRITE|FILE_TXT);
    
    if(file_handle == INVALID_HANDLE)
    {
        Print("Failed to create file: ", Export_Path);
        return;
    }
    
    // Start JSON structure
    FileWriteString(file_handle, "{\n");
    FileWriteString(file_handle, "  \"export_time\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",\n");
    FileWriteString(file_handle, "  \"timeframe\": \"" + PeriodToString(Export_Timeframe) + "\",\n");
    FileWriteString(file_handle, "  \"bars_count\": " + IntegerToString(Bars_To_Export) + ",\n");
    FileWriteString(file_handle, "  \"data\": {\n");
    
    // Export data for each symbol
    for(int i = 0; i < symbol_count; i++)
    {
        string symbol = symbols[i];
        StringTrimLeft(symbol);
        StringTrimRight(symbol);
        
        Print("Exporting data for ", symbol);
        
        // Write symbol data
        FileWriteString(file_handle, "    \"" + symbol + "\": [\n");
        
        // Get historic data
        int bars_available = iBars(symbol, Export_Timeframe);
        int bars_to_export = MathMin(Bars_To_Export, bars_available);
        
        for(int j = 0; j < bars_to_export; j++)
        {
            datetime time = iTime(symbol, Export_Timeframe, j);
            double open = iOpen(symbol, Export_Timeframe, j);
            double high = iHigh(symbol, Export_Timeframe, j);
            double low = iLow(symbol, Export_Timeframe, j);
            double close = iClose(symbol, Export_Timeframe, j);
            long volume = iVolume(symbol, Export_Timeframe, j);
            
            // Write bar data as JSON object
            string bar_json = "      {\n";
            bar_json += "        \"time\": \"" + TimeToString(time, TIME_DATE|TIME_SECONDS) + "\",\n";
            bar_json += "        \"timestamp\": " + IntegerToString(time) + ",\n";
            bar_json += "        \"open\": " + DoubleToString(open, 5) + ",\n";
            bar_json += "        \"high\": " + DoubleToString(high, 5) + ",\n";
            bar_json += "        \"low\": " + DoubleToString(low, 5) + ",\n";
            bar_json += "        \"close\": " + DoubleToString(close, 5) + ",\n";
            bar_json += "        \"volume\": " + IntegerToString(volume) + "\n";
            bar_json += "      }";
            
            if(j < bars_to_export - 1) bar_json += ",";
            bar_json += "\n";
            
            FileWriteString(file_handle, bar_json);
        }
        
        FileWriteString(file_handle, "    ]");
        if(i < symbol_count - 1) FileWriteString(file_handle, ",");
        FileWriteString(file_handle, "\n");
        
        Print("Exported ", bars_to_export, " bars for ", symbol);
    }
    
    // Close JSON structure
    FileWriteString(file_handle, "  }\n");
    FileWriteString(file_handle, "}\n");
    
    FileClose(file_handle);
    
    Print("Historic data exported to: ", full_path);
    Print("File saved in MQL4/Files/", Export_Path);
}

//+------------------------------------------------------------------+
//| Function to export on command (can be called from OnChartEvent) |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,
                  const long &lparam,
                  const double &dparam,
                  const string &sparam)
{
    // Press 'E' to export data
    if(id == CHARTEVENT_KEYDOWN && lparam == 'E')
    {
        Print("Manual export triggered");
        ExportHistoricData();
    }
}