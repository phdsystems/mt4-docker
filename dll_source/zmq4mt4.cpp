/**
 * ZeroMQ DLL for MT4
 * This is what we NEED to build for direct MT4->ZeroMQ publishing
 * Compile as 32-bit DLL for MT4 compatibility
 */

#include <windows.h>
#include <zmq.h>
#include <string>
#include <map>

#define EXPORT extern "C" __declspec(dllexport)

// Global ZeroMQ context
void* g_context = nullptr;
std::map<int, void*> g_sockets;
int g_next_socket_id = 1;
std::string g_last_error;

// Initialize DLL
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        g_context = zmq_ctx_new();
        break;
    case DLL_PROCESS_DETACH:
        if (g_context) {
            zmq_ctx_destroy(g_context);
        }
        break;
    }
    return TRUE;
}

// Create a publisher socket and bind to address
EXPORT int ZMQ_CreatePublisher(const char* bind_address)
{
    if (!g_context) {
        g_last_error = "ZeroMQ context not initialized";
        return -1;
    }
    
    // Create PUB socket
    void* socket = zmq_socket(g_context, ZMQ_PUB);
    if (!socket) {
        g_last_error = "Failed to create socket";
        return -1;
    }
    
    // Set socket options
    int hwm = 10000;
    zmq_setsockopt(socket, ZMQ_SNDHWM, &hwm, sizeof(hwm));
    
    // Bind to address
    if (zmq_bind(socket, bind_address) != 0) {
        g_last_error = "Failed to bind to " + std::string(bind_address);
        zmq_close(socket);
        return -1;
    }
    
    // Store socket and return ID
    int socket_id = g_next_socket_id++;
    g_sockets[socket_id] = socket;
    
    return socket_id;
}

// Publish a message with topic
EXPORT int ZMQ_PublishMessage(int socket_id, const char* topic, const char* message)
{
    auto it = g_sockets.find(socket_id);
    if (it == g_sockets.end()) {
        g_last_error = "Invalid socket ID";
        return -1;
    }
    
    void* socket = it->second;
    
    // Send topic
    if (zmq_send(socket, topic, strlen(topic), ZMQ_SNDMORE) == -1) {
        g_last_error = "Failed to send topic";
        return -1;
    }
    
    // Send message
    if (zmq_send(socket, message, strlen(message), 0) == -1) {
        g_last_error = "Failed to send message";
        return -1;
    }
    
    return 1; // Success
}

// Close publisher socket
EXPORT void ZMQ_ClosePublisher(int socket_id)
{
    auto it = g_sockets.find(socket_id);
    if (it != g_sockets.end()) {
        zmq_close(it->second);
        g_sockets.erase(it);
    }
}

// Get last error message
EXPORT const char* ZMQ_GetLastError()
{
    return g_last_error.c_str();
}

/**
 * To compile this DLL:
 * 
 * 1. Install ZeroMQ development files
 * 2. Use Visual Studio or MinGW
 * 3. Compile as 32-bit DLL (important for MT4!)
 * 
 * Example with MinGW:
 * g++ -m32 -shared -o zmq4mt4.dll zmq4mt4.cpp -lzmq -lws2_32
 * 
 * Example with Visual Studio:
 * - Create Win32 DLL project
 * - Add ZeroMQ includes and libs
 * - Build Release x86
 */