#ifndef MT4ZMQ_H
#define MT4ZMQ_H

#ifdef _WIN32
    #ifdef MT4ZMQ_EXPORTS
        #define MT4ZMQ_API __declspec(dllexport)
    #else
        #define MT4ZMQ_API __declspec(dllimport)
    #endif
#else
    #define MT4ZMQ_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Initialize ZeroMQ context
MT4ZMQ_API int zmq_init_context(void);

// Cleanup ZeroMQ context  
MT4ZMQ_API void zmq_cleanup_context(void);

// Create publisher socket
MT4ZMQ_API int zmq_create_publisher(const wchar_t* address);

// Create subscriber socket
MT4ZMQ_API int zmq_create_subscriber(const wchar_t* address);

// Subscribe to topic (empty string = all)
MT4ZMQ_API int zmq_subscribe(int socket_handle, const wchar_t* topic);

// Send message (for publisher)
MT4ZMQ_API int zmq_send_message(int socket_handle, const wchar_t* topic, const wchar_t* message);

// Receive message (for subscriber) - returns message length
MT4ZMQ_API int zmq_receive_message(int socket_handle, wchar_t* topic_buffer, int topic_size, 
                                   wchar_t* message_buffer, int message_size, int timeout_ms);

// Close socket
MT4ZMQ_API void zmq_close_socket(int socket_handle);

// Get last error
MT4ZMQ_API int zmq_get_last_error(wchar_t* error_buffer, int buffer_size);

// Utility functions
MT4ZMQ_API int zmq_poll_socket(int socket_handle, int timeout_ms);
MT4ZMQ_API const wchar_t* zmq_version(void);

#ifdef __cplusplus
}
#endif

#endif // MT4ZMQ_H