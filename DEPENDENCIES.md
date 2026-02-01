# Dependencies & Project Layout

## 依赖库
- PySide6 — Qt for Python (GUI)
- vtk — VTK for 3D 渲染与互动（替代 pyqtgraph 的渲染部分）
- pyzmq — ZeroMQ bindings (PUB/SUB)
- numpy — numerical arrays

安装：
```
pip install -r requirements.txt
```

## 项目结构
```
/home/jed/Project/Voxel3D/
├─ v3d/                  # 模块化包
│  ├─ __init__.py
│  ├─ scene_model.py     # 数据模型（points / segments / 随机生成 / 导出）
│  ├─ renderer.py        # 基于 VTK 的渲染器（高性能批量渲染）
│  ├─ zmq_sub.py         # ZMQ Subscriber（QThread）
│  └─ ui.py              # MainWindow：组合 Model + Renderer + ZMQ
├─ main.py               # 程序入口（极简）
├─ pub.py                # 测试发布器
├─ sample.json           # 示例数据
├─ tests/                # 单元测试
│  └─ test_scene_model.py
├─ requirements.txt
└─ README.md
```

## 测试运行
- 运行单元测试（需要安装 pytest）:
```
pip install pytest
pytest -q
```

## 注意事项
- 3D 渲染依赖系统 OpenGL 驱动。在无 GUI 的环境（如某些容器）可能无法运行。
- 如果要把 `v3d` 转为可打包为 pip 包，可添加 `setup.py` 或 `pyproject.toml`。
