//+------------------------------------------------------------------+
//|                                                    ZeroMQLib.mqh |
//|                              ZeroMQ Direct Publishing from MT4   |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property strict

// This is what we NEED but don't have yet - a DLL
#import "zmq4mt4.dll"
    // Initialize publisher socket
    int ZMQ_CreatePublisher(string bind_address);
    
    // Send message with topic
    int ZMQ_PublishMessage(int socket, string topic, string message);
    
    // Close socket
    void ZMQ_ClosePublisher(int socket);
    
    // Get last error
    string ZMQ_GetLastError();
#import

//+------------------------------------------------------------------+
//| ZeroMQ Publisher Class (What it SHOULD be)                       |
//+------------------------------------------------------------------+
class CZeroMQPublisher
{
private:
    int     m_socket;
    bool    m_initialized;
    string  m_address;
    
public:
    CZeroMQPublisher() : m_socket(-1), m_initialized(false) {}
    
    ~CZeroMQPublisher()
    {
        if(m_initialized)
            Close();
    }
    
    bool Initialize(string address = "tcp://*:5556")
    {
        m_address = address;
        m_socket = ZMQ_CreatePublisher(address);
        
        if(m_socket > 0)
        {
            m_initialized = true;
            Print("ZeroMQ Publisher initialized on ", address);
            return true;
        }
        
        Print("Failed to initialize ZeroMQ: ", ZMQ_GetLastError());
        return false;
    }
    
    bool PublishTick(string symbol, double bid, double ask, double spread, int volume)
    {
        if(!m_initialized) return false;
        
        // Create JSON message
        string message = StringFormat(
            "{\"type\":\"tick\",\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.1f,\"volume\":%d,\"timestamp\":%d}",
            symbol, bid, ask, spread, volume, (int)TimeGMT()
        );
        
        // Topic for subscription filtering
        string topic = "tick." + symbol;
        
        // Publish via ZeroMQ
        int result = ZMQ_PublishMessage(m_socket, topic, message);
        
        return result > 0;
    }
    
    bool PublishBar(string symbol, ENUM_TIMEFRAMES period, 
                    double open, double high, double low, double close, 
                    long volume, datetime time)
    {
        if(!m_initialized) return false;
        
        string tf = PeriodToString(period);
        
        string message = StringFormat(
            "{\"type\":\"bar\",\"symbol\":\"%s\",\"timeframe\":\"%s\",\"open\":%.5f,\"high\":%.5f,\"low\":%.5f,\"close\":%.5f,\"volume\":%d,\"time\":%d}",
            symbol, tf, open, high, low, close, (int)volume, (int)time
        );
        
        string topic = StringFormat("bar.%s.%s", symbol, tf);
        
        int result = ZMQ_PublishMessage(m_socket, topic, message);
        
        return result > 0;
    }
    
    void Close()
    {
        if(m_initialized && m_socket > 0)
        {
            ZMQ_ClosePublisher(m_socket);
            m_initialized = false;
            Print("ZeroMQ Publisher closed");
        }
    }
    
private:
    string PeriodToString(ENUM_TIMEFRAMES period)
    {
        switch(period)
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
            default:         return "M1";
        }
    }
};