from pathlib import Path

import pytest

from pyexec.dependencyInference.inferDependencys import InferDockerfile


@pytest.mark.slow
def test_bayes():
    id: InferDockerfile = InferDockerfile(Path("/home/michael/v2/examples/bayes/"))
    result: str = id.infer_dockerfile()
    print(result)
    assert "Theano" in result and "Lasagne" in result


@pytest.mark.slow
def test_test_runner():
    id: InferDockerfile = InferDockerfile(Path("/home/michael/test-runner"))
    result = id.infer_dockerfile()
    print(result)
    assert False


def test_test_runner_timeout():
    with pytest.raises(InferDockerfile.TimeoutException):
        id: InferDockerfile = InferDockerfile(Path("/home/michael/test-runner"))
        result = id.infer_dockerfile(3)
        print(result)
