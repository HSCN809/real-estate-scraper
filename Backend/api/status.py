class TaskStatus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskStatus, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        self.is_running = False
        self.message = "Hazir"
        self.progress = 0
        self.total = 0
        self.current = 0
        self.details = ""
        # Retry mekanizmasi icin
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

    def to_dict(self):
        return {
            "is_running": self.is_running,
            "message": self.message,
            "progress": self.progress,
            "total": self.total,
            "current": self.current,
            "details": self.details,
            "failed_pages_count": self.failed_pages_count,
            "retry_round": self.retry_round,
            "max_retries": self.max_retries,
            "is_retrying": self.is_retrying,
            "successful_retries": self.successful_retries,
        }


# Global instance
task_status = TaskStatus()
