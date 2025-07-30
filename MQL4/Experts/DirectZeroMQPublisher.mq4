//+------------------------------------------------------------------+
//|                                        DirectZeroMQPublisher.mq4 |
//|                    Direct ZeroMQ Publishing from MT4 (CORRECT)   |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

// This is the CORRECT architecture - MT4 as the publisher

// Since we don't have the actual ZMQ DLL, we'll use named pipes
// But this shows what the architecture SHOULD be

//--- Input parameters
input string InpZMQAddress = "tcp://*:5556";              // ZeroMQ bind address
input string InpSymbols = "EURUSD,GBPUSD,USDJPY,AUDUSD"; // Symbols to publish
input int    InpPublishInterval = 100;                    // Publish interval (ms)

// For now, using named pipe as workaround
string PipeName = "\\\\.\\pipe\\MT4_ZMQ_Publisher";
int    PipeHandle = INVALID_HANDLE;
string Symbols[];
int    SymbolCount;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== Direct ZeroMQ Publisher EA ===");
    Print("This EA should publish directly via ZeroMQ");
    Print("Currently using named pipe due to missing DLL");
    
    // Parse symbols
    SymbolCount = StringSplit(InpSymbols, ',', Symbols);
    
    // In the correct implementation, we would:
    // 1. Load the ZeroMQ DLL
    // 2. Create a PUB socket
    // 3. Bind to the address
    
    // For now, open named pipe
    PipeHandle = FileOpen(PipeName, FILE_WRITE|FILE_BIN|FILE_ANSI);
    
    if(PipeHandle == INVALID_HANDLE)
    {
        // Fallback to file
        PipeHandle = FileOpen("direct_zmq_data.json", FILE_WRITE|FILE_SHARE_READ|FILE_ANSI);
        if(PipeHandle == INVALID_HANDLE)
        {
            Print("Failed to open output");
            return INIT_FAILED;
        }
    }
    
    // Write configuration message
    string config = StringFormat(
        "{\"type\":\"config\",\"publisher\":\"MT4\",\"address\":\"%s\",\"symbols\":%d}\n",
        InpZMQAddress, SymbolCount
    );
    FileWriteString(PipeHandle, config);
    FileFlush(PipeHandle);
    
    EventSetMillisecondTimer(InpPublishInterval);
    
    Comment("Direct ZeroMQ Publisher\n",
            "Should bind to: ", InpZMQAddress, "\n",
            "Publishing ", SymbolCount, " symbols");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    
    if(PipeHandle != INVALID_HANDLE)
    {
        FileClose(PipeHandle);
    }
    
    Comment("");
}

//+------------------------------------------------------------------+
//| Timer function - This is where MT4 publishes                    |
//+------------------------------------------------------------------+
void OnMillisecondTimer()
{
    // IN A PROPER IMPLEMENTATION:
    // This would publish directly to ZeroMQ subscribers
    // No intermediate bridge needed!
    
    for(int i = 0; i < SymbolCount; i++)
    {
        string symbol = Symbols[i];
        
        double bid = MarketInfo(symbol, MODE_BID);
        double ask = MarketInfo(symbol, MODE_ASK);
        
        if(bid > 0 && ask > 0)
        {
            double spread = (ask - bid) / MarketInfo(symbol, MODE_POINT);
            int volume = (int)MarketInfo(symbol, MODE_VOLUME);
            
            // This is what we would do with the DLL:
            // string topic = "tick." + symbol;
            // string message = CreateTickJSON(symbol, bid, ask, spread, volume);
            // ZMQ_PublishMessage(socket, topic, message);
            
            // Current workaround:
            string json = StringFormat(
                "{\"type\":\"tick\",\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.1f,\"volume\":%d,\"timestamp\":%d,\"publisher\":\"MT4_DIRECT\"}\n",
                symbol, bid, ask, spread, volume, (int)TimeGMT()
            );
            
            FileWriteString(PipeHandle, json);
        }
    }
    
    FileFlush(PipeHandle);
}

//+------------------------------------------------------------------+
//| What the architecture SHOULD be:                                 |
//|                                                                  |
//| MT4 EA (This file)                                              |
//|    ↓                                                            |
//| ZeroMQ DLL                                                      |
//|    ↓                                                            |
//| Direct TCP Socket (PUB)                                         |
//|    ↓                                                            |
//| Subscribers (Python, Node.js, etc)                             |
//|                                                                  |
//| Benefits:                                                        |
//| - No intermediate bridge                                         |
//| - Lowest possible latency                                        |
//| - MT4 is the actual publisher                                   |
//| - Direct control from MQL4                                       |
//+------------------------------------------------------------------+