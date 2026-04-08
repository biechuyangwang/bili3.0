# -*- coding: utf-8 -*-
"""
响应处理模块 - 定义响应接口与关键词匹配实现

扩展方式：新建类实现 handle_danmaku / handle_super_chat / handle_gift 方法，
然后用 CompositeResponseHandler 串联即可，无需修改其他文件。
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("danmaku_bot.responder")


class KeywordResponseHandler:
    """关键词匹配响应器"""

    def __init__(self, rules: Dict[str, str], sc_template: str = ""):
        self.rules = rules
        self.sc_template = sc_template

    def handle_danmaku(self, uname: str, msg: str, uid: int, medal_level: int) -> Optional[str]:
        for keyword, response in self.rules.items():
            if keyword in msg:
                logger.debug("关键词匹配 '%s' -> '%s'", keyword, response)
                return response
        return None

    def handle_super_chat(self, uname: str, message: str, price: int, uid: int) -> Optional[str]:
        if self.sc_template:
            return self.sc_template.format(uname=uname, message=message, price=price)
        return f"感谢 {uname} 的SC！"
       
    def handle_gift(self, uname: str, gift_name: str, num: int, coin_type: str,
                    price: int = 0) -> Optional[str]:
        # 仅对金瓜子礼物回复，且总价值 >= 1000 电池（100000金瓜子）
        total = price * num
        if coin_type == "gold" and total >= 99000:
            return f"感谢 {uname} 赠送的 {gift_name}x{num}~"
        return None


class CompositeResponseHandler:
    """链式响应器：依次调用多个 handler，返回第一个非 None 结果"""

    def __init__(self, handlers: List):
        self.handlers = handlers

    def handle_danmaku(self, uname: str, msg: str, uid: int, medal_level: int) -> Optional[str]:
        for h in self.handlers:
            result = h.handle_danmaku(uname, msg, uid, medal_level)
            if result is not None:
                return result
        return None

    def handle_super_chat(self, uname: str, message: str, price: int, uid: int) -> Optional[str]:
        for h in self.handlers:
            result = h.handle_super_chat(uname, message, price, uid)
            if result is not None:
                return result
        return None

    def handle_gift(self, uname: str, gift_name: str, num: int, coin_type: str) -> Optional[str]:
        for h in self.handlers:
            result = h.handle_gift(uname, gift_name, num, coin_type)
            if result is not None:
                return result
        return None
