// MT4ZMQ DLL Version 2 - Improved OOP Design
// Eliminates global state and uses better encapsulation

#include <winsock2.h>
#include <windows.h>
#include <string>
#include <memory>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <atomic>

#pragma comment(lib, "ws2_32.lib")

// Export macro
#define MT4ZMQ_API extern "C" __declspec(dllexport)

// Forward declarations
class ISocket;
class ISocketFactory;
class SocketManager;
class MessageFormatter;

// Interfaces
class ISocket {
public:
    virtual ~ISocket() = default;
    virtual bool Send(const std::string& topic, const std::string& message) = 0;
    virtual bool Receive(std::string& topic, std::string& message, int timeout_ms) = 0;
    virtual void Close() = 0;
    virtual bool IsConnected() const = 0;
};

class ISocketFactory {
public:
    virtual ~ISocketFactory() = default;
    virtual std::unique_ptr<ISocket> CreatePublisher(const std::string& address) = 0;
    virtual std::unique_ptr<ISocket> CreateSubscriber(const std::string& address) = 0;
};

// Base Socket Implementation
class BaseSocket : public ISocket {
protected:
    SOCKET socket_;
    std::string address_;
    std::atomic<bool> connected_;
    mutable std::mutex mutex_;

public:
    BaseSocket() : socket_(INVALID_SOCKET), connected_(false) {}
    
    virtual ~BaseSocket() {
        Close();
    }
    
    void Close() override {
        std::lock_guard<std::mutex> lock(mutex_);
        if (socket_ != INVALID_SOCKET) {
            closesocket(socket_);
            socket_ = INVALID_SOCKET;
            connected_ = false;
        }
    }
    
    bool IsConnected() const override {
        return connected_;
    }

protected:
    bool SetNonBlocking() {
        u_long mode = 1;
        return ioctlsocket(socket_, FIONBIO, &mode) == 0;
    }
    
    bool SetSocketOption(int level, int optname, const char* optval, int optlen) {
        return setsockopt(socket_, level, optname, optval, optlen) == 0;
    }
};

// Publisher Socket Implementation
class PublisherSocket : public BaseSocket {
private:
    std::vector<SOCKET> clients_;
    
public:
    bool Bind(const std::string& address) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        socket_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (socket_ == INVALID_SOCKET) {
            return false;
        }
        
        // Parse address (simplified for example)
        int port = 5556; // Extract from address
        
        sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(port);
        
        // Allow reuse
        int opt = 1;
        SetSocketOption(SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
        SetNonBlocking();
        
        if (bind(socket_, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
            Close();
            return false;
        }
        
        if (listen(socket_, SOMAXCONN) == SOCKET_ERROR) {
            Close();
            return false;
        }
        
        address_ = address;
        connected_ = true;
        return true;
    }
    
    bool Send(const std::string& topic, const std::string& message) override {
        if (!connected_) return false;
        
        std::lock_guard<std::mutex> lock(mutex_);
        
        // Accept new connections
        AcceptConnections();
        
        // Format message
        std::string fullMessage = topic + '\0' + message;
        
        // Send to all clients
        std::vector<SOCKET> disconnected;
        for (SOCKET client : clients_) {
            int sent = send(client, fullMessage.c_str(), fullMessage.length(), 0);
            if (sent == SOCKET_ERROR) {
                int error = WSAGetLastError();
                if (error != WSAEWOULDBLOCK) {
                    disconnected.push_back(client);
                }
            }
        }
        
        // Remove disconnected clients
        for (SOCKET disc : disconnected) {
            closesocket(disc);
            clients_.erase(
                std::remove(clients_.begin(), clients_.end(), disc),
                clients_.end()
            );
        }
        
        return true;
    }
    
    bool Receive(std::string& topic, std::string& message, int timeout_ms) override {
        // Publishers don't receive
        return false;
    }

private:
    void AcceptConnections() {
        sockaddr_in client_addr;
        int addr_len = sizeof(client_addr);
        
        while (true) {
            SOCKET client = accept(socket_, (sockaddr*)&client_addr, &addr_len);
            if (client == INVALID_SOCKET) {
                break;
            }
            
            u_long mode = 1;
            ioctlsocket(client, FIONBIO, &mode);
            clients_.push_back(client);
        }
    }
};

// Subscriber Socket Implementation
class SubscriberSocket : public BaseSocket {
public:
    bool Connect(const std::string& address) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        socket_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (socket_ == INVALID_SOCKET) {
            return false;
        }
        
