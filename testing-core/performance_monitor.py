"""
Pi-LMS Performance Monitor
Comprehensive system for tracking time spent per phase and system resource consumption
"""

import time
import psutil
import tracemalloc
import threading
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PhaseMetrics:
    """Metrics for a single phase of operation"""
    phase_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    cpu_usage_start: float = 0.0
    cpu_usage_end: float = 0.0
    memory_usage_start: float = 0.0
    memory_usage_end: float = 0.0
    memory_peak: float = 0.0
    disk_io_start: Dict[str, float] = None
    disk_io_end: Dict[str, float] = None
    network_io_start: Dict[str, float] = None
    network_io_end: Dict[str, float] = None
    custom_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.disk_io_start is None:
            self.disk_io_start = {}
        if self.disk_io_end is None:
            self.disk_io_end = {}
        if self.network_io_start is None:
            self.network_io_start = {}
        if self.network_io_end is None:
            self.network_io_end = {}
        if self.custom_metrics is None:
            self.custom_metrics = {}

@dataclass
class SessionMetrics:
    """Complete metrics for a testing session"""
    session_id: str
    operation_type: str
    start_time: float
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    phases: List[PhaseMetrics] = None
    system_info: Dict[str, Any] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.phases is None:
            self.phases = []
        if self.system_info is None:
            self.system_info = {}
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class ResourceMonitor:
    """System resource monitoring utilities"""
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage in MB"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total / (1024 * 1024),
            "available": memory.available / (1024 * 1024),
            "used": memory.used / (1024 * 1024),
            "percent": memory.percent
        }
    
    @staticmethod
    def get_disk_io() -> Dict[str, float]:
        """Get disk I/O statistics"""
        disk_io = psutil.disk_io_counters()
        if disk_io:
            return {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count
            }
        return {}
    
    @staticmethod
    def get_network_io() -> Dict[str, float]:
        """Get network I/O statistics"""
        net_io = psutil.net_io_counters()
        if net_io:
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        return {}
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get comprehensive system information"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / (1024 * 1024 * 1024),  # GB
            "platform": psutil.os.name,
            "boot_time": psutil.boot_time(),
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }

