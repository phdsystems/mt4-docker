//PriceType.mqh
//Copyright 2024, PhD Systems
//https://www.phdsystems.co.za

class _PriceType {

   enum PriceType {
      PRICE_TYPE_CLOSE,      // Close
      PRICE_TYPE_OPEN,       // Open
      PRICE_TYPE_HIGH,       // High
      PRICE_TYPE_LOW,        // Low
      PRICE_TYPE_MEDIAN,     // Median
      PRICE_TYPE_TYPICAL,    // Typical
      PRICE_TYPE_WEIGHTED,   // Weighted
      PRICE_TYPE_AVERAGE,    // Average (high+low+open+close)/4
      PRICE_TYPE_MEDIAN_BODY,    // Average median body (open+close)/2
      PRICE_TYPE_TREND_BIAS,    // Trend biased price
      PRICE_TYPE_EXTREME_TREND_BIAS,   // Trend biased (extreme) price
      PRICE_TYPE_HA_CLOSE,    // Heiken ashi close
      PRICE_TYPE_HA_OPEN ,    // Heiken ashi open
      PRICE_TYPE_HA_HIGH,     // Heiken ashi high
      PRICE_TYPE_HA_LOW,      // Heiken ashi low
      PRICE_TYPE_HA_MEDIAN,   // Heiken ashi median
      PRICE_TYPE_HA_TYPICAL,  // Heiken ashi typical
      PRICE_TYPE_HA_WEIGHTED, // Heiken ashi weighted
      PRICE_TYPE_HA_AVERAGE,  // Heiken ashi average
      PRICE_TYPE_HA_MEDIAN_BIAS,  // Heiken ashi median body
      PRICE_TYPE_HA_TREND_BIAS,  // Heiken ashi trend biased price
      PRICE_TYPE_HA_EXTREME_TREND_BIAS, // Heiken ashi trend biased (extreme) price
      PRICE_TYPE_HA_BETTER_FORMULA_CLOSE,   // Heiken ashi (better formula) close
      PRICE_TYPE_HA_BETTER_FORMULA_OPEN,   // Heiken ashi (better formula) open
      PRICE_TYPE_HA_BETTER_FORMULA_HIGH,    // Heiken ashi (better formula) high
      PRICE_TYPE_HA_BETTER_FORMULA_LOW,     // Heiken ashi (better formula) low
      PRICE_TYPE_HA_BETTER_FORMULA_MEDIAN,  // Heiken ashi (better formula) median
      PRICE_TYPE_HA_BETTER_FORMULA_TYPICAL, // Heiken ashi (better formula) typical
      PRICE_TYPE_HA_BETTER_FORMULA_WEIGHTED,// Heiken ashi (better formula) weighted
      PRICE_TYPE_HA_BETTER_FORMULA_AVERAGE, // Heiken ashi (better formula) average
      PRICE_TYPE_HA_BETTER_FORMULA_MEDIAN_BODY, // Heiken ashi (better formula) median body
      PRICE_TYPE_HA_BETTER_FORMULA_TREND_BIAS, // Heiken ashi (better formula) trend biased price
      PRICE_TYPE_HA_BETTER_FORMULA_EXTREME_TREND_BIAS // Heiken ashi (better formula) trend biased (extreme) price
   };
   
   public: static string getPriceTypeDesc(PriceType l_priceType) {
      
      return EnumToString(l_priceType);
   }
};

