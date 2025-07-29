# EA Testing Guide

This guide explains how to use the EA Testing Framework in MT4 Docker.

## Overview

The EA Testing Framework provides automated testing capabilities for Expert Advisors (EAs) in MetaTrader 4. It includes:

- **EATester.mq4** - Main testing EA that runs various test suites
- **EATestFramework.mqh** - Include file with testing utilities and assertions
- **test_ea.sh** - Script to run EA tests in the container

## Quick Start

### Running EATester

```bash
# Run all tests
./bin/test_ea.sh EATester ALL

# Run specific test suite
./bin/test_ea.sh EATester BASIC
./bin/test_ea.sh EATester TRADING
./bin/test_ea.sh EATester INDICATORS
./bin/test_ea.sh EATester ERRORS
./bin/test_ea.sh EATester PERFORMANCE
```

### Testing Your Own EA

1. Include the test framework in your EA:
```mql4
#include <EATestFramework.mqh>
```

2. Add test parameter:
```mql4
input bool InpRunTests = false; // Run tests on init
```

3. Create test functions and run them in OnInit() when testing

## Using the Test Framework

### Basic Assertions

```mql4
CTestSuite* testSuite = new CTestSuite("MyEA");

// Boolean assertions
testSuite.AssertTrue("Test name", condition);
testSuite.AssertFalse("Test name", condition);

// Numeric assertions
testSuite.AssertEquals("Test name", expected, actual, tolerance);
testSuite.AssertNotEquals("Test name", value1, value2);
testSuite.AssertGreater("Test name", value1, value2);
testSuite.AssertLess("Test name", value1, value2);

// String assertions
testSuite.AssertStringEquals("Test name", expected, actual);

// Null checks
testSuite.AssertNull("Test name", handle);
testSuite.AssertNotNull("Test name", handle);
```

### Example Test Suite

```mql4
void TestMyIndicator() {
    CTestSuite* suite = new CTestSuite("MyIndicator");
    
    // Test calculation
    double result = MyIndicatorCalculation(1.1234, 14);
    suite.AssertEquals("Indicator calculation", 1.1250, result, 0.0001);
    
    // Test edge cases
    suite.AssertTrue("Handle zero input", MyIndicatorCalculation(0, 14) >= 0);
    
    // Generate report
    suite.PrintSummary();
    suite.GenerateReport("my_indicator_test.txt");
    
    delete suite;
}
```

## Test Data Generation

The framework includes utilities for generating test data:

```mql4
// Generate price data
double prices[];
CTestDataGenerator::GeneratePriceData(prices, 100, 1.1234, 0.0010);

// Generate OHLC data
double open[], high[], low[], close[];
CTestDataGenerator::GenerateOHLC(open, high, low, close, 100, 1.1234, 0.0010);

// Generate time series
datetime times[];
CTestDataGenerator::GenerateTimeSeries(times, 100, 3600); // 1 hour bars
```

## Performance Testing

Use the performance timer for benchmarking:

```mql4
CPerformanceTimer timer("My Operation");

// Your code here
PerformComplexCalculation();

timer.PrintElapsed(); // Prints: "My Operation took 123 ms"
```

## Test Reports

Test results are saved to:
- Container: `/mt4/MQL4/Files/ea_test_report.txt`
- Host: `./test_reports/`

Reports include:
- Test summary (total, passed, failed)
- Individual test results
- Execution time
- Success rate

## Best Practices

1. **Test Categories**
   - Unit tests for individual functions
   - Integration tests for component interaction
   - Performance tests for optimization
   - Error handling tests for robustness

2. **Test Naming**
   - Use descriptive test names
   - Include what is being tested and expected outcome

3. **Test Independence**
   - Each test should be independent
   - Clean up any test data or orders

4. **Continuous Testing**
   - Run tests before deploying EAs
   - Include tests in CI/CD pipeline
   - Test after MT4 updates

## Troubleshooting

### EA won't compile
- Check syntax errors in Experts log
- Ensure test framework is deployed: `./bin/test_ea.sh`

### Tests hang
- Check EA logs: `./bin/view_logs.sh`
- Verify container is running: `./bin/check_status.sh`
- Tests timeout after 60 seconds by default

### No test results
- Check Files directory in container
- Ensure EA has write permissions
- Verify test report generation is enabled

## Example: Testing a Grid EA

```mql4
void TestGridLogic() {
    CTestSuite* suite = new CTestSuite("GridEA");
    
    // Test grid level calculation
    double basePrice = 1.1000;
    double gridSize = 0.0010; // 10 pips
    
    for (int i = 0; i < 5; i++) {
        double expectedLevel = basePrice + (i * gridSize);
        double actualLevel = CalculateGridLevel(basePrice, i, gridSize);
        suite.AssertEquals("Grid level " + IntegerToString(i), 
                          expectedLevel, actualLevel);
    }
    
    // Test position sizing
    double lots = CalculateGridLotSize(1000, 5, 0.01);
    suite.AssertGreater("Lot size positive", lots, 0);
    suite.AssertLess("Lot size reasonable", lots, 1.0);
    
    suite.GenerateReport("grid_ea_test.txt");
    delete suite;
}
```

## Integration with CI/CD

Add to your GitHub Actions workflow:

```yaml
- name: Run EA Tests
  run: |
    ./bin/test_ea.sh EATester ALL
    ./bin/test_ea.sh MyCustomEA ALL
    
- name: Upload Test Reports
  uses: actions/upload-artifact@v3
  with:
    name: ea-test-reports
    path: test_reports/
```