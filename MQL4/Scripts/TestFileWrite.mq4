//+------------------------------------------------------------------+
//|                                              TestFileWrite.mq4   |
//|                                        Test File Writing Script  |
//+------------------------------------------------------------------+
#property copyright "Test"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart() {
    string filename = "test_output.csv";
    int handle = FileOpen(filename, FILE_WRITE|FILE_CSV);
    
    if (handle != INVALID_HANDLE) {
        FileWrite(handle, "Time", "Symbol", "Bid", "Ask");
        FileWrite(handle, TimeToString(TimeCurrent()), Symbol(), Bid, Ask);
        FileClose(handle);
        
        Print("File written successfully: ", filename);
        Alert("Test file created: ", filename);
    } else {
        Print("Failed to create file: ", filename);
        Alert("Failed to create file!");
    }
}