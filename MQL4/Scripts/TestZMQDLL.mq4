//+------------------------------------------------------------------+
//|                                                  TestZMQDLL.mq4  |
//|                                 Test ZeroMQ DLL functionality    |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

#include <MT4ZMQ.mqh>

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
    Print("=== Testing MT4ZMQ DLL ===");
    
    // Test 1: Get ZeroMQ version
    Print("Test 1: Getting ZeroMQ version...");
    string version = GetZMQVersion();
    Print("ZeroMQ Version: ", version);
    
    // Test 2: Create publisher
    Print("\nTest 2: Creating publisher...");
    CZMQPublisher publisher;
    
    if (publisher.Create("tcp://*:5557"))
    {
        Print("✓ Publisher created successfully");
        
        // Test 3: Send messages
        Print("\nTest 3: Sending test messages...");
        
        // Send tick data
        if (publisher.SendTick("EURUSD", 1.0850, 1.0852))
        {
            Print("✓ Tick message sent");
        }
        else
        {
            Print("✗ Failed to send tick message");
        }
        
        // Send custom message
        if (publisher.SendMessage("test", "Hello from MT4!"))
        {
            Print("✓ Custom message sent");
        }
        else
        {
            Print("✗ Failed to send custom message");
        }
        
        // Send bar data
        if (publisher.SendBar("EURUSD", PERIOD_M1))
        {
            Print("✓ Bar message sent");
        }
        else
        {
            Print("✗ Failed to send bar message");
        }
        
        // Test 4: Create subscriber in same process
        Print("\nTest 4: Creating subscriber...");
        CZMQSubscriber subscriber;
        
        if (subscriber.Create("tcp://localhost:5557"))
        {
            Print("✓ Subscriber created successfully");
            
            // Subscribe to all messages
            if (subscriber.Subscribe(""))
            {
                Print("✓ Subscribed to all topics");
                
                // Send and receive a message
                publisher.SendMessage("test.echo", "{\"data\":\"Echo test\"}");
                
                string topic, message;
                if (subscriber.Receive(topic, message, 1000))
                {
                    Print("✓ Received message:");
                    Print("  Topic: ", topic);
                    Print("  Message: ", message);
                }
                else
                {
                    Print("✗ No message received (timeout)");
                }
            }
            else
            {
                Print("✗ Failed to subscribe");
            }
            
            subscriber.Close();
        }
        else
        {
            Print("✗ Failed to create subscriber");
        }
        
        publisher.Close();
    }
    else
    {
        Print("✗ Failed to create publisher");
        
        // Get error
        string error = "                                                  ";
        zmq_get_last_error(error, StringLen(error));
        Print("Error: ", error);
    }
    
    Print("\n=== Test completed ===");
    
    Alert("ZeroMQ DLL test completed. Check the Experts log for results.");
}