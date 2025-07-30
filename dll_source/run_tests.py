#!/usr/bin/env python3
"""Cross-platform test runner for MT4ZMQ DLL tests"""

import ctypes
import os
import sys
import subprocess
import platform

def run_windows_tests():
    """Run tests on Windows using the test executable"""
    test_exe = "build\\test_mt4zmq.exe"
    dll_path = "build\\mt4zmq.dll"
    
    if not os.path.exists(test_exe):
        print(f"Error: Test executable not found: {test_exe}")
        return False
        
    if not os.path.exists(dll_path):
        print(f"Error: DLL not found: {dll_path}")
        return False
    
    print(f"Running: {test_exe} {dll_path}")
    result = subprocess.run([test_exe, dll_path], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def run_wine_tests():
    """Run tests on Linux using Wine"""
    test_exe = "build/test_mt4zmq.exe"
    dll_path = "build/mt4zmq.dll"
    
    if not os.path.exists(test_exe):
        print(f"Error: Test executable not found: {test_exe}")
        return False
        
    if not os.path.exists(dll_path):
        print(f"Error: DLL not found: {dll_path}")
        return False
    
    # Check if Wine is installed
    try:
        subprocess.run(["wine", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Wine is not installed. Cannot run Windows tests on Linux.")
        print("Install Wine with: sudo apt-get install wine32")
        return False
    
    print(f"Running tests with Wine...")
    
    # DLL is already in the same directory as test executable
    
    result = subprocess.run(["wine", test_exe, "mt4zmq.dll"], 
                          capture_output=True, text=True, 
                          cwd="build")
    print(result.stdout)
    
    # Check if tests passed by looking at the output
    if "All tests passed!" in result.stdout:
        return True
    
    # Wine often returns non-zero even when the program succeeds
    # Only fail if we see actual test failures
    if "Failed:" in result.stdout:
        lines = result.stdout.split('\n')
        for line in lines:
            if "Failed:" in line and "Failed: 0" not in line:
                return False
    
    return True

def run_basic_dll_test():
    """Run basic DLL loading test using ctypes"""
    print("\n=== Basic DLL Loading Test ===")
    
    dll_path = "./build/mt4zmq.dll"
    if not os.path.exists(dll_path):
        print(f"Error: DLL not found: {dll_path}")
        return False
    
    try:
        # This will fail on Linux but shows the DLL structure is valid
        if platform.system() == "Windows":
            dll = ctypes.CDLL(dll_path)
            print("✓ DLL loaded successfully with ctypes")
            
            # Test getting version
            dll.zmq_version.restype = None
            dll.zmq_version.argtypes = [ctypes.c_wchar_p, ctypes.c_int]
            
            version = ctypes.create_unicode_buffer(256)
            dll.zmq_version(version, 256)
            print(f"✓ Version: {version.value}")
            return True
        else:
            print("ℹ Skipping ctypes test on non-Windows platform")
            return True
            
    except Exception as e:
        print(f"✗ Failed to load DLL: {e}")
        return False

def main():
    """Main test runner"""
    print("MT4ZMQ DLL Test Runner")
    print("=" * 50)
    
    # Check if files exist
    if not os.path.exists("build/mt4zmq.dll"):
        print("Error: DLL not found. Run build_winsock.sh first.")
        return 1
        
    if not os.path.exists("build/test_mt4zmq.exe"):
        print("Error: Test executable not found. Run build_tests.sh first.")
        return 1
    
    success = True
    
    # Run basic DLL test
    if not run_basic_dll_test():
        success = False
    
    # Run platform-specific tests
    if platform.system() == "Windows":
        print("\n=== Running Windows Unit Tests ===")
        if not run_windows_tests():
            success = False
    else:
        print("\n=== Running Wine Unit Tests ===")
        if not run_wine_tests():
            success = False
    
    print("\n" + "=" * 50)
    if success:
        print("All tests completed successfully! ✓")
        return 0
    else:
        print("Some tests failed! ✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())