//+------------------------------------------------------------------+
//|                                        TestZMQDLLIntegration.mq4 |
//|                           Test MT4 ZeroMQ DLL Integration        |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

// Import DLL functions directly for testing
#import "mt4zmq.dll"
    int    zmq_init();
    void   zmq_term();
    int    zmq_create_publisher(string address);
    int    zmq_send_message(int handle, string topic, string message);
    int    zmq_close(int handle);
    void   zmq_get_last_error(string &error, int len);
#import

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
    Print("=== Testing MT4 ZeroMQ DLL Integration ===");
    
    // Test 1: Initialize ZeroMQ
    Print("Test 1: Initializing ZeroMQ context...");
    int init_result = zmq_init();
    if (init_result == 0)
    {
        Print("✓ ZeroMQ context initialized successfully");
    }
    else
    {
        Print("✗ Failed to initialize ZeroMQ context");
        return;
    }
    
    // Test 2: Create publisher
    Print("\nTest 2: Creating publisher socket...");
    string bind_address = "tcp://*:5556";
    int publisher = zmq_create_publisher(bind_address);
    
    if (publisher > 0)
    {
        Print("✓ Publisher created successfully on ", bind_address);
        Print("  Handle: ", publisher);
    }
    else
    {
        string error = "                                                                ";
        zmq_get_last_error(error, StringLen(error));
        Print("✗ Failed to create publisher: ", StringTrimRight(error));
        zmq_term();
        return;
    }
    
    // Test 3: Send test messages
    Print("\nTest 3: Sending test messages...");
    
    // Send tick data
    string tick_topic = "tick.EURUSD";
    string tick_message = "{\"symbol\":\"EURUSD\",\"bid\":1.1000,\"ask\":1.1001,\"timestamp\":\"" + TimeToString(TimeGMT()) + "\"}";
    
    int result = zmq_send_message(publisher, tick_topic, tick_message);
    if (result == 0)
    {
        Print("✓ Tick message sent successfully");
        Print("  Topic: ", tick_topic);
        Print("  Message: ", tick_message);
    }
    else
    {
        Print("✗ Failed to send tick message");
    }
    
    // Send status message
    string status_topic = "status";
    string status_message = "{\"type\":\"test\",\"status\":\"DLL integration working\",\"mt4_build\":" + IntegerToString(TerminalInfoInteger(TERMINAL_BUILD)) + "}";
    
    result = zmq_send_message(publisher, status_topic, status_message);
    if (result == 0)
    {
        Print("✓ Status message sent successfully");
    }
    else
    {
        Print("✗ Failed to send status message");
    }
    
    // Test 4: Clean up
    Print("\nTest 4: Cleaning up...");
    
    result = zmq_close(publisher);
    if (result == 0)
    {
        Print("✓ Publisher closed successfully");
    }
    else
    {
        Print("✗ Failed to close publisher");
    }
    
    zmq_term();
    Print("✓ ZeroMQ context terminated");
    
    // Summary
    Print("\n=== Test Summary ===");
    Print("DLL Location: ", TerminalInfoString(TERMINAL_DATA_PATH), "\\MQL4\\Libraries\\mt4zmq.dll");
    Print("All tests completed!");
    Print("To verify messages are being received, run:");
    Print("  python3 clients/python/zmq_subscriber.py");
}