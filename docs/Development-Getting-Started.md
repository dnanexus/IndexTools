# IndexTools

IndexTools complies with [PEP-518](https://www.python.org/dev/peps/pep-0518/) _"Specifying Minimum Build System Requirements for Python Projects"_. We leverage the new _pyproject.toml_ specification to streamline our development process. The prerequisites to start development in IndexTools are `python3.6` and `poetry`. Poetry is a dependency management and packaging tool that supports [PEP-518](https://www.python.org/dev/peps/pep-0518/) _pyproject.toml_ files. It allows you to interactively declare the libraries your project depends on and also manages the install/update them for you.

This document outlines two approaches to resolving the aforementioned dependencies:

* [Dockerize quick-start](#docker-quick-start)
* [local installation with optional pyenv dependency](#local-dev)

Once prerequisites are resolved, move to the [Install IndexTools](#install-indextools) section to begin IndexTools development.

## Docker quick-start

The repository contains a [Dockerfile for IndexTools](/docker/Dockerfile) development. pulling and running this image can kickstart the development process.

### Download and run image

Currently, we host a docker image containing Indextools on [Docker Hub](https://hub.docker.com/r/commandlinegirl/indextools-dev).

```bash
docker run --rm -it -v <IndexTools project root>:/IndexTools  commandlinegirl/indextools-dev:0.0.1 /bin/bash
```

Executing this command will:

1. Download the image indextools-dev:0.0.1 from Docker Hub.
2. Initialize a container running the image indextools-dev:0.0.1
3. Create and mount a volume to the container in `/IndexTools` containing the IndexTools repository.
4. Enter a `bash` shell interactively in the image environment.
5. Remove the container on exit.

In the bash session in the image `cd` to `/IndexTools` and perform the steps outlined in the [Install IndexTools](#install-indextools) section.

## Local Dev

If developing directly on your local machine using virtual environments, you'll need `python3.6` and poetry to resolve pyproject.toml configurations. If you already have `python3.6` feel free to skip the pyenv sections.

### Install Poetry

Follow the installation instructions at https://poetry.eustace.io/docs/#installation.

For most developers, this should be:

```bash
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
```

Once installed either restart the shell or `source` your `~/.bashrc`/`~/.bash_profile` file. and verify the following command runs successfully:

```bash
poetry --version
```

### Install pyenv (optional)

[Pyenv](https://github.com/pyenv/pyenv) is used to vendor python versions; alongside the `pyenv virtualenv` extension it can also manage virtual environments. The recommendation is to install pyenv and its extensions with _homebrew_. If need be, other installation methods are available in the [pyenv documentation](https://github.com/pyenv/pyenv#installation).

```bash
brew update
brew install "pyenv"
brew install "pyenv-virtualenv"
```

Once installed, verify that your `~/.bashrc`/`~/.bash_profile` file contains the following pyenv initialization. If it does not, add the lines:

```bash
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Now you can install `python3.6` and create a virtualenv for IndexTools development:

```bash
cd <IndexTools project root>
pyenv install 3.6.8
pyenv virtualenv 3.6.8 Indextools
pyenv local indextools
```

From now on all python commands will use the _indextools_ virtual environment.

#### Install failed, "zlib not available" on macOS Mojave

If you're on Mojave installation on macOS, your `pyenv` installation may fail. Luckily this issue [has been encountered by other](https://github.com/pyenv/pyenv/issues/1219) and there is a known workaround. In the terminal run the following command:

```bash
open /Library/Developer/CommandLineTools/Packages/macOS_SDK_headers_for_macOS_10.14.pkg
```

Follow the directions and prompts to install the macOS backports. Afterward, reattempt the pyenv `brew` installation.

## Install IndexTools

After resolving `poetry` and `python3.6` dependencies you can install Indextools:

```bash
cd <IndexTools project root>
poetry install
```

This will install the remaining dependencies required to develop IndexTools. Happy developing!
