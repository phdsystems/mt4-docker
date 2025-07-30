#define MT4ZMQ_EXPORTS
#include "mt4zmq.h"
#include <zmq.h>
#include <windows.h>
#include <string>
#include <map>
#include <mutex>
#include <codecvt>
#include <locale>

// Global state
static void* g_context = nullptr;
static std::map<int, void*> g_sockets;
static int g_next_handle = 1;
static std::wstring g_last_error;
static std::mutex g_mutex;

// Utility to convert wide string to UTF-8
std::string WideToUTF8(const std::wstring& wide) {
    if (wide.empty()) return "";
    int size = WideCharToMultiByte(CP_UTF8, 0, wide.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string result(size - 1, '\0');
    WideCharToMultiByte(CP_UTF8, 0, wide.c_str(), -1, &result[0], size, nullptr, nullptr);
    return result;
}

// Utility to convert UTF-8 to wide string
std::wstring UTF8ToWide(const std::string& utf8) {
    if (utf8.empty()) return L"";
    int size = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, nullptr, 0);
    std::wstring result(size - 1, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, &result[0], size);
    return result;
}

// DLL entry point
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
        case DLL_PROCESS_ATTACH:
            // Initialize when DLL is loaded
            break;
        case DLL_PROCESS_DETACH:
            // Cleanup when DLL is unloaded
            if (g_context) {
                zmq_ctx_destroy(g_context);
                g_context = nullptr;
            }
            break;
    }
    return TRUE;
}

// Initialize ZeroMQ context
MT4ZMQ_API int zmq_init_context(void) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    if (g_context) {
        return 1; // Already initialized
    }
    
    g_context = zmq_ctx_new();
    if (!g_context) {
        g_last_error = L"Failed to create ZeroMQ context";
        return 0;
    }
    
    // Set context options
    zmq_ctx_set(g_context, ZMQ_IO_THREADS, 2);
    
    return 1;
}

// Cleanup ZeroMQ context
MT4ZMQ_API void zmq_cleanup_context(void) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    // Close all sockets
    for (auto& pair : g_sockets) {
        zmq_close(pair.second);
    }
    g_sockets.clear();
    
    // Destroy context
    if (g_context) {
        zmq_ctx_destroy(g_context);
        g_context = nullptr;
    }
}

// Create publisher socket
MT4ZMQ_API int zmq_create_publisher(const wchar_t* address) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    if (!g_context) {
        g_last_error = L"Context not initialized";
        return -1;
    }
    
    void* socket = zmq_socket(g_context, ZMQ_PUB);
    if (!socket) {
        g_last_error = L"Failed to create publisher socket";
        return -1;
    }
    
    // Set socket options
    int hwm = 10000;
    zmq_setsockopt(socket, ZMQ_SNDHWM, &hwm, sizeof(hwm));
    
    int linger = 1000; // 1 second linger on close
    zmq_setsockopt(socket, ZMQ_LINGER, &linger, sizeof(linger));
    
    // Bind to address
    std::string addr_utf8 = WideToUTF8(address);
    if (zmq_bind(socket, addr_utf8.c_str()) != 0) {
        g_last_error = L"Failed to bind to address: " + std::wstring(address);
        zmq_close(socket);
        return -1;
    }
    
    // Store socket
    int handle = g_next_handle++;
    g_sockets[handle] = socket;
    
    return handle;
}

// Create subscriber socket
MT4ZMQ_API int zmq_create_subscriber(const wchar_t* address) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    if (!g_context) {
        g_last_error = L"Context not initialized";
        return -1;
    }
    
    void* socket = zmq_socket(g_context, ZMQ_SUB);
    if (!socket) {
        g_last_error = L"Failed to create subscriber socket";
        return -1;
    }
    
    // Set socket options
    int hwm = 10000;
    zmq_setsockopt(socket, ZMQ_RCVHWM, &hwm, sizeof(hwm));
    
    // Connect to address
    std::string addr_utf8 = WideToUTF8(address);
    if (zmq_connect(socket, addr_utf8.c_str()) != 0) {
        g_last_error = L"Failed to connect to address: " + std::wstring(address);
        zmq_close(socket);
        return -1;
    }
    
    // Store socket
    int handle = g_next_handle++;
    g_sockets[handle] = socket;
    
    return handle;
}

// Subscribe to topic
MT4ZMQ_API int zmq_subscribe(int socket_handle, const wchar_t* topic) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    auto it = g_sockets.find(socket_handle);
    if (it == g_sockets.end()) {
        g_last_error = L"Invalid socket handle";
        return 0;
    }
    
    std::string topic_utf8 = WideToUTF8(topic ? topic : L"");
    if (zmq_setsockopt(it->second, ZMQ_SUBSCRIBE, topic_utf8.c_str(), topic_utf8.length()) != 0) {
        g_last_error = L"Failed to subscribe to topic";
        return 0;
    }
    
    return 1;
}

