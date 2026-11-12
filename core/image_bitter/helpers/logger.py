
_enabled = False

def enable_logging() -> None:
    global _enabled
    _enabled = True

def log(message: any) -> None:
    if _enabled:
        print(message)

def log_error(e: Exception, traceback: str) -> None:
    print(e)
    print(str)
