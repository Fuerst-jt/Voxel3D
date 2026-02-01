# 3D Viewer (PySide6 + VTK + ZMQ)

快速演示一个上位机程序，可以：

- 在三维空间显示 **点（points）** 与 **线段（segments）**（基于 VTK，支持高性能批量绘制）
- 从 `sample.json` 载入并显示场景
- 通过 ZMQ SUB 接收实时 JSON 消息并更新场景

## 安装依赖 ✅

本项目**强依赖 VTK**（用于渲染）。为保证“开箱即用”，请在运行前先安装所有依赖：

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果你使用系统包管理器或需要特定平台的 wheel，请先确认 `vtk` 在你的平台上可用。

## 运行示例

1. 先启动发布脚本（发送模拟数据）：

```
python pub.py
```

2. 启动 GUI：

```
python main.py
```

3. 在 GUI 中可以点击 **Load JSON** 打开 `sample.json`，也可以启动 `Start SUB` 按钮接收 `pub.py` 发来的实时消息。

## JSON 格式

示例格式：

```json
{
  "points": [ {"x":0,"y":0,"z":0,"size":8,"color":[1,0,0,1]} ],
  "segments": [ {"start":[0,0,0],"end":[1,1,1],"color":[0,1,0,1],"width":2} ]
}
```

## 注意事项 ⚠️

- ZMQ 发布/订阅需要时间建立连接（PUB/SUB）。如发现 GUI 未及时接收到消息，稍等 0.2s 再观察。
- 本项目改为使用 `vtk` 渲染：如果在无头/容器环境运行，可能需要额外的配置或使用 OSMesa。若遇到性能问题，建议使用 `vtk` 的批量渲染方案（已在 `v3d.renderer` 中实现）。

## 版本与打包

- 当前包版本在 `v3d.__version__` 与 `setup.cfg` 中声明为 `0.1.0`。
- 打包说明：使用 `PyInstaller` 可以生成单文件可执行程序（将尽量打包依赖库以减少运行时依赖）。示例脚本位于 `scripts/pack.sh`（Linux/macOS）和 `scripts/pack_windows.bat`（Windows）。

示例（Linux/macOS，在对应平台运行）：

```bash
./scripts/pack.sh linux
```

注意事项：
- PyInstaller 必须在目标平台上运行以生成正确的平台可执行文件（在 macOS 上构建 macOS 二进制，在 Windows 上构建 Windows 二进制）。
- VTK 包含大型二进制组件，打包后可执行文件体积会较大；某些系统级依赖（如 OpenGL 驱动）仍然会使用系统实现，无法完全移除。

如果你希望我自动化 CI 打包工作流（GitHub Actions 在三平台构建），我可以继续添加。

---

如需我把功能扩展为增量更新（只增/删改单个点）、保存截图或录制轨迹，我可以继续实现。