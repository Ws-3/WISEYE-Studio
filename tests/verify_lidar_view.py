"""Desktop-only regression: validate geometry and render all point-cloud projections."""
import math
from pathlib import Path
import apps.desktop_app.main
from PySide6.QtWidgets import QApplication
from apps.desktop_app.lidar_view import LidarView, clean_points, project_point

app=QApplication([])
assert clean_points([[1,2,3],[float('nan'),0,0],[1,2],['bad',0,0],None]) == [(1.,2.,3.)]
assert project_point((10,2,3),'front') == (2,3)
assert project_point((10,2,3),'top') == (2,10)
# Height must affect the 3D projection, unlike the previous X/Y-only view.
a=project_point((10,0,0),'3d');b=project_point((10,0,2),'3d')
assert abs(b[1]-a[1])>1
view=LidarView();view.resize(900,550);view.show()
points=[[10,y,z] for y in [-2,-1,0,1,2] for z in [-1,0,1]]
view.set_points(points,len(points),576)
for i in range(3):
 view.mode.setCurrentIndex(i);app.processEvents()
 assert view.grab().save(str(Path('runtime') / f'lidar_projection_{i}.png'))
view.set_points([],0,576);app.processEvents();view.grab()
print('PASS: finite input, front/top axes, 3D height, three rendered views and empty scan')
view.close()
