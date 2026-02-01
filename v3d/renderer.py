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

        # point locator for picking (built after points are set)
        self.point_locator = vtk.vtkPointLocator()

        # selection pipeline: points for selected indices
        self.selection_points = vtk.vtkPoints()
        self.selection_poly = vtk.vtkPolyData()
        self.selection_poly.SetPoints(self.selection_points)

        self.selection_scales = vtk.vtkFloatArray()
        self.selection_scales.SetName('Scale')
        self.selection_poly.GetPointData().AddArray(self.selection_scales)

        self.selection_colors = vtk.vtkUnsignedCharArray()
        self.selection_colors.SetNumberOfComponents(3)
        self.selection_colors.SetName('Color')
        self.selection_poly.GetPointData().SetScalars(self.selection_colors)

        self.selection_glyph_mapper = vtk.vtkGlyph3DMapper()
        self.selection_glyph_mapper.SetInputData(self.selection_poly)
        self.selection_glyph_mapper.SetSourceConnection(self.sphere.GetOutputPort())
        self.selection_glyph_mapper.ScalingOn()
        self.selection_glyph_mapper.SetScaleArray('Scale')
        self.selection_glyph_mapper.SetColorModeToDirectScalars()

        self.selection_actor = vtk.vtkActor()
        self.selection_actor.SetMapper(self.selection_glyph_mapper)
        self.ren.AddActor(self.selection_actor)
        self.actors.append(self.selection_actor)

        # track selected point ids
        self.selected_ids = []

        # keep original per-point scales and colors so we can restore on deselect
        self._orig_scales = []
        self._orig_colors = []

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
        self.grid_actor = self._create_grid(extent=100, spacing=1.0)
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

        # reset original lists
        self._orig_scales = []
        self._orig_colors = []

        for p in pts:
            x, y, z = float(p.get('x', 0)), float(p.get('y', 0)), float(p.get('z', 0))
            idp = self.point_points.InsertNextPoint(x, y, z)
            scale = float(p.get('size', 6)) * 0.05
            self.point_scales.InsertNextValue(scale)
            rgb = _to_uchar_rgb(p.get('color', [1, 1, 1, 1]))
            self.point_colors.InsertNextTuple3(rgb[0], rgb[1], rgb[2])
            # store originals so we can restore on deselect
            self._orig_scales.append(scale)
            self._orig_colors.append((rgb[0], rgb[1], rgb[2]))

        self.point_poly.Modified()

        # rebuild locator for picking
        try:
            self.point_locator.SetDataSet(self.point_poly)
            self.point_locator.BuildLocator()
        except Exception:
            pass

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
        # update selection actor (keep selection after re-render)
        self._update_selection_actor()

        # reset camera and render
        self.ren.ResetCamera()
        self.interactor_widget.GetRenderWindow().Render()

    def _update_selection_actor(self):
        # Update the main point arrays to reflect selection highlights and
        # restore original values for deselected points.
        n = self.point_points.GetNumberOfPoints()
        # ensure orig arrays length matches; if not, rebuild from arrays
        if len(self._orig_scales) != n:
            try:
                self._orig_scales = [self.point_scales.GetValue(i) for i in range(n)]
            except Exception:
                self._orig_scales = [0.05 for _ in range(n)]
        if len(self._orig_colors) != n:
            try:
                self._orig_colors = [tuple(int(c) for c in self.point_colors.GetTuple(i)) for i in range(n)]
            except Exception:
                self._orig_colors = [(255, 255, 255) for _ in range(n)]

        # restore all to original
        for i in range(n):
            try:
                self.point_scales.SetValue(i, float(self._orig_scales[i]))
            except Exception:
                pass
            try:
                r, g, b = self._orig_colors[i]
                self.point_colors.SetTuple3(i, int(r), int(g), int(b))
            except Exception:
                pass

        # apply highlight (enlarge + red) for selected ids
        for pid in list(self.selected_ids):
            if pid < 0 or pid >= n:
                continue
            try:
                new_scale = float(self._orig_scales[pid]) * 2.5
                self.point_scales.SetValue(pid, new_scale)
                self.point_colors.SetTuple3(pid, 255, 0, 0)
            except Exception:
                continue

        # mark modified
        self.point_poly.Modified()

    def pick_and_select(self, display_x: int, display_y: int, multi: bool = True):
        """Pick nearest point from display coordinates (Qt coords) and add to selection.

        Returns selected point index or None.
        """
        if vtk is None:
            return None
        # convert Qt y to VTK display y (origin at lower-left)
        height = self.interactor_widget.height()
        vtk_y = height - display_y

        picker = vtk.vtkCellPicker()
        # increase tolerance to make picking easier
        picker.SetTolerance(0.01)
        ok = picker.Pick(display_x, vtk_y, 0, self.ren)
        pick_pos = picker.GetPickPosition()

        # Prefer candidates within a small world-space radius, then pick
        # the one with smallest screen-space distance to the click.
        pid = -1
        candidates = []
        try:
            idlist = vtk.vtkIdList()
            search_radius = 4.0
            self.point_locator.FindPointsWithinRadius(search_radius, pick_pos, idlist)
            for ii in range(idlist.GetNumberOfIds()):
                cid = idlist.GetId(ii)
                px, py, pz = self.point_points.GetPoint(cid)
                # convert world -> display
                self.ren.SetWorldPoint(px, py, pz, 1.0)
                self.ren.WorldToDisplay()
                dpx, dpy, _ = self.ren.GetDisplayPoint()
                dxs = dpx - display_x
                dys = dpy - vtk_y
                candidates.append((dxs*dxs + dys*dys, cid))
        except Exception:
            candidates = []

        if candidates:
            candidates.sort(key=lambda x: x[0])
            # threshold in pixels (20 px) — allow a larger tolerance for easier picking
            if candidates[0][0] > (20*20):
                return None
            pid = candidates[0][1]
        else:
            # fallback: use locator closest point in world-space
            try:
                pid = self.point_locator.FindClosestPoint(pick_pos)
            except Exception:
                pid = -1
            if pid < 0:
                return None
            px, py, pz = self.point_points.GetPoint(pid)
            dx = px - pick_pos[0]
            dy = py - pick_pos[1]
            dz = pz - pick_pos[2]
            dist2 = dx*dx + dy*dy + dz*dz
            if dist2 > (2.0 * 2.0):
                return None

        # selection logic: if multi (Alt pressed) then toggle membership
        if not multi:
            self.selected_ids = [pid]
        else:
            if pid in self.selected_ids:
                try:
                    self.selected_ids.remove(pid)
                except ValueError:
                    pass
            else:
                self.selected_ids.append(pid)

        self._update_selection_actor()
        self.interactor_widget.GetRenderWindow().Render()
        return pid
