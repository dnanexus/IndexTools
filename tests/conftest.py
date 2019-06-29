from pathlib import Path
import pytest


class DataPath(object):
    def __init__(self, datadir_obj):
        self.datadir_obj = datadir_obj

    def __getitem__(self, path):
        pypath = self.datadir_obj[path]
        return Path(pypath)


@pytest.fixture
def datapath(datadir):
    return DataPath(datadir)


@pytest.fixture
def datapath_copy(datadir_copy):
    return DataPath(datadir_copy)
