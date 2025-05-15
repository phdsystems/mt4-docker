//+------------------------------------------------------------------+
//|                                              AutoDeploy_EA.mq4   |
//+------------------------------------------------------------------+
#property copyright "Auto-Deploy EA"
#property version   "1.00"
#property strict

int OnInit() {
    Print("AutoDeploy EA Started at " + TimeToStr(TimeCurrent()));
    CreateFile("ea_status.log", "EA INITIALIZED");
    EventSetTimer(30);
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
    EventKillTimer();
    CreateFile("ea_status.log", "EA STOPPED");
}

void OnTimer() {
    CreateFile("ea_status.log", "RUNNING - " + TimeToStr(TimeCurrent()));
    Print("Heartbeat: " + TimeToStr(TimeCurrent()));
}

void OnTick() {
    static datetime lastLog = 0;
    if(TimeCurrent() - lastLog > 60) {
        lastLog = TimeCurrent();
        CreateFile("ea_activity.log", "Tick at " + TimeToStr(TimeCurrent()));
    }
    Comment("AutoDeploy EA\n" + TimeToStr(TimeCurrent()) + "\nBid: " + DoubleToStr(Bid, Digits));
}

void CreateFile(string filename, string content) {
    int handle = FileOpen(filename, FILE_WRITE|FILE_TXT);
    if(handle != INVALID_HANDLE) {
        FileWriteString(handle, content);
        FileClose(handle);
    }
}
//+------------------------------------------------------------------+
