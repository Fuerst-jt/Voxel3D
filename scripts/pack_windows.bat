@echo off
REM Run on Windows to build a one-file executable with PyInstaller
set APP_NAME=voxel3d


echo Build complete. Output in dist\npy -m PyInstaller --onefile --noconfirm --clean --name %APP_NAME% --hidden-import=vtkmodules --hidden-import=vtkmodules.qt.QVTKRenderWindowInteractor --hidden-import=vtkmodules.util.numpy_support --hidden-import=vtkmodules.all main.py