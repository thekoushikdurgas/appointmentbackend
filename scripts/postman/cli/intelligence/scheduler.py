"""Smart scheduler for automated test execution."""

import time
from typing import Callable, Optional, Dict, Any
from datetime import datetime
from threading import Thread

# Try to import schedule, but make it optional
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    # Create a minimal schedule mock
    class schedule:
        @staticmethod
        def every(seconds):
            class Every:
                def seconds(self):
                    return self
                def do(self, func):
                    return None
            return Every()
        
        @staticmethod
        def run_pending():
            pass
        
        @staticmethod
        def clear(job_id=None):
            pass


class SmartScheduler:
    """Schedules and manages automated test runs."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.scheduler_thread: Optional[Thread] = None
    
    def add_job(
        self,
        job_id: str,
        test_function: Callable,
        interval_seconds: int = 300,
        **kwargs
    ) -> bool:
        """Add a scheduled test job.
        
        Args:
            job_id: Unique job identifier
            test_function: Function to execute
            interval_seconds: Interval between runs (seconds)
            **kwargs: Additional arguments to pass to test function
        
        Returns:
            True if job added successfully
        """
        if job_id in self.jobs:
            return False
        
        # Schedule the job (if schedule is available)
        if SCHEDULE_AVAILABLE:
            schedule.every(interval_seconds).seconds.do(
                self._wrap_test_function(job_id, test_function, **kwargs)
            )
        
        self.jobs[job_id] = {
            "test_function": test_function,
            "interval_seconds": interval_seconds,
            "kwargs": kwargs,
            "last_run": None,
            "next_run": datetime.now().timestamp() + interval_seconds,
            "run_count": 0,
            "success_count": 0,
            "failure_count": 0
        }
        
        return True
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if job removed successfully
        """
        if job_id not in self.jobs:
            return False
        
        # Clear the job from schedule
        if SCHEDULE_AVAILABLE:
            schedule.clear(job_id)
        del self.jobs[job_id]
        
        return True
    
    def _wrap_test_function(self, job_id: str, test_function: Callable, **kwargs):
        """Wrap test function to track execution.
        
        Args:
            job_id: Job identifier
            test_function: Function to wrap
            **kwargs: Arguments to pass to function
        """
        def wrapped():
            job = self.jobs.get(job_id)
            if not job:
                return
            
            job["last_run"] = datetime.now()
            job["run_count"] += 1
            
            try:
                result = test_function(**kwargs)
                if result and result.get("success", False):
                    job["success_count"] += 1
                else:
                    job["failure_count"] += 1
            except Exception as e:
                job["failure_count"] += 1
                print(f"Job {job_id} failed: {e}")
            
            # Update next run time
            job["next_run"] = datetime.now().timestamp() + job["interval_seconds"]
        
        return wrapped
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            return
        
        self.running = True
        
        def run_scheduler():
            while self.running:
                if SCHEDULE_AVAILABLE:
                    schedule.run_pending()
                time.sleep(1)
        
        self.scheduler_thread = Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if SCHEDULE_AVAILABLE:
            schedule.clear()
        self.jobs.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status.
        
        Returns:
            Status dictionary
        """
        return {
            "running": self.running,
            "job_count": len(self.jobs),
            "jobs": {
                job_id: {
                    "interval_seconds": job["interval_seconds"],
                    "last_run": job["last_run"].isoformat() if job["last_run"] else None,
                    "next_run": datetime.fromtimestamp(job["next_run"]).isoformat() if job["next_run"] else None,
                    "run_count": job["run_count"],
                    "success_count": job["success_count"],
                    "failure_count": job["failure_count"]
                }
                for job_id, job in self.jobs.items()
            }
        }

