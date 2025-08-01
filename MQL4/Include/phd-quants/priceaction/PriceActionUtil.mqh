//PriceActionUtil.mqh
//Copyright 2024, PhD Systems
//https://www.phdsystems.co.za

#include <oop/util/CsvUtil.mqh>
#include <oop/util/TimeUtil.mqh>
#include <oop/util/JsonUtil.mqh>
#include <oop/domain/mt4/Mt4OHLC.mqh>

class PriceActionUtil {
   
   public: static double getPriceDecimalPoints() {
   
      switch(Digits) {
         
         case 1: return(1); //e.g. NAS100 pair
         case 2: return(0.1); //e.g. ??
         case 3: return(0.01); //e.g. EURJPY pair
         case 4: return(0.001); //e.g. USDRZA pair
         case 5: return(0.0001); //e.g. EURUSD pair
         default: return(0.01); //e.g. SP_CrudeOil
      }
   }
   
   public: static string _constructPriceOhlc(int l_barIndex) {
               
         return StringFormat("{\"symbol\": \"%s\", \"date\": \"%s\", \"time\": \"%s\", \"timeframe\": \"%d\", \"open\": %.5f, \"high\": %.5f, \"low\": %.5f, \"close\": %.5f }", 
                             Symbol(), 
                             TimeToStr(TimeCurrent(), TIME_DATE),
                             TimeToStr(TimeCurrent(), TIME_MINUTES), 
                             Period(),
                             Mt4OHLC::getOpen(l_barIndex), 
                             Mt4OHLC::getHigh(l_barIndex), 
                             Mt4OHLC::getLow(l_barIndex), 
                             Mt4OHLC::getClose(l_barIndex));
   } 
      
   public: static string __constructPriceOhlc(int l_barIndex) {//Indicator Date, Timeframe, 
                                                               //Price Open, Price High, Price Low, Price Close         
         string escapeQuote = CsvUtil::escapeQuote();
         string csvComma = CsvUtil::csvComma();
         
         
         //[18, 12, 6, 9, 12, 3, 9]
         //[{18, 12, 6, 9, 12, 3, 9}, {18, 12, 6, 9, 12, 3, 9}]
         
         /*
         export const sampleData = [
           { t: '2023-07-01', o: 100, h: 110, l: 90, c: 105 },
           { t: '2023-07-02', o: 105, h: 115, l: 95, c: 110 },
           { t: '2023-07-03', o: 110, h: 120, l: 100, c: 115 },
           // Add more data points as needed
         ];         
         */
         
         return escapeQuote + (string)TimeCurrent() + escapeQuote + csvComma
                              + escapeQuote + (string)Period() + escapeQuote + csvComma
                              + escapeQuote + (string)Mt4OHLC::getOpen(l_barIndex) + escapeQuote + csvComma
                              + escapeQuote + (string)Mt4OHLC::getHigh(l_barIndex) + escapeQuote + csvComma
                              + escapeQuote + (string)Mt4OHLC::getLow(l_barIndex) + escapeQuote + csvComma
                              + escapeQuote + (string)Mt4OHLC::getClose(l_barIndex) + escapeQuote;
   }
   
   int entry;
   /*private: static int getEntry() {
      
      return entry;
   }*/
   public: static string constructOhlc(int l_barIndex = 0) {
         /*
         entry++;
         string csvComma = "";
         if (entry > 1) csvComma = CsvUtil::csvComma();         
         */
         string csvComma = CsvUtil::csvComma();
         string escapeJsonQuote = JasonUtil::escapeJsonQuote();
         string escapeJsonObjectStart = JasonUtil::escapeJsonObjectStart();
         string escapeJsonObjectEnd = JasonUtil::escapeJsonObjectEnd();
         string escapeJsonNextEntry = JasonUtil::escapeJsonNextEntry();
 
         double _volume = iVolume(Symbol(), Period(), l_barIndex);
         
         return escapeJsonObjectStart
                            + escapeJsonQuote + "symbol" + escapeJsonQuote + ":" + escapeJsonQuote + Symbol() + escapeJsonQuote + escapeJsonNextEntry
                            + escapeJsonQuote + "timeframe" + escapeJsonQuote + ":" + escapeJsonQuote + (string)Period() + escapeJsonQuote + escapeJsonNextEntry
                            + escapeJsonQuote + "date" + escapeJsonQuote + ":" + escapeJsonQuote + TimeUtil::convertCurrentTimeToString() + escapeJsonQuote + escapeJsonNextEntry
                            + escapeJsonQuote + "open" + escapeJsonQuote + ":" + escapeJsonQuote + (string) Mt4OHLC::getOpen(l_barIndex) + escapeJsonQuote + escapeJsonNextEntry
                            + escapeJsonQuote + "high" + escapeJsonQuote + ":" + escapeJsonQuote + (string) Mt4OHLC::getHigh(l_barIndex) + escapeJsonQuote + escapeJsonNextEntry
                            + escapeJsonQuote + "low" + escapeJsonQuote + ":" + escapeJsonQuote + (string) Mt4OHLC::getLow(l_barIndex) + escapeJsonQuote + escapeJsonNextEntry
                            + escapeJsonQuote + "close" + escapeJsonQuote + ":" + escapeJsonQuote + (string) Mt4OHLC::getClose(l_barIndex) + escapeJsonQuote + escapeJsonNextEntry
                            + escapeJsonQuote + "volume" + escapeJsonQuote + ":" + escapeJsonQuote + _volume + escapeJsonQuote
                            + escapeJsonObjectEnd
                            + csvComma
                            ;
   }         
};