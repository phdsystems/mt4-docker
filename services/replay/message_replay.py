#!/usr/bin/env python3
"""
Message Replay System for MT4 Market Data
Allows recording and replaying of market data for backtesting and analysis
"""

import asyncio
import zmq
import zmq.asyncio
import json
import time
import gzip
import sqlite3
import logging
from typing import Dict, List, Optional, Any, Generator, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from enum import Enum
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ReplayMode(Enum):
    """Replay modes"""
    REALTIME = "realtime"      # Replay at original speed
    FAST = "fast"              # Replay as fast as possible
    STEPPED = "stepped"        # Manual step through messages
    ACCELERATED = "accelerated" # Replay at Nx speed


@dataclass
class MarketMessage:
    """Market data message"""
    timestamp: float
    topic: str
    symbol: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @staticmethod
    def from_json(json_str: str) -> 'MarketMessage':
        data = json.loads(json_str)
        return MarketMessage(**data)


class MessageRecorder:
    """Records market data messages to storage"""
    
    def __init__(self, storage_path: str, zmq_address: str = "tcp://localhost:5556"):
        """
        Initialize recorder
        
        Args:
            storage_path: Path to storage directory
            zmq_address: ZeroMQ publisher address
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.zmq_address = zmq_address
        
        self.context = zmq.asyncio.Context()
        self.socket = None
        self.db_conn = None
        self.current_file = None
        self.file_handle = None
        self.message_count = 0
        self.start_time = None
        self.logger = logging.getLogger(__name__)
        
        # Buffer for batch writing
        self.buffer = []
        self.buffer_size = 1000
        self.last_flush = time.time()
        self.flush_interval = 5  # seconds
    
    async def start(self):
        """Start recording"""
        # Connect to ZeroMQ
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.zmq_address)
        self.socket.subscribe(b"")  # Subscribe to all topics
        
        # Initialize database
        self._init_database()
        
        # Create new recording session
        self.start_time = time.time()
        session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create data file
        self.current_file = self.storage_path / f"recording_{session_name}.jsonl.gz"
        self.file_handle = gzip.open(self.current_file, 'wt')
        
        # Insert session record
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO recording_sessions (name, start_time, file_path, status)
            VALUES (?, ?, ?, 'recording')
        """, (session_name, self.start_time, str(self.current_file)))
        self.db_conn.commit()
        self.session_id = cursor.lastrowid
        
        self.logger.info(f"Started recording session: {session_name}")
        
        # Start recording loop
        await self._recording_loop()
    
    def _init_database(self):
        """Initialize SQLite database for indexing"""
        db_path = self.storage_path / "recordings.db"
        self.db_conn = sqlite3.connect(str(db_path))
        
        # Create tables
        self.db_conn.executescript("""
            CREATE TABLE IF NOT EXISTS recording_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL,
                file_path TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'recording',
                metadata TEXT
            );
            
            CREATE TABLE IF NOT EXISTS message_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                topic TEXT NOT NULL,
                symbol TEXT NOT NULL,
                file_offset INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES recording_sessions(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_timestamp ON message_index(timestamp);
            CREATE INDEX IF NOT EXISTS idx_symbol ON message_index(symbol);
            CREATE INDEX IF NOT EXISTS idx_session_symbol ON message_index(session_id, symbol);
        """)
        self.db_conn.commit()
    
    async def _recording_loop(self):
        """Main recording loop"""
        try:
            while True:
                # Receive message
                topic, message = await self.socket.recv_multipart()
                
                # Parse message
                topic_str = topic.decode()
                data = json.loads(message.decode())
                
                # Extract symbol from topic
                symbol = ""
                if topic_str.startswith("tick."):
                    symbol = topic_str[5:]
                
                # Create message object
                msg = MarketMessage(
                    timestamp=time.time(),
                    topic=topic_str,
                    symbol=symbol,
                    data=data
                )
                
                # Add to buffer
                self.buffer.append(msg)
                
                # Flush if needed
                if len(self.buffer) >= self.buffer_size or \
                   time.time() - self.last_flush > self.flush_interval:
                    await self._flush_buffer()
        
        except Exception as e:
            self.logger.error(f"Recording error: {e}")
        finally:
            await self.stop()
    
    async def _flush_buffer(self):
        """Flush buffer to disk"""
        if not self.buffer:
            return
        
        # Get file position before writing
        file_pos = self.file_handle.tell()
        
        # Write messages
        cursor = self.db_conn.cursor()
        
        for msg in self.buffer:
            # Write to file
            self.file_handle.write(msg.to_json() + '\n')
            
            # Index in database
            cursor.execute("""
                INSERT INTO message_index (session_id, timestamp, topic, symbol, file_offset)
                VALUES (?, ?, ?, ?, ?)
            """, (self.session_id, msg.timestamp, msg.topic, msg.symbol, file_pos))
            
            file_pos = self.file_handle.tell()
            self.message_count += 1
        
        # Update session record
        cursor.execute("""
            UPDATE recording_sessions 
            SET message_count = ? 
            WHERE id = ?
        """, (self.message_count, self.session_id))
        
        self.db_conn.commit()
        self.file_handle.flush()
        
        self.logger.debug(f"Flushed {len(self.buffer)} messages to disk")
        self.buffer.clear()
        self.last_flush = time.time()
    
    async def stop(self):
        """Stop recording"""
        # Flush remaining messages
        await self._flush_buffer()
        
        # Update session record
        if self.db_conn and self.session_id:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                UPDATE recording_sessions 
                SET end_time = ?, status = 'completed'
                WHERE id = ?
            """, (time.time(), self.session_id))
            self.db_conn.commit()
        
        # Close resources
        if self.file_handle:
            self.file_handle.close()
        
        if self.socket:
            self.socket.close()
        
        if self.db_conn:
            self.db_conn.close()
        
        self.context.term()
        
        self.logger.info(f"Recording stopped. Total messages: {self.message_count}")


class MessageReplayer:
    """Replays recorded market data messages"""
    
    def __init__(self, storage_path: str, zmq_address: str = "tcp://*:5559"):
        """
        Initialize replayer
        
        Args:
            storage_path: Path to storage directory
            zmq_address: ZeroMQ publisher address for replay
        """
        self.storage_path = Path(storage_path)
        self.zmq_address = zmq_address
        
        self.context = zmq.asyncio.Context()
        self.socket = None
        self.db_conn = None
        self.logger = logging.getLogger(__name__)
        
        # Replay state
        self.mode = ReplayMode.REALTIME
        self.speed_multiplier = 1.0
        self.current_session = None
        self.is_playing = False
        self.current_position = 0
        self.filters = {}  # Symbol filters
    
    async def start(self):
        """Start replay server"""
        # Create publisher socket
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(self.zmq_address)
        
        # Connect to database
        db_path = self.storage_path / "recordings.db"
        self.db_conn = sqlite3.connect(str(db_path))
        self.db_conn.row_factory = sqlite3.Row
        
        self.logger.info(f"Replay server started on {self.zmq_address}")
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List available recording sessions"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT id, name, start_time, end_time, message_count, status
            FROM recording_sessions
            ORDER BY start_time DESC
        """)
        
        sessions = []
        for row in cursor:
            session = dict(row)
            session['duration'] = row['end_time'] - row['start_time'] if row['end_time'] else None
            sessions.append(session)
        
        return sessions
    
    def load_session(self, session_id: int) -> bool:
        """Load a recording session"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT * FROM recording_sessions WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if not row:
            self.logger.error(f"Session {session_id} not found")
            return False
        
        self.current_session = dict(row)
        self.current_position = 0
        self.logger.info(f"Loaded session: {self.current_session['name']}")
        return True
    
    def set_mode(self, mode: ReplayMode, speed_multiplier: float = 1.0):
        """Set replay mode"""
        self.mode = mode
        self.speed_multiplier = speed_multiplier
        self.logger.info(f"Replay mode set to {mode.value} (speed: {speed_multiplier}x)")
    
    def set_filters(self, symbols: Optional[List[str]] = None):
        """Set symbol filters"""
        self.filters['symbols'] = symbols
        self.logger.info(f"Filters set: {self.filters}")
    
    async def play(self, start_time: Optional[float] = None, end_time: Optional[float] = None):
        """Start replay"""
        if not self.current_session:
            self.logger.error("No session loaded")
            return
        
        self.is_playing = True
        
        # Open data file
        file_path = Path(self.current_session['file_path'])
        
        # Get messages to replay
        messages = self._get_messages(start_time, end_time)
        
        if not messages:
            self.logger.warning("No messages to replay")
            return
        
        self.logger.info(f"Starting replay of {len(messages)} messages")
        
        # Replay based on mode
        if self.mode == ReplayMode.REALTIME:
            await self._replay_realtime(messages, file_path)
        elif self.mode == ReplayMode.FAST:
            await self._replay_fast(messages, file_path)
        elif self.mode == ReplayMode.ACCELERATED:
            await self._replay_accelerated(messages, file_path)
        elif self.mode == ReplayMode.STEPPED:
            await self._replay_stepped(messages, file_path)
    
    def _get_messages(self, start_time: Optional[float], end_time: Optional[float]) -> List[Dict]:
        """Get messages to replay"""
        query = """
            SELECT * FROM message_index 
            WHERE session_id = ?
        """
        params = [self.current_session['id']]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if self.filters.get('symbols'):
            placeholders = ','.join(['?' for _ in self.filters['symbols']])
            query += f" AND symbol IN ({placeholders})"
            params.extend(self.filters['symbols'])
        
        query += " ORDER BY timestamp"
        
        cursor = self.db_conn.cursor()
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor]
    
    async def _replay_realtime(self, messages: List[Dict], file_path: Path):
        """Replay at original speed"""
        with gzip.open(file_path, 'rt') as f:
            prev_timestamp = None
            
            for msg_index in messages:
                if not self.is_playing:
                    break
                
                # Read message from file
                f.seek(msg_index['file_offset'])
                line = f.readline()
                msg = MarketMessage.from_json(line)
                
                # Calculate delay
                if prev_timestamp:
                    delay = (msg.timestamp - prev_timestamp) / self.speed_multiplier
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                # Publish message
                await self._publish_message(msg)
                
                prev_timestamp = msg.timestamp
                self.current_position += 1
    
    async def _replay_fast(self, messages: List[Dict], file_path: Path):
        """Replay as fast as possible"""
        with gzip.open(file_path, 'rt') as f:
            for msg_index in messages:
                if not self.is_playing:
                    break
                
                # Read and publish message
                f.seek(msg_index['file_offset'])
                line = f.readline()
                msg = MarketMessage.from_json(line)
                
                await self._publish_message(msg)
                self.current_position += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.001)
    
    async def _replay_accelerated(self, messages: List[Dict], file_path: Path):
        """Replay at accelerated speed"""
        # Similar to realtime but with speed multiplier
        await self._replay_realtime(messages, file_path)
    
    async def _replay_stepped(self, messages: List[Dict], file_path: Path):
        """Manual step through messages"""
        self.logger.info("Stepped mode - use step() method to advance")
        # Implementation would wait for manual step() calls
    
    async def _publish_message(self, msg: MarketMessage):
        """Publish a message"""
        topic = msg.topic.encode()
        data = json.dumps(msg.data).encode()
        
        await self.socket.send_multipart([topic, data])
        
        self.logger.debug(f"Published: {msg.topic} - {msg.symbol}")
    
    async def pause(self):
        """Pause replay"""
        self.is_playing = False
        self.logger.info("Replay paused")
    
    async def resume(self):
        """Resume replay"""
        self.is_playing = True
        self.logger.info("Replay resumed")
    
    async def stop(self):
        """Stop replay server"""
        self.is_playing = False
        
        if self.socket:
            self.socket.close()
        
        if self.db_conn:
            self.db_conn.close()
        
        self.context.term()
        self.logger.info("Replay server stopped")


class ReplayAnalyzer:
    """Analyze recorded market data"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.db_conn = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """Connect to database"""
        db_path = self.storage_path / "recordings.db"
        self.db_conn = sqlite3.connect(str(db_path))
        self.db_conn.row_factory = sqlite3.Row
    
    def analyze_session(self, session_id: int) -> Dict[str, Any]:
        """Analyze a recording session"""
        cursor = self.db_conn.cursor()
        
        # Get session info
        cursor.execute("SELECT * FROM recording_sessions WHERE id = ?", (session_id,))
        session = dict(cursor.fetchone())
        
        # Get symbol statistics
        cursor.execute("""
            SELECT symbol, COUNT(*) as count,
                   MIN(timestamp) as first_tick,
                   MAX(timestamp) as last_tick
            FROM message_index
            WHERE session_id = ?
            GROUP BY symbol
        """, (session_id,))
        
        symbols = {}
        for row in cursor:
            symbols[row['symbol']] = {
                'count': row['count'],
                'first_tick': row['first_tick'],
                'last_tick': row['last_tick'],
                'duration': row['last_tick'] - row['first_tick']
            }
        
        # Get message rate statistics
        cursor.execute("""
            SELECT 
                CAST(timestamp AS INTEGER) as second,
                COUNT(*) as count
            FROM message_index
            WHERE session_id = ?
            GROUP BY CAST(timestamp AS INTEGER)
        """, (session_id,))
        
        rates = [row['count'] for row in cursor]
        
        analysis = {
            'session': session,
            'symbols': symbols,
            'statistics': {
                'total_messages': session['message_count'],
                'duration': session['end_time'] - session['start_time'] if session['end_time'] else 0,
                'avg_rate_per_second': np.mean(rates) if rates else 0,
                'max_rate_per_second': np.max(rates) if rates else 0,
                'min_rate_per_second': np.min(rates) if rates else 0
            }
        }
        
        return analysis
    
    def export_to_csv(self, session_id: int, output_path: str, symbol: Optional[str] = None):
        """Export session data to CSV"""
        import csv
        
        # Get messages
        query = """
            SELECT m.*, s.file_path
            FROM message_index m
            JOIN recording_sessions s ON m.session_id = s.id
            WHERE m.session_id = ?
        """
        params = [session_id]
        
        if symbol:
            query += " AND m.symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY m.timestamp"
        
        cursor = self.db_conn.cursor()
        cursor.execute(query, params)
        
        # Open output file
        with open(output_path, 'w', newline='') as csvfile:
            writer = None
            file_path = None
            file_handle = None
            
            for row in cursor:
                # Open data file if needed
                if file_path != row['file_path']:
                    if file_handle:
                        file_handle.close()
                    file_path = row['file_path']
                    file_handle = gzip.open(file_path, 'rt')
                
                # Read message
                file_handle.seek(row['file_offset'])
                line = file_handle.readline()
                msg = MarketMessage.from_json(line)
                
                # Create CSV writer with headers from first message
                if writer is None:
                    fieldnames = ['timestamp', 'symbol'] + list(msg.data.keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                
                # Write row
                row_data = {'timestamp': msg.timestamp, 'symbol': msg.symbol}
                row_data.update(msg.data)
                writer.writerow(row_data)
            
            if file_handle:
                file_handle.close()
        
        self.logger.info(f"Exported to {output_path}")


# Example usage
async def record_example():
    """Example recording"""
    recorder = MessageRecorder("/tmp/mt4_recordings")
    
    try:
        await recorder.start()
    except KeyboardInterrupt:
        await recorder.stop()


async def replay_example():
    """Example replay"""
    replayer = MessageReplayer("/tmp/mt4_recordings")
    await replayer.start()
    
    # List sessions
    sessions = replayer.list_sessions()
    for session in sessions:
        print(f"Session: {session['name']} - {session['message_count']} messages")
    
    if sessions:
        # Load first session
        replayer.load_session(sessions[0]['id'])
        
        # Set replay mode
        replayer.set_mode(ReplayMode.ACCELERATED, speed_multiplier=10.0)
        
        # Start replay
        await replayer.play()
    
    await replayer.stop()


def analyze_example():
    """Example analysis"""
    analyzer = ReplayAnalyzer("/tmp/mt4_recordings")
    analyzer.connect()
    
    # Analyze first session
    analysis = analyzer.analyze_session(1)
    print(json.dumps(analysis, indent=2))
    
    # Export to CSV
    analyzer.export_to_csv(1, "/tmp/mt4_data.csv", symbol="EURUSD")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "record":
            asyncio.run(record_example())
        elif sys.argv[1] == "replay":
            asyncio.run(replay_example())
        elif sys.argv[1] == "analyze":
            analyze_example()
    else:
        print("Usage: python message_replay.py [record|replay|analyze]")