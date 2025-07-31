//+------------------------------------------------------+
//|                     PriceAction.mqh                  |
//|               Copyright 2022, PhD Systems            |
//|              https://www.phdsystems.co.za            |
//+------------------------------------------------------+

#property copyright "Copyright 2022, PhD Systems Pty Ltd."
#property link      "https://www.phdsystems.co.za"
#property version   "1.00"
#property strict

class PriceAction {

   private:
      double      open;
      double      high;
      double      low;
      double      close;

   public: PriceAction(double l_open, double l_high, double l_low, double l_close) {
      
      open = l_open;
      high = l_high;
      low = l_low;
      close = l_close;
   }
   
   public: void update(double l_open, double l_high, double l_low, double l_close) {
      
      open = l_open;
      high = l_high;
      low = l_low;
      close = l_close;
   }   
      
   public: PriceAction() {      
   }       
   
   public: double getOpen() {
      
      return open;
   }

   public: void setOpen(double l_open) {
      
      open = l_open;
   }
   
   
   public: double getHigh() {
      
      return high;
   }

   public: void setHigh(double l_high) {
      
      high = l_high;
   }
   
   
   public: double getLow() {
      
      return low;
   }

   public: void setLow(double l_low) {
      
      low = l_low;
   }
   
   
   public: double getClose() {
      
      return close;
   }

   public: void setClose(double l_close) {
      
      close = l_close;
   }                  
};

