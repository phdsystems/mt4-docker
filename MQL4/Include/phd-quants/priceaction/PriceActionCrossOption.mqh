//+----------------------------------------------------------------+
//|              PriceActionCrossOption.mqh                        |
//|             Copyright © 2022, PhD Systems                      |
//|             https://www.phdsystems.co.za                       |
//+----------------------------------------------------------------+
#property strict

enum PriceActionCrossOption {
   
   ON_PA_OPEN,
   ON_PA_HIGH,
   ON_PA_LOW,   
   ON_PA_CLOSE
};

string getPriceActionCrossOptionDesc(int l_crossStrategy) {
   
   switch(l_crossStrategy) {
   
      case ON_PA_OPEN: {
         
         return "ON_PA_OPEN";
      }
      
      case ON_PA_HIGH:{
         
         return "ON_PA_HIGH";
      }
      case ON_PA_LOW:{
         
         return "ON_PA_LOW";
      }
            
      case ON_PA_CLOSE:{
         
         return "ON_PA_CLOSE";
      }    
   }
   
   return "-1";     
}