# storage/locks.py
# Lock simples (opcional no MVP). Você pode evoluir depois.
from pathlib import Path
import time

def acquire_lock(lock_path: Path, timeout_s: float = 5.0, poll_s: float = 0.05) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            lock_path.mkdir(parents=True, exist_ok=False)
            return True
        except FileExistsError:
            time.sleep(poll_s)
    return False

def release_lock(lock_path: Path) -> None:
    if lock_path.exists() and lock_path.is_dir():
        for p in lock_path.iterdir():
            p.unlink()
        lock_path.rmdir()
