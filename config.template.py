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

# ===== 发送设置 =====
SEND_COOLDOWN = 3.0  # 发弹幕最小间隔（秒），避免触发 B 站频率限制

# ===== 响应规则 =====
# 关键词匹配：弹幕中包含 key 则回复 value，首次匹配生效
RESPONSE_RULES = {
    "你好": "您好呀~",
    "早上好": "早上坏！",
    "晚安": "好梦~",
    "点歌": "收到请求啦，稍等哦~",
    "关注": "感谢！欢迎来到直播间~",
}

# SC 感谢模板
SC_THANK_YOU_TEMPLATE = "感谢 {uname} 的醒目留言~"

# ===== 日志 =====
LOG_LEVEL = "INFO"