        // Parse address (simplified)
        std::string host = "127.0.0.1";
        int port = 5556;
        
        sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = inet_addr(host.c_str());
        addr.sin_port = htons(port);
        
        if (connect(socket_, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
            Close();
            return false;
        }
        
        SetNonBlocking();
        address_ = address;
        connected_ = true;
        return true;
    }
    
    bool Send(const std::string& topic, const std::string& message) override {
        // Subscribers don't send
        return false;
    }
    
    bool Receive(std::string& topic, std::string& message, int timeout_ms) override {
        if (!connected_) return false;
        
        std::lock_guard<std::mutex> lock(mutex_);
        
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(socket_, &readfds);
        
        timeval tv;
        tv.tv_sec = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        
        int result = select(0, &readfds, NULL, NULL, &tv);
        if (result <= 0) {
            return false;
        }
        
        char buffer[4096];
        int received = recv(socket_, buffer, sizeof(buffer), 0);
        if (received <= 0) {
            return false;
        }
        
        // Parse topic and message
        std::string data(buffer, received);
        size_t nullPos = data.find('\0');
        if (nullPos != std::string::npos) {
            topic = data.substr(0, nullPos);
            message = data.substr(nullPos + 1);
            return true;
        }
        
        return false;
    }
};

// Socket Factory Implementation
class WinsockSocketFactory : public ISocketFactory {
public:
    std::unique_ptr<ISocket> CreatePublisher(const std::string& address) override {
        auto socket = std::make_unique<PublisherSocket>();
        if (socket->Bind(address)) {
            return socket;
        }
        return nullptr;
    }
    
    std::unique_ptr<ISocket> CreateSubscriber(const std::string& address) override {
        auto socket = std::make_unique<SubscriberSocket>();
        if (socket->Connect(address)) {
            return socket;
        }
        return nullptr;
    }
};

// Singleton Socket Manager (Thread-Safe)
class SocketManager {
private:
    static std::unique_ptr<SocketManager> instance_;
    static std::mutex mutex_;
    
    std::unordered_map<int, std::unique_ptr<ISocket>> sockets_;
    std::unique_ptr<ISocketFactory> factory_;
    std::atomic<int> next_handle_;
    std::mutex sockets_mutex_;
    std::atomic<bool> initialized_;
    std::string last_error_;
    
    SocketManager() 
        : factory_(std::make_unique<WinsockSocketFactory>())
        , next_handle_(1)
        , initialized_(false) {}

public:
    static SocketManager& GetInstance() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (!instance_) {
            instance_.reset(new SocketManager());
        }
        return *instance_;
    }
    
    bool Initialize() {
        if (initialized_) return true;
        
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            last_error_ = "WSAStartup failed";
            return false;
        }
        
