// Simplified MT4ZMQ DLL - Mock implementation for testing
#include <windows.h>
#include <winsock2.h>
#include <string>
#include <cstring>

#pragma comment(lib, "ws2_32.lib")

#define MT4ZMQ_API extern "C" __declspec(dllexport)

// Mock socket storage
static SOCKET g_socket = INVALID_SOCKET;
static bool g_initialized = false;

// Initialize Winsock
MT4ZMQ_API int zmq_init() {
    if (g_initialized) return 0;
    
    WSADATA wsaData;
    int result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        return -1;
    }
    
    g_initialized = true;
    return 0;
}

// Create a mock publisher socket
MT4ZMQ_API int zmq_create_publisher(const wchar_t* address) {
    if (!g_initialized) {
        if (zmq_init() != 0) return -1;
    }
    
    // Create TCP socket
    g_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (g_socket == INVALID_SOCKET) {
        return -1;
    }
    
    // For now, just return success
    // In real implementation, would bind to address
    return 1; // Return mock handle
}

// Send message
MT4ZMQ_API int zmq_send_message(int handle, const wchar_t* topic, const wchar_t* message) {
    if (g_socket == INVALID_SOCKET) return -1;
    
    // Convert wide strings to narrow
    int topic_len = WideCharToMultiByte(CP_UTF8, 0, topic, -1, NULL, 0, NULL, NULL);
    int msg_len = WideCharToMultiByte(CP_UTF8, 0, message, -1, NULL, 0, NULL, NULL);
    
    // For mock, just return success
    return 0;
}

// Close socket
MT4ZMQ_API int zmq_close(int handle) {
    if (g_socket != INVALID_SOCKET) {
        closesocket(g_socket);
        g_socket = INVALID_SOCKET;
    }
    return 0;
}

// Cleanup
MT4ZMQ_API void zmq_term() {
    if (g_socket != INVALID_SOCKET) {
        closesocket(g_socket);
        g_socket = INVALID_SOCKET;
    }
    
    if (g_initialized) {
        WSACleanup();
        g_initialized = false;
    }
}

// Version info
MT4ZMQ_API void zmq_version(wchar_t* version, int len) {
    const wchar_t* ver = L"4.3.4-mock";
    wcsncpy(version, ver, len);
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
