"""
亲子英语播客引擎 — 配置文件
Parent-Child English Podcast Engine Configuration
"""

from pathlib import Path

# ============================================================
# 路径配置
# ============================================================
BASE_DIR = Path(__file__).parent
EPISODES_DIR = BASE_DIR / "episodes"
INBOX_DIR = BASE_DIR / "content_sources" / "user_inbox"
VOCABULARY_DIR = BASE_DIR / "vocabulary"
LEARNER_STATE_PATH = BASE_DIR / "learner_state.json"

# AI Briefing pipeline (复用 TTS/上传模块)
AI_BRIEFING_DIR = BASE_DIR.parent / "ai-briefing"

# ============================================================
# 播客基本信息
# ============================================================
PODCAST_NAME = "宝宝英语日课"
PODCAST_DESCRIPTION = "每天15分钟，和宝宝一起学地道英语"
PODCAST_HOSTS = {
    "narrator_en": "Aria",      # 英文原声（妈妈角色）
    "narrator_zh": "递归",       # 中文讲解
}

# ============================================================
# TTS 语音配置
# ============================================================
EDGE_TTS_VOICES = {
    "en_normal": ("en-US-AriaNeural", "+0%"),       # 英文正常速
    "en_slow": ("en-US-AriaNeural", "-15%"),         # 英文慢速（跟读）
    "zh_host": ("zh-CN-XiaoxiaoNeural", "+0%"),      # 中文讲解（Edge 备选）
}

COSYVOICE_VOICES = {
    "zh_host": "longcheng",     # 中文讲解主声（CosyVoice）
}

# 全局语速倍率（ffmpeg atempo）
TTS_SPEED_RATIO = 1.0  # 英语学习不加速

# ============================================================
# 停顿配置（毫秒）
# ============================================================
PAUSES = {
    "part_change": 1200,        # Part 切换（场景→讲解→跟读→实践）
    "scene_sentence": 600,      # 场景内句间
    "decode_example": 500,      # 讲解中例句间
    "shadow_gap": 2000,         # 跟读空白（用户跟读时间）
    "shadow_repeat": 800,       # 慢速重复前
    "speaker_change": 400,      # 中英切换
}

# ============================================================
# 场景主题库
# ============================================================
SCENE_CATEGORIES = {
    "daily_routine": {
        "name": "日常作息",
        "scenes": [
            "morning_wakeup",       # 起床
            "getting_dressed",      # 穿衣
            "brushing_teeth",       # 刷牙
            "mealtime_breakfast",   # 早餐
            "mealtime_lunch",       # 午餐
            "mealtime_dinner",      # 晚餐
            "nap_time",             # 午睡
            "bath_time",            # 洗澡
            "bedtime_routine",      # 睡前
            "diaper_change",        # 换尿布
        ],
    },
    "picture_books": {
        "name": "绘本共读",
        "scenes": [
            "reading_together",     # 一起读绘本
            "asking_questions",     # 提问引导
            "describing_pictures",  # 描述画面
            "retelling_story",      # 复述故事
            "singing_nursery",      # 唱儿歌
        ],
    },
    "outdoor": {
        "name": "户外活动",
        "scenes": [
            "playground",           # 游乐场
            "going_for_walk",       # 散步
            "grocery_shopping",     # 超市购物
            "park_nature",          # 公园/自然
            "car_ride",             # 车上
        ],
    },
    "play_time": {
        "name": "游戏互动",
        "scenes": [
            "building_blocks",      # 积木
            "drawing_coloring",     # 画画
            "play_dough",           # 橡皮泥
            "hide_and_seek",        # 躲猫猫
            "pretend_play",         # 过家家
            "water_play",           # 玩水
            "music_dance",          # 音乐舞蹈
        ],
    },
    "emotions": {
        "name": "情绪引导",
        "scenes": [
            "comforting_crying",    # 安抚哭闹
            "praise_encourage",     # 表扬鼓励
            "setting_boundaries",   # 设定边界
            "sharing_turns",        # 分享/轮流
            "saying_sorry",         # 道歉和好
            "handling_tantrums",    # 处理发脾气
        ],
    },
    "learning": {
        "name": "认知启蒙",
        "scenes": [
            "colors_shapes",        # 颜色形状
            "counting_numbers",     # 数字数数
            "animals_sounds",       # 动物和叫声
            "body_parts",           # 身体部位
            "weather_seasons",      # 天气季节
            "food_taste",           # 食物味道
        ],
    },
}

# ============================================================
# LLM 配置
# ============================================================
DASHSCOPE_API_KEY = "sk-e1151b380b82414d9b29470dd5ec448f"

LLM_PLANNING = {
    "model": "qwen-plus",
    "max_tokens": 4000,
}

LLM_SCRIPT = {
    "model": "qwen-max",
    "max_tokens": 8192,
}

# ============================================================
# 质量门禁
# ============================================================
QUALITY_GATES = {
    "min_segments": 20,
    "min_characters": 2000,
    "min_english_ratio": 0.3,       # 英文内容至少占 30%
    "max_segment_length": 200,       # 单段最大字数
    "min_shadow_sentences": 6,       # 跟读至少 6 句
    "min_phrases": 4,                # 核心表达至少 4 个
}

# AI 套话黑名单（中英双语）
CLICHE_BLACKLIST = [
    "让我们一起", "值得注意", "赋能", "闭环", "由此可见",
    "综上所述", "不言而喻", "让我们深入",
    "Let's dive in", "Without further ado", "Having said that",
    "It goes without saying",
]

# ============================================================
# 服务器配置（复用递归大师的基建）
# ============================================================
SERVER = "134.175.228.73"
SERVER_PASS = "Yumoshucheng@"
SERVER_PODCAST_DIR = "/opt/english-podcast"

# 飞书通知
FEISHU_APP_ID = "cli_a931766ee7789cc7"
FEISHU_APP_SECRET = "4rw86K89yOjmFGavvx4ZKhXMSVXhOQ2m"
FEISHU_USER_OPEN_ID = "ou_d6c763932edf1695f18399f0e4387ec4"
