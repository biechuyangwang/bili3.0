# -*- coding: utf-8 -*-
"""
配置文件 - 填入你的 B 站账号凭据和目标直播间信息

获取方式：浏览器登录 bilibili.com → F12 → Application → Cookies
注意：不要将真实凭据提交到版本控制！
"""

# ===== 账号凭据 =====
SESSDATA = ""
BILI_JCT = ""
BUVID3 = ""

# ===== 直播间设置 =====
ROOM_ID = 0  # 目标直播间号（URL 中的数字）
BOT_UID = 0  # 机器人账号的 UID，用于过滤自己发的弹幕（0 = 不过滤）

# ===== 发送设置 =====
SEND_COOLDOWN = 3.0  # 发弹幕最小间隔（秒），避免触发 B 站频率限制

# ===== 响应规则 =====
# 关键词匹配：弹幕中包含 key 则回复 value，首次匹配生效
# 注意："点歌" 由下方的点歌模块处理，此处无需重复配置
RESPONSE_RULES = {
    "你好": "您好呀~",
    "早上好": "早上坏！",
    "晚安": "好梦~",
    "关注": "感谢！欢迎来到直播间~",
}

# SC 感谢模板
SC_THANK_YOU_TEMPLATE = "感谢 {uname} 的醒目留言~"

# ===== 点歌设置 =====
# 需要本机安装 LX Music（洛雪音乐）桌面版
# 文档：https://lxmusic.toside.cn/desktop/scheme-url
SONG_REQUEST_KEYWORD = "点歌"   # 触发点歌的关键词前缀
SONG_REQUEST_SOURCE = "tx"     # 搜索源：tx(腾讯), wy(网易), kg(酷狗), kw(酷我), mg(咪咕)

# ===== 日志 =====
LOG_LEVEL = "INFO"
