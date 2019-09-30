from indextools.index import VolumeInterval, group_lpt


def test_lpt():
    ivls = [
        VolumeInterval("1", 1, 10, 100),
        VolumeInterval("2", 1, 10, 10),
        VolumeInterval("3", 1, 10, 200),
        VolumeInterval("4", 1, 10, 50),
        VolumeInterval("5", 1, 10, 45)
    ]
    groups = group_lpt(ivls, 3)
    assert set(tuple(sorted(i.contig for i in group)) for group in groups) == {
        ("1",), ("3",), ("2", "4", "5")
    }
