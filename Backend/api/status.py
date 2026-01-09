class TaskStatus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskStatus, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance
    
    def reset(self):
        self.is_running = False
        self.message = "Hazır"
        self.progress = 0
        self.total = 0
        self.current = 0
        self.details = ""
        self.should_stop = False  # Durdurma flag'i
        self.stopped_early = False  # Erken durduruldu mu?
        # Retry mekanizması için
        self.failed_pages_count = 0
        self.retry_round = 0
        self.max_retries = 3
        self.is_retrying = False
        self.successful_retries = 0
    
    def update(self, message=None, progress=None, current=None, total=None, details=None):
        if message is not None:
            self.message = message
        if progress is not None:
            self.progress = progress
        if current is not None:
            self.current = current
        if total is not None:
            self.total = total
        if details is not None:
            self.details = details
            
    def set_running(self, running: bool):
        self.is_running = running
    
    def request_stop(self):
        """Taramayı durdurmayı talep et"""
        self.should_stop = True
        self.message = "Durdurma isteği alındı, mevcut veriler kaydediliyor..."
    
    def is_stop_requested(self) -> bool:
        """Durdurma talep edildi mi?"""
        return self.should_stop

    def to_dict(self):
        return {
            "is_running": self.is_running,
            "message": self.message,
            "progress": self.progress,
            "total": self.total,
            "current": self.current,
            "details": self.details,
            "should_stop": self.should_stop,
            "stopped_early": self.stopped_early,
            "failed_pages_count": self.failed_pages_count,
            "retry_round": self.retry_round,
            "max_retries": self.max_retries,
            "is_retrying": self.is_retrying,
            "successful_retries": self.successful_retries
        }

# Global instance
task_status = TaskStatus()
