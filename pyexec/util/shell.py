import subprocess
from typing import Optional, Tuple


def run_command(command: str, timeout: Optional[int] = None) -> Tuple[str, str]:
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    out, err = process.communicate(timeout=timeout)
    return out.decode("utf-8"), err.decode("utf-8")
