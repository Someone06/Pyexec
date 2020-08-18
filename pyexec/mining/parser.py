from typing import List

from pydefects.util.shell import run_command


def parse_top_4000_packages_json(filePath: str) -> List[str]:
    command = "awk '/project/ {print $2}' " + filePath + "  | sed 's/\\\"//g' | shuf"
    out, _ = run_command(command)
    return out.splitlines()