class PerformanceMonitor:
    """Main performance monitoring class"""
    
    def __init__(self, db_path: str = "testing/performance_data.db"):
        self.db_path = db_path
        self.current_session: Optional[SessionMetrics] = None
        self.current_phase: Optional[PhaseMetrics] = None
        self.monitoring_active = False
        self.resource_monitor = ResourceMonitor()
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for storing performance data"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    operation_type TEXT,
                    start_time REAL,
                    end_time REAL,
                    total_duration REAL,
                    system_info TEXT,
                    errors TEXT,
                    warnings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    phase_name TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    cpu_usage_start REAL,
                    cpu_usage_end REAL,
                    memory_usage_start REAL,
                    memory_usage_end REAL,
                    memory_peak REAL,
                    disk_io_start TEXT,
                    disk_io_end TEXT,
                    network_io_start TEXT,
                    network_io_end TEXT,
                    custom_metrics TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            
            conn.commit()
    
    def start_session(self, operation_type: str, session_id: Optional[str] = None) -> str:
        """Start a new performance monitoring session"""
        if session_id is None:
            session_id = f"{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        self.current_session = SessionMetrics(
            session_id=session_id,
            operation_type=operation_type,
            start_time=time.time(),
            system_info=self.resource_monitor.get_system_info()
        )
        
        self.monitoring_active = True
        logger.info(f"Started performance monitoring session: {session_id}")
        return session_id
    
    def end_session(self) -> Optional[SessionMetrics]:
        """End the current monitoring session"""
        if not self.current_session:
            logger.warning("No active session to end")
            return None
        
        self.current_session.end_time = time.time()
        self.current_session.total_duration = (
            self.current_session.end_time - self.current_session.start_time
        )
        
        # End any active phase
        if self.current_phase:
            self.end_phase()
        
        # Save to database
        self._save_session_to_db(self.current_session)
        
        session = self.current_session
        self.current_session = None
        self.monitoring_active = False
        
        logger.info(f"Ended performance monitoring session: {session.session_id}")
        return session
    
    def start_phase(self, phase_name: str, custom_metrics: Optional[Dict[str, Any]] = None) -> str:
        """Start monitoring a specific phase"""
        if not self.current_session:
            raise ValueError("No active session. Call start_session() first.")
        
        # End previous phase if active
        if self.current_phase:
            self.end_phase()
        
        # Start memory tracing for this phase
        tracemalloc.start()
        
        self.current_phase = PhaseMetrics(
            phase_name=phase_name,
            start_time=time.time(),
            cpu_usage_start=self.resource_monitor.get_cpu_usage(),
            memory_usage_start=self.resource_monitor.get_memory_usage()["used"],
            disk_io_start=self.resource_monitor.get_disk_io(),
            network_io_start=self.resource_monitor.get_network_io(),
            custom_metrics=custom_metrics or {}
        )
        
        logger.info(f"Started phase: {phase_name}")
        return phase_name
    
    def end_phase(self) -> Optional[PhaseMetrics]:
        """End the current phase"""
        if not self.current_phase:
            logger.warning("No active phase to end")
            return None
        
        if not self.current_session:
            logger.warning("No active session for phase end")
            return None
        
        self.current_phase.end_time = time.time()
        self.current_phase.duration = (
            self.current_phase.end_time - self.current_phase.start_time
        )
        
        # Get final resource measurements
        try:
            self.current_phase.cpu_usage_end = self.resource_monitor.get_cpu_usage()
            self.current_phase.memory_usage_end = self.resource_monitor.get_memory_usage()["used"]
            self.current_phase.disk_io_end = self.resource_monitor.get_disk_io()
            self.current_phase.network_io_end = self.resource_monitor.get_network_io()
        except Exception as e:
            logger.warning(f"Failed to get final resource measurements: {e}")
        
        # Get memory peak
        try:
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                self.current_phase.memory_peak = peak / (1024 * 1024)  # Convert to MB
                tracemalloc.stop()
        except Exception as e:
            logger.warning(f"Failed to get memory peak: {e}")
        
        # Add to session
        self.current_session.phases.append(self.current_phase)
        
        phase = self.current_phase
        self.current_phase = None
        
        logger.info(f"Ended phase: {phase.phase_name} (duration: {phase.duration:.2f}s)")
        return phase
    
    def add_custom_metric(self, key: str, value: Any):
        """Add a custom metric to the current phase"""
        if self.current_phase:
            self.current_phase.custom_metrics[key] = value
        elif self.current_session:
            # If no phase but session exists, add to session metadata
            logger.warning(f"No active phase for custom metric '{key}', adding to session")
            if "custom_metrics" not in self.current_session.system_info:
                self.current_session.system_info["custom_metrics"] = {}
            self.current_session.system_info["custom_metrics"][key] = value
        else:
            logger.warning(f"No active phase or session for custom metric '{key}'")
    
    def add_error(self, error_message: str):
        """Add an error to the current session"""
        if self.current_session:
            self.current_session.errors.append(f"{datetime.now().isoformat()}: {error_message}")
        logger.error(error_message)
    
    def add_warning(self, warning_message: str):
        """Add a warning to the current session"""
        if self.current_session:
            self.current_session.warnings.append(f"{datetime.now().isoformat()}: {warning_message}")
        logger.warning(warning_message)
    
    def _save_session_to_db(self, session: SessionMetrics):
        """Save session data to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Save session
                conn.execute("""
                    INSERT OR REPLACE INTO sessions 
                    (session_id, operation_type, start_time, end_time, total_duration, 
                     system_info, errors, warnings)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id,
                    session.operation_type,
                    session.start_time,
                    session.end_time,
                    session.total_duration,
                    json.dumps(session.system_info),
                    json.dumps(session.errors),
                    json.dumps(session.warnings)
                ))
                
                # Save phases
                for phase in session.phases:
                    conn.execute("""
                        INSERT INTO phases 
                        (session_id, phase_name, start_time, end_time, duration,
                         cpu_usage_start, cpu_usage_end, memory_usage_start, 
                         memory_usage_end, memory_peak, disk_io_start, disk_io_end,
                         network_io_start, network_io_end, custom_metrics)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session.session_id,
                        phase.phase_name,
                        phase.start_time,
                        phase.end_time,
                        phase.duration,
                        phase.cpu_usage_start,
                        phase.cpu_usage_end,
                        phase.memory_usage_start,
                        phase.memory_usage_end,
                        phase.memory_peak,
                        json.dumps(phase.disk_io_start),
                        json.dumps(phase.disk_io_end),
                        json.dumps(phase.network_io_start),
                        json.dumps(phase.network_io_end),
                        json.dumps(phase.custom_metrics)
                    ))
                
                conn.commit()
                logger.info(f"Saved session data to database: {session.session_id}")
                
        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
    
    def get_session_data(self, session_id: str) -> Optional[SessionMetrics]:
        """Retrieve session data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get session
                session_row = conn.execute("""
                    SELECT * FROM sessions WHERE session_id = ?
                """, (session_id,)).fetchone()
                
                if not session_row:
                    return None
                
                # Get phases
                phase_rows = conn.execute("""
                    SELECT * FROM phases WHERE session_id = ? ORDER BY start_time
                """, (session_id,)).fetchall()
                
                # Reconstruct session
                session = SessionMetrics(
                    session_id=session_row[0],
                    operation_type=session_row[1],
                    start_time=session_row[2],
                    end_time=session_row[3],
                    total_duration=session_row[4],
                    system_info=json.loads(session_row[5]) if session_row[5] else {},
                    errors=json.loads(session_row[6]) if session_row[6] else [],
                    warnings=json.loads(session_row[7]) if session_row[7] else []
                )
                
                # Reconstruct phases
                for phase_row in phase_rows:
                    phase = PhaseMetrics(
                        phase_name=phase_row[2],
                        start_time=phase_row[3],
                        end_time=phase_row[4],
                        duration=phase_row[5],
                        cpu_usage_start=phase_row[6],
                        cpu_usage_end=phase_row[7],
                        memory_usage_start=phase_row[8],
                        memory_usage_end=phase_row[9],
                        memory_peak=phase_row[10],
                        disk_io_start=json.loads(phase_row[11]) if phase_row[11] else {},
                        disk_io_end=json.loads(phase_row[12]) if phase_row[12] else {},
                        network_io_start=json.loads(phase_row[13]) if phase_row[13] else {},
                        network_io_end=json.loads(phase_row[14]) if phase_row[14] else {},
                        custom_metrics=json.loads(phase_row[15]) if phase_row[15] else {}
                    )
                    session.phases.append(phase)
                
                return session
                
        except Exception as e:
            logger.error(f"Failed to retrieve session data: {e}")
            return None
    
    def get_all_sessions(self, operation_type: Optional[str] = None) -> List[SessionMetrics]:
        """Get all sessions, optionally filtered by operation type"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if operation_type:
                    session_rows = conn.execute("""
                        SELECT session_id FROM sessions 
                        WHERE operation_type = ? 
                        ORDER BY start_time DESC
                    """, (operation_type,)).fetchall()
                else:
                    session_rows = conn.execute("""
                        SELECT session_id FROM sessions 
                        ORDER BY start_time DESC
                    """).fetchall()
                
                sessions = []
                for row in session_rows:
                    session = self.get_session_data(row[0])
                    if session:
                        sessions.append(session)
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to retrieve sessions: {e}")
            return []

# Context manager for easy phase monitoring
@asynccontextmanager
async def monitor_phase(monitor: PerformanceMonitor, phase_name: str, custom_metrics: Optional[Dict[str, Any]] = None):
    """Async context manager for monitoring phases"""
    monitor.start_phase(phase_name, custom_metrics)
    try:
        yield monitor
    except Exception as e:
        monitor.add_error(f"Error in phase {phase_name}: {str(e)}")
        raise
    finally:
        monitor.end_phase()

# Decorator for monitoring functions
def monitor_function(monitor: PerformanceMonitor, phase_name: Optional[str] = None):
    """Decorator to monitor function execution"""
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            name = phase_name or f"{func.__name__}"
            async with monitor_phase(monitor, name):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            name = phase_name or f"{func.__name__}"
            monitor.start_phase(name)
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                monitor.add_error(f"Error in {name}: {str(e)}")
                raise
            finally:
                monitor.end_phase()
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator