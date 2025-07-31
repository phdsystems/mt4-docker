# MT4 Docker Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MT4 DOCKER CONTAINER                          │
│                                                                         │
│  ┌─────────────────┐    ┌──────────────┐    ┌────────────────────┐   │
│  │   Supervisor    │────│     Xvfb     │────│      X11VNC       │   │
│  │   (Process Mgr) │    │  (Virtual    │    │   (VNC Server)    │   │
│  │                 │    │   Display)   │    │   Port: 5900      │   │
│  └────────┬────────┘    └──────────────┘    └────────────────────┘   │
│           │                                                             │
│  ┌────────┴────────┐    ┌──────────────────────────────────────┐     │
│  │  Wine (32-bit)  │────│         MT4 Terminal.exe            │     │
│  │  Windows Layer  │    │  - Trading Platform                  │     │
│  │                 │    │  - Chart Display                     │     │
│  └────────────────┘    │  - EA Execution                      │     │
│                         └────────────┬─────────────────────────┘     │
│                                      │                                 │
│  ┌───────────────────────────────────┴────────────────────────────┐  │
│  │                        MQL4 File System                         │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐   │  │
│  │  │   Experts/  │  │  Indicators/ │  │     Scripts/       │   │  │
│  │  │  - EAs      │  │  - Custom    │  │  - One-time       │   │  │
│  │  │  - Trading  │  │  - Analysis  │  │  - Utilities      │   │  │
│  │  └─────────────┘  └──────────────┘  └────────────────────┘   │  │
│  │                                                                 │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐   │  │
│  │  │ Libraries/  │  │    Files/    │  │     Logs/          │   │  │
│  │  │ - DLLs     │  │  - CSV Data  │  │  - Trading Logs   │   │  │
│  │  │ - mt4zmq   │  │  - Reports   │  │  - Expert Logs    │   │  │
│  │  └─────────────┘  └──────────────┘  └────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            DATA FLOW PATHS                              │
└─────────────────────────────────────────────────────────────────────────┘

Path 1: File-Based Export (Currently Working)
═════════════════════════════════════════════
MT4 Terminal ──► Manual Export (F2) ──► CSV File ──► Web Viewer
     │                                      │
     └── Chart Save As ─────────────────────┘

Path 2: EA-Based Export (Requires Compilation)
══════════════════════════════════════════════
MT4 Terminal ──► DataExporter EA ──► CSV File ──► File Watcher ──► Web UI
                      │                               │
                      └── Auto Export ────────────────┘

Path 3: DLL-Based Streaming (High Performance)
══════════════════════════════════════════════
MT4 Terminal ──► EA with DLL ──► mt4zmq.dll ──► TCP Socket ──► Subscribers
     │               │                │                           │
     └── Real-time ──┘                └── ZeroMQ Protocol ───────┘
```

## Component Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         COMPONENT LAYERS                           │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────────── Presentation Layer ───────────────────────┐
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │  VNC Client  │  │  Web Interface  │  │  REST API       │   │
│  │  Port: 5900  │  │  Port: 8081     │  │  Port: 8080     │   │
│  └──────────────┘  └─────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────── Application Layer ────────────────────────┐
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ MT4 Terminal │  │ Python Services │  │ Node.js Bridge  │   │
│  │  - Trading   │  │  - Data Server  │  │  - WebSocket    │   │
│  │  - EAs       │  │  - File Monitor │  │  - Real-time    │   │
│  └──────────────┘  └─────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────── Infrastructure Layer ─────────────────────┐
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │    Docker    │  │      Wine       │  │   Supervisor    │   │
│  │  Container   │  │   Windows       │  │   Process       │   │
│  │  Management  │  │   Emulation     │  │   Management    │   │
│  └──────────────┘  └─────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      NETWORK TOPOLOGY                           │
└─────────────────────────────────────────────────────────────────┘

                        ┌─────────────┐
                        │   Browser   │
                        │ (Web Viewer)│
                        └──────┬──────┘
                               │ HTTP
                               │ :8081
                    ┌──────────┴──────────┐
                    │   Host Machine      │
                    │                     │
    VNC :5900 ──────┤                     ├────── API :8080
                    │                     │
                    └──────────┬──────────┘
                               │ Docker Network
                    ┌──────────┴──────────┐
                    │   MT4 Container     │
                    │  ┌───────────────┐  │
                    │  │ MT4 Terminal  │  │
                    │  │               │  │
                    │  │ ┌───────────┐ │  │
                    │  │ │    EA     │ │  │
                    │  │ │    ↓      │ │  │     ┌──────────────┐
                    │  │ │ mt4zmq.dll│─┼──┼─────│ Python Sub   │
                    │  │ └───────────┘ │  │ TCP │              │
                    │  └───────────────┘  │:5555└──────────────┘
                    │                     │
                    │                     │     ┌──────────────┐
                    │                     ├─────│ Node.js Sub  │
                    │                     │ TCP │              │
                    │                     │:5555└──────────────┘
                    └─────────────────────┘
```

