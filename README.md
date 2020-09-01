# Pyexec

Pyexec can be used to mine projects from GitHub, infer enviroments for them and execute their pytest testsuit if present.

[![License LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Python 3.7](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org)

## Prerequisites
To run or use Pyexec you need several dependendencys:
    - Command line tools: git, wget, cloc
    - Docker and docker-compose
    - redis-server
    - nodejs
    - A fork of V2 (https://github.com/v2-project/v2)
    - python 3.8 and pipenv (https://github.com/pypa/pipenv)

## Installation
Use the instruction for v2 and set it up.
Use `pipenv` to setup your environment after cloning the pyexec repository.
If you are only interested in running Pyexec,
it is sufficient to install only the run dependencies by running
```bash
pipenv install
```
To run the tool (consider `foo.py` as an example here), use
```bash
pipenv run python foo.py
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

### Output
The program creates the folder ~/pyexec-output. 
In this foder a folder with the timestap at start is created for every run of Pyexec.

## Bugs
Pyexec uses the temporary folder /tmp/pyexec_cache for checking out repositorys.
This folder should be deleted automatically when pyexec competes its run.
However some project contain "__pycache__" folders with root privilages.
Attepemting to delete such a folder causes a PermissionError by the operating system.
However, the folder should be deleted automatically when the machine is shut down (because it is placed int the /tmp foder).
Alternatively, the fodler can be deleted manually after pyexec completes.

If two instances of pyexec attempt to mine the same project at the same time this will cause errors.

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
