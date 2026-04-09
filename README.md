# BiliBot - B站直播间弹幕智能响应机器人

基于 `bilibili-api` + `blivedm` 的直播间弹幕自动响应机器人，支持**多房间同时监控**、弹幕关键词回复、点歌、查歌、礼物/SC/上舰感谢、进场欢迎、自动禁言、粉丝排行、数据统计等功能。

## 环境要求

- Python 3.9+
- pip
- Git

## 快速开始

### 1. 克隆本项目

```bash
git clone https://github.com/biechuyangwang/bili3.0.git
cd bili3.0
```

### 2. 拉取依赖库源码

本项目依赖两个第三方库，它们的源码不在本仓库中（已通过 `.gitignore` 排除），需要单独克隆：

```bash
# bilibili-api - B站全功能 API 调用库
git clone https://github.com/Nemo2011/bilibili-api.git

# blivedm - B站直播弹幕 WebSocket 客户端
git clone https://github.com/xfgryujk/blivedm.git
```

### 3. 安装 Python 依赖

```bash
# 安装 bilibili-api（通过 pip）
pip install bilibili-api-python aiohttp

# blivedm 需从源码安装（PyPI 版本过旧，本项目依赖 1.1.5+）
cd blivedm
pip install -e .
cd ..
```

### 4. 配置凭据

项目提供了配置模板，首次使用时复制并填入你的真实信息：

```bash
cp config.template.py config.py
```

编辑 `config.py`，填入凭据和直播间号：

```python
SESSDATA = "你的 SESSDATA"
BILI_JCT = "你的 bili_jct"
BUVID3 = "你的 buvid3"
ROOM_ID = 12345  # 直播间 URL 中的数字
```

> **重要**：`config.py` 包含个人凭据，已在 `.gitignore` 中排除，不会被提交到版本控制。

**凭据获取方式：**

