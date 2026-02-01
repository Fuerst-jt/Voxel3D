"""
High-performance VTK renderer.

Points are rendered using a single vtkPolyData + vtkGlyph3DMapper (batching),
and segments (lines) are rendered using a vtkPolyData with vtkCellArray.
This reduces actor count and improves performance for large datasets.
"""
from typing import Any

try:
    import vtkmodules.all as vtk
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    from vtkmodules.util.numpy_support import numpy_to_vtk
except Exception:
    vtk = None
    QVTKRenderWindowInteractor = None


def _to_uchar_rgb(color):
    # accept [r,g,b,a] floats 0-1, return 3-uint8
    return [int(max(0, min(1, c)) * 255) for c in color[:3]]


class SceneRenderer:
    def __init__(self, interactor_widget: Any):
        if vtk is None or QVTKRenderWindowInteractor is None:
            raise RuntimeError('VTK is required for SceneRenderer')

        self.interactor_widget = interactor_widget
        self.ren = vtk.vtkRenderer()
        rw = interactor_widget.GetRenderWindow()
        rw.AddRenderer(self.ren)
        self.iren = rw.GetInteractor()
        self.actors = []

        # set Trackball camera style
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)

        # prepare point pipeline (empty, will fill in render)
        self.point_poly = vtk.vtkPolyData()
        self.point_points = vtk.vtkPoints()
        self.point_poly.SetPoints(self.point_points)

        self.point_scales = vtk.vtkFloatArray()
        self.point_scales.SetName('Scale')
        self.point_poly.GetPointData().AddArray(self.point_scales)

        self.point_colors = vtk.vtkUnsignedCharArray()
        self.point_colors.SetNumberOfComponents(3)
        self.point_colors.SetName('Color')
        self.point_poly.GetPointData().SetScalars(self.point_colors)

        # glyph mapper for spheres
        self.sphere = vtk.vtkSphereSource()
        self.sphere.SetThetaResolution(8)
        self.sphere.SetPhiResolution(8)

        self.glyph_mapper = vtk.vtkGlyph3DMapper()
        self.glyph_mapper.SetInputData(self.point_poly)
        self.glyph_mapper.SetSourceConnection(self.sphere.GetOutputPort())
        self.glyph_mapper.ScalingOn()
        self.glyph_mapper.SetScaleArray('Scale')
        self.glyph_mapper.SetColorModeToDirectScalars()

        self.point_actor = vtk.vtkActor()
        self.point_actor.SetMapper(self.glyph_mapper)
        self.ren.AddActor(self.point_actor)
        self.actors.append(self.point_actor)

        # line actor placeholders
        self.line_poly = vtk.vtkPolyData()
        self.line_points = vtk.vtkPoints()
        self.line_poly.SetPoints(self.line_points)
        self.lines_cells = vtk.vtkCellArray()
        self.line_poly.SetLines(self.lines_cells)

        self.line_colors = vtk.vtkUnsignedCharArray()
        self.line_colors.SetNumberOfComponents(3)
        self.line_colors.SetName('Color')
        self.line_poly.GetCellData().SetScalars(self.line_colors)

        self.line_mapper = vtk.vtkPolyDataMapper()
        self.line_mapper.SetInputData(self.line_poly)
        self.line_actor = vtk.vtkActor()
        self.line_actor.SetMapper(self.line_mapper)
        self.ren.AddActor(self.line_actor)
        self.actors.append(self.line_actor)

        # add XOY grid (spacing 1.0 m, extent +/-10m by default)
        self.grid_actor = self._create_grid(extent=10, spacing=1.0)
        if self.grid_actor is not None:
            self.ren.AddActor(self.grid_actor)

    def clear(self):
        # clear point and line data
        self.point_points.Reset()
        self.point_scales.Reset()
        self.point_colors.Reset()
        self.point_poly.GetPointData().Modified()

        self.line_points.Reset()
        self.lines_cells.Reset()
        self.line_colors.Reset()
        self.line_poly.GetCellData().Modified()

        self.interactor_widget.GetRenderWindow().Render()

    def _create_grid(self, extent=10, spacing=1.0):
        """Create a grid on the XOY plane centered at origin.

        extent: half-extent in meters (draw lines from -extent to +extent)
        spacing: grid spacing in meters
        """
        if vtk is None:
            return None

        pts = vtk.vtkPoints()
        lines = vtk.vtkCellArray()

        n_steps = int((2 * extent) / spacing)
        # ensure inclusive endpoints
        xs = [(-extent + i * spacing) for i in range(n_steps + 1)]
        ys = xs

        pid = 0
        # horizontal lines (constant y, varying x)
        for y in ys:
            start_id = None
            for x in xs:
                pts.InsertNextPoint(float(x), float(y), 0.0)
                if start_id is None:
                    start_id = pid
                pid += 1
            # create polyline for this row
            poly = vtk.vtkPolyLine()
            poly.GetPointIds().SetNumberOfIds(len(xs))
            for i in range(len(xs)):
                poly.GetPointIds().SetId(i, start_id + i)
            lines.InsertNextCell(poly)

        # vertical lines (constant x, varying y)
        for x in xs:
            start_id = None
            for y in ys:
                pts.InsertNextPoint(float(x), float(y), 0.0)
                if start_id is None:
                    start_id = pid
                pid += 1
            poly = vtk.vtkPolyLine()
            poly.GetPointIds().SetNumberOfIds(len(ys))
            for i in range(len(ys)):
                poly.GetPointIds().SetId(i, start_id + i)
            lines.InsertNextCell(poly)

        grid_poly = vtk.vtkPolyData()
        grid_poly.SetPoints(pts)
        grid_poly.SetLines(lines)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(grid_poly)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.7, 0.7, 0.7)
        actor.GetProperty().SetLighting(False)
        actor.GetProperty().SetLineWidth(1)
        return actor

    def render(self, model):
        # batch points
        pts = model.points
        segs = model.segments

        self.point_points.Reset()
        self.point_scales.Reset()
        self.point_colors.Reset()

        for p in pts:
            x, y, z = float(p.get('x', 0)), float(p.get('y', 0)), float(p.get('z', 0))
            idp = self.point_points.InsertNextPoint(x, y, z)
            scale = float(p.get('size', 6)) * 0.05
            self.point_scales.InsertNextValue(scale)
            rgb = _to_uchar_rgb(p.get('color', [1, 1, 1, 1]))
            self.point_colors.InsertNextTuple3(rgb[0], rgb[1], rgb[2])

        self.point_poly.Modified()

        # batch lines
        self.line_points.Reset()
        self.lines_cells.Reset()
        self.line_colors.Reset()
        pid = 0
        for seg in segs:
            s = seg.get('start')
            e = seg.get('end')
            if not s or not e:
                continue
            p0 = self.line_points.InsertNextPoint(float(s[0]), float(s[1]), float(s[2]))
            p1 = self.line_points.InsertNextPoint(float(e[0]), float(e[1]), float(e[2]))
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, pid)
            line.GetPointIds().SetId(1, pid+1)
            self.lines_cells.InsertNextCell(line)
            pid += 2
            rgb = _to_uchar_rgb(seg.get('color', [1,1,1,1]))
            self.line_colors.InsertNextTuple3(rgb[0], rgb[1], rgb[2])

        self.line_poly.Modified()

        # reset camera and render
        self.ren.ResetCamera()
        self.interactor_widget.GetRenderWindow().Render()
