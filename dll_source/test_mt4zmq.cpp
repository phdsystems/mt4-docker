// Unit tests for MT4ZMQ DLL
#include <windows.h>
#include <iostream>
#include <string>
#include <cassert>

// Function pointers for DLL functions
typedef int (*zmq_init_fn)();
typedef void (*zmq_term_fn)();
typedef int (*zmq_create_publisher_fn)(const wchar_t*);
typedef int (*zmq_create_subscriber_fn)(const wchar_t*);
typedef int (*zmq_send_message_fn)(int, const wchar_t*, const wchar_t*);
typedef int (*zmq_recv_message_fn)(int, wchar_t*, int, wchar_t*, int, int);
typedef int (*zmq_subscribe_fn)(int, const wchar_t*);
typedef int (*zmq_close_fn)(int);
typedef void (*zmq_version_fn)(wchar_t*, int);
typedef void (*zmq_get_last_error_fn)(wchar_t*, int);

// Test framework
class TestFramework {
private:
    HMODULE dll;
    int passed;
    int failed;
    
    // Function pointers
    zmq_init_fn zmq_init;
    zmq_term_fn zmq_term;
    zmq_create_publisher_fn zmq_create_publisher;
    zmq_create_subscriber_fn zmq_create_subscriber;
    zmq_send_message_fn zmq_send_message;
    zmq_recv_message_fn zmq_recv_message;
    zmq_subscribe_fn zmq_subscribe;
    zmq_close_fn zmq_close;
    zmq_version_fn zmq_version;
    zmq_get_last_error_fn zmq_get_last_error;

public:
    TestFramework() : dll(nullptr), passed(0), failed(0) {}
    
    bool LoadDLL(const char* path) {
        dll = LoadLibraryA(path);
        if (!dll) {
            std::cerr << "Failed to load DLL: " << GetLastError() << std::endl;
            return false;
        }
        
        // Load functions
        zmq_init = (zmq_init_fn)GetProcAddress(dll, "zmq_init");
        zmq_term = (zmq_term_fn)GetProcAddress(dll, "zmq_term");
        zmq_create_publisher = (zmq_create_publisher_fn)GetProcAddress(dll, "zmq_create_publisher");
        zmq_create_subscriber = (zmq_create_subscriber_fn)GetProcAddress(dll, "zmq_create_subscriber");
        zmq_send_message = (zmq_send_message_fn)GetProcAddress(dll, "zmq_send_message");
        zmq_recv_message = (zmq_recv_message_fn)GetProcAddress(dll, "zmq_recv_message");
        zmq_subscribe = (zmq_subscribe_fn)GetProcAddress(dll, "zmq_subscribe");
        zmq_close = (zmq_close_fn)GetProcAddress(dll, "zmq_close");
        zmq_version = (zmq_version_fn)GetProcAddress(dll, "zmq_version");
        zmq_get_last_error = (zmq_get_last_error_fn)GetProcAddress(dll, "zmq_get_last_error");
        
        return zmq_init && zmq_term && zmq_create_publisher && zmq_create_subscriber &&
               zmq_send_message && zmq_recv_message && zmq_subscribe && zmq_close &&
               zmq_version && zmq_get_last_error;
    }
    
    ~TestFramework() {
        if (dll) {
            FreeLibrary(dll);
        }
    }
    
    void Test(const std::string& name, bool condition) {
        if (condition) {
            std::cout << "[PASS] " << name << std::endl;
            passed++;
        } else {
            std::cout << "[FAIL] " << name << std::endl;
            failed++;
        }
    }
    
    void TestEqual(const std::string& name, int expected, int actual) {
        Test(name, expected == actual);
        if (expected != actual) {
            std::cout << "       Expected: " << expected << ", Got: " << actual << std::endl;
        }
    }
    
    void TestNotEqual(const std::string& name, int notExpected, int actual) {
        Test(name, notExpected != actual);
        if (notExpected == actual) {
            std::cout << "       Got unexpected value: " << actual << std::endl;
        }
    }
    
