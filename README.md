# BiliBot - B站直播间弹幕智能响应机器人

基于 `bilibili-api` + `blivedm` 的直播间弹幕自动响应原型。

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

### 5. 运行

#### 命令行模式

```bash
python main.py
```

正常启动后会看到：

```
14:30:00 [danmaku_bot] INFO: ========================================
14:30:00 [danmaku_bot] INFO: 弹幕机器人已启动，监听房间 12345
14:30:00 [danmaku_bot] INFO: 按 Ctrl+C 停止
14:30:00 [danmaku_bot] INFO: ========================================
14:30:01 [danmaku_bot.handler] INFO: [弹幕] 某用户 (uid=123, 勋章=5): 你好
14:30:01 [danmaku_bot.sender] INFO: 已发送弹幕: 你好呀~
```

按 `Ctrl+C` 优雅退出。

#### GUI 模式

```bash
python gui.py
```

启动后会打开一个暗色主题的控制面板界面：

- **顶栏**：输入房间号，点击「连接」按钮连接直播间，连接后按钮变为「断开」
- **弹幕区**（左侧）：实时显示弹幕、SC、礼物消息，按类型着色
- **点歌列表**（右侧）：显示点歌记录（歌曲名、点歌人、时间）

> GUI 模式下日志仅写入文件（`logs/danmaku.log`），不输出到控制台。

## 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SEND_COOLDOWN` | 发弹幕最小间隔（秒） | 3.0 |
| `RESPONSE_RULES` | 关键词→回复映射 | 见文件 |
| `SC_THANK_YOU_TEMPLATE` | SC 感谢模板 | `感谢 {uname} 的醒目留言~` |
| `BOT_UID` | 机器人账号 UID，用于过滤自己发的弹幕 | `0`（不过滤） |
| `SONG_REQUEST_KEYWORD` | 点歌触发关键词 | `"点歌"` |
| `SONG_REQUEST_SOURCE` | 点歌搜索源（`tx`/`wy`/`kg`/`kw`/`mg`） | `"tx"` |
| `LOG_LEVEL` | 日志级别 | INFO |

## 项目结构

```
bili3.0/
├── config.template.py  # 配置模板（不含真实凭据）
├── config.py           # 实际配置（从模板复制后填入凭据，不提交到 git）
├── responder.py        # 响应处理（接口 + 关键词匹配 + 链式响应器）
├── song_request.py     # 点歌模块（LX Music scheme URL）
├── sender.py           # 弹幕发送（带限流）
├── bot.py              # 消息处理器（接收→过滤→响应→发送）
├── gui.py              # GUI 图形界面（暗色主题控制面板）
├── main.py             # CLI 入口
├── bilibili-api/       # bilibili-api 源码（需单独克隆）
└── blivedm/            # blivedm 源码（需单独克隆，已 pip install -e .）
```

## 弹幕过滤机制

本项目通过多层过滤来决定哪些弹幕需要回复，避免无意义的刷屏响应。

### 1. 自身弹幕过滤（`bot.py`）

在 `DanmakuBotHandler._on_danmaku()` 中，比对弹幕发送者的 `uid` 与 `config.BOT_UID`：

- 发送者 UID == 机器人 UID 时跳过，**避免机器人回复自己发的弹幕形成死循环**
- `BOT_UID` 设为 `0` 时禁用此过滤

### 2. 本房间粉丝过滤（`bot.py`）

在 `DanmakuBotHandler._on_danmaku()` 中，比对弹幕中的 `medal_room_id` 与当前直播间的真实房间号：

- 启动时通过 `LiveRoom.get_room_play_info()` 将 URL 中的短号解析为真实房间号
- 只有 `medal_room_id == 真实房间号` 的弹幕才会被处理
- 未佩戴勋章（`medal_room_id == 0`）或佩戴其他房间勋章的用户弹幕直接忽略
- 这确保机器人只回复**本直播间的粉丝**

### 3. 关键词匹配过滤（`responder.py`）

`KeywordResponseHandler.handle_danmaku()` 对通过前置过滤的弹幕进行关键词匹配：

- 遍历 `config.py` 中 `RESPONSE_RULES` 定义的 `{关键词: 回复}` 映射
- 弹幕内容**包含**某个关键词时，返回对应的回复文本
- **不包含任何关键词的弹幕直接忽略**（返回 `None`，不触发发送）

