"""Small standard-library process diagnostics; unavailable fields remain null."""
import os
import platform
import threading
import time
from pathlib import Path


class ProcessStats:
    def __init__(self):
        self.lock=threading.Lock()
        self.wall=time.monotonic()
        self.cpu=time.process_time()
        self.percent=0.0

    def snapshot(self):
        with self.lock:
            now,cpu=time.monotonic(),time.process_time()
            if now-self.wall>=.5:
                self.percent=100*(cpu-self.cpu)/(now-self.wall)
                self.wall,self.cpu=now,cpu
            rss=available=None
            try:
                for line in Path("/proc/self/status").read_text().splitlines():
                    if line.startswith("VmRSS:"): rss=int(line.split()[1])*1024
                for line in Path("/proc/meminfo").read_text().splitlines():
                    if line.startswith("MemAvailable:"): available=int(line.split()[1])*1024
            except (OSError,ValueError): pass
            return dict(processCpuPercent=round(self.percent,2),rssBytes=rss,
                        availableMemoryBytes=available,architecture=platform.machine(),
                        pid=os.getpid(),measurementHost=platform.node())
