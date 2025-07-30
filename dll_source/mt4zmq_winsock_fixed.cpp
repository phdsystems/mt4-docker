// MT4ZMQ DLL - Windows Socket Implementation
// This provides ZeroMQ-like functionality using native Windows sockets

#include <winsock2.h>
#include <windows.h>
#include <string>
#include <map>
#include <vector>
#include <cstring>
#include <sstream>
#include <algorithm>

#pragma comment(lib, "ws2_32.lib")

#define MT4ZMQ_API extern "C" __declspec(dllexport)

// Socket wrapper class
class ZMQSocket {
public:
    SOCKET socket;
    std::string type;
    std::string address;
    bool is_bound;
    std::vector<SOCKET> clients;
    
    ZMQSocket() : socket(INVALID_SOCKET), is_bound(false) {}
    
    ~ZMQSocket() {
        Close();
    }
    
    void Close() {
        if (socket != INVALID_SOCKET) {
            closesocket(socket);
            socket = INVALID_SOCKET;
        }
        for (SOCKET client : clients) {
            closesocket(client);
        }
        clients.clear();
    }
};

// Global state
static bool g_initialized = false;
static int g_next_handle = 1;
static std::map<int, ZMQSocket*> g_sockets;
static CRITICAL_SECTION g_cs;
static char g_last_error[256] = {0};

// Thread-safe operations
class CriticalSectionLock {
    CRITICAL_SECTION* cs;
public:
    CriticalSectionLock(CRITICAL_SECTION* pcs) : cs(pcs) {
        EnterCriticalSection(cs);
    }
    ~CriticalSectionLock() {
        LeaveCriticalSection(cs);
    }
};

// Helper functions
void SetLastError(const char* error) {
    strncpy_s(g_last_error, sizeof(g_last_error), error, _TRUNCATE);
}

std::string WideToUtf8(const wchar_t* wide) {
    if (!wide) return "";
    int len = WideCharToMultiByte(CP_UTF8, 0, wide, -1, NULL, 0, NULL, NULL);
    if (len == 0) return "";
    
    std::vector<char> buffer(len);
    WideCharToMultiByte(CP_UTF8, 0, wide, -1, buffer.data(), len, NULL, NULL);
    return std::string(buffer.data());
}

// Parse address like "tcp://*:5556"
bool ParseAddress(const std::string& addr, std::string& host, int& port) {
    if (addr.substr(0, 6) != "tcp://") {
        SetLastError("Invalid address format (must be tcp://...)");
        return false;
    }
    
    std::string hostPort = addr.substr(6);
    size_t colonPos = hostPort.find(':');
    if (colonPos == std::string::npos) {
        SetLastError("Invalid address format (missing port)");
        return false;
    }
    
    host = hostPort.substr(0, colonPos);
    if (host == "*") host = "0.0.0.0";
    
    try {
        port = std::stoi(hostPort.substr(colonPos + 1));
    } catch (...) {
        SetLastError("Invalid port number");
        return false;
    }
    
    return true;
}

// Convert string IP to binary
bool StringToAddr(const std::string& ip, struct in_addr* addr) {
    unsigned long ulAddr = inet_addr(ip.c_str());
    if (ulAddr == INADDR_NONE && ip != "255.255.255.255") {
        return false;
    }
    addr->s_addr = ulAddr;
    return true;
}

// Initialize
MT4ZMQ_API int zmq_init() {
    if (g_initialized) return 0;
    
    WSADATA wsaData;
    int result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        SetLastError("WSAStartup failed");
        return -1;
    }
    
    InitializeCriticalSection(&g_cs);
    g_initialized = true;
    return 0;
}

// Create publisher socket
MT4ZMQ_API int zmq_create_publisher(const wchar_t* address) {
    if (!g_initialized) {
        if (zmq_init() != 0) return -1;
    }
    
    CriticalSectionLock lock(&g_cs);
    
    std::string addr = WideToUtf8(address);
    std::string host;
    int port;
    
    if (!ParseAddress(addr, host, port)) {
        return -1;
    }
    
    // Create TCP socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        SetLastError("Failed to create socket");
        return -1;
    }
    
    // Allow reuse
    int opt = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
    
    // Set non-blocking mode
    u_long mode = 1;
    ioctlsocket(sock, FIONBIO, &mode);
    
    // Bind
    sockaddr_in addr_in;
    addr_in.sin_family = AF_INET;
    addr_in.sin_port = htons(port);
    
    if (!StringToAddr(host, &addr_in.sin_addr)) {
        closesocket(sock);
        SetLastError("Invalid IP address");
        return -1;
    }
    
    if (bind(sock, (sockaddr*)&addr_in, sizeof(addr_in)) == SOCKET_ERROR) {
        closesocket(sock);
        SetLastError("Failed to bind socket");
        return -1;
    }
    
    // Listen
    if (listen(sock, SOMAXCONN) == SOCKET_ERROR) {
        closesocket(sock);
        SetLastError("Failed to listen on socket");
        return -1;
    }
    
    // Create socket wrapper
    ZMQSocket* zmqSock = new ZMQSocket();
    zmqSock->socket = sock;
    zmqSock->type = "PUB";
    zmqSock->address = addr;
    zmqSock->is_bound = true;
    
    int handle = g_next_handle++;
    g_sockets[handle] = zmqSock;
    
    return handle;
}

// Accept new connections (non-blocking)
void AcceptConnections(ZMQSocket* sock) {
    sockaddr_in client_addr;
    int addr_len = sizeof(client_addr);
    
    while (true) {
        SOCKET client = accept(sock->socket, (sockaddr*)&client_addr, &addr_len);
        if (client == INVALID_SOCKET) {
            break; // No more pending connections
        }
        
        // Set client to non-blocking
        u_long mode = 1;
        ioctlsocket(client, FIONBIO, &mode);
        
        sock->clients.push_back(client);
    }
}

// Send message to all connected clients
MT4ZMQ_API int zmq_send_message(int handle, const wchar_t* topic, const wchar_t* message) {
    CriticalSectionLock lock(&g_cs);
    
    auto it = g_sockets.find(handle);
    if (it == g_sockets.end()) {
        SetLastError("Invalid handle");
        return -1;
    }
    
    ZMQSocket* sock = it->second;
    
    // Accept any new connections
    AcceptConnections(sock);
    
    // Prepare message (topic + null + message)
    std::string topicStr = WideToUtf8(topic);
    std::string msgStr = WideToUtf8(message);
    
    std::string fullMsg = topicStr + '\0' + msgStr;
    
    // Send to all clients
    std::vector<SOCKET> disconnected;
    for (SOCKET client : sock->clients) {
        int sent = send(client, fullMsg.c_str(), fullMsg.length(), 0);
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
        auto end_it = std::remove(sock->clients.begin(), sock->clients.end(), disc);
        sock->clients.erase(end_it, sock->clients.end());
    }
    
    return 0;
}

