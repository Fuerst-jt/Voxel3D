"""
Renderer adapts a SceneModel to a pyqtgraph.opengl GLViewWidget.
"""
from typing import Optional
import numpy as np
import pyqtgraph.opengl as gl

class SceneRenderer:
    def __init__(self, view: gl.GLViewWidget):
        self.view = view
        self.scatter: Optional[gl.GLScatterPlotItem] = None
        self.lines = []

    def clear(self):
        if self.scatter is not None:
            self.view.removeItem(self.scatter)
            self.scatter = None
        for l in self.lines:
            self.view.removeItem(l)
        self.lines = []

    def render(self, model):
        self.clear()
        pts = model.points
        segs = model.segments
        if pts:
            pos = np.array([[p.get('x',0), p.get('y',0), p.get('z',0)] for p in pts], dtype=float)
            sizes = np.array([p.get('size',6) for p in pts], dtype=float)
            cols = np.array([p.get('color',[1,1,1,1]) for p in pts], dtype=float)
            self.scatter = gl.GLScatterPlotItem(pos=pos, size=sizes, color=cols)
            self.view.addItem(self.scatter)
        for seg in segs:
            s = seg.get('start')
            e = seg.get('end')
            if not s or not e:
                continue
            pts = np.vstack([s, e])
            color = seg.get('color', [1,1,1,1])
            line = gl.GLLinePlotItem(pos=pts, color=color, width=seg.get('width',2), antialias=True)
            self.view.addItem(line)
            self.lines.append(line)