    void RunTests() {
        std::cout << "\n=== MT4ZMQ DLL Unit Tests ===" << std::endl;
        
        // Test 1: DLL Functions Loaded
        Test("DLL functions loaded", true);
        
        // Test 2: Initialize
        TestEqual("zmq_init() returns 0", 0, zmq_init());
        
        // Test 3: Double initialize
        TestEqual("zmq_init() when already initialized returns 0", 0, zmq_init());
        
        // Test 4: Version
        wchar_t version[256];
        zmq_version(version, 256);
        Test("zmq_version() returns non-empty string", wcslen(version) > 0);
        std::wcout << L"       Version: " << version << std::endl;
        
        // Test 5: Create publisher with valid address
        int pub = zmq_create_publisher(L"tcp://*:5558");
        Test("zmq_create_publisher() returns valid handle", pub > 0);
        
        // Test 6: Create publisher with invalid address
        int bad_pub = zmq_create_publisher(L"invalid://address");
        TestEqual("zmq_create_publisher() with invalid address returns -1", -1, bad_pub);
        
        // Test 7: Get last error after failure
        wchar_t error[256];
        zmq_get_last_error(error, 256);
        Test("zmq_get_last_error() returns error message", wcslen(error) > 0);
        std::wcout << L"       Error: " << error << std::endl;
        
        // Test 8: Send message with valid handle
        TestEqual("zmq_send_message() with valid handle returns 0", 
                  0, zmq_send_message(pub, L"test.topic", L"test message"));
        
        // Test 9: Send message with invalid handle
        TestEqual("zmq_send_message() with invalid handle returns -1", 
                  -1, zmq_send_message(9999, L"test", L"test"));
        
        // Test 10: Create subscriber
        int sub = zmq_create_subscriber(L"tcp://127.0.0.1:5558");
        Test("zmq_create_subscriber() returns valid handle", sub > 0);
        
        // Test 11: Subscribe
        TestEqual("zmq_subscribe() returns 0", 0, zmq_subscribe(sub, L""));
        
        // Test 12: Close valid handle
        TestEqual("zmq_close() with valid handle returns 0", 0, zmq_close(pub));
        
        // Test 13: Close invalid handle
        TestEqual("zmq_close() with invalid handle returns -1", -1, zmq_close(9999));
        
        // Test 14: Close already closed handle
        TestEqual("zmq_close() with already closed handle returns -1", -1, zmq_close(pub));
        
        // Test 15: Pub/Sub communication
        std::cout << "\n--- Testing Pub/Sub Communication ---" << std::endl;
        
        int pub2 = zmq_create_publisher(L"tcp://*:5559");
        Test("Create publisher for communication test", pub2 > 0);
        
        int sub2 = zmq_create_subscriber(L"tcp://127.0.0.1:5559");
        Test("Create subscriber for communication test", sub2 > 0);
        
        zmq_subscribe(sub2, L"");
        
        // Give time for connection
        Sleep(100); // Windows Sleep function
        
        // Send message
        TestEqual("Send test message", 0, 
                  zmq_send_message(pub2, L"unit.test", L"{\"test\":\"data\"}"));
        
        // Receive message
        wchar_t topic[256], message[1024];
        int recv_result = zmq_recv_message(sub2, topic, 256, message, 1024, 1000);
        TestEqual("Receive test message", 0, recv_result);
        
        if (recv_result == 0) {
            Test("Received topic matches sent topic", wcscmp(topic, L"unit.test") == 0);
            Test("Received message matches sent message", wcscmp(message, L"{\"test\":\"data\"}") == 0);
        }
        
        // Test 16: Receive with timeout
        int timeout_result = zmq_recv_message(sub2, topic, 256, message, 1024, 100);
        TestEqual("Receive with timeout returns -1", -1, timeout_result);
        
        // Cleanup
        zmq_close(pub2);
        zmq_close(sub2);
        zmq_close(sub);
        
        // Test 17: Terminate
        zmq_term();
        Test("zmq_term() completed", true);
        
        // Test 18: Operations after terminate
        int post_term = zmq_create_publisher(L"tcp://*:5560");
        Test("Can create publisher after zmq_term()", post_term > 0);
        if (post_term > 0) {
            zmq_close(post_term);
        }
        
        zmq_term();
    }
    
    void PrintSummary() {
        std::cout << "\n=== Test Summary ===" << std::endl;
        std::cout << "Passed: " << passed << std::endl;
        std::cout << "Failed: " << failed << std::endl;
        std::cout << "Total:  " << (passed + failed) << std::endl;
        
        if (failed == 0) {
            std::cout << "\nAll tests passed! ✓" << std::endl;
        } else {
            std::cout << "\nSome tests failed! ✗" << std::endl;
        }
    }
};

int main(int argc, char* argv[]) {
    const char* dll_path = "mt4zmq.dll";
    if (argc > 1) {
        dll_path = argv[1];
    }
    
    TestFramework tests;
    
    if (!tests.LoadDLL(dll_path)) {
        std::cerr << "Failed to load DLL from: " << dll_path << std::endl;
        return 1;
    }
    
    tests.RunTests();
    tests.PrintSummary();
    
    return 0;
}