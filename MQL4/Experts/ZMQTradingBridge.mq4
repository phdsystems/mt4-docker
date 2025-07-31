//+------------------------------------------------------------------+
//|                                            ZMQTradingBridge.mq4  |
//|                       Real ZeroMQ Integration for Trading        |
//+------------------------------------------------------------------+
#property copyright "Trading Bridge"
#property version   "1.00"
#property strict

// Import real libzmq functions
#import "libzmq.dll"
   int zmq_ctx_new();
   int zmq_ctx_destroy(int context);
   int zmq_socket(int context, int type);
   int zmq_connect(string endpoint);
   int zmq_bind(string endpoint);
   int zmq_recv(int socket, uchar &buffer[], int len, int flags);
   int zmq_send(int socket, uchar &buffer[], int len, int flags);
   int zmq_close(int socket);
   int zmq_setsockopt(int socket, int option, int &value, int len);
#import

// ZeroMQ socket types
#define ZMQ_REP 4
#define ZMQ_REQ 3
#define ZMQ_PUB 1
#define ZMQ_SUB 2

// Socket options
#define ZMQ_RCVTIMEO 27
#define ZMQ_SNDTIMEO 28

// Global variables
int ctx = 0;
int cmd_socket = 0;
int pub_socket = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize ZeroMQ context
    ctx = zmq_ctx_new();
    if(ctx == 0) {
        Print("Failed to create ZMQ context");
        return INIT_FAILED;
    }
    
    // Create REP socket for receiving commands
    cmd_socket = zmq_socket(ctx, ZMQ_REP);
    if(cmd_socket == 0) {
        Print("Failed to create command socket");
        return INIT_FAILED;
    }
    
    // Bind to command port
    if(zmq_bind(cmd_socket, "tcp://*:5557") != 0) {
        Print("Failed to bind command socket");
        return INIT_FAILED;
    }
    
    // Create PUB socket for status updates
    pub_socket = zmq_socket(ctx, ZMQ_PUB);
    if(pub_socket == 0) {
        Print("Failed to create publisher socket");
        return INIT_FAILED;
    }
    
    // Bind publisher
    if(zmq_bind(pub_socket, "tcp://*:5558") != 0) {
        Print("Failed to bind publisher socket");
        return INIT_FAILED;
    }
    
    // Set receive timeout
    int timeout = 100; // 100ms
    zmq_setsockopt(cmd_socket, ZMQ_RCVTIMEO, timeout, 4);
    
    Print("ZMQ Trading Bridge initialized");
    Print("Commands on port 5557, Status on port 5558");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(cmd_socket != 0) zmq_close(cmd_socket);
    if(pub_socket != 0) zmq_close(pub_socket);
    if(ctx != 0) zmq_ctx_destroy(ctx);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check for incoming commands
    uchar recv_buffer[1024];
    int recv_len = zmq_recv(cmd_socket, recv_buffer, 1024, 0);
    
    if(recv_len > 0) {
        // Convert to string
        string command = CharArrayToString(recv_buffer, 0, recv_len);
        Print("Received command: ", command);
        
        // Process command
        string response = ProcessCommand(command);
        
        // Send response
        uchar send_buffer[];
        StringToCharArray(response, send_buffer);
        zmq_send(cmd_socket, send_buffer, ArraySize(send_buffer)-1, 0);
        
        // Publish status update
        PublishStatus(command, response);
    }
}

//+------------------------------------------------------------------+
//| Process trading command                                          |
//+------------------------------------------------------------------+
string ProcessCommand(string command)
{
    string parts[];
    int count = StringSplit(command, '|', parts);
    
    if(count < 1) return "ERROR|Invalid command format";
    
    string cmd = parts[0];
    
    // OPEN|BUY|EURUSD|0.1|0|0
    if(cmd == "OPEN" && count >= 6) {
        string direction = parts[1];
        string symbol = parts[2];
        double lots = StringToDouble(parts[3]);
        double sl = StringToDouble(parts[4]);
        double tp = StringToDouble(parts[5]);
        
        int op_type = (direction == "BUY") ? OP_BUY : OP_SELL;
        double price = (op_type == OP_BUY) ? MarketInfo(symbol, MODE_ASK) : MarketInfo(symbol, MODE_BID);
        
        int ticket = OrderSend(symbol, op_type, lots, price, 3, sl, tp, "ZMQ Bridge", 0, 0, clrGreen);
        
        if(ticket > 0) {
            return StringFormat("OK|%d|%.5f", ticket, price);
        } else {
            return StringFormat("ERROR|%d|%s", GetLastError(), ErrorDescription(GetLastError()));
        }
    }
    
    // CLOSE|12345
    else if(cmd == "CLOSE" && count >= 2) {
        int ticket = StrToInteger(parts[1]);
        
        if(OrderSelect(ticket, SELECT_BY_TICKET)) {
            double close_price = (OrderType() == OP_BUY) ? 
                MarketInfo(OrderSymbol(), MODE_BID) : 
                MarketInfo(OrderSymbol(), MODE_ASK);
            
            if(OrderClose(ticket, OrderLots(), close_price, 3, clrRed)) {
                return StringFormat("OK|%d|%.5f", ticket, close_price);
            } else {
                return StringFormat("ERROR|%d|%s", GetLastError(), ErrorDescription(GetLastError()));
            }
        } else {
            return "ERROR|Order not found";
        }
    }
    
    // STATUS
    else if(cmd == "STATUS") {
        return StringFormat("OK|Connected|%.5f|%.5f", AccountBalance(), AccountEquity());
    }
    
    return "ERROR|Unknown command: " + cmd;
}

//+------------------------------------------------------------------+
//| Publish status update                                            |
//+------------------------------------------------------------------+
void PublishStatus(string command, string result)
{
    string status = TimeToString(TimeCurrent()) + "|" + command + "|" + result;
    
    uchar buffer[];
    StringToCharArray("STATUS|" + status, buffer);
    zmq_send(pub_socket, buffer, ArraySize(buffer)-1, 0);
}

//+------------------------------------------------------------------+
//| Error description function                                       |
//+------------------------------------------------------------------+
string ErrorDescription(int error_code)
{
    switch(error_code) {
        case 0: return "No error";
        case 1: return "No error returned";
        case 2: return "Common error";
        case 3: return "Invalid trade parameters";
        case 4: return "Trade server is busy";
        case 5: return "Old version of the client terminal";
        case 6: return "No connection with trade server";
        case 7: return "Not enough rights";
        case 8: return "Too frequent requests";
        case 9: return "Malfunctional trade operation";
        case 64: return "Account disabled";
        case 65: return "Invalid account";
        case 128: return "Trade timeout";
        case 129: return "Invalid price";
        case 130: return "Invalid stops";
        case 131: return "Invalid trade volume";
        case 132: return "Market is closed";
        case 133: return "Trade is disabled";
        case 134: return "Not enough money";
        case 135: return "Price changed";
        case 136: return "Off quotes";
        case 137: return "Broker is busy";
        case 138: return "Requote";
        case 139: return "Order is locked";
        case 140: return "Long positions only allowed";
        case 141: return "Too many requests";
        case 145: return "Modification denied because order is too close to market";
        case 146: return "Trade context is busy";
        case 147: return "Expirations are denied by broker";
        case 148: return "Amount of open and pending orders has reached the limit";
        case 149: return "An attempt to open an order opposite when hedging is disabled";
        case 150: return "An attempt to close an order contravening the FIFO rule";
        default: return "Unknown error";
    }
}