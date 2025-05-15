//+------------------------------------------------------------------+
//|                                              AutoDeploy_EA.mq4   |
//|                                   Auto-Deploy Expert Advisor     |
//+------------------------------------------------------------------+
#property copyright "Auto-Deploy EA v5.0"
#property version   "5.00"
#property strict

// Global variables
datetime lastStatusUpdate = 0;
string statusFile = "ea_status.log";
string activityFile = "ea_activity.log";
string connectionFile = "connection_status.log";
int heartbeatCount = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Create status file
    WriteStatus("EA INITIALIZED - " + TimeToStr(TimeCurrent()));
    
    Print("=================================");
    Print("Auto-Deploy EA v5.0 Started");
    Print("Account: ", AccountNumber());
    Print("Company: ", AccountCompany());
    Print("Server: ", AccountServer());
    Print("Symbol: ", Symbol());
    Print("Period: ", Period());
    Print("Balance: ", AccountBalance());
    Print("Server Time: ", TimeToStr(TimeCurrent()));
    Print("=================================");
    
    // Check connection
    CheckConnection();
    
    // Write initialization info to file
    WriteActivity("EA Initialized on " + Symbol() + " " + GetPeriodString());
    
    // Set timer for periodic updates
    EventSetTimer(30);
    
    // Update chart comment
    UpdateComment();
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    WriteStatus("EA STOPPED - Reason: " + GetDeinitReasonText(reason));
    Comment("");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Update comment on each tick
    UpdateComment();
    
    // Log activity every minute
    if(TimeCurrent() - lastStatusUpdate > 60)
    {
        lastStatusUpdate = TimeCurrent();
        string status = StringFormat("RUNNING - Time: %s, Bid: %s, Ask: %s, Spread: %d", 
                                    TimeToStr(TimeCurrent()), 
                                    DoubleToStr(Bid, Digits), 
                                    DoubleToStr(Ask, Digits),
                                    MarketInfo(Symbol(), MODE_SPREAD));
        WriteStatus(status);
        WriteActivity("Tick - " + status);
    }
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
    heartbeatCount++;
    string timerMsg = StringFormat("Timer Update #%d - %s", heartbeatCount, TimeToStr(TimeCurrent()));
    WriteActivity(timerMsg);
    Print(timerMsg);
    
    // Update status file
    WriteStatus("HEARTBEAT #" + IntegerToString(heartbeatCount) + " - " + TimeToStr(TimeCurrent()));
    
    // Check connection every 5 heartbeats
    if(heartbeatCount % 5 == 0)
    {
        CheckConnection();
    }
}

//+------------------------------------------------------------------+
//| Update chart comment                                             |
//+------------------------------------------------------------------+
void UpdateComment()
{
    string comment = StringFormat(
        "=== Auto-Deploy EA v5.0 ===\n" +
        "Status: RUNNING\n" +
        "Account: %d\n" +
        "Server: %s\n" +
        "Symbol: %s\n" +
        "Time: %s\n" +
        "Bid: %s | Ask: %s\n" +
        "Spread: %d points\n" +
        "Heartbeats: %d\n" +
        "===",
        AccountNumber(),
        AccountServer(),
        Symbol(),
        TimeToStr(TimeCurrent()),
        DoubleToStr(Bid, Digits),
        DoubleToStr(Ask, Digits),
        MarketInfo(Symbol(), MODE_SPREAD),
        heartbeatCount
    );
    
    Comment(comment);
}

//+------------------------------------------------------------------+
//| Check connection status                                          |
//+------------------------------------------------------------------+
void CheckConnection()
{
    bool connected = (AccountNumber() > 0);
    string status;
    
    if(connected)
    {
        status = StringFormat("CONNECTED - Account: %d, Server: %s, Company: %s", 
                             AccountNumber(), AccountServer(), AccountCompany());
    }
    else
    {
        status = "NOT CONNECTED - No valid account";
    }
    
    WriteConnectionStatus(status);
    Print("Connection: ", status);
}

//+------------------------------------------------------------------+
//| Write status to file                                             |
//+------------------------------------------------------------------+
void WriteStatus(string message)
{
    int handle = FileOpen(statusFile, FILE_WRITE|FILE_TXT);
    if(handle != INVALID_HANDLE)
    {
        FileWriteString(handle, message);
        FileClose(handle);
    }
}

//+------------------------------------------------------------------+
//| Write activity log                                               |
//+------------------------------------------------------------------+
void WriteActivity(string message)
{
    int handle = FileOpen(activityFile, FILE_WRITE|FILE_READ|FILE_TXT);
    if(handle != INVALID_HANDLE)
    {
        FileSeek(handle, 0, SEEK_END);
        FileWriteString(handle, TimeToStr(TimeCurrent()) + " - " + message + "\n");
        FileClose(handle);
    }
}

//+------------------------------------------------------------------+
//| Write connection status                                          |
//+------------------------------------------------------------------+
void WriteConnectionStatus(string message)
{
    int handle = FileOpen(connectionFile, FILE_WRITE|FILE_TXT);
    if(handle != INVALID_HANDLE)
    {
        FileWriteString(handle, message);
        FileClose(handle);
    }
}

//+------------------------------------------------------------------+
//| Get period string                                                |
//+------------------------------------------------------------------+
string GetPeriodString()
{
    switch(Period())
    {
        case PERIOD_M1:  return "M1";
        case PERIOD_M5:  return "M5";
        case PERIOD_M15: return "M15";
        case PERIOD_M30: return "M30";
        case PERIOD_H1:  return "H1";
        case PERIOD_H4:  return "H4";
        case PERIOD_D1:  return "D1";
        case PERIOD_W1:  return "W1";
        case PERIOD_MN1: return "MN1";
        default:         return "Unknown";
    }
}

//+------------------------------------------------------------------+
//| Get deinitialization reason text                                 |
//+------------------------------------------------------------------+
string GetDeinitReasonText(int reasonCode)
{
    switch(reasonCode)
    {
        case REASON_REMOVE:      return "EA removed from chart";
        case REASON_RECOMPILE:   return "EA recompiled";
        case REASON_CHARTCHANGE: return "Symbol or timeframe changed";
        case REASON_CHARTCLOSE:  return "Chart closed";
        case REASON_PARAMETERS:  return "Input parameters changed";
        case REASON_ACCOUNT:     return "Account changed";
        case REASON_TEMPLATE:    return "New template applied";
        case REASON_INITFAILED:  return "OnInit() failed";
        case REASON_CLOSE:       return "Terminal closed";
        default:                 return "Unknown reason (" + IntegerToString(reasonCode) + ")";
    }
}
//+------------------------------------------------------------------+
