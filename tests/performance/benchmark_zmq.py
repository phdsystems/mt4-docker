#!/usr/bin/env python3
"""
ZeroMQ Performance Benchmarks for MT4 Docker
"""

import time
import zmq
import json
import multiprocessing
import statistics
from typing import List, Dict, Any
import pytest
import numpy as np


class ZMQBenchmark:
    """Benchmark ZeroMQ message throughput and latency"""
    
    def __init__(self):
        self.context = zmq.Context()
        self.results: Dict[str, Any] = {}
    
    def benchmark_throughput(self, message_size: int, num_messages: int) -> Dict[str, float]:
        """Benchmark message throughput"""
        # Create publisher
        publisher = self.context.socket(zmq.PUB)
        publisher.bind("tcp://127.0.0.1:5555")
        
        # Create subscriber
        subscriber = self.context.socket(zmq.SUB)
        subscriber.connect("tcp://127.0.0.1:5555")
        subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        
        # Allow connection to establish
        time.sleep(0.1)
        
        # Prepare message
        message = b"x" * message_size
        
        # Send messages
        start_time = time.time()
        for _ in range(num_messages):
            publisher.send(message)
        send_time = time.time() - start_time
        
        # Receive messages
        received = 0
        start_time = time.time()
        while received < num_messages and time.time() - start_time < 10:
            try:
                msg = subscriber.recv(zmq.NOBLOCK)
                received += 1
            except zmq.Again:
                continue
        receive_time = time.time() - start_time
        
        # Clean up
        publisher.close()
        subscriber.close()
        
        # Calculate metrics
        throughput_send = num_messages / send_time
        throughput_receive = received / receive_time
        bandwidth_mbps = (received * message_size * 8) / (receive_time * 1_000_000)
        
        return {
            "messages_sent": num_messages,
            "messages_received": received,
            "message_size_bytes": message_size,
            "send_time_seconds": send_time,
            "receive_time_seconds": receive_time,
            "send_throughput_msg_per_sec": throughput_send,
            "receive_throughput_msg_per_sec": throughput_receive,
            "bandwidth_mbps": bandwidth_mbps,
            "packet_loss_percent": ((num_messages - received) / num_messages) * 100
        }
    
    def benchmark_latency(self, num_samples: int = 1000) -> Dict[str, float]:
        """Benchmark round-trip latency"""
        # Create REQ-REP pair for latency testing
        client = self.context.socket(zmq.REQ)
        client.connect("tcp://127.0.0.1:5556")
        
        server = self.context.socket(zmq.REP)
        server.bind("tcp://127.0.0.1:5556")
        
        # Start server in separate thread
        def server_loop():
            for _ in range(num_samples):
                message = server.recv()
                server.send(message)
        
        import threading
        server_thread = threading.Thread(target=server_loop)
        server_thread.start()
        
        # Measure latencies
        latencies = []
        for i in range(num_samples):
            start = time.perf_counter()
            client.send(f"ping_{i}".encode())
            reply = client.recv()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to milliseconds
        
        server_thread.join()
        client.close()
        server.close()
        
        # Calculate statistics
        return {
            "samples": num_samples,
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "avg_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "stdev_latency_ms": statistics.stdev(latencies),
            "p95_latency_ms": np.percentile(latencies, 95),
            "p99_latency_ms": np.percentile(latencies, 99)
        }
    
    def benchmark_pubsub_scalability(self, num_subscribers: int) -> Dict[str, Any]:
        """Benchmark pub-sub with multiple subscribers"""
        publisher = self.context.socket(zmq.PUB)
        publisher.bind("tcp://127.0.0.1:5557")
        
        # Create subscribers
        subscribers = []
        for i in range(num_subscribers):
            sub = self.context.socket(zmq.SUB)
            sub.connect("tcp://127.0.0.1:5557")
            sub.setsockopt(zmq.SUBSCRIBE, b"")
            subscribers.append(sub)
        
        time.sleep(0.5)  # Allow connections
        
        # Send messages
        num_messages = 1000
        start_time = time.time()
        
        for i in range(num_messages):
            message = json.dumps({
                "id": i,
                "timestamp": time.time(),
                "data": "test_message"
            }).encode()
            publisher.send_multipart([b"topic", message])
        
        send_time = time.time() - start_time
        
        # Receive messages on all subscribers
        receive_counts = []
        for sub in subscribers:
            count = 0
            start = time.time()
            while time.time() - start < 2:  # 2 second timeout
                try:
                    topic, msg = sub.recv_multipart(zmq.NOBLOCK)
                    count += 1
                except zmq.Again:
                    continue
            receive_counts.append(count)
        
        # Clean up
        publisher.close()
        for sub in subscribers:
            sub.close()
        
        return {
            "num_subscribers": num_subscribers,
            "messages_sent": num_messages,
            "send_time_seconds": send_time,
            "send_rate_msg_per_sec": num_messages / send_time,
            "receive_counts": receive_counts,
            "avg_messages_received": statistics.mean(receive_counts),
            "min_messages_received": min(receive_counts),
            "max_messages_received": max(receive_counts),
            "delivery_rate_percent": (statistics.mean(receive_counts) / num_messages) * 100
        }