## Directory Structure

```
mt4-docker/
│
├── MQL4/                    # MT4 Programming Files
│   ├── Experts/            # Expert Advisors (EAs)
│   │   ├── DataExporter.mq4
│   │   └── *.ex4           # Compiled EAs
│   ├── Include/            # Header Files
│   │   └── MT4ZMQ.mqh     # ZeroMQ Integration
│   ├── Libraries/          # DLL Files
│   │   └── mt4zmq.dll     # ZeroMQ Library
│   └── Files/              # Data Export
│       └── *.csv          # Market Data
│
├── dll_source/             # DLL Source Code
│   ├── mt4zmq.cpp         # C++ Implementation
│   └── build/             # Compiled Output
│
├── services/               # Microservices
│   ├── web_data_server.py # Data API
│   ├── websocket/         # Real-time Bridge
│   └── zeromq_bridge/     # ZMQ Services
│
├── web/                    # Web Interface
│   ├── data-viewer.html   # Main UI
│   └── standalone.html    # Offline Viewer
│
├── infra/                  # Infrastructure
│   ├── docker/            # Docker Configs
│   ├── scripts/           # Deployment
│   └── monitoring/        # Observability
│
└── bin/                    # Utility Scripts
    ├── quick_start.sh     # Start System
    ├── check_status.sh    # Health Check
    └── monitor.sh         # Live Monitor
```

## Data Export Methods

```
┌────────────────────────────────────────────────────────────────┐
│                    DATA EXPORT METHODS                         │
└────────────────────────────────────────────────────────────────┘

1. Manual Export (Working)
   ══════════════════════
   MT4 → History Center (F2) → Export Button → CSV File
    │
    └─→ Chart → Right Click → Save As → CSV File

2. EA File Export (Needs Compilation)
   ═══════════════════════════════════
   MT4 → DataExporter EA → FileWrite() → MQL4/Files/*.csv
    │                          │
    └─→ Continuous Export ─────┘

3. DLL Streaming (High Performance)
   ════════════════════════════════
   MT4 → EA → mt4zmq.dll → TCP Socket → Multiple Subscribers
    │           │              │
    └─→ Real-time Data ────────┴─→ No File I/O

4. Alternative Methods
   ══════════════════
   - Copy from Market Watch window
   - Screenshot OCR
   - Terminal logs parsing
   - Memory reading (advanced)
```

## Security Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                             │
└────────────────────────────────────────────────────────────────┘

Application Security:
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ VNC Password    │────▶│ .env Credentials │────▶│ API Keys    │
│ Protection      │     │ Isolation        │     │ Management  │
└─────────────────┘     └──────────────────┘     └─────────────┘

Network Security:
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Docker Network  │────▶│ Port Isolation   │────▶│ Firewall    │
│ Isolation       │     │ (Internal Only)  │     │ Rules       │
└─────────────────┘     └──────────────────┘     └─────────────┘

Data Security:
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Local Storage   │────▶│ No Cloud Upload  │────▶│ Encrypted   │
│ Only            │     │ (Privacy)        │     │ Volumes     │
└─────────────────┘     └──────────────────┘     └─────────────┘
```

## Performance Characteristics

```
┌────────────────────────────────────────────────────────────────┐
│                  PERFORMANCE METRICS                           │
└────────────────────────────────────────────────────────────────┘

File-Based Export:
- Latency: 1-5 seconds
- Throughput: ~100 msgs/sec
- Storage: High (CSV files)

DLL Streaming:
- Latency: <1ms
- Throughput: 20,000+ msgs/sec
- Storage: None (memory only)

Resource Usage:
- CPU: 10-20% (idle), 30-50% (active trading)
- Memory: 512MB-1GB
- Disk: 100MB + data files
- Network: Minimal (local only)
```

This architecture enables MT4 to run in a containerized environment with multiple data export options, from simple file-based exports to high-performance network streaming.