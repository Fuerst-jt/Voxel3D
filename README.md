# 3D Viewer (PySide6 + pyqtgraph + ZMQ)

快速演示一个上位机程序，可以：

- 在三维空间显示 **点（points）** 与 **线段（segments）**
- 从 `sample.json` 载入并显示场景
- 通过 ZMQ SUB 接收实时 JSON 消息并更新场景

## 安装依赖 ✅

建议创建 venv：

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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
- 如果需要带 topic 或自定义 schema，可把样例消息发给我，我可以修改接收和解析逻辑。 

---

如需我把功能扩展为增量更新（只增/删改单个点）、保存截图或录制轨迹，我可以继续实现。