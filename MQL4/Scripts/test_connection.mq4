//+------------------------------------------------------------------+
//|                                           test_connection.mq4    |
//+------------------------------------------------------------------+
#property copyright "Connection Test"
#property version   "1.00"
#property strict

void OnStart() {
    Print("Connection Test Starting...");
    
    // Check account info
    if(AccountNumber() > 0) {
        Print("Account Number: ", AccountNumber());
        Print("Account Name: ", AccountName());
        Print("Account Server: ", AccountServer());
        Print("Account Company: ", AccountCompany());
        Print("Account Currency: ", AccountCurrency());
        Print("Account Balance: ", AccountBalance());
        Print("Connection Status: CONNECTED");
        
        // Write to file
        int handle = FileOpen("connection_test.log", FILE_WRITE|FILE_TXT);
        if(handle != INVALID_HANDLE) {
            FileWriteString(handle, "CONNECTED - Account: " + IntegerToString(AccountNumber()));
            FileClose(handle);
        }
    } else {
        Print("Connection Status: NOT CONNECTED");
        Print("Account Number is 0 - Not logged in");
        
        // Write to file
        int handle = FileOpen("connection_test.log", FILE_WRITE|FILE_TXT);
        if(handle != INVALID_HANDLE) {
            FileWriteString(handle, "NOT CONNECTED");
            FileClose(handle);
        }
    }
}
//+------------------------------------------------------------------+
