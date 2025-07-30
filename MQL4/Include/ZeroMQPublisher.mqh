//+------------------------------------------------------------------+
//|                                             ZeroMQPublisher.mqh  |
//|                                   ZeroMQ Publisher for MT4       |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property version   "1.00"
#property strict

// Import DLL functions
#import "mt4zmq.dll"
    int  zmq_init(string addresses);
    int  zmq_publish_tick(string symbol, double bid, double ask, double spread, int volume);
    int  zmq_publish_bar(string symbol, int timeframe, double open, double high, double low, double close, long volume, datetime time);
    void zmq_shutdown();
    int  zmq_get_stats(int &messages_sent, int &bytes_sent);
#import

//+------------------------------------------------------------------+
//| ZeroMQ Publisher Class                                           |
//+------------------------------------------------------------------+
class CZeroMQPublisher
{
private:
    bool        m_initialized;
    int         m_messages_sent;
    string      m_addresses;
    
public:
    //+------------------------------------------------------------------+
    //| Constructor                                                       |
    //+------------------------------------------------------------------+
    CZeroMQPublisher() : m_initialized(false), m_messages_sent(0)
    {
    }
    
    //+------------------------------------------------------------------+
    //| Destructor                                                        |
    //+------------------------------------------------------------------+
    ~CZeroMQPublisher()
    {
        if(m_initialized)
            Shutdown();
    }
    
    //+------------------------------------------------------------------+
    //| Initialize ZeroMQ publisher                                       |
    //+------------------------------------------------------------------+
    bool Initialize(string addresses = "tcp://127.0.0.1:5555")
    {
        if(m_initialized)
            return true;
            
        m_addresses = addresses;
        
        int result = zmq_init(addresses);
        if(result > 0)
        {
            m_initialized = true;
            Print("ZeroMQ Publisher initialized on: ", addresses);
            return true;
        }
        
        Print("Failed to initialize ZeroMQ Publisher");
        return false;
    }
    
    //+------------------------------------------------------------------+
    //| Shutdown publisher                                                |
    //+------------------------------------------------------------------+
    void Shutdown()
    {
        if(!m_initialized)
            return;
            
        zmq_shutdown();
        m_initialized = false;
        Print("ZeroMQ Publisher shutdown. Total messages sent: ", m_messages_sent);
    }
    
    //+------------------------------------------------------------------+
    //| Publish tick data                                                |
    //+------------------------------------------------------------------+
    bool PublishTick(string symbol, double bid, double ask)
    {
        if(!m_initialized)
            return false;
            
        double spread = (ask - bid) / Point;
        int volume = (int)MarketInfo(symbol, MODE_VOLUME);
        
        int result = zmq_publish_tick(symbol, bid, ask, spread, volume);
        if(result > 0)
        {
            m_messages_sent++;
            return true;
        }
        
        return false;
    }
    
    //+------------------------------------------------------------------+
    //| Publish bar data                                                 |
    //+------------------------------------------------------------------+
    bool PublishBar(string symbol, ENUM_TIMEFRAMES timeframe, int shift = 1)
    {
        if(!m_initialized)
            return false;
            
        double open = iOpen(symbol, timeframe, shift);
        double high = iHigh(symbol, timeframe, shift);
        double low = iLow(symbol, timeframe, shift);
        double close = iClose(symbol, timeframe, shift);
        long volume = iVolume(symbol, timeframe, shift);
        datetime time = iTime(symbol, timeframe, shift);
        
        int result = zmq_publish_bar(symbol, timeframe, open, high, low, close, volume, time);
        if(result > 0)
        {
            m_messages_sent++;
            return true;
        }
        
        return false;
    }
    
    //+------------------------------------------------------------------+
    //| Get publisher statistics                                          |
    //+------------------------------------------------------------------+
    void GetStats(int &messages_sent, int &bytes_sent)
    {
        if(!m_initialized)
        {
            messages_sent = 0;
            bytes_sent = 0;
            return;
        }
        
        zmq_get_stats(messages_sent, bytes_sent);
    }
    
    //+------------------------------------------------------------------+
    //| Check if initialized                                             |
    //+------------------------------------------------------------------+
    bool IsInitialized() const { return m_initialized; }
    
    //+------------------------------------------------------------------+
    //| Get total messages sent                                          |
    //+------------------------------------------------------------------+
    int GetMessagesSent() const { return m_messages_sent; }
};

//+------------------------------------------------------------------+
//| Global instance (optional)                                        |
//+------------------------------------------------------------------+
CZeroMQPublisher g_ZMQPublisher;