# Pytest benchmarks
@pytest.mark.benchmark(group="throughput")
def test_small_message_throughput(benchmark):
    """Benchmark small message throughput (tick data size)"""
    zmq_bench = ZMQBenchmark()
    result = benchmark(zmq_bench.benchmark_throughput, 128, 10000)
    assert result["packet_loss_percent"] < 1.0


@pytest.mark.benchmark(group="throughput")
def test_large_message_throughput(benchmark):
    """Benchmark large message throughput (OHLC data size)"""
    zmq_bench = ZMQBenchmark()
    result = benchmark(zmq_bench.benchmark_throughput, 1024, 5000)
    assert result["packet_loss_percent"] < 1.0


@pytest.mark.benchmark(group="latency")
def test_round_trip_latency(benchmark):
    """Benchmark round-trip latency"""
    zmq_bench = ZMQBenchmark()
    result = benchmark(zmq_bench.benchmark_latency, 1000)
    assert result["avg_latency_ms"] < 10.0  # Should be sub-10ms


@pytest.mark.benchmark(group="scalability")
def test_pubsub_10_subscribers(benchmark):
    """Benchmark with 10 subscribers"""
    zmq_bench = ZMQBenchmark()
    result = benchmark(zmq_bench.benchmark_pubsub_scalability, 10)
    assert result["delivery_rate_percent"] > 95.0


@pytest.mark.benchmark(group="scalability")
def test_pubsub_50_subscribers(benchmark):
    """Benchmark with 50 subscribers"""
    zmq_bench = ZMQBenchmark()
    result = benchmark(zmq_bench.benchmark_pubsub_scalability, 50)
    assert result["delivery_rate_percent"] > 90.0


def main():
    """Run benchmarks and print results"""
    print("MT4 ZeroMQ Performance Benchmarks")
    print("=" * 50)
    
    bench = ZMQBenchmark()
    
    # Throughput tests
    print("\n1. Throughput Benchmarks:")
    for size, count in [(64, 100000), (256, 50000), (1024, 10000), (4096, 5000)]:
        print(f"\n  Message size: {size} bytes, Count: {count}")
        result = bench.benchmark_throughput(size, count)
        print(f"    Send rate: {result['send_throughput_msg_per_sec']:.0f} msg/s")
        print(f"    Receive rate: {result['receive_throughput_msg_per_sec']:.0f} msg/s")
        print(f"    Bandwidth: {result['bandwidth_mbps']:.2f} Mbps")
        print(f"    Packet loss: {result['packet_loss_percent']:.2f}%")
    
    # Latency tests
    print("\n2. Latency Benchmarks:")
    latency_result = bench.benchmark_latency(5000)
    print(f"    Min: {latency_result['min_latency_ms']:.3f} ms")
    print(f"    Avg: {latency_result['avg_latency_ms']:.3f} ms")
    print(f"    Max: {latency_result['max_latency_ms']:.3f} ms")
    print(f"    P95: {latency_result['p95_latency_ms']:.3f} ms")
    print(f"    P99: {latency_result['p99_latency_ms']:.3f} ms")
    
    # Scalability tests
    print("\n3. Scalability Benchmarks:")
    for num_subs in [1, 5, 10, 25, 50]:
        result = bench.benchmark_pubsub_scalability(num_subs)
        print(f"\n  Subscribers: {num_subs}")
        print(f"    Send rate: {result['send_rate_msg_per_sec']:.0f} msg/s")
        print(f"    Delivery rate: {result['delivery_rate_percent']:.1f}%")
        print(f"    Min received: {result['min_messages_received']}")
        print(f"    Max received: {result['max_messages_received']}")


if __name__ == "__main__":
    main()