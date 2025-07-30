//+------------------------------------------------------------------+
//|                                         MultibrokerPublisher.mq4 |
//|                                   Copyright 2024, Multi-broker   |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, Multi-broker System"
#property link      ""
#property version   "1.00"
#property strict

// Import ZeroMQ DLL functions
#import "mt4zmq.dll"
    int    zmq_init();
    void   zmq_term();
    int    zmq_create_publisher(string address);
    void   zmq_destroy_publisher(int handle);
    int    zmq_send_message(int handle, string topic, string message);
    int    zmq_poll(int handle, int timeout);
    string zmq_get_last_error();
    int    zmq_get_version();
    int    zmq_is_connected(int handle);
    void   zmq_set_debug(bool enable);
#import

// Global variables
int g_zmqHandle = -1;
string g_brokerID = "";
bool g_isPublishing = false;

//+------------------------------------------------------------------+
//| Script program start function                                     |
//+------------------------------------------------------------------+
void OnStart()
{
    // Get broker ID from environment or generate from account
    g_brokerID = GetBrokerID();
    
    Print("Multi-broker Publisher starting for broker: ", g_brokerID);
    
    // Initialize ZeroMQ
    if (zmq_init() != 0)
    {
        Print("Failed to initialize ZeroMQ library");
        return;
    }
    
    // Create publisher
    string publishAddress = "tcp://*:5556";
    g_zmqHandle = zmq_create_publisher(publishAddress);
    
    if (g_zmqHandle < 0)
    {
        Print("Failed to create ZeroMQ publisher on ", publishAddress);
        zmq_term();
        return;
    }
    
    Print("ZeroMQ publisher created successfully on ", publishAddress);
    
    // Get symbols to publish from input or environment
    string symbols = GetSymbolsToPublish();
    string symbolArray[];
    int symbolCount = StringSplit(symbols, ',', symbolArray);
    
    // Start publishing loop
    g_isPublishing = true;
    int tickCount = 0;
    
    while (g_isPublishing && !IsStopped())
    {
        // Publish ticks for all symbols
        for (int i = 0; i < symbolCount; i++)
        {
            string symbol = StringTrimLeft(StringTrimRight(symbolArray[i]));
            if (symbol != "")
            {
                PublishTick(symbol);
                tickCount++;
            }
        }
        
        // Brief delay
        Sleep(100);
        
        // Log progress every 100 ticks
        if (tickCount % 100 == 0)
        {
            Print("Published ", tickCount, " ticks for broker ", g_brokerID);
        }
    }
    
    // Cleanup
    zmq_destroy_publisher(g_zmqHandle);
    zmq_term();
    
    Print("Multi-broker Publisher stopped. Total ticks: ", tickCount);
}

//+------------------------------------------------------------------+
//| Get broker ID                                                     |
//+------------------------------------------------------------------+
string GetBrokerID()
{
    // Try to get from global variable
    string brokerID = GlobalVariableGet("BROKER_ID");
    
    if (brokerID == "")
    {
        // Generate from account info
        brokerID = StringFormat("broker_%d_%s", 
            AccountNumber(), 
            StringSubstr(AccountCompany(), 0, 10));
        
        // Remove spaces and special characters
        StringReplace(brokerID, " ", "_");
        StringReplace(brokerID, ".", "");
        StringReplace(brokerID, ",", "");
    }
    
    return brokerID;
}

//+------------------------------------------------------------------+
//| Get symbols to publish                                            |
//+------------------------------------------------------------------+
string GetSymbolsToPublish()
{
    // Try to get from global variable
    string symbols = GlobalVariableGet("PUBLISH_SYMBOLS");
    
    if (symbols == "")
    {
        // Default major pairs
        symbols = "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCHF,USDCAD,NZDUSD,XAUUSD";
    }
    
    return symbols;
}

//+------------------------------------------------------------------+
//| Publish tick data for a symbol                                    |
//+------------------------------------------------------------------+
void PublishTick(string symbol)
{
    // Check if symbol exists
    if (!SymbolSelect(symbol, true))
    {
        Print("Symbol not found: ", symbol);
        return;
    }
    
    // Get tick data
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double spread = (ask - bid) / SymbolInfoDouble(symbol, SYMBOL_POINT);
    long volume = SymbolInfoInteger(symbol, SYMBOL_VOLUME);
    
    // Create JSON message with broker info
    string message = StringFormat(
        "{\"broker_id\":\"%s\",\"broker_name\":\"%s\",\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.1f,\"volume\":%d,\"timestamp\":%d,\"server_time\":\"%s\"}",
        g_brokerID,
        AccountCompany(),
        symbol,
        bid,
        ask,
        spread,
        volume,
        TimeCurrent(),
        TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS)
    );
    
    // Create topic with broker ID
    string topic = StringFormat("tick.%s.%s", g_brokerID, symbol);
    
    // Send message
    int result = zmq_send_message(g_zmqHandle, topic, message);
    
    if (result != 0)
    {
        Print("Failed to send message for ", symbol, ": ", zmq_get_last_error());
    }
}

//+------------------------------------------------------------------+
//| Global variable operations                                        |
//+------------------------------------------------------------------+
string GlobalVariableGet(string name)
{
    if (GlobalVariableCheck(name))
    {
        double value = GlobalVariableGet(name);
        // For string storage, we would need a different approach
        // This is simplified
        return "";
    }
    return "";
}

//+------------------------------------------------------------------+