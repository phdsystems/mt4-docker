//+------------------------------------------------------------------+
//|                                               DataExportZMQ.mq4  |
//|                          Export historic data via Files and ZMQ  |
//+------------------------------------------------------------------+
#property copyright "Data Export with ZMQ"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

#include <phd-quants/integration/zmq/Zmq.mqh>

// Input parameters
input bool     Enable_ZMQ_Stream = true;                     // Stream data via ZeroMQ
input int      ZMQ_Port = 32771;                            // ZeroMQ port
input bool     Export_On_Init = true;                       // Export on initialization
input int      Export_Bars = 500;                           // Number of bars to export
input string   Export_Symbols = "EURUSD,GBPUSD,USDJPY";    // Symbols to export
input ENUM_TIMEFRAMES Export_Period = PERIOD_M5;            // Timeframe

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("DataExportZMQ initializing...");
    
    // Initialize ZeroMQ if enabled
    if(Enable_ZMQ_Stream)
    {
        if(!Zmq::bindPublisherSocket(ZMQ_Port))
        {
            Print("Failed to bind ZMQ publisher on port ", ZMQ_Port);
            return(INIT_FAILED);
        }
        Print("ZMQ publisher bound on port ", ZMQ_Port);
    }
    
    // Export initial data if requested
    if(Export_On_Init)
    {
        ExportAllData();
    }
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(Enable_ZMQ_Stream)
    {
        Zmq::unbindPublisherSocket(ZMQ_Port);
        Zmq::shutDownContext();
    }
    Print("DataExportZMQ stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Export current tick data
    if(Enable_ZMQ_Stream)
    {
        string tick_json = CreateTickJSON(Symbol(), Bid, Ask);
        PublishData("tick", tick_json);
    }
}

//+------------------------------------------------------------------+
//| Create tick data JSON                                            |
//+------------------------------------------------------------------+
string CreateTickJSON(string symbol, double bid, double ask)
{
    string json = "{";
    json += "\"type\":\"tick\",";
    json += "\"symbol\":\"" + symbol + "\",";
    json += "\"time\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",";
    json += "\"timestamp\":" + IntegerToString(TimeCurrent()) + ",";
    json += "\"bid\":" + DoubleToString(bid, 5) + ",";
    json += "\"ask\":" + DoubleToString(ask, 5) + ",";
    json += "\"spread\":" + DoubleToString((ask-bid)*10000, 1);
    json += "}";
    
    return json;
}

//+------------------------------------------------------------------+
//| Export all configured data                                       |
//+------------------------------------------------------------------+
void ExportAllData()
{
    Print("Starting data export...");
    
    // Parse symbols
    string symbols[];
    int count = StringSplit(Export_Symbols, ',', symbols);
    
    // Export data for each symbol
    for(int i = 0; i < count; i++)
    {
        string symbol = symbols[i];
        StringTrimLeft(symbol);
        StringTrimRight(symbol);
        
        ExportSymbolData(symbol, Export_Period, Export_Bars);
    }
    
    Print("Data export completed");
}

//+------------------------------------------------------------------+
//| Export data for a specific symbol                                |
//+------------------------------------------------------------------+
void ExportSymbolData(string symbol, int timeframe, int bars)
{
    Print("Exporting ", bars, " bars for ", symbol);
    
    // Create filename
    string filename = symbol + "_" + PeriodToString(timeframe) + "_" + 
                     TimeToString(TimeCurrent(), TIME_DATE) + ".json";
    StringReplace(filename, " ", "_");
    StringReplace(filename, ":", "");
    
    int handle = FileOpen(filename, FILE_WRITE|FILE_TXT);
    if(handle == INVALID_HANDLE)
    {
        Print("Failed to create file: ", filename);
        return;
    }
    
    // Start JSON array
    FileWriteString(handle, "[\n");
    
    // Get available bars
    int available = iBars(symbol, timeframe);
    int export_count = MathMin(bars, available);
    
    // Export bar data
    for(int i = export_count - 1; i >= 0; i--)
    {
        datetime time = iTime(symbol, timeframe, i);
        double open = iOpen(symbol, timeframe, i);
        double high = iHigh(symbol, timeframe, i);
        double low = iLow(symbol, timeframe, i);
        double close = iClose(symbol, timeframe, i);
        long volume = iVolume(symbol, timeframe, i);
        
        string bar_json = "  {";
        bar_json += "\"symbol\":\"" + symbol + "\",";
        bar_json += "\"timeframe\":\"" + PeriodToString(timeframe) + "\",";
        bar_json += "\"time\":\"" + TimeToString(time, TIME_DATE|TIME_SECONDS) + "\",";
        bar_json += "\"timestamp\":" + IntegerToString(time) + ",";
        bar_json += "\"open\":" + DoubleToString(open, 5) + ",";
        bar_json += "\"high\":" + DoubleToString(high, 5) + ",";
        bar_json += "\"low\":" + DoubleToString(low, 5) + ",";
        bar_json += "\"close\":" + DoubleToString(close, 5) + ",";
        bar_json += "\"volume\":" + IntegerToString(volume);
        bar_json += "}";
        
        if(i > 0) bar_json += ",";
        bar_json += "\n";
        
        FileWriteString(handle, bar_json);
        
        // Also publish via ZMQ if enabled
        if(Enable_ZMQ_Stream && i == 0) // Only publish latest bar
        {
            PublishData("bar", bar_json);
        }
    }
    
    FileWriteString(handle, "]\n");
    FileClose(handle);
    
    Print("Exported ", export_count, " bars to ", filename);
}

//+------------------------------------------------------------------+
//| Publish data via ZeroMQ                                         |
//+------------------------------------------------------------------+
void PublishData(string type, string data)
{
    if(Enable_ZMQ_Stream)
    {
        string message = "{\"type\":\"" + type + "\",\"data\":" + data + "}";
        if(!Zmq::publish(message))
        {
            Print("Failed to publish: ", message);
        }
    }
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
        default: return IntegerToString(period);
    }
}

//+------------------------------------------------------------------+
//| Timer function for periodic exports                              |
//+------------------------------------------------------------------+
void OnTimer()
{
    // Can be used to export data periodically
    // ExportAllData();
}