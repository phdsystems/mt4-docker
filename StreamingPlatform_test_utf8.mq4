//+------------------------------------------------------------------+
//|                                             StreamingPlatform_test.mq4 |
//|                             Copyright © 2018, PhD Systems        |
//|                               https://www.phdsystems.co.za       |
//+------------------------------------------------------------------+
#property copyright "Copyright 2016, PhD Systems"
#property link      "https://www.phdinvest.co.za"
#property version   "1.00"  
#property strict

#include <phd-quants/integration/zmq/Zmq.mqh>

int OnInit() {

    Print("Initializing StreamingPlatform @ ----");
    
    const int PUB_PORT = 32770;
    if(!Zmq::bindPublisherSocket(PUB_PORT)) {
        Print("Failed to bind ZMQ publisher socket on port ", PUB_PORT);
        return(INIT_FAILED);
    }
    
    Print("ZMQ publisher bound successfully on port ", PUB_PORT);
    return(INIT_SUCCEEDED);
}

string _data;
void OnTick() {

    if (!IsStopped()) {
        
        Print(StringFormat("BIDING %f", Bid));
        _data = StringFormat("{\"symbol\":\"%s\",\"bid\":%f,\"ask\":%f,\"time\":\"%s\"}", 
                            Symbol(), Bid, Ask, TimeToString(TimeCurrent()));
        
        if(!Zmq::publish(_data)) {
            Print("Failed to publish data: ", _data);
        }
    }
}

void OnDeinit(const int reason) {
    
    const int PUB_PORT = 32770;
    Zmq::unbindPublisherSocket(PUB_PORT);
    
    // Shutdown ZeroMQ Context
    Zmq::shutDownContext();
    Print("StreamingPlatform shutdown complete");
}