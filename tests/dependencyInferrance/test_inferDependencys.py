from pyexec.dependencyInference.inferDependencys import InferDockerfile


def test_bayes():
    id: InferDockerfile = InferDockerfile("/home/michael/v2/examples/bayes/")
    result: str = id.inferDockerfile()
    print(result)
    assert "Theano" in result and "Lasagne" in result