```python
# config.py 中配置关键词规则，只有命中关键词的弹幕才会回复
RESPONSE_RULES = {
    "你好": "您好呀~",
    "早上好": "早上坏！",
}
```

### 4. 礼物类型过滤（`responder.py`）

`KeywordResponseHandler.handle_gift()` 对礼物消息按 `coin_type` 过滤：

- **金瓜子礼物**（`coin_type == "gold"`）：发送感谢回复
- **银瓜子礼物**（`coin_type == "silver"`）：直接忽略，避免免费礼物刷屏

### 5. 发送限流保护（`sender.py`）

`DanmakuSender` 内置了发送间隔限制：

- 通过 `config.SEND_COOLDOWN`（默认 3.0 秒）控制最小发送间隔
- 使用 `asyncio.Lock` 保证并发安全，多条待发送消息会排队等待
- 避免触发 B 站的频率限制

### 6. 链式响应器（`responder.py`）

`CompositeResponseHandler` 实现了责任链模式：

- 依次调用多个 handler，返回**第一个非 None** 的结果
- 后续 handler 不再执行（短路机制）
- 可用于在关键词匹配前插入 AI 处理，AI 不回复时再走关键词兜底

### 过滤流程总结

```
弹幕到达
  │
  ├─ 以"点歌"开头？── 是 → 不过滤自身和粉丝，直接处理
  │
  ├─ 是否机器人自己？── 是 → 跳过
  │
  ├─ 是否本房间粉丝？── 否 → 跳过
  │
  ├─ 关键词匹配？── 未命中 → 忽略
  │                 └─ 命中 → 限流检查 → 发送回复
  │
SC 消息  → 始终回复感谢
礼物消息 → 金瓜子？→ 回复感谢 / 银瓜子？→ 忽略
```

## 点歌功能