// Send message
MT4ZMQ_API int zmq_send_message(int socket_handle, const wchar_t* topic, const wchar_t* message) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    auto it = g_sockets.find(socket_handle);
    if (it == g_sockets.end()) {
        g_last_error = L"Invalid socket handle";
        return 0;
    }
    
    void* socket = it->second;
    
    // Convert to UTF-8
    std::string topic_utf8 = WideToUTF8(topic ? topic : L"");
    std::string message_utf8 = WideToUTF8(message ? message : L"");
    
    // Send topic (if not empty)
    if (!topic_utf8.empty()) {
        if (zmq_send(socket, topic_utf8.c_str(), topic_utf8.length(), ZMQ_SNDMORE) == -1) {
            g_last_error = L"Failed to send topic";
            return 0;
        }
    }
    
    // Send message
    if (zmq_send(socket, message_utf8.c_str(), message_utf8.length(), 0) == -1) {
        g_last_error = L"Failed to send message";
        return 0;
    }
    
    return 1;
}

// Receive message
MT4ZMQ_API int zmq_receive_message(int socket_handle, wchar_t* topic_buffer, int topic_size,
                                   wchar_t* message_buffer, int message_size, int timeout_ms) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    auto it = g_sockets.find(socket_handle);
    if (it == g_sockets.end()) {
        g_last_error = L"Invalid socket handle";
        return -1;
    }
    
    void* socket = it->second;
    
    // Set receive timeout
    zmq_setsockopt(socket, ZMQ_RCVTIMEO, &timeout_ms, sizeof(timeout_ms));
    
    // Receive topic
    zmq_msg_t topic_msg;
    zmq_msg_init(&topic_msg);
    
    if (zmq_msg_recv(&topic_msg, socket, 0) == -1) {
        zmq_msg_close(&topic_msg);
        if (zmq_errno() == EAGAIN) {
            return 0; // Timeout
        }
        g_last_error = L"Failed to receive topic";
        return -1;
    }
    
    // Copy topic to buffer
    std::string topic_str((char*)zmq_msg_data(&topic_msg), zmq_msg_size(&topic_msg));
    std::wstring topic_wide = UTF8ToWide(topic_str);
    
    if (topic_buffer && topic_size > 0) {
        wcsncpy_s(topic_buffer, topic_size, topic_wide.c_str(), _TRUNCATE);
    }
    
    int more = 0;
    size_t more_size = sizeof(more);
    zmq_getsockopt(socket, ZMQ_RCVMORE, &more, &more_size);
    zmq_msg_close(&topic_msg);
    
    // Receive message if multipart
    if (more) {
        zmq_msg_t msg;
        zmq_msg_init(&msg);
        
        if (zmq_msg_recv(&msg, socket, 0) == -1) {
            zmq_msg_close(&msg);
            g_last_error = L"Failed to receive message";
            return -1;
        }
        
        // Copy message to buffer
        std::string msg_str((char*)zmq_msg_data(&msg), zmq_msg_size(&msg));
        std::wstring msg_wide = UTF8ToWide(msg_str);
        
        if (message_buffer && message_size > 0) {
            wcsncpy_s(message_buffer, message_size, msg_wide.c_str(), _TRUNCATE);
        }
        
        int msg_len = (int)msg_wide.length();
        zmq_msg_close(&msg);
        
        return msg_len;
    } else {
        // Single part message - topic is the message
        if (message_buffer && message_size > 0) {
            wcsncpy_s(message_buffer, message_size, topic_wide.c_str(), _TRUNCATE);
        }
        if (topic_buffer && topic_size > 0) {
            topic_buffer[0] = L'\0';
        }
        return (int)topic_wide.length();
    }
}

// Close socket
MT4ZMQ_API void zmq_close_socket(int socket_handle) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    auto it = g_sockets.find(socket_handle);
    if (it != g_sockets.end()) {
        zmq_close(it->second);
        g_sockets.erase(it);
    }
}

// Get last error
MT4ZMQ_API int zmq_get_last_error(wchar_t* error_buffer, int buffer_size) {
    if (error_buffer && buffer_size > 0) {
        wcsncpy_s(error_buffer, buffer_size, g_last_error.c_str(), _TRUNCATE);
    }
    return (int)g_last_error.length();
}

// Poll socket
MT4ZMQ_API int zmq_poll_socket(int socket_handle, int timeout_ms) {
    std::lock_guard<std::mutex> lock(g_mutex);
    
    auto it = g_sockets.find(socket_handle);
    if (it == g_sockets.end()) {
        return -1;
    }
    
    zmq_pollitem_t items[1];
    items[0].socket = it->second;
    items[0].fd = 0;
    items[0].events = ZMQ_POLLIN;
    items[0].revents = 0;
    
    int result = zmq_poll(items, 1, timeout_ms);
    
    if (result > 0 && (items[0].revents & ZMQ_POLLIN)) {
        return 1; // Data available
    }
    
    return 0; // No data or timeout
}

// Get version
MT4ZMQ_API const wchar_t* zmq_version(void) {
    static std::wstring version_str;
    int major, minor, patch;
    zmq_version(&major, &minor, &patch);
    version_str = L"ZeroMQ " + std::to_wstring(major) + L"." + 
                  std::to_wstring(minor) + L"." + std::to_wstring(patch);
    return version_str.c_str();
}