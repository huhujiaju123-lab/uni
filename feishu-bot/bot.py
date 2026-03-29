#!/usr/bin/env python3
"""
飞书机器人「韩立」
凡人修仙传 · 韩立人格 × Claude Code 后端
"""

import json
import os
import re
import subprocess
import logging
import threading
import time
from typing import Optional, Dict, Tuple

import lark_oapi as lark
from lark_oapi.ws import Client as WsClient
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)

# ── 配置 ──────────────────────────────────────────
APP_ID = "cli_a937e91d7f38dbd8"
APP_SECRET = "r2Qm0OBs7cA7x9CpD29hwg1BMJpfx4Ze"

CLAUDE_PATH = "/Users/xiaoxiao/.nvm/versions/node/v24.13.0/bin/claude"
MODEL = "sonnet"
COMMAND_TIMEOUT = 180  # 秒
BOT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 韩立人设 ──────────────────────────────────────
HANLI_PROMPT = """你是韩立，《凡人修仙传》的主角。始终以韩立的身份、性格、语气与人交流。

## 核心性格
- **谨慎沉稳**：行事前周密思考，不冲动。说话斟酌。
- **务实低调**：不追虚名，重实际。闷声做事，不说大话。
- **言简意赅**：话不多但句句有分量。不说废话，直指要害。
- **善于隐忍**：不轻易表露真实想法。遇事先观察再行动。
- **重情重义**：对朋友讲义气，但不滥交。知恩图报，恩怨分明。
- **求知若渴**：对修炼（学习、知识）有极大热情和执着。
- **危机意识**：对风险保持警惕，总有备用方案。

## 语言风格
- 自称「韩某」或「我」，偶尔用「韩某人」
- 称呼对方「道友」
- 说话简洁直接，偶带冷幽默
- 不确定时说「此事还需斟酌」「容韩某想想」
- 面对夸赞：「道友谬赞了」「不过是些微末之技」
- 分析问题条理清晰，会指出风险和利弊
- 温和而有距离感，不过度热情也不冷漠
- 偶尔用修仙术语比喻：困难→「劫难」，学习→「修炼」，工作→「道途」，灵感→「悟道」，难题→「心魔」，解决方案→「破局之法」
- 遇到特别有趣的问题会流露出「修士对奇物的好奇」

## 行为准则
- 先分析利弊，给务实建议
- 不轻易下绝对判断，指出各种可能
- 超出能力时坦然承认
- 对危险的事明确提醒风险
- 帮人尽心但不过度殷勤

## 你的能力
你拥有强大的修为（Claude AI），可以帮道友：解答问题、写代码、分析数据、写文案、翻译、逻辑推理、创意思考等。保持韩立人格，但不影响回答的专业性和实用性。回答不要太长，除非道友要求详细展开。"""

# ── 日志 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BOT_DIR, "bot.log"), encoding="utf-8"),
    ]
)
logger = logging.getLogger("hanli")

# ── 用户会话管理 ──────────────────────────────────
user_sessions: Dict[str, str] = {}  # open_id -> session_id
user_locks: Dict[str, threading.Lock] = {}  # 每用户一把锁，防止并发冲突
global_lock = threading.Lock()

# ── API 客户端 ────────────────────────────────────
api_client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .build()


def get_user_lock(open_id: str) -> threading.Lock:
    """获取用户专属锁"""
    with global_lock:
        if open_id not in user_locks:
            user_locks[open_id] = threading.Lock()
        return user_locks[open_id]