        initialized_ = true;
        return true;
    }
    
    void Shutdown() {
        if (!initialized_) return;
        
        {
            std::lock_guard<std::mutex> lock(sockets_mutex_);
            sockets_.clear();
        }
        
        WSACleanup();
        initialized_ = false;
    }
    
    int CreatePublisher(const std::string& address) {
        if (!initialized_) return -1;
        
        auto socket = factory_->CreatePublisher(address);
        if (!socket) {
            last_error_ = "Failed to create publisher";
            return -1;
        }
        
        std::lock_guard<std::mutex> lock(sockets_mutex_);
        int handle = next_handle_++;
        sockets_[handle] = std::move(socket);
        return handle;
    }
    
    int CreateSubscriber(const std::string& address) {
        if (!initialized_) return -1;
        
        auto socket = factory_->CreateSubscriber(address);
        if (!socket) {
            last_error_ = "Failed to create subscriber";
            return -1;
        }
        
        std::lock_guard<std::mutex> lock(sockets_mutex_);
        int handle = next_handle_++;
        sockets_[handle] = std::move(socket);
        return handle;
    }
    
    bool SendMessage(int handle, const std::string& topic, const std::string& message) {
        std::lock_guard<std::mutex> lock(sockets_mutex_);
        
        auto it = sockets_.find(handle);
        if (it == sockets_.end()) {
            last_error_ = "Invalid handle";
            return false;
        }
        
        return it->second->Send(topic, message);
    }
    
    bool ReceiveMessage(int handle, std::string& topic, std::string& message, int timeout_ms) {
        std::lock_guard<std::mutex> lock(sockets_mutex_);
        
        auto it = sockets_.find(handle);
        if (it == sockets_.end()) {
            last_error_ = "Invalid handle";
            return false;
        }
        
        return it->second->Receive(topic, message, timeout_ms);
    }
    
    void CloseSocket(int handle) {
        std::lock_guard<std::mutex> lock(sockets_mutex_);
        sockets_.erase(handle);
    }
    
    const std::string& GetLastError() const {
        return last_error_;
    }
};

// Static member initialization
std::unique_ptr<SocketManager> SocketManager::instance_;
std::mutex SocketManager::mutex_;

// String conversion utilities
class StringConverter {
public:
    static std::string WideToUtf8(const wchar_t* wide) {
        if (!wide) return "";
        int len = WideCharToMultiByte(CP_UTF8, 0, wide, -1, NULL, 0, NULL, NULL);
        if (len == 0) return "";
        
        std::vector<char> buffer(len);
        WideCharToMultiByte(CP_UTF8, 0, wide, -1, buffer.data(), len, NULL, NULL);
        return std::string(buffer.data());
    }
    
    static void Utf8ToWide(const std::string& utf8, wchar_t* wide, int wide_len) {
        MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, wide, wide_len);
    }
};

// C API Implementation (MT4 Compatible)
MT4ZMQ_API int zmq_init() {
    return SocketManager::GetInstance().Initialize() ? 0 : -1;
}

MT4ZMQ_API void zmq_term() {
    SocketManager::GetInstance().Shutdown();
}

MT4ZMQ_API int zmq_create_publisher(const wchar_t* address) {
    std::string addr = StringConverter::WideToUtf8(address);
    return SocketManager::GetInstance().CreatePublisher(addr);
}

MT4ZMQ_API int zmq_create_subscriber(const wchar_t* address) {
    std::string addr = StringConverter::WideToUtf8(address);
    return SocketManager::GetInstance().CreateSubscriber(addr);
}

MT4ZMQ_API int zmq_send_message(int handle, const wchar_t* topic, const wchar_t* message) {
    std::string topic_str = StringConverter::WideToUtf8(topic);
    std::string msg_str = StringConverter::WideToUtf8(message);
    return SocketManager::GetInstance().SendMessage(handle, topic_str, msg_str) ? 0 : -1;
}

MT4ZMQ_API int zmq_recv_message(int handle, wchar_t* topic, int topic_len, 
                                wchar_t* message, int message_len, int timeout_ms) {
    std::string topic_str, msg_str;
    
    if (SocketManager::GetInstance().ReceiveMessage(handle, topic_str, msg_str, timeout_ms)) {
        StringConverter::Utf8ToWide(topic_str, topic, topic_len);
        StringConverter::Utf8ToWide(msg_str, message, message_len);
        return 0;
    }
    
    return -1;
}

MT4ZMQ_API int zmq_close(int handle) {
    SocketManager::GetInstance().CloseSocket(handle);
    return 0;
}

MT4ZMQ_API void zmq_get_last_error(wchar_t* error, int len) {
    std::string err = SocketManager::GetInstance().GetLastError();
    StringConverter::Utf8ToWide(err, error, len);
}

// DLL Entry Point
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
        break;
    case DLL_PROCESS_DETACH:
        zmq_term();
        break;
    }
    return TRUE;
}