// Create subscriber socket
MT4ZMQ_API int zmq_create_subscriber(const wchar_t* address) {
    if (!g_initialized) {
        if (zmq_init() != 0) return -1;
    }
    
    CriticalSectionLock lock(&g_cs);
    
    std::string addr = WideToUtf8(address);
    std::string host;
    int port;
    
    if (!ParseAddress(addr, host, port)) {
        return -1;
    }
    
    // Replace localhost with 127.0.0.1
    if (host == "localhost") host = "127.0.0.1";
    
    // Create TCP socket
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        SetLastError("Failed to create socket");
        return -1;
    }
    
    // Connect
    sockaddr_in addr_in;
    addr_in.sin_family = AF_INET;
    addr_in.sin_port = htons(port);
    
    if (!StringToAddr(host, &addr_in.sin_addr)) {
        closesocket(sock);
        SetLastError("Invalid IP address");
        return -1;
    }
    
    if (connect(sock, (sockaddr*)&addr_in, sizeof(addr_in)) == SOCKET_ERROR) {
        closesocket(sock);
        SetLastError("Failed to connect");
        return -1;
    }
    
    // Set non-blocking mode
    u_long mode = 1;
    ioctlsocket(sock, FIONBIO, &mode);
    
    // Create socket wrapper
    ZMQSocket* zmqSock = new ZMQSocket();
    zmqSock->socket = sock;
    zmqSock->type = "SUB";
    zmqSock->address = addr;
    zmqSock->is_bound = false;
    
    int handle = g_next_handle++;
    g_sockets[handle] = zmqSock;
    
    return handle;
}

// Subscribe to topic (simplified - accepts all for now)
MT4ZMQ_API int zmq_subscribe(int handle, const wchar_t* topic) {
    // In real ZeroMQ, this would filter messages
    // For simplicity, we accept all messages
    return 0;
}

// Receive message (non-blocking)
MT4ZMQ_API int zmq_recv_message(int handle, wchar_t* topic, int topic_len, 
                                wchar_t* message, int message_len, int timeout_ms) {
    CriticalSectionLock lock(&g_cs);
    
    auto it = g_sockets.find(handle);
    if (it == g_sockets.end()) {
        SetLastError("Invalid handle");
        return -1;
    }
    
    ZMQSocket* sock = it->second;
    if (sock->type != "SUB") {
        SetLastError("Not a subscriber socket");
        return -1;
    }
    
    // Simple receive with timeout
    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(sock->socket, &readfds);
    
    timeval tv;
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    
    int result = select(0, &readfds, NULL, NULL, &tv);
    if (result <= 0) {
        return -1; // Timeout or error
    }
    
    // Receive data
    char buffer[4096];
    int received = recv(sock->socket, buffer, sizeof(buffer), 0);
    if (received <= 0) {
        return -1;
    }
    
    // Parse topic and message (separated by null)
    std::string data(buffer, received);
    size_t nullPos = data.find('\0');
    if (nullPos == std::string::npos) {
        return -1;
    }
    
    std::string topicStr = data.substr(0, nullPos);
    std::string msgStr = data.substr(nullPos + 1);
    
    // Convert to wide strings
    MultiByteToWideChar(CP_UTF8, 0, topicStr.c_str(), -1, topic, topic_len);
    MultiByteToWideChar(CP_UTF8, 0, msgStr.c_str(), -1, message, message_len);
    
    return 0;
}

// Close socket
MT4ZMQ_API int zmq_close(int handle) {
    CriticalSectionLock lock(&g_cs);
    
    auto it = g_sockets.find(handle);
    if (it == g_sockets.end()) {
        return -1;
    }
    
    delete it->second;
    g_sockets.erase(it);
    
    return 0;
}

// Cleanup
MT4ZMQ_API void zmq_term() {
    if (!g_initialized) return;
    
    {
        CriticalSectionLock lock(&g_cs);
        
        // Close all sockets
        for (auto& pair : g_sockets) {
            delete pair.second;
        }
        g_sockets.clear();
    }
    
    DeleteCriticalSection(&g_cs);
    WSACleanup();
    g_initialized = false;
}

// Get version
MT4ZMQ_API void zmq_version(wchar_t* version, int len) {
    const wchar_t* ver = L"4.3.4-winsock";
    wcsncpy_s(version, len, ver, _TRUNCATE);
}

// Get last error
MT4ZMQ_API void zmq_get_last_error(wchar_t* error, int len) {
    MultiByteToWideChar(CP_UTF8, 0, g_last_error, -1, error, len);
}

// DLL entry point
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
        break;
    case DLL_PROCESS_DETACH:
        zmq_term();
        break;
    }
    return TRUE;
}