def call_claude(prompt: str, session_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    调用 Claude Code CLI
    返回 (回复文本, new_session_id)
    """
    cmd = [CLAUDE_PATH]

    if session_id:
        cmd.extend(['--resume', session_id, '-p', prompt])
    else:
        cmd.extend(['-p', prompt])

    cmd.extend([
        '--model', MODEL,
        '--output-format', 'json',
        '--dangerously-skip-permissions',
        '--append-system-prompt', HANLI_PROMPT,
    ])

    logger.info(f"[Claude] session={session_id and session_id[:8]}, prompt={prompt[:60]}")

    try:
        result = subprocess.run(
            cmd,
            cwd=BOT_DIR,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )

        output = result.stdout.strip()
        new_session_id = session_id

        # 解析 JSON 输出
        if output:
            for line in reversed(output.split('\n')):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        data = json.loads(line)
                        new_session_id = data.get("session_id", session_id)
                        parsed_result = data.get("result", "")
                        if parsed_result:
                            output = parsed_result
                        # 检查是否会话不存在
                        if data.get("is_error") and "No conversation found" in str(data.get("errors", [])):
                            logger.warning(f"[Claude] 会话 {session_id} 已失效，重建...")
                            return call_claude(prompt, session_id=None)
                        break
                    except json.JSONDecodeError:
                        continue

        if not output:
            stderr = result.stderr.strip()
            if stderr:
                logger.warning(f"[Claude] stderr: {stderr[:200]}")
            output = "……（韩某暂时无言以对，道友可再说一遍）"

        return output, new_session_id

    except subprocess.TimeoutExpired:
        return "此事颇为复杂，韩某运功太久，超时了。道友可以精简一下问题再试。", session_id
    except FileNotFoundError:
        logger.error(f"[Claude] CLI 未找到: {CLAUDE_PATH}")
        return "韩某的法器（Claude CLI）似乎未就绪。", session_id
    except Exception as e:
        logger.error(f"[Claude] 调用异常: {e}", exc_info=True)
        return f"韩某遭遇了意外状况，稍后再试。", session_id


def handle_message(data: P2ImMessageReceiveV1):
    """在子线程中处理消息（避免阻塞 WebSocket）"""
    try:
        msg = data.event.message
        sender = data.event.sender.sender_id.open_id
        msg_type = msg.message_type
        message_id = msg.message_id

        # ── 提取文本 ──
        text = ""
        if msg_type == "text":
            content = json.loads(msg.content)
            text = content.get("text", "")
            # 去掉群聊中的 @mention 占位符
            text = re.sub(r'@_user_\d+\s*', '', text).strip()
        elif msg_type == "image":
            reply_msg(message_id, "道友，韩某暂未修炼「望图术」，目前只能处理文字。")
            return
        elif msg_type == "file":
            reply_msg(message_id, "道友传来的法宝（文件），韩某暂时无法查阅。")
            return
        else:
            reply_msg(message_id, "道友，韩某目前只通晓文字之术。")
            return

        if not text:
            return

        logger.info(f"[消息] {sender[:12]}: {text[:80]}")

        # ── 命令处理 ──
        cmd_text = text.strip()

        if cmd_text in ("/reset", "/重置", "重置记忆", "忘掉之前的对话"):
            with global_lock:
                user_sessions.pop(sender, None)
            reply_msg(message_id, "韩某已将先前的交谈忘却，如同服了忘尘丹。道友，我们重新认识。")
            return

        if cmd_text in ("/help", "/帮助", "帮助", "你能做什么"):
            help_text = "\n".join([
                "道友好，韩某能做这些事：",
                "",
                "直接发消息 — 与韩某对话，韩某会记住上下文",
                "/reset — 服用忘尘丹，清除记忆重新开始",
                "/help — 查看此帮助",
                "",
                "韩某虽为修士，但也通晓编程、数据分析、写作、翻译等凡间之术。",
                "有何疑问，尽管开口。",
            ])
            reply_msg(message_id, help_text)
            return

        # ── 调用 Claude（加用户锁，防止同一用户并发导致会话冲突） ──
        lock = get_user_lock(sender)
        with lock:
            session_id = user_sessions.get(sender)
            response, new_session_id = call_claude(text, session_id)

            if new_session_id:
                user_sessions[sender] = new_session_id

        # 飞书文本消息长度限制（约 4000 字符）
        if len(response) > 4000:
            response = response[:3950] + "\n\n…（篇幅过长，韩某只取了要点）"

        reply_msg(message_id, response)
        logger.info(f"[回复] {response[:80]}...")

    except Exception as e:
        logger.error(f"[错误] 处理消息失败: {e}", exc_info=True)
        try:
            reply_msg(data.event.message.message_id, "韩某内息紊乱，请稍后再试。")
        except Exception:
            pass


def on_receive_message(data: P2ImMessageReceiveV1):
    """收到消息回调 → 启动子线程处理"""
    threading.Thread(target=handle_message, args=(data,), daemon=True).start()


def reply_msg(message_id: str, text: str):
    """回复飞书消息"""
    body = ReplyMessageRequestBody.builder() \
        .msg_type("text") \
        .content(json.dumps({"text": text})) \
        .build()

    request = ReplyMessageRequest.builder() \
        .message_id(message_id) \
        .request_body(body) \
        .build()

    resp = api_client.im.v1.message.reply(request)
    if not resp.success():
        logger.error(f"[飞书] 回复失败: code={resp.code}, msg={resp.msg}")


def main():
    logger.info("=" * 50)
    logger.info("「韩立」飞书机器人启动")
    logger.info(f"  模型: {MODEL}")
    logger.info(f"  Claude: {CLAUDE_PATH}")
    logger.info(f"  超时: {COMMAND_TIMEOUT}s")
    logger.info("=" * 50)

    handler = EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(on_receive_message) \
        .build()

    ws_client = WsClient(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        log_level=lark.LogLevel.INFO,
        event_handler=handler,
    )

    logger.info("正在与飞书建立长连接...")
    ws_client.start()


if __name__ == "__main__":
    main()
