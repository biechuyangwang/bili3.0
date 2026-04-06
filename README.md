# BiliBot - B站直播间弹幕智能响应机器人

基于 `bilibili-api` + `blivedm` 的直播间弹幕自动响应原型。

## 环境要求

- Python 3.9+
- pip

## 安装步骤

```bash
# 1. 进入项目目录
cd D:/github/bili3.0

# 2. 安装依赖
pip install bilibili-api-python aiohttp

# 3. blivedm 需从源码安装（PyPI 版本过旧）
cd blivedm
pip install -e .
cd ..
```

## 获取账号凭据

1. 浏览器登录 [bilibili.com](https://www.bilibili.com)
2. 按 `F12` 打开开发者工具 → `Application`（应用） → `Cookies` → `https://www.bilibili.com`
3. 找到并复制以下三个值：
   - **SESSDATA**
   - **bili_jct**
   - **buvid3**

> 注意：从 Chrome 开发者工具复制时，不要勾选"显示已解码的网址"。

## 配置

项目提供了配置模板 `config.template.py`，首次使用时：

```bash
# 复制模板为 config.py
cp config.template.py config.py
```

然后编辑 `config.py`，填入你的真实凭据和直播间号：

```python
SESSDATA = "你的 SESSDATA"
BILI_JCT = "你的 bili_jct"
BUVID3 = "你的 buvid3"
ROOM_ID = 12345  # 直播间 URL 中的数字
```

> **重要**：`config.py` 包含个人凭据，已在 `.gitignore` 中排除，不会被提交到版本控制。

可自定义的配置项：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SEND_COOLDOWN` | 发弹幕最小间隔（秒） | 3.0 |
| `RESPONSE_RULES` | 关键词→回复映射 | 见文件 |
| `SC_THANK_YOU_TEMPLATE` | SC 感谢模板 | `感谢 {uname} 的醒目留言~` |
| `LOG_LEVEL` | 日志级别 | INFO |

## 运行

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

## 项目结构

```
bili3.0/
├── config.template.py  # 配置模板（不含真实凭据）
├── config.py           # 实际配置（从模板复制后填入凭据，不提交到 git）
├── responder.py        # 响应处理（接口 + 关键词匹配）
├── sender.py           # 弹幕发送（带限流）
├── bot.py              # 消息处理器（接收→响应→发送）
├── main.py             # 入口
└── blivedm/            # blivedm 源码（已 pip install -e .）
```

## 扩展指南

接入 AI 智能响应只需两步：

1. 新建一个 handler 类，实现 `handle_danmaku(uname, msg, uid, medal_level)` 方法
2. 在 `main.py` 中用 `CompositeResponseHandler` 将其串联到关键词匹配器之前

```python
# 示例：接入 LLM
class AIResponseHandler:
    def handle_danmaku(self, uname, msg, uid, medal_level):
        # 调用你的 LLM API
        return llm_call(msg)

    def handle_super_chat(self, uname, message, price, uid):
        return None

    def handle_gift(self, uname, gift_name, num, coin_type):
        return None

# main.py 中替换 responder 构建方式
responder = CompositeResponseHandler([
    AIResponseHandler(),          # AI 优先处理
    KeywordResponseHandler(...),  # 关键词兜底
])
```
