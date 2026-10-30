# 快捷调色 BlendRaw

Blender 实时合成器调色插件。把一整套调色模块封装成一个 **BlendRaw** 节点组，用面板直接驱动，不需要进节点编辑器逐节点改参数。

本项目是原 Serpens（可视化节点式插件生成器）版本的**结构化重写**：界面、算子、预设、接线全部是手写 Python，调色算法仍由 `assets/BlendRaw_Node_E.blend` 里的节点组提供（资产内容零改动）。

- 作者：亮锅不服LAO（[qaddons.com](https://qaddons.com/)、[Bilibili](https://space.bilibili.com/429605217)）
- 版本：`0.3.0`
- 适用：**Blender 5.0+**
- 位置：3D 视图 / 合成器节点编辑器 / 图像编辑器的 `BRaw` 面板

---

## 功能

| 模块 | 内容 |
|---|---|
| 颜色调整 | 白平衡、去灰（Standard / Khronos PBR / AgX / Filmic）、基本（曝光、对比、高光/阴影、白/黑）、锐化、Hue/Saturation/Value |
| 选择颜色 | R / G / B / C / M / Y 六色独立调节 Hue、Saturation、Bright |
| 曲线 | Hue Correct、RGB Curves（Black/White Level） |
| 其他 | 颜色平衡（Lift/Gamma/Gain）、暗角（含椭圆遮罩宽高） |
| 炫光效果 | 整体（阈值/模糊/强度）、Bloom、星芒、条斑、残影、太阳光束 |
| 工作流 | 一键初始化/修复、分区静音与重置、预设（分类保存/加载/删除）、到文件输出、预览器与组输出自动接线 |
| 视口 | 3D 视图合成器三态（禁用 / 摄像机 / 总是），所有窗口与工作区统一生效 |
| 色彩空间 | 一键转为 Raw（把视图变换烘焙进节点组），并可随时还原（含 Look） |
| 示波器 | 图像编辑器面板内嵌直方图 / 波形图 / 矢量示波器 |
| 其他 | 合成器背景板缩放 Gizmo（放大/缩小/自适应） |

---

## 安装

1. 把整个 `blendraw` 文件夹放到对应 Blender 版本的插件目录：

   ```
   Windows: %APPDATA%\Blender Foundation\Blender\5.3\scripts\addons\blendraw
   macOS:   ~/Library/Application Support/Blender/5.3/scripts/addons/blendraw
   Linux:   ~/.config/blender/5.3/scripts/addons/blendraw
   ```

   也可以用 `Edit → Preferences → Add-ons → Install…` 直接安装打包好的 zip。

2. 重启 Blender。
3. `Edit → Preferences → Add-ons`，搜索 **BlendRaw** 或 **快捷调色**，勾选启用。
4. 3D 视图按 `N`，打开 **BRaw** 标签页（标签名可在插件偏好设置里修改）。

> 复制文件后必须重启 Blender，Python 模块有缓存。

## 快速开始

1. 打开面板，点 **初始化**（已存在节点组时显示为「修复节点组」）。
   插件会创建合成器节点树、`Render Layers / File Output / Viewer / Group Output` 并接好线。
2. 拖动各分区滑块即可实时调色；点分区标题可静音，点右侧 ⟲ 重置该分区。
3. 想切到节点编辑：点 **转换为 Raw**，插件的节点组会接管色彩变换；再点一次还原。

---

## 目录结构

```
blendraw/
├─ __init__.py          # bl_info、注册/注销、偏好设置、加载回调、视口同步定时器
├─ compat.py            # Blender 5.x API 适配（compositing_node_group、区域/空间遍历）
├─ paths.py             # 资源路径
├─ presets.py           # 预设存储（磁盘格式与旧版一致）
├─ core/
│  ├─ spec.py           # 声明式 UI 表：分区 → 节点 → 插座 → 标签 → 重置值
│  ├─ state.py          # Scene 属性与更新回调（视口同步、色彩空间、预设刷新）
│  └─ tree.py           # 安全的节点查找/接线/文件输出/单例复用
├─ ui/
│  ├─ panels.py         # 三个面板共用一套绘制逻辑
│  └─ icons.py          # 图标与预览图
├─ ops/
│  ├─ initialize.py     # 初始化 / 清理
│  ├─ reset.py          # 一个参数化重置算子（按分区）
│  ├─ presets.py        # 分类与预设的增删查改、列表控件
│  └─ gizmo.py          # 背景板缩放
├─ localdb/             # 中文翻译表
├─ assets/              # BlendRaw 节点组资产、logo
└─ tests/headless_check.py  # 无头自检
```

## 开发

### 添加一个可调分区

1. 在 `core/spec.py` 的 `PALETTE_SECTIONS`（或 `EFFECT_SECTIONS`）里加一条 `Section`：

   ```python
   Section(
       "my_section", "My Section", "Q_My Node",          # key / 标题 / BlendRaw 内的组节点名
       fields=(
           Field("Strength", "Q_My Node", "Strength", 1),  # 标签 / 组内节点 / 插座名 / 旧索引
       ),
   )
   ```

2. 需要重置默认值就往 `RESETS` 里加一条同名 key。
3. 面板会自动出现该分区，重置按钮自动可用。

> `Field` 同时记录插座名和历史序号：名字优先，序号兜底。Blender 5.0 把很多节点参数从 RNA 属性改成了插座，序号用于兼容旧节点组。

### 自检

```bash
blender --background --factory-startup --python tests/headless_check.py
```

会验证：属性注册、初始化接线、全部分区绑定可解析、重置值写入、色彩空间往返（含开关丢失/手动改动）、文件输出开关、预设存取、清理与注销，以及算子/面板标识符是否都存在。失败时进程退出码为 1，可直接用于发布前检查。

---

## 已知限制

- **Blender 5.2.x 不可用**：该版本在加载本插件节点资产时会原生崩溃（`create_compositor_nodes_rna_for_strip_modifier` → 未捕获的 C++ 异常）。该问题与插件代码无关，空场景直接 `open_mainfile` 加载同一个 `.blend` 即可复现。请使用 **5.0** 或 **5.3+**。
- 节点资产由 Blender 5.0 保存，因此只保证在 5.0+ 打开。
- 视口合成器三态以面板为准：用 Blender 原生下拉框临时修改，会在约 1.5 秒内被统一回面板选择（这是「所有窗口一致」的实现方式）。
- 预设以 `.blend` 文件存放在用户配置目录：`<Blender 用户配置>/config/BlendRaw Presets/<分类>/<名称>.blend`，与旧版本格式兼容。

## 从 0.2.0（Serpens 版）升级

- 调色数据保存在节点组里，**不受影响**；预设文件可直接继续使用。
- 算子标识符由 `sna.*` 改为 `braw.*`；如果给旧算子手动绑过快捷键，需要重新绑定。
- 场景属性由 `sna_*` 改为 `braw_*`：旧场景中面板标签页、预设面板开关、示波器开关等 UI 状态会回到默认值。
- 13 个独立的重置算子合并为一个 `braw.reset_section`。

## 致谢

- 感谢 [朔朔的搅拌机日常](https://space.bilibili.com/1220061774) 提供部分调色节点组。
