//+------------------------------------------------------------------+
//|                                                      MT4ZMQ.mqh  |
//|                           ZeroMQ Direct Integration for MT4      |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property strict

//+------------------------------------------------------------------+
//| DLL imports - using wide strings for MT4 compatibility           |
//+------------------------------------------------------------------+
#import "mt4zmq.dll"
    int    zmq_init_context();
    void   zmq_cleanup_context();
    int    zmq_create_publisher(string address);
    int    zmq_create_subscriber(string address);
    int    zmq_subscribe(int socket_handle, string topic);
    int    zmq_send_message(int socket_handle, string topic, string message);
    int    zmq_receive_message(int socket_handle, string &topic_buffer, int topic_size, 
                               string &message_buffer, int message_size, int timeout_ms);
    void   zmq_close_socket(int socket_handle);
    int    zmq_get_last_error(string &error_buffer, int buffer_size);
    int    zmq_poll_socket(int socket_handle, int timeout_ms);
    string zmq_version();
#import

//+------------------------------------------------------------------+
//| ZMQ Publisher Class                                              |
//+------------------------------------------------------------------+
class CZMQPublisher
{
private:
    int     m_socket;
    bool    m_initialized;
    string  m_address;
    
public:
    CZMQPublisher() : m_socket(-1), m_initialized(false) 
    {
        // Initialize context on first use
        if (!zmq_init_context())
        {
            Print("Failed to initialize ZeroMQ context");
        }
    }
    
    ~CZMQPublisher()
    {
        Close();
    }
    
    bool Create(string address = "tcp://*:5556")
    {
        if (m_initialized)
            return true;
            
        m_address = address;
        m_socket = zmq_create_publisher(address);
        
        if (m_socket > 0)
        {
            m_initialized = true;
            Print("ZMQ Publisher created on ", address);
            return true;
        }
        
        string error = "                                                  ";
        zmq_get_last_error(error, StringLen(error));
        Print("Failed to create publisher: ", error);
        return false;
    }
    
    bool SendTick(string symbol, double bid, double ask)
    {
        if (!m_initialized)
            return false;
            
        double spread = (ask - bid) / Point;
        long volume = Volume[0];
        
        string message = StringFormat(
            "{\"type\":\"tick\",\"symbol\":\"%s\",\"bid\":%.5f,\"ask\":%.5f,\"spread\":%.1f,\"volume\":%d,\"timestamp\":%d}",
            symbol, bid, ask, spread, (int)volume, (int)TimeGMT()
        );
        
        string topic = "tick." + symbol;
        
        if (zmq_send_message(m_socket, topic, message))
        {
            return true;
        }
        
        return false;
    }
    
    bool SendBar(string symbol, ENUM_TIMEFRAMES timeframe, int shift = 1)
    {
        if (!m_initialized)
            return false;
            
        string tf = PeriodToString(timeframe);
        
        string message = StringFormat(
            "{\"type\":\"bar\",\"symbol\":\"%s\",\"timeframe\":\"%s\",\"open\":%.5f,\"high\":%.5f,\"low\":%.5f,\"close\":%.5f,\"volume\":%d,\"time\":%d}",
            symbol, tf,
            iOpen(symbol, timeframe, shift),
            iHigh(symbol, timeframe, shift),
            iLow(symbol, timeframe, shift),
            iClose(symbol, timeframe, shift),
            (int)iVolume(symbol, timeframe, shift),
            (int)iTime(symbol, timeframe, shift)
        );
        
        string topic = StringFormat("bar.%s.%s", symbol, tf);
        
        return zmq_send_message(m_socket, topic, message) > 0;
    }
    
    bool SendMessage(string topic, string message)
    {
        if (!m_initialized)
            return false;
            
        return zmq_send_message(m_socket, topic, message) > 0;
    }
    
    void Close()
    {
        if (m_initialized && m_socket > 0)
        {
            zmq_close_socket(m_socket);
            m_socket = -1;
            m_initialized = false;
            Print("ZMQ Publisher closed");
        }
    }
    
    bool IsInitialized() const { return m_initialized; }
    int  GetSocket() const { return m_socket; }
    
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

//+------------------------------------------------------------------+
//| ZMQ Subscriber Class                                             |
//+------------------------------------------------------------------+
class CZMQSubscriber
{
private:
    int     m_socket;
    bool    m_initialized;
    string  m_address;
    
public:
    CZMQSubscriber() : m_socket(-1), m_initialized(false) 
    {
        zmq_init_context();
    }
    
    ~CZMQSubscriber()
    {
        Close();
    }
    
    bool Create(string address = "tcp://localhost:5556")
    {
        if (m_initialized)
            return true;
            
        m_address = address;
        m_socket = zmq_create_subscriber(address);
        
        if (m_socket > 0)
        {
            m_initialized = true;
            Print("ZMQ Subscriber connected to ", address);
            return true;
        }
        
        string error = "                                                  ";
        zmq_get_last_error(error, StringLen(error));
        Print("Failed to create subscriber: ", error);
        return false;
    }
    
    bool Subscribe(string topic = "")
    {
        if (!m_initialized)
            return false;
            
        return zmq_subscribe(m_socket, topic) > 0;
    }
    
    bool Receive(string &topic, string &message, int timeout_ms = 1000)
    {
        if (!m_initialized)
            return false;
            
        // Prepare buffers
        topic = "                                                                                ";
        message = "                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ";
        
        int result = zmq_receive_message(m_socket, topic, StringLen(topic), 
                                         message, StringLen(message), timeout_ms);
        
        if (result > 0)
        {
            // Trim strings
            topic = StringTrimRight(topic);
            message = StringTrimRight(message);
            return true;
        }
        
        return false;
    }
    
    bool Poll(int timeout_ms = 0)
    {
        if (!m_initialized)
            return false;
            
        return zmq_poll_socket(m_socket, timeout_ms) > 0;
    }
    
    void Close()
    {
        if (m_initialized && m_socket > 0)
        {
            zmq_close_socket(m_socket);
            m_socket = -1;
            m_initialized = false;
            Print("ZMQ Subscriber closed");
        }
    }
    
    bool IsInitialized() const { return m_initialized; }
    int  GetSocket() const { return m_socket; }
};

//+------------------------------------------------------------------+
//| Global functions for easy use                                    |
//+------------------------------------------------------------------+
string GetZMQVersion()
{
    return zmq_version();
}