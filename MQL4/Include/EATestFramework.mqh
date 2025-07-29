//+------------------------------------------------------------------+
//|                                              EATestFramework.mqh  |
//|                                       EA Testing Framework Include |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "MT4 Docker"
#property link      "https://github.com/mt4-docker"
#property strict

// Test result structure
struct TestResult {
    string testName;
    bool passed;
    string message;
    datetime timestamp;
    double executionTime;
};

// Test suite class
class CTestSuite {
private:
    TestResult m_results[];
    int m_totalTests;
    int m_passedTests;
    int m_failedTests;
    string m_suiteName;
    int m_fileHandle;
    
public:
    // Constructor
    CTestSuite(string suiteName) {
        m_suiteName = suiteName;
        m_totalTests = 0;
        m_passedTests = 0;
        m_failedTests = 0;
        m_fileHandle = INVALID_HANDLE;
        ArrayResize(m_results, 0);
    }
    
    // Destructor
    ~CTestSuite() {
        if (m_fileHandle != INVALID_HANDLE) {
            FileClose(m_fileHandle);
        }
    }
    
    // Assert functions
    void AssertTrue(string testName, bool condition, string message = "") {
        RecordTest(testName, condition, message);
    }
    
    void AssertFalse(string testName, bool condition, string message = "") {
        RecordTest(testName, !condition, message);
    }
    
    void AssertEquals(string testName, double expected, double actual, double tolerance = 0.00001) {
        bool passed = MathAbs(expected - actual) <= tolerance;
        string msg = StringFormat("Expected: %.5f, Actual: %.5f", expected, actual);
        RecordTest(testName, passed, msg);
    }
    
    void AssertNotEquals(string testName, double expected, double actual, double tolerance = 0.00001) {
        bool passed = MathAbs(expected - actual) > tolerance;
        string msg = StringFormat("Should not equal: %.5f", expected);
        RecordTest(testName, passed, msg);
    }
    
    void AssertGreater(string testName, double value1, double value2) {
        bool passed = value1 > value2;
        string msg = StringFormat("%.5f should be > %.5f", value1, value2);
        RecordTest(testName, passed, msg);
    }
    
    void AssertLess(string testName, double value1, double value2) {
        bool passed = value1 < value2;
        string msg = StringFormat("%.5f should be < %.5f", value1, value2);
        RecordTest(testName, passed, msg);
    }
    
    void AssertStringEquals(string testName, string expected, string actual) {
        bool passed = (expected == actual);
        string msg = "Expected: '" + expected + "', Actual: '" + actual + "'";
        RecordTest(testName, passed, msg);
    }
    
    void AssertNull(string testName, int handle) {
        bool passed = (handle == INVALID_HANDLE || handle == 0);
        RecordTest(testName, passed, "Should be null/invalid");
    }
    
    void AssertNotNull(string testName, int handle) {
        bool passed = (handle != INVALID_HANDLE && handle != 0);
        RecordTest(testName, passed, "Should not be null/invalid");
    }
    
    // Get test statistics
    int GetTotalTests() { return m_totalTests; }
    int GetPassedTests() { return m_passedTests; }
    int GetFailedTests() { return m_failedTests; }
    double GetSuccessRate() { 
        return m_totalTests > 0 ? (m_passedTests * 100.0 / m_totalTests) : 0; 
    }
    
    // Generate report
    void GenerateReport(string filename = "") {
        if (filename == "") {
            filename = m_suiteName + "_report.txt";
        }
        
        m_fileHandle = FileOpen(filename, FILE_WRITE|FILE_TXT);
        if (m_fileHandle == INVALID_HANDLE) {
            Print("Cannot create report file: ", filename);
            return;
        }
        
        // Write header
        FileWriteString(m_fileHandle, "=== Test Suite: " + m_suiteName + " ===\n");
        FileWriteString(m_fileHandle, "Date: " + TimeToString(TimeCurrent()) + "\n");
        FileWriteString(m_fileHandle, "Total Tests: " + IntegerToString(m_totalTests) + "\n");
        FileWriteString(m_fileHandle, "Passed: " + IntegerToString(m_passedTests) + "\n");
        FileWriteString(m_fileHandle, "Failed: " + IntegerToString(m_failedTests) + "\n");
        FileWriteString(m_fileHandle, "Success Rate: " + DoubleToString(GetSuccessRate(), 2) + "%\n");
        FileWriteString(m_fileHandle, "\n--- Test Results ---\n");
        
        // Write individual results
        for (int i = 0; i < ArraySize(m_results); i++) {
            string status = m_results[i].passed ? "[PASS]" : "[FAIL]";
            FileWriteString(m_fileHandle, 
                status + " " + m_results[i].testName + 
                " - " + m_results[i].message + "\n"
            );
        }
        
        FileClose(m_fileHandle);
        m_fileHandle = INVALID_HANDLE;
        
        Print("Test report generated: ", filename);
    }
    
