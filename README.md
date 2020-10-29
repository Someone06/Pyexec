# Pyexec

Pyexec can be used to mine projects from GitHub, infer environments for them and execute their Pytest test suite if present.

[![License LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org)

## Prerequisites
Pyexec has several dependencies:
    * Command line tools: cloc, wget, sed, tr, wc and several other basic command-line programs
    * Docker and docker-compose
    * redis-server
    * nodejs
    * A fork of V2 (https://github.com/v2-project/v2)
    * python 3.8 and pipenv (https://github.com/pypa/pipenv)
Further dependencies are automatically managed through pipenv.

## Installation
Use the instruction for V2 and set it up.
Ensure you have cloc and wget installed.
Use pipenv to setup your environment after cloning the Pyexec repository.
If you are only interested in running Pyexec,
it is sufficient to install only the run dependencies by running
```bash
pipenv install
```
For development,
it is necessary to install a few further dependencies by
```bash
pipenv install --dev
```
## Usage
To mine 100 random packages from PyPI use
```bash
pipenv run python3 pyexec-miner -r 100
```
To mine packages listed in a file packages.txt (Format: Name of a PyPI package, one per line)
```bash
pipenv run python3 pyexec-miner -p package.txt
```

## Output
The program creates the folder ~/pyexec-output. 
In this folder a folder with the time stamp at start is created for every run of Pyexec.

## Bugs
Pyexec uses the temporary folder /tmp/pyexec_cache for checking out repositories.
This folder should be deleted automatically when Pyexec competes its run.
However some project contain "\_\_pycache\_\_" folders with root privileges.
Attempting to delete such a folder causes a PermissionError by the operating system.
To clean up such folder during a run of Pyexec take a look at the clean.sh script.
Additionally, the folder can be deleted manually after Pyexec completes.

If a mined git repository does not contain any Python files then attempting to calculate the average cyclomatic complexity of that repository will fail with an error entry in the log.

If two instances of Pyexec attempt to mine the same project at the same time this will cause errors.

## License
This file is part of Pyexec.

Pyexec is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Pyexec is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with PyDefects.  If not, see
[https://www.gnu.org/licenses/](https://www.gnu.org/licenses/).