1. 浏览器登录 [bilibili.com](https://www.bilibili.com)
2. 按 `F12` 打开开发者工具 → `Application`（应用） → `Cookies` → `https://www.bilibili.com`
3. 找到并复制以下三个值：
   - **SESSDATA**
   - **bili_jct**
   - **buvid3**

> 注意：从 Chrome 开发者工具复制时，不要勾选"显示已解码的网址"。

### 5. （可选）配置敏感词

创建 `ban_words.txt` 文件启用自动禁言功能：

```
# 敏感词列表 - 每行一个，# 开头为注释
敏感词1
敏感词2
```

文件不存在时自动禁言功能不生效，不影响其他功能。

### 6. 运行

#### GUI 模式（推荐）

```bash
python gui.py
```

启动后会打开一个暗色主题的控制面板界面：

- **顶栏**：输入房间号，点击「连接」按钮连接直播间
- **房间标签页**：每个已连接房间拥有独立标签，显示房间号和连接状态（彩色圆点）
- **弹幕区**（左侧）：实时显示弹幕、SC、礼物、上舰等消息，按类型着色，每个房间独立
- **功能面板**（右侧）：点歌列表、粉丝排行、数据统计等，每个房间独立
- **标签切换**：点击标签切换房间，滚动位置自动保留
- **右键断开**：右键点击标签可断开该房间连接
- **设置菜单**：设置面板可独立开关各功能

> 多房间模式：连接第一个房间后，按钮变为「添加房间」，可同时监控最多 5 个直播间。每个房间的弹幕、点歌、排行、统计完全独立。
>
> GUI 模式下日志按房间分别写入文件（`logs/{房间号}/danmaku.log`），每日轮转，保留 30 天。

#### 命令行模式

```bash
python main.py
```

按 `Ctrl+C` 优雅退出。

## 功能列表

### 弹幕关键词回复

在 `config.py` 的 `RESPONSE_RULES` 中配置关键词→回复映射，弹幕命中关键词时自动回复：

```python
RESPONSE_RULES = {
    "你好": "您好呀~",
    "早上好": "早上坏！",
}
```

### 点歌

基于 LX Music（洛雪音乐）桌面版的 `lxmusic://` 协议实现。

**前置条件**：本机需要安装 [LX Music 桌面版](https://github.com/lyswhut/LXMusicDesktop)。

粉丝发送：

```
点歌 晴天
点歌 晴天 周杰伦
```

机器人会唤起 LX Music 搜索并添加到"稍后播放"列表，同时回复确认弹幕。

搜索源通过 `config.SONG_REQUEST_SOURCE` 配置：`tx`(腾讯/QQ音乐, 默认)、`wy`(网易云)、`kg`(酷狗)、`kw`(酷我)、`mg`(咪咕)。

### 查歌

粉丝发送 `查歌 歌名` 或 `查歌 歌名 歌手`，机器人通过 QQ Music 搜索并回复歌曲信息。

```
查歌 晴天        → 回复搜索到的第一首歌名和歌手
查歌 晴天 周杰伦  → 按歌手过滤结果
```

### 礼物感谢

- **金瓜子礼物**：总价值 >= 990000 金瓜子（约 99 元）时自动发送感谢弹幕
- **银瓜子礼物**：忽略，避免刷屏

### SC（醒目留言）感谢

收到 SC 后自动发送感谢弹幕，模板可配置：

```python
SC_THANK_YOU_TEMPLATE = "感谢 {uname} 的醒目留言~"
```

### 上舰感谢

收到上舰（舰长/提督/总督）消息后自动发送感谢弹幕，按舰队等级使用不同模板：

```python
GUARD_TEMPLATES = {
    1: "感谢 {uname} 开通总督！太给力了！",   # 总督
    2: "感谢 {uname} 开通提督！感谢支持！",   # 提督
    3: "感谢 {uname} 开通舰长！欢迎上船！",   # 舰长
}
```

### 进场欢迎

用户进入直播间时自动发送欢迎弹幕，带双冷却机制防止刷屏：

- `WELCOME_COOLDOWN_GLOBAL`：全局冷却（秒），两次欢迎之间的最小间隔
- `WELCOME_COOLDOWN_USER`：用户冷却（分钟），同一用户两次被欢迎的最小间隔

### 自动禁言

检测到弹幕包含 `ban_words.txt` 中的敏感词时，自动禁言发送者。禁言时长通过 `config.BAN_DURATION` 配置（小时）。文件不存在时功能不生效。

### 人气显示

GUI 模式下底栏实时显示直播间人气值（来自心跳包）。

### 粉丝排行榜

GUI 右侧面板展示粉丝勋章排行和大航海（舰队）成员列表。

### 数据统计面板

GUI 右侧面板展示统计数据：弹幕数、礼物数、SC 数、上舰数等，支持按时间范围查看。

## 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SEND_COOLDOWN` | 发弹幕最小间隔（秒） | 3.0 |
| `RESPONSE_RULES` | 关键词→回复映射 | 见文件 |
| `SC_THANK_YOU_TEMPLATE` | SC 感谢模板 | `感谢 {uname} 的醒目留言~` |
| `GUARD_TEMPLATES` | 上舰感谢模板（按等级） | 见文件 |
| `BOT_UID` | 机器人 UID，过滤自己发的弹幕 | `0`（不过滤） |
| `WELCOME_COOLDOWN_GLOBAL` | 欢迎全局冷却（秒） | 10.0 |
| `WELCOME_COOLDOWN_USER` | 欢迎用户冷却（分钟） | 5.0 |
| `WELCOME_TEMPLATE` | 欢迎模板 | `欢迎 {uname} 进入直播间~` |
| `SONG_REQUEST_KEYWORD` | 点歌触发关键词 | `"点歌"` |
| `SONG_REQUEST_SOURCE` | 点歌搜索源 | `"tx"` |
| `SONG_SEARCH_KEYWORD` | 查歌触发关键词 | `"查歌"` |
| `BAN_DURATION` | 禁言时长（小时） | 1 |
| `LOG_LEVEL` | 日志级别 | INFO |

## 项目结构

```
bili3.0/
├── config.template.py  # 配置模板（不含真实凭据）
├── config.py           # 实际配置（从模板复制后填入凭据，不提交到 git）
├── ban_words.txt       # 敏感词列表（每行一个，# 注释，可选）
├── responder.py        # 响应处理（接口 + 关键词匹配 + 链式响应器）
├── song_request.py     # 点歌模块（LX Music scheme URL）
├── song_search.py      # 查歌模块（QQ Music 搜索）
├── sender.py           # 弹幕发送（带限流）
├── bot.py              # 消息处理器（弹幕/SC/礼物/上舰/欢迎/禁言/查歌）
├── fan_ranking.py      # 粉丝排行（勋章排行 + 大航海列表）
├── stats_collector.py  # 数据统计收集（线程安全）
├── gui.py              # GUI 图形界面（暗色主题控制面板）
├── main.py             # CLI 入口
├── bilibili-api/       # bilibili-api 源码（需单独克隆）
└── blivedm/            # blivedm 源码（需单独克隆，已 pip install -e .）
```

## 弹幕过滤机制

本项目通过多层过滤来决定哪些弹幕需要回复，避免无意义的刷屏响应。

### 过滤流程

```
弹幕到达
  │
  ├─ 以"点歌"/"查歌"开头？── 是 → 直接处理（不过滤自身和粉丝）
  │
  ├─ 是否机器人自己？── 是 → 跳过
  │
  ├─ 是否本房间粉丝？── 否 → 跳过
  │
  ├─ 匹配敏感词？── 是 → 自动禁言
  │
  ├─ 关键词匹配？── 未命中 → 忽略
  │                 └─ 命中 → 限流检查 → 发送回复
  │
SC 消息    → 始终回复感谢
礼物消息   → 金瓜子且 >= 990000（约99元）→ 回复感谢 / 否则忽略
上舰消息   → 按等级（总督/提督/舰长）回复不同感谢模板
进场消息   → 冷却检查通过后回复欢迎
```

## 扩展指南

接入新的响应功能只需两步：

1. 新建一个 handler 类，实现 `handle_danmaku(uname, msg, uid, medal_level)` 等方法
2. 在 `main.py` 的 `CompositeResponseHandler` 链中插入（顺序 = 优先级）

当前响应器链：

```python
responder = CompositeResponseHandler([
    SongRequestHandler(...),       # 1. 点歌优先处理
    KeywordResponseHandler(...),   # 2. 关键词兜底
])
```
