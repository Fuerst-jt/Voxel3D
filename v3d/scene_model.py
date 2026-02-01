"""
Scene data model: points and segments, export/import, random generation.
"""
import json
import random
from typing import List, Dict, Any

class SceneModel:
    def __init__(self):
        self.points: List[Dict[str, Any]] = []
        self.segments: List[Dict[str, Any]] = []

    def clear(self):
        self.points = []
        self.segments = []

    def set_from_dict(self, data: Dict[str, Any]):
        self.points = data.get('points', []) if isinstance(data, dict) else []
        self.segments = data.get('segments', []) if isinstance(data, dict) else []

    def to_dict(self) -> Dict[str, Any]:
        return {'points': self.points, 'segments': self.segments}

    def export_json(self, path: str):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def randomize(self, n_points: int = 20, n_segments: int = 5, bounds=((-5,5),(-5,5),(-2,2))):
        self.clear()
        bx, by, bz = bounds
        for i in range(n_points):
            x = random.uniform(*bx)
            y = random.uniform(*by)
            z = random.uniform(*bz)
            pt = {'id': f'p{i}', 'x': x, 'y': y, 'z': z, 'size': random.uniform(4,10), 'color': [random.random(), random.random(), random.random(), 1.0]}
            self.points.append(pt)
        for i in range(n_segments):
            s = random.choice(self.points)
            e = random.choice(self.points)
            seg = {'start': [s['x'], s['y'], s['z']], 'end': [e['x'], e['y'], e['z']], 'color': [random.random(), random.random(), random.random(), 1.0], 'width': 2}
            self.segments.append(seg)

    @property
    def counts(self):
        return len(self.points), len(self.segments)
