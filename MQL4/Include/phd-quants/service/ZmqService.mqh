//+------------------------------------------------------------------+
//|                           ZmqService.mqh                         |
//|                    Copyright © 2018, PhD Systems                 |
//|                     https://www.phdsystems.co.za                 |
//+------------------------------------------------------------------+
#property copyright "Copyright 2016, PhD Systems"
#property link      "https://www.phdinvest.co.za"
#property version   "1.00" 
#property strict

// Required: MQL-ZMQ from https://github.com/dingmaotu/mql-zmq
#include <phd-quants/integration/zmq/Zmq.mqh>

extern string ZEROMQ_PROTOCOL = "tcp";
//extern string HOSTNAME = "*";
extern string HOSTNAME = "127.0.0.1";
extern int MILLISECOND_TIMER = 0;

Context context("ZmqService");

// CREATE ZMQ_PUB SOCKET
Socket pubSocket(context, ZMQ_PUB);

class ZmqService {
   
   public:
      static void bindPublisherSocket(const int PUB_PORT) {
      
      EventSetMillisecondTimer(MILLISECOND_TIMER);     // Set Millisecond Timer to get client socket input
      
      context.setBlocky(false);  
      
      Print("[PUB] Binding MT4 Server to Socket on Port " + IntegerToString(PUB_PORT) + "..");
      pubSocket.bind(StringFormat("%s://%s:%d", ZEROMQ_PROTOCOL, HOSTNAME, PUB_PORT));
      pubSocket.setSendHighWaterMark(1);
      pubSocket.setLinger(0);
   }
   
   public:
      static void unbindPublisherSocket(const int PUB_PORT) {
      
         pubSocket.unbind(StringFormat("%s://%s:%d", ZEROMQ_PROTOCOL, HOSTNAME, PUB_PORT));
      }
   
   public:
      static void publish(string data){
            
         ZmqMsg reply(data);
         pubSocket.send(reply, true);
   }
   
   public:
      static void shutDownContext() {
      
         context.shutdown();
         context.destroy(0);
         EventKillTimer();
   }
};