    // Print summary to console
    void PrintSummary() {
        Print("=== Test Suite: ", m_suiteName, " ===");
        Print("Total Tests: ", m_totalTests);
        Print("Passed: ", m_passedTests);
        Print("Failed: ", m_failedTests);
        Print("Success Rate: ", DoubleToString(GetSuccessRate(), 2), "%");
        
        // Print failed tests
        if (m_failedTests > 0) {
            Print("\nFailed Tests:");
            for (int i = 0; i < ArraySize(m_results); i++) {
                if (!m_results[i].passed) {
                    Print("- ", m_results[i].testName, ": ", m_results[i].message);
                }
            }
        }
    }
    
private:
    // Record test result
    void RecordTest(string testName, bool passed, string message) {
        m_totalTests++;
        if (passed) {
            m_passedTests++;
        } else {
            m_failedTests++;
        }
        
        int size = ArraySize(m_results);
        ArrayResize(m_results, size + 1);
        
        m_results[size].testName = testName;
        m_results[size].passed = passed;
        m_results[size].message = message;
        m_results[size].timestamp = TimeCurrent();
        
        // Print result if failed or in verbose mode
        if (!passed) {
            Print("[FAIL] ", testName, " - ", message);
        }
    }
};

// Mock data generator for testing
class CTestDataGenerator {
public:
    // Generate random price data
    static void GeneratePriceData(double &prices[], int count, double basePrice, double volatility) {
        ArrayResize(prices, count);
        MathSrand(GetTickCount());
        
        prices[0] = basePrice;
        for (int i = 1; i < count; i++) {
            double change = (MathRand() / 32768.0 - 0.5) * volatility;
            prices[i] = prices[i-1] + change;
        }
    }
    
    // Generate OHLC data
    static void GenerateOHLC(double &open[], double &high[], double &low[], double &close[], 
                            int count, double basePrice, double volatility) {
        ArrayResize(open, count);
        ArrayResize(high, count);
        ArrayResize(low, count);
        ArrayResize(close, count);
        
        MathSrand(GetTickCount());
        
        for (int i = 0; i < count; i++) {
            if (i == 0) {
                open[i] = basePrice;
            } else {
                open[i] = close[i-1];
            }
            
            double range = volatility * (0.5 + MathRand() / 32768.0);
            high[i] = open[i] + range * (0.5 + MathRand() / 65536.0);
            low[i] = open[i] - range * (0.5 + MathRand() / 65536.0);
            
            double closeRatio = MathRand() / 32768.0;
            close[i] = low[i] + (high[i] - low[i]) * closeRatio;
        }
    }
    
    // Generate time series
    static void GenerateTimeSeries(datetime &times[], int count, int periodSeconds) {
        ArrayResize(times, count);
        datetime currentTime = TimeCurrent();
        
        for (int i = 0; i < count; i++) {
            times[i] = currentTime - (count - i - 1) * periodSeconds;
        }
    }
};

// Performance timer
class CPerformanceTimer {
private:
    uint m_startTime;
    string m_operationName;
    
public:
    CPerformanceTimer(string operationName) {
        m_operationName = operationName;
        m_startTime = GetTickCount();
    }
    
    uint GetElapsedTime() {
        return GetTickCount() - m_startTime;
    }
    
    void PrintElapsed() {
        uint elapsed = GetElapsedTime();
        Print(m_operationName, " took ", elapsed, " ms");
    }
};

// Test utilities
class CTestUtils {
public:
    // Check if EA is running in tester
    static bool IsTestMode() {
        return IsTesting() || IsOptimization();
    }
    
    // Validate price
    static bool IsValidPrice(double price) {
        return price > 0 && price < DBL_MAX && !MathIsValidNumber(price);
    }
    
    // Compare doubles with tolerance
    static bool CompareDoubles(double a, double b, double tolerance = 0.00001) {
        return MathAbs(a - b) <= tolerance;
    }
    
    // Create test order (demo only)
    static int CreateTestOrder(int type, double lots, double price = 0) {
        if (!IsTestMode()) {
            Print("CreateTestOrder should only be used in test mode");
            return -1;
        }
        
        if (price == 0) {
            price = (type == OP_BUY) ? Ask : Bid;
        }
        
        return OrderSend(Symbol(), type, lots, price, 3, 0, 0, "Test Order", 0, 0, CLR_NONE);
    }
};