基于 [LX Music（洛雪音乐）](https://github.com/lyswhut/LXMusicDesktop) 桌面版的自定义协议 URL（`lxmusic://`）实现点歌功能。

### 前置条件

本机需要安装 LX Music 桌面版，它会注册 `lxmusic://` 协议，系统收到该协议 URL 后会自动唤起应用。

### 使用方式

粉丝在直播间发送以下格式的弹幕：

```
点歌 歌名
点歌 歌名 歌手
```

示例：
- `点歌 晴天` — 搜索歌名"晴天"
- `点歌 晴天 周杰伦` — 搜索歌名"晴天"且歌手为"周杰伦"

### 工作原理

1. `SongRequestHandler`（`song_request.py`）检测弹幕是否以点歌关键词开头
2. 解析出歌名和可选的歌手
3. 构造 LX Music 的 `music/searchPlay` scheme URL：

```
lxmusic://music/searchPlay?data={"name":"歌名","singer":"歌手","source":"tx","playLater":true}
```

4. 通过 `webbrowser.open()` 打开该 URL，系统唤起 LX Music
5. LX Music 使用指定源搜索歌曲，并添加到"稍后播放"列表
6. 机器人回复弹幕确认，如 `已收到点歌：晴天 - 周杰伦，稍后播放~`

### 响应器链

点歌 handler 通过 `CompositeResponseHandler` 串联在关键词匹配器之前：

```
弹幕 → SongRequestHandler（点歌优先处理）
                 ↓ 未匹配
       KeywordResponseHandler（关键词兜底）
```

点歌 handler 返回非 None 时短路，关键词匹配器不再执行。

### 搜索源

| 配置值 | 来源 |
|--------|------|
| `tx` | 腾讯/QQ音乐（默认） |
| `wy` | 网易云音乐 |
| `kg` | 酷狗音乐 |
| `kw` | 酷我音乐 |
| `mg` | 咪咕音乐 |

通过 `config.SONG_REQUEST_SOURCE` 配置。

### LX Music scheme URL 参考

完整文档：https://lxmusic.toside.cn/desktop/scheme-url

本项目使用的 action：

| Action | 格式 | 说明 |
|--------|------|------|
| `music/searchPlay` | `lxmusic://music/searchPlay?data=<json>` | 按歌名/歌手搜索并播放 |
| `music/search` | `lxmusic://music/search/<source>/<keywords>` | 打开搜索页面 |
| `music/play` | `lxmusic://music/play?data=<json>` | 播放指定歌曲（需完整元数据） |
| `player/play` | `lxmusic://player/play` | 继续播放 |
| `player/skipNext` | `lxmusic://player/skipNext` | 下一首 |

## 弹幕消息结构

blivedm 解析后的消息对象包含丰富的字段，可以用来做更精细的过滤。以下是三种主要消息类型的结构。

### DanmakuMessage（普通弹幕）

来源：`blivedm.models.web.DanmakuMessage`

| 字段 | 类型 | 说明 | 可用于过滤的场景 |
|------|------|------|-----------------|
| `msg` | str | 弹幕文本内容 | 关键词匹配 |
| `uid` | int | 发送者用户ID | 黑名单 / 白名单 |
| `uname` | str | 发送者用户名 | 识别特定用户 |
| `medal_level` | int | 粉丝勋章等级 | 按粉丝等级过滤 |
| `medal_name` | str | 粉丝勋章名称 | 区分是否为本直播间粉丝 |
| `medal_room_id` | int | 勋章所属房间ID | 判断是否为本房间粉丝 |
| `admin` | int | 是否房管（1=是） | 识别房管消息 |
| `privilege_type` | int | 舰队类型（0非舰队, 1总督, 2提督, 3舰长） | 优先回复舰队成员 |
| `vip` | int | 是否月费老爷 | — |
| `svip` | int | 是否年费老爷 | — |
| `user_level` | int | 用户等级 | 过滤低等级用户 |
| `dm_type` | int | 弹幕类型（0文本, 1表情, 2语音） | 过滤非文本弹幕 |
| `msg_type` | int | 是否礼物弹幕/节奏风暴 | 过滤系统弹幕 |
| `is_mirror` | bool | 是否跨房弹幕 | 过滤跨房弹幕 |
| `wealth_level` | int | 荣耀等级 | — |
| `title` | str | 当前头衔 | — |
| `font_size` | int | 字体尺寸 | — |
| `color` | int | 弹幕颜色 | — |
| `timestamp` | int | 时间戳 | — |

### SuperChatMessage（醒目留言 / SC）

来源：`blivedm.models.web.SuperChatMessage`

| 字段 | 类型 | 说明 | 可用于过滤的场景 |
|------|------|------|-----------------|
| `message` | str | SC 消息内容 | 关键词提取 |
| `price` | int | 价格（人民币） | 按金额分级回复 |
| `uid` | int | 发送者用户ID | 用户识别 |
| `uname` | str | 发送者用户名 | 回复模板 |
| `guard_level` | int | 舰队等级（0非舰队, 1总督, 2提督, 3舰长） | 舰队成员特殊感谢 |
| `user_level` | int | 用户等级 | — |
| `id` | int | SC ID，删除时使用 | — |
| `gift_id` / `gift_name` | int / str | 对应的礼物信息 | — |

### GiftMessage（礼物消息）

来源：`blivedm.models.web.GiftMessage`

| 字段 | 类型 | 说明 | 可用于过滤的场景 |
|------|------|------|-----------------|
| `gift_name` | str | 礼物名 | 按礼物类型回复 |
| `num` | int | 数量 | 多连礼物特殊回复 |
| `coin_type` | str | 瓜子类型（`"silver"` 或 `"gold"`） | 过滤银瓜子（当前已实现） |
| `price` | int | 单价瓜子数 | 按价值分级 |
| `total_coin` | int | 总瓜子数 | 按总价值分级 |
| `uid` | int | 发送者用户ID | 用户识别 |
| `uname` | str | 发送者用户名 | 回复模板 |
| `guard_level` | int | 舰队等级 | 舰队成员特殊感谢 |
| `medal_level` | int | 粉丝勋章等级 | — |
| `medal_name` | str | 粉丝勋章名称 | — |

### GuardBuyMessage（上舰消息）

来源：`blivedm.models.web.GuardBuyMessage`

| 字段 | 类型 | 说明 | 可用于过滤的场景 |
|------|------|------|-----------------|
| `uid` | int | 用户ID | 用户识别 |
| `username` | str | 用户名 | 回复模板 |
| `guard_level` | int | 舰队等级（1总督, 2提督, 3舰长） | 按等级不同回复 |
| `num` | int | 数量（月数） | 多月上舰特殊感谢 |
| `price` | int | 单价金瓜子数 | — |
| `gift_name` | str | 礼物名 | — |

## 基于弹幕结构的扩展过滤示例

当前项目只使用了 `msg`（关键词）和 `coin_type`（金/银瓜子）两个维度做过滤。利用上面列出的字段，可以实现更精细的过滤策略。

### 示例 1：仅回复本直播间粉丝（勋章过滤）

```python
class FanOnlyHandler:
    """仅回复佩戴本直播间勋章的粉丝"""
    def __init__(self, room_id: int):
        self._room_id = room_id

    def handle_danmaku(self, uname, msg, uid, medal_level):
        # medal_room_id == 本房间 才回复，排除游客和隔壁粉丝
        if medal_level > 0 and message.medal_room_id == self._room_id:
            # 走后续关键词或 AI 逻辑
            ...
        return None
```

### 示例 2：按粉丝勋章等级分级回复

```python
class MedalLevelHandler:
    """高等级粉丝优先，低等级只走简单关键词"""
    def handle_danmaku(self, uname, msg, uid, medal_level):
        if medal_level >= 20:
            return f"亲爱的 {uname}，收到啦~"
        elif medal_level >= 5:
            return "收到~"
        # 等级太低不回复
        return None
```

### 示例 3：过滤非文本弹幕和跨房弹幕

```python
# 在 bot.py 的 _on_danmaku 中，调用 responder 前先过滤
def _on_danmaku(self, client, message):
    # 过滤表情弹幕、语音弹幕
    if message.dm_type != 0:
        return
    # 过滤跨房弹幕
    if message.is_mirror:
        return
    # 过滤节奏风暴等系统弹幕
    if message.msg_type != 0:
        return
    # 过滤房管消息（避免误回复房管公告）
    if message.admin:
        return
    # 正常处理...
```

### 示例 4：按 SC 金额分级感谢

```python
class TieredSCHandler:
    def handle_super_chat(self, uname, message, price, uid):
        if price >= 100:
            return f"感谢 {uname} 的大额SC！！爱你！"
        elif price >= 30:
            return f"感谢 {uname} 的醒目留言~"
        else:
            return f"谢谢 {uname}~"
```

### 示例 5：按礼物总价值回复（替代当前的金/银过滤）

```python
class GiftValueHandler:
    MIN_TOTAL_COIN = 1000  # 最低 1000 瓜子（约 1 元）才回复

    def handle_gift(self, uname, gift_name, num, coin_type):
        total = message.price * message.num
        if total >= self.MIN_TOTAL_COIN:
            return f"感谢 {uname} 赠送的 {gift_name}x{num}~"
        return None
```

### 可用的过滤维度汇总

| 维度 | 对应字段 | 典型用途 |
|------|---------|---------|
| 弹幕内容 | `msg` | 关键词匹配（已实现） |
| 弹幕类型 | `dm_type` | 过滤表情/语音弹幕 |
| 系统弹幕 | `msg_type` | 过滤节奏风暴 |
| 跨房弹幕 | `is_mirror` | 只回复本房间弹幕 |
| 用户身份 | `uid`, `uname` | 黑名单 / 白名单 |
| 粉丝勋章 | `medal_level`, `medal_room_id` | 仅回复本房间粉丝，或按等级分级 |
| 舰队身份 | `privilege_type`, `guard_level` | 舰队成员优先回复 |
| 房管身份 | `admin` | 过滤房管公告弹幕 |
| 用户等级 | `user_level` | 过滤低等级/小号 |
| 瓜子类型 | `coin_type` | 金/银过滤（已实现） |
| 礼物价值 | `price`, `total_coin` | 按金额分级回复 |
| SC 价格 | `price` | 按金额分级感谢 |
| 上舰等级 | `guard_level` | 区分舰长/提督/总督 |

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

添加新 handler 示例：

```python
# 示例：接入 LLM
class AIResponseHandler:
    def handle_danmaku(self, uname, msg, uid, medal_level):
        return llm_call(msg)

    def handle_super_chat(self, uname, message, price, uid):
        return None

    def handle_gift(self, uname, gift_name, num, coin_type):
        return None

# main.py 中插入到链中
responder = CompositeResponseHandler([
    AIResponseHandler(),           # AI 最优先
    SongRequestHandler(...),       # 点歌次之
    KeywordResponseHandler(...),   # 关键词兜底
])
```
