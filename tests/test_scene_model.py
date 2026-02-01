import os
import json
import tempfile
from v3d.scene_model import SceneModel


def test_randomize_and_export():
    m = SceneModel()
    m.randomize(n_points=10, n_segments=3)
    p, s = m.counts
    assert p == 10
    assert s == 3
    d = m.to_dict()
    assert 'points' in d and 'segments' in d
    # export to temp file
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    try:
        m.export_json(path)
        with open(path, 'r') as f:
            loaded = json.load(f)
        assert len(loaded['points']) == 10
        assert len(loaded['segments']) == 3
    finally:
        os.remove(path)
