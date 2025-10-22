#!/usr/bin/env python3
"""
Resource monitoring module for EyeWitness
Monitors memory usage and provides resource limits
"""

import psutil
import os
import sys


class ResourceMonitor:
    """Monitor system resources and enforce limits"""
    
    def __init__(self, memory_limit_percent=80):
        """
        Initialize resource monitor
        
        Args:
            memory_limit_percent (int): Maximum memory usage percentage allowed
        """
        self.memory_limit_percent = memory_limit_percent
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.get_memory_usage()
        
    def get_memory_usage(self):
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_memory_percent(self):
        """Get current memory usage as percentage of system memory"""
        return self.process.memory_percent()
    
    def check_memory_limit(self):
        """
        Check if memory usage exceeds limit
        
        Returns:
            tuple: (is_over_limit, current_usage_mb, limit_mb)
        """
        current_percent = self.get_memory_percent()
        current_mb = self.get_memory_usage()
        total_mb = psutil.virtual_memory().total / 1024 / 1024
        limit_mb = (total_mb * self.memory_limit_percent) / 100
        
        is_over = current_percent > self.memory_limit_percent
        
        return is_over, current_mb, limit_mb
    
    def get_recommended_threads(self, base_threads=None):
        """
        Get recommended thread count based on available memory
        
        Args:
            base_threads (int): Base thread count (default: CPU cores * 2)
            
        Returns:
            int: Recommended thread count
        """
        if base_threads is None:
            base_threads = psutil.cpu_count() * 2
        
        # Get available memory in GB
        available_gb = psutil.virtual_memory().available / 1024 / 1024 / 1024
        
        # Estimate ~200MB per thread for Firefox instances
        max_threads_by_memory = int(available_gb * 1024 / 200)
        
        # Use the minimum of CPU-based and memory-based calculations
        recommended = min(base_threads, max_threads_by_memory, 20)
        
        # Ensure at least 1 thread
        return max(1, recommended)
    
    def format_memory_info(self):
        """
        Get formatted memory information string
        
        Returns:
            str: Formatted memory info
        """
        mem = psutil.virtual_memory()
        current_mb = self.get_memory_usage()
        
        return (f"Memory: {current_mb:.1f}MB used "
                f"({mem.percent:.1f}% of {mem.total / 1024 / 1024 / 1024:.1f}GB total)")
    
    def should_reduce_threads(self, current_threads):
        """
        Check if thread count should be reduced due to memory pressure
        
        Args:
            current_threads (int): Current number of threads
            
        Returns:
            tuple: (should_reduce, recommended_threads)
        """
        is_over, current_mb, limit_mb = self.check_memory_limit()
        
        if not is_over:
            return False, current_threads
        
        # Reduce threads by 25% if over limit
        new_threads = max(1, int(current_threads * 0.75))
        
        return True, new_threads


def check_disk_space(path, min_gb=1):
    """
    Check if sufficient disk space is available
    
    Args:
        path (str): Path to check disk space for
        min_gb (float): Minimum required space in GB
        
    Returns:
        tuple: (has_space, available_gb, total_gb)
    """
    try:
        stat = psutil.disk_usage(path)
        available_gb = stat.free / 1024 / 1024 / 1024
        total_gb = stat.total / 1024 / 1024 / 1024
        
        has_space = available_gb >= min_gb
        
        return has_space, available_gb, total_gb
    except Exception:
        # If we can't check, assume we have space
        return True, 0, 0


def get_system_info():
    """
    Get formatted system information
    
    Returns:
        str: System information string
    """
    cpu_count = psutil.cpu_count()
    mem = psutil.virtual_memory()
    
    info = f"System: {cpu_count} CPU cores, "
    info += f"{mem.total / 1024 / 1024 / 1024:.1f}GB RAM "
    info += f"({mem.available / 1024 / 1024 / 1024:.1f}GB available)"
    
    return info