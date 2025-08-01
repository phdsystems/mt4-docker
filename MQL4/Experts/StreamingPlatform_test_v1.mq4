//+------------------------------------------------------------------+
//|                           ZmqService.mqh                         |
//|                    Copyright © 2018, PhD Systems                 |
//|                     https://www.phdsystems.co.za                 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2016, PhD Systems"
#property link      "https://www.phdinvest.co.za"
#property version   "1.00" 
#property strict

#include <oop/service/ZmqService.mqh>

int OnInit() {

   Print("Initializing StreamingPlatform @ ----");
  
   const int PUB_PORT = 32770;
   ZmqService::bindPublisherSocket(PUB_PORT);
   
   return(INIT_SUCCEEDED);
}

string _data;
void OnTick() {

   if ( !IsStopped() ) {
      
      //ZmqService::publish(StreamingPlatform::stream());
      Print(StringFormat("BIDING %f", Bid));
      _data = StringFormat("BIDING %f", Bid);
      
      ZmqService::publish(_data);
   }
}

void OnDeinit(const int reason) {
       
   const int PUB_PORT = 32770;
   ZmqService::unbindPublisherSocket(PUB_PORT);
   
   // Shutdown ZeroMQ Context
   ZmqService::shutDownContext();
}