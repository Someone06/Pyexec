from pyexec.util.shell import run_command
import pytest
import subprocess


def test_run_command_simple():
    out, err = run_command("echo \"Test\"")
    assert(out == "Test\n")


def test_run_command_error():
    out, err = run_command(">&2 echo \"error\"")
    assert(err == "error\n")


def test_run_command_timeout():
    with pytest.raises(subprocess.TimeoutExpired):
        out, err = run_command("sleep 5s && echo \"done\"", 2)
