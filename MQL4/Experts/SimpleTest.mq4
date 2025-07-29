//+------------------------------------------------------------------+
//|                                                   SimpleTest.mq4 |
//+------------------------------------------------------------------+
#property copyright "Test EA"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("SimpleTest EA Started");
    Comment("SimpleTest EA Running\nTime: ", TimeToStr(TimeCurrent()));
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Comment("");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    Comment("SimpleTest EA\nTime: ", TimeToStr(TimeCurrent()), "\nBid: ", Bid);
}
//+------------------------------------------------------------------+