#!/usr/bin/env python3
"""
Performance Tests for MT4 Docker ZeroMQ
Tests throughput, latency, and resource usage
"""

import time
import zmq
import json
import psutil
import threading
import statistics
from typing import List, Dict, Any
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PerformanceTest:
    """Performance testing framework"""
    
    def __init__(self):
        self.results = {
            'throughput': [],
            'latency': [],
            'cpu_usage': [],
            'memory_usage': []
        }
    
    def test_zmq_throughput(self, duration: int = 10) -> Dict[str, Any]:
        """Test ZeroMQ message throughput"""
        print(f"\n=== Testing ZeroMQ Throughput ({duration}s) ===")
        
        context = zmq.Context()
        
        # Setup publisher
        publisher = context.socket(zmq.PUB)
        publisher.bind("tcp://127.0.0.1:15556")
        
        # Setup subscriber
        subscriber = context.socket(zmq.SUB)
        subscriber.connect("tcp://127.0.0.1:15556")
        subscriber.subscribe(b"")
        
        # Allow connection time
        time.sleep(0.5)
        
        # Message counter
        messages_sent = 0
        messages_received = 0
        
        # Receiver thread
        def receiver():
            nonlocal messages_received
            subscriber.setsockopt(zmq.RCVTIMEO, 100)
            while not stop_event.is_set():
                try:
                    topic, msg = subscriber.recv_multipart()
                    messages_received += 1
                except zmq.Again:
                    pass
        
        stop_event = threading.Event()
        receiver_thread = threading.Thread(target=receiver)
        receiver_thread.start()
        
        # Send messages for duration
        start_time = time.time()
        message = json.dumps({
            "symbol": "EURUSD",
            "bid": 1.1000,
            "ask": 1.1001,
            "timestamp": 0
        }).encode()
        
        while time.time() - start_time < duration:
            publisher.send_multipart([b"tick.EURUSD", message])
            messages_sent += 1
        
        # Stop receiver
        stop_event.set()
        receiver_thread.join()
        
        # Calculate results
        elapsed = time.time() - start_time
        throughput_sent = messages_sent / elapsed
        throughput_received = messages_received / elapsed
        
        # Cleanup
        publisher.close()
        subscriber.close()
        context.term()
        
        results = {
            'messages_sent': messages_sent,
            'messages_received': messages_received,
            'duration': elapsed,
            'throughput_sent': throughput_sent,
            'throughput_received': throughput_received,
            'loss_rate': (messages_sent - messages_received) / messages_sent * 100
        }
        
        print(f"Messages sent: {messages_sent:,}")
        print(f"Messages received: {messages_received:,}")
        print(f"Throughput: {throughput_sent:,.0f} msgs/sec")
        print(f"Loss rate: {results['loss_rate']:.2f}%")
        
        return results
    
    def test_zmq_latency(self, num_samples: int = 1000) -> Dict[str, Any]:
        """Test ZeroMQ message latency"""
        print(f"\n=== Testing ZeroMQ Latency ({num_samples} samples) ===")
        
        context = zmq.Context()
        
        # Setup request-reply pattern for latency testing
        server = context.socket(zmq.REP)
        server.bind("tcp://127.0.0.1:15557")
        
        client = context.socket(zmq.REQ)
        client.connect("tcp://127.0.0.1:15557")
        
        # Server thread
        def server_thread():
            while not stop_event.is_set():
                try:
                    server.setsockopt(zmq.RCVTIMEO, 100)
                    message = server.recv()
                    server.send(message)
                except zmq.Again:
                    pass
        
        stop_event = threading.Event()
        thread = threading.Thread(target=server_thread)
        thread.start()
        
        # Measure latencies
        latencies = []
        
        for i in range(num_samples):
            start = time.perf_counter()
            client.send(b"ping")
            reply = client.recv()
            end = time.perf_counter()
            
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
        
        # Stop server
        stop_event.set()
        thread.join()
        
        # Cleanup
        server.close()
        client.close()
        context.term()
        
        # Calculate statistics
        results = {
            'samples': num_samples,
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'mean_ms': statistics.mean(latencies),
            'median_ms': statistics.median(latencies),
            'stdev_ms': statistics.stdev(latencies),
            'p95_ms': sorted(latencies)[int(0.95 * num_samples)],
            'p99_ms': sorted(latencies)[int(0.99 * num_samples)]
        }
        
        print(f"Latency - Mean: {results['mean_ms']:.3f}ms")
        print(f"Latency - Median: {results['median_ms']:.3f}ms")
        print(f"Latency - 95th percentile: {results['p95_ms']:.3f}ms")
        print(f"Latency - 99th percentile: {results['p99_ms']:.3f}ms")
        
        return results
    
    def test_json_serialization(self, num_iterations: int = 100000) -> Dict[str, Any]:
        """Test JSON serialization performance"""
        print(f"\n=== Testing JSON Serialization ({num_iterations:,} iterations) ===")
        
        # Sample market data
        tick_data = {
            "symbol": "EURUSD",
            "bid": 1.10123,
            "ask": 1.10125,
            "spread": 0.2,
            "volume": 12345,
            "timestamp": 1642345678,
            "ms": 123
        }
        
        # Test serialization
        start = time.perf_counter()
        for _ in range(num_iterations):
            json_str = json.dumps(tick_data)
        serialization_time = time.perf_counter() - start
        
        # Test deserialization
        json_str = json.dumps(tick_data)
        start = time.perf_counter()
        for _ in range(num_iterations):
            data = json.loads(json_str)
        deserialization_time = time.perf_counter() - start
        
        results = {
            'iterations': num_iterations,
            'serialization_total_ms': serialization_time * 1000,
            'serialization_per_msg_us': (serialization_time / num_iterations) * 1000000,
            'deserialization_total_ms': deserialization_time * 1000,
            'deserialization_per_msg_us': (deserialization_time / num_iterations) * 1000000,
            'total_per_msg_us': ((serialization_time + deserialization_time) / num_iterations) * 1000000
        }
        
        print(f"Serialization: {results['serialization_per_msg_us']:.2f}µs per message")
        print(f"Deserialization: {results['deserialization_per_msg_us']:.2f}µs per message")
        print(f"Total: {results['total_per_msg_us']:.2f}µs per round trip")
        
        return results
    
    def test_memory_usage(self, num_messages: int = 10000) -> Dict[str, Any]:
        """Test memory usage with message queuing"""
        print(f"\n=== Testing Memory Usage ({num_messages:,} messages) ===")
        
        process = psutil.Process()
        
        # Initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create messages
        messages = []
        for i in range(num_messages):
            msg = {
                "id": i,
                "symbol": "EURUSD",
                "bid": 1.1000 + i * 0.00001,
                "ask": 1.1001 + i * 0.00001,
                "timestamp": time.time(),
                "extra_data": "x" * 100  # Add some bulk
            }
            messages.append(json.dumps(msg))
        
        # Memory after creating messages
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Calculate message size
        total_size = sum(len(msg) for msg in messages)
        avg_msg_size = total_size / num_messages
        
        # Clear messages
        messages.clear()
        
        # Final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        results = {
            'num_messages': num_messages,
            'initial_memory_mb': initial_memory,
            'peak_memory_mb': peak_memory,
            'final_memory_mb': final_memory,
            'memory_used_mb': peak_memory - initial_memory,
            'avg_message_size_bytes': avg_msg_size,
            'total_size_mb': total_size / 1024 / 1024
        }
        
        print(f"Memory used: {results['memory_used_mb']:.2f} MB")
        print(f"Average message size: {results['avg_message_size_bytes']:.0f} bytes")
        print(f"Memory per message: {results['memory_used_mb'] / num_messages * 1024:.2f} KB")
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests"""
        print("=" * 60)
        print("MT4 Docker ZeroMQ Performance Test Suite")
        print("=" * 60)
        
        all_results = {}
        
        # Run tests
        all_results['throughput'] = self.test_zmq_throughput(duration=5)
        all_results['latency'] = self.test_zmq_latency(num_samples=1000)
        all_results['serialization'] = self.test_json_serialization(num_iterations=50000)
        all_results['memory'] = self.test_memory_usage(num_messages=5000)
        
        # Summary
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"Throughput: {all_results['throughput']['throughput_sent']:,.0f} msgs/sec")
        print(f"Latency (median): {all_results['latency']['median_ms']:.3f} ms")
        print(f"JSON processing: {all_results['serialization']['total_per_msg_us']:.2f} µs/msg")
        print(f"Memory efficiency: {all_results['memory']['memory_used_mb'] / all_results['memory']['num_messages'] * 1024:.2f} KB/msg")
        
        # Performance rating
        if (all_results['throughput']['throughput_sent'] > 10000 and
            all_results['latency']['median_ms'] < 1.0 and
            all_results['serialization']['total_per_msg_us'] < 50):
            print("\n✅ EXCELLENT PERFORMANCE - Production Ready!")
        elif (all_results['throughput']['throughput_sent'] > 5000 and
              all_results['latency']['median_ms'] < 2.0):
            print("\n✅ GOOD PERFORMANCE - Suitable for most use cases")
        else:
            print("\n⚠️ PERFORMANCE NEEDS OPTIMIZATION")
        
        return all_results


if __name__ == "__main__":
    try:
        import zmq
    except ImportError:
        print("PyZMQ not installed. Install with: pip install pyzmq")
        sys.exit(1)
    
    tester = PerformanceTest()
    results = tester.run_all_tests()
    
    # Save results
    with open('performance_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to performance_results.json")