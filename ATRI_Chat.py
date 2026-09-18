# ATRI_Chat.py - ATRI聊天
# 版本：v1.5.5


# 更新日志
# 1.1
# - 添加 USE_YAML 和 FORCE_USE_JSON 两个布尔值 - 2026.7.9
# - 修改表情包处理规则，删除旧的JSON表情键，使用传统的格式`表情.gif`代替 - 2026.7.9
# - 修改系统提示词 - 2026.7.9
# - 修改大量方法以适配 JSON 和 YAML 两种格式 - 2026.7.9

# 1.2
# - 添加对管道符"|"的解析和处理；现在一共四种解析方式：JSON、YAML、管道符|和正则解析 - 2026.7.9
# - 修改递归总结提示词 - 2026.7.9
# - 分离解密程序，使其完全黑盒化，防止开源解密代码泄露语言模型API密钥 - 2026.7.9

# 1.3
# - 添加布尔值 GALGAME 和 USE_PIPE_SYMBOL - 2026.7.9
# - 适配新的加密模块 - 2026.8.18
# - 修改日志系统 - 2026.8.19

# 1.4
# - 重构前端界面 - 2026.09.09
# - 精简前端代码 - 2026.09.09

# 1.5
# - 重构并精简后端代码 - 2026.09.09
# - 提示词分离 - 2026.09.09
# - 删除"USE_BETA"、"USE_JSON"、"USE_YAML"、"USE_PIPE_SYMBOL"和"FORCE_USE_JSON"等 - 2026.09.09
# - 精简代码、优化前端界面 - 2026.09.10
# - 调整立绘(Doll)大小 - 2026.09.10
# - 增加更多 docstring - 2026.09.10
# - 增加彩蛋 - 2026.09.10
# - 增加整理记忆动画 - 2026.09.10
# - 启动时直接显示UI界面，并进入"思考中……"阶段 - 2026.09.11
# - 修改前端界面 - 2026.09.11 
# - 丰富注释内容 - 2026.09.11

# Tasking
# 1. 启动时背景改为先取上下文，失败再回退默认


import sys
import os
import requests
import json
import pygame
import time
import re
import logging
import traceback
import random
import heapq
import yaml
from datetime import datetime
from typing import Optional
from volcengine.ApiInfo import ApiInfo
from volcengine.Credentials import Credentials
from volcengine.ServiceInfo import ServiceInfo
from volcengine.base.Service import Service
from openai import OpenAI
from zai import ZhipuAiClient
from dataclasses import dataclass
from PyQt6.QtGui import (
    QFont, QPainter, QPixmap, QColor, QPen, QPainterPath,
    QShortcut, QKeySequence
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit,
    QLabel, QScrollArea, QFrame, QGraphicsBlurEffect,
    QGraphicsScene, QGraphicsPixmapItem
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QThread, QObject, QTimer, QRectF, QPoint
)
import ATRI_Crypto


# 常量与路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "Data", "Data[1].bin")
PROMPTS_DIR = os.path.join(BASE_DIR, "Prompts")
MEMORY_CORE_DIR = os.path.join(BASE_DIR, "Memory_Core")
DEBUG_DIR = os.path.join(BASE_DIR, "Debug")
SHORT_TERM_MEMORY_FILE = os.path.join(BASE_DIR, "Short_Term_Memory.json")
LONG_TERM_MEMORY_FILE = os.path.join(BASE_DIR, "Long_Term_Memory.json")

SCENE_DIR = os.path.join(BASE_DIR, "Resources", "Scene")
SCENE_DEFAULT = "客厅.png"
SCENE_FALLBACK_NAME = "客厅"
SCENE_EXTS = (".png",)  # 只使用 .png

DEFAULT_BG_PATH = os.path.join(SCENE_DIR, SCENE_DEFAULT)
DEFAULT_CHAR_PATH = os.path.join(BASE_DIR, "Resources", "Doll", "Atri.png")

TTS_API_URL = "http://127.0.0.1:9880/tts"


# 通用标记
EXIT_FLAG = "🤐"
COT_OPEN = "【"
COT_SPLIT = "】\n"
BOOT_MSG = "<OOC>请依据上下文和'日记'进行回复"
TIME_TAG_FMT = " <OOC>{}</OOC>"


# 字体
def get_platform_font() -> str:
    """获取当前平台适配字体"""
    p = sys.platform
    if p.startswith("win"):
        return "Microsoft YaHei"
    elif p.startswith("linux"):
        return "Inter"
    return "DejaVu Sans"

FONT_FAMILY = get_platform_font()


# 上下文窗口
COT_KEEP_COUNT = 2
CHAT_TEMPERATURE = 1.3
SUMMARY_TEMPERATURE = 1.0
MAX_TOKENS = 8192
SUMMARY_CONTEXT_COUNT = 4


# 记忆核心类别
MEMORY_CATEGORIES = ("diary", "promise", "plan", "preference", "motivation", "pivotal_memory")


# 日志系统
def setup_logger(level_name: str = "INFO") -> logging.Logger:
    """初始化并返回全局日志记录器"""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger = logging.getLogger("ATRI")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    for h in logger.handlers:
        h.setLevel(level)
    return logger

logger = setup_logger()


# 配置数据类
@dataclass
class AppConfig:
    model: str = ""
    provider: str = ""
    api_key: str = ""
    volc_access_key: str = ""
    volc_secret_key: str = ""
    max_history_messages: int = 20
    short_term_memory_messages: int = 10
    summary_history_length: int = 30
    memory_days: int = 3
    use_translation: bool = False
    use_cot: bool = False
    log_level: str = "INFO"

    tts_ref_audio: str = ""
    tts_prompt_text: str = ""
    tts_prompt_lang: str = "ja"
    tts_text_lang: str = "zh"

    @classmethod
    def load(cls) -> "AppConfig":
        """加载并解密配置文件，返回配置对象"""
        try:
            raw = ATRI_Crypto.load_and_decrypt(CONFIG_FILE)
        except FileNotFoundError:
            logger.error("配置文件不存在，请先运行 ATRI_Chat_Setting.py 进行配置")
            sys.exit(1)
        except RuntimeError as e:
            logger.error(f"解密失败: {e}")
            logger.error("请运行 ATRI_Chat_Setting.py 重新配置或使用超级密码恢复")
            sys.exit(1)
        except Exception as e:
            logger.error(f"未知错误: {e}")
            sys.exit(1)

        provider = raw.get("PROVIDER", "")
        key_field = {"深度求索": "CHAT_API_KEY", "智谱": "CHAT_API_KEY2"}.get(provider)
        if not key_field:
            logger.error(f"不支持的模型提供商：{provider}")
            sys.exit(1)
        api_key = raw.get(key_field, "")
        if not api_key:
            logger.error(f"模型提供商为 {provider} 但未配置密钥")
            sys.exit(1)

        use_translation = raw.get("USE_TRANSLATION", False)
        volc_ak = raw.get("VOLC_ACCESS_KEY", "")
        volc_sk = raw.get("VOLC_SECRET_KEY", "")
        if use_translation and (not volc_ak or not volc_sk):
            logger.error("启用翻译但火山引擎密钥缺失")
            sys.exit(1)

        return cls(
            model=raw.get("MODEL", ""),
            provider=provider,
            api_key=api_key,
            volc_access_key=volc_ak,
            volc_secret_key=volc_sk,
            max_history_messages=raw.get("MAX_HISTORY_MESSAGES", 20),
            short_term_memory_messages=raw.get("SHORT_TERM_MEMORY_MESSAGES", 10),
            summary_history_length=raw.get("SUMMARY_HISTORY_LENGTH", 30),
            memory_days=raw.get("MEMORY_DAYS", 3),
            use_translation=use_translation,
            use_cot=raw.get("USE_COT", False),
            log_level=raw.get("LOG_LEVEL", "INFO"),
            tts_ref_audio=os.path.join(BASE_DIR, "Resources", "Audio", "Reference.wav"),
            tts_prompt_text="あなた方ヒトがそのように総称する精密機械に属していますが",
            tts_prompt_lang="ja",
            tts_text_lang="ja" if use_translation else "zh",
        )


# 提示词加载器
class PromptLoader:
    _cache: dict[str, str] = {}

    @classmethod
    def load(cls, filename: str) -> str:
        """读取提示词文件并缓存"""
        if filename in cls._cache:
            return cls._cache[filename]
        path = os.path.join(PROMPTS_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"提示词文件不存在: {path}")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        cls._cache[filename] = content
        return content


    @classmethod
    def render(cls, filename: str, **kwargs) -> str:
        """读取并格式化提示词模板"""
        template = cls.load(filename)
        if kwargs:
            return template.format(**kwargs)
        return template


# 工具函数
def clean_brackets(text: str) -> str:
    """合并连续重复的括号"""
    if not isinstance(text, str):
        return text
    return re.sub(r"([（(）)])\1+", r"\1", text)


def clean_single_square_brackets(text: str) -> str:
    """移除单个方括号标记"""
    if not isinstance(text, str):
        return text
    return text.replace("【", "").replace("】", "")


# 获取不同格式的日期以应对不同场合
def get_timeinfo_1() -> str:
    """获取中文长格式时间"""
    now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"{now.strftime('%Y年%m月%d日')}{weekdays[now.weekday()]} {now.strftime('%H:%M')}"

def get_timeinfo_2() -> str:
    """获取中文短格式时间"""
    now = datetime.now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return f"{now.strftime('%m月%d日')}周{weekdays[now.weekday()]} {now.strftime('%H点%M分')}"

def get_timeinfo_3() -> str:
    """获取仅日期格式时间"""
    return datetime.now().strftime("%Y年%m月%d日")

def parse_diary_date(date_str: str) -> datetime:
    """解析日记日期字符串"""
    for fmt in ("%Y年%m月%d日", "%m月%d日"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.min


# 后端服务主类
class BackendService:
    def __init__(self):
        """初始化后端服务"""
        self.cfg = AppConfig.load()
        self.logger = setup_logger(self.cfg.log_level)
        self.logger.info("成功加载并解密配置文件")

        # 提前创建必要目录
        for d in (MEMORY_CORE_DIR, DEBUG_DIR):
            os.makedirs(d, exist_ok=True)

        self._translate_svc = None

        self._init_ai_client()
        self._init_audio()

        self.memory_core = self._load_memory_core()
        self.related_memories: list[dict] = []
        self.last_ai_response: str = ""

        self.system_prompt_1 = self._build_base_prompt()
        self.system_prompt_2 = (
            self.system_prompt_1
            + "\n\n# 你的记忆\n*记忆不是限制，请灵活运用而不是盲目遵守*\n"
            + self._format_memory_for_prompt()
        )

        self.backend_history: list[dict] = [{"role": "system", "content": self.system_prompt_2}]
        self.backend_long_history: list[dict] = []

        self._load_short_term_memory()

        self.use_chatai = self._test_chatai_service()
        self.tts_success = self._test_tts_service()

        self.opening_line = self._generate_opening_line()


    def _init_ai_client(self):
        """初始化 AI 客户端"""
        if self.cfg.provider == "深度求索":
            self.client = OpenAI(api_key=self.cfg.api_key, base_url="https://api.deepseek.com")
        elif self.cfg.provider == "智谱":
            self.client = ZhipuAiClient(api_key=self.cfg.api_key)
        self.logger.info(f"已初始化 {self.cfg.provider} 客户端，模型: {self.cfg.model}")


    def _init_audio(self):
        """初始化音频系统并清理旧音频"""
        pygame.mixer.init()
        try:
            for f in os.listdir(DEBUG_DIR):
                if f.lower().endswith(".wav"):
                    try:
                        os.unlink(os.path.join(DEBUG_DIR, f))
                    except OSError:
                        pass
        except Exception as e:
            self.logger.warning(f"清理 Debug 音频失败: {e}")
        self.logger.info("音频系统已初始化")


    def _build_base_prompt(self) -> str:
        """构建基础系统提示词"""
        cot_section = ""
        if self.cfg.use_cot:
            cot_section = "\n## 内心独白\n格式：`【……】`\n处理：提供你的语境和独白；由程序自动提取"
        base = PromptLoader.render("System_Base.txt", cot_section=cot_section)
        yaml_prompt = PromptLoader.load("Format_Yaml.txt")
        return base + "\n\n" + yaml_prompt


    def _load_memory_core(self) -> dict:
        """加载全部记忆核心数据"""
        core = {cat: [] for cat in MEMORY_CATEGORIES}
        try:
            for cat in MEMORY_CATEGORIES:
                path = os.path.join(MEMORY_CORE_DIR, f"Memory_Core_{cat}.json")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if cat == "diary":
                            for entry in data:
                                entry.setdefault("essences", [])
                        core[cat] = data
        except Exception as e:
            self.logger.warning(f"加载记忆核心失败: {e}")
        return core


    def _save_memory_category(self, cat: str):
        """保存单个记忆类别"""
        path = os.path.join(MEMORY_CORE_DIR, f"Memory_Core_{cat}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.memory_core[cat], f, ensure_ascii=False, indent=4)


    def _save_memory_core(self, summary_data):
        """保存总结后的记忆核心数据"""
        try:
            if isinstance(summary_data, str):
                summary_data = json.loads(summary_data)

            # 日记按日期合并去重
            if "diary" in summary_data:
                existing = {e["date"]: e for e in self.memory_core["diary"]}
                existing.update({e["date"]: e for e in summary_data["diary"]})
                self.memory_core["diary"] = sorted(
                    existing.values(), key=lambda x: parse_diary_date(x["date"])
                )
                self._save_memory_category("diary")

            # 其他类别直接覆盖
            for cat in MEMORY_CATEGORIES:
                if cat != "diary" and cat in summary_data:
                    self.memory_core[cat] = summary_data[cat]
                    self._save_memory_category(cat)

            self.logger.info("记忆核心已保存")
        except Exception as e:
            self.logger.warning(f"保存记忆核心失败: {e}")


    def _format_memory_for_prompt(self, days: Optional[int] = None) -> str:
        """将记忆核心格式化为提示词文本"""
        if days is None:
            days = self.cfg.memory_days

        lines: list[str] = []
        sections = (
            ("promise", "## 约定", lambda p, i: f"{i}. {p}"),
            ("preference", "## 用户偏好", lambda p, _: str(p)),
            ("motivation", "## 动机", lambda m, i: f"{i}. {m}"),
            ("plan", "## 计划", lambda p, _: f"{p['date']}: {p['content']}"),
            ("pivotal_memory", "## 关键记忆", lambda m, _: str(m)),
        )
        for key, header, fmt in sections:
            items = self.memory_core[key]
            if items:
                lines.append(header)
                lines.extend(fmt(item, i) for i, item in enumerate(items, 1))

        recent = self._get_recent_diary(days)
        if recent:
            lines.append("## 日记")
            lines.extend(f"{e['date']}: {e['content']}" for e in recent)

        return "\n".join(lines).strip()


    def _get_recent_diary(self, days: int = 3) -> list:
        """获取最近的日记"""
        diary = self.memory_core.get("diary", [])
        if not diary:
            return []
        return heapq.nlargest(days, diary, key=lambda x: parse_diary_date(x["date"]))


    def _match_essences(self, text: str, recent_dates: set[str]) -> list[dict]:
        """根据文本关键词 essences 匹配日记"""
        if not isinstance(text, str):
            return []
        lowered = text.lower()
        matched = []
        for entry in self.memory_core.get("diary", []):
            if entry["date"] in recent_dates:
                continue
            for essence in entry.get("essences", []):
                if essence.lower() in lowered:
                    matched.append({
                        "date": entry["date"],
                        "content": entry["content"],
                        "matched_essence": essence,
                    })
                    break
        return matched


    def _select_related_memories(self, ai_text: str, user_text: str) -> list[dict]:
        """选择与当前对话相关的记忆"""
        recent_dates = {e["date"] for e in self._get_recent_diary(self.cfg.memory_days)}
        all_matched = (
            self._match_essences(ai_text, recent_dates)
            + self._match_essences(user_text, recent_dates)
        )
        unique = []
        seen = set()
        for m in all_matched:
            if m["date"] not in seen:
                seen.add(m["date"])
                unique.append(m)

        by_essence: dict[str, list] = {}
        for m in unique:
            by_essence.setdefault(m["matched_essence"], []).append(m)

        essences = list(by_essence.keys())
        n = len(essences)

        if n == 0:
            return []
        if n == 1:
            pool = by_essence[essences[0]]
            if len(pool) <= 3:
                return pool
            return pool[:3] + random.sample(pool[3:], min(2, len(pool) - 3))

        if n <= 5:
            selected = [by_essence[e][0] for e in essences if by_essence[e]]
            all_pool = [m for e in essences for m in by_essence[e]]
            remaining = [m for m in all_pool if m not in selected]
            random_count = max(0, 5 - len(selected))
            selected.extend(random.sample(remaining, min(random_count, len(remaining))))
            return selected[:5]

        first_items = [by_essence[e][0] for e in essences if by_essence[e]]
        return random.sample(first_items, min(5, len(first_items)))


    def _load_short_term_memory(self):
        """加载短期记忆到历史"""
        if not os.path.exists(SHORT_TERM_MEMORY_FILE):
            self.logger.info("未找到短期记忆")
            return
        try:
            with open(SHORT_TERM_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            filtered = [m for m in data if m.get("role") != "system"]
            self.backend_history.extend(filtered[-self.cfg.short_term_memory_messages:])
            self.backend_long_history.extend(filtered[-SUMMARY_CONTEXT_COUNT:])
            self.logger.info(
                f"后端历史: {len(self.backend_history)} 条 | "
                f"长历史: {len(self.backend_long_history)} 条"
            )
        except Exception as e:
            self.logger.warning(f"加载短期记忆出错: {e}")


    def _save_short_term_memory(self):
        """保存短期记忆"""
        try:
            with open(SHORT_TERM_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.backend_history, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.logger.warning(f"保存短期记忆失败: {e}")


    def _save_long_term_memory(self):
        """保存长期记忆"""
        try:
            non_system = [m for m in self.backend_history if m.get("role") != "system"]
            if not non_system:
                return
            existing = []
            if os.path.exists(LONG_TERM_MEMORY_FILE):
                with open(LONG_TERM_MEMORY_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing_keys = {(m.get("role"), m.get("content")) for m in existing}
            new_msgs = [
                m for m in non_system
                if (m.get("role"), m.get("content")) not in existing_keys
            ]
            if not new_msgs:
                return

            with open(LONG_TERM_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(existing + new_msgs, f, ensure_ascii=False, indent=4)
            self.logger.info(f"保存 {len(new_msgs)} 条新消息到长期记忆")
        except Exception as e:
            self.logger.warning(f"保存长期记忆出错: {e}")


    def _append_message(self, role: str, content: str) -> dict:
        """向后端历史、后端长历史中添加消息"""
        msg = {"role": role, "content": content}
        self.backend_history.append(msg)
        self.backend_long_history.append(msg)
        return msg


    @staticmethod
    def _clean_history(history: list, keep_count: int = 0):
        """清理历史中较老AI消息的CoT前缀"""
        ai_indices = [i for i, m in enumerate(history) if m["role"] == "assistant"]
        if keep_count > 0:
            ai_indices = ai_indices[:-keep_count] if keep_count < len(ai_indices) else []
        for idx in ai_indices:
            c = history[idx]["content"]
            if c.startswith(COT_OPEN) and COT_SPLIT in c:
                history[idx]["content"] = c.split(COT_SPLIT, 1)[1]


    def _clean_reasoning_content(self):
        """清理历史中的思维链内容"""
        keep = COT_KEEP_COUNT if self.cfg.use_cot else 0
        for hist in (self.backend_history, self.backend_long_history):
            self._clean_history(hist, keep)


    def _trim_context_window(self):
        """裁剪上下文窗口，成对删除旧消息"""
        system_msg = self.backend_history[0]
        dialogue = self.backend_history[1:]
        max_d = max(0, self.cfg.max_history_messages - 1)

        if len(dialogue) > max_d:
            drop = len(dialogue) - max_d
            drop += drop % 2  # 保持 user/assistant 成对
            dialogue = dialogue[drop:]

        self.backend_history = [system_msg] + dialogue


    def _chat_completion(self, messages, temperature, response_format=None):
        """统一调用 chat.completions，返回 content, reasoning, tokens"""
        kwargs = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": MAX_TOKENS,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        content = msg.content
        reasoning = getattr(msg, "reasoning_content", "") or ""
        tokens = response.usage.total_tokens
        return content, reasoning, tokens


    def _call_chatai(self) -> tuple[str, str, Optional[int]]:
        """调用聊天AI接口"""
        if self.backend_history and self.backend_history[0]["role"] == "system":
            self.backend_history[0]["content"] = self._build_system_with_memories()
        self._clean_reasoning_content()
        self._trim_context_window()
        self.logger.debug(f"请求条数: {len(self.backend_history)}")
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("后端历史: %s",
                              json.dumps(self.backend_history, ensure_ascii=False, indent=2))
            self.logger.debug("后端长历史: %s",
                              json.dumps(self.backend_long_history, ensure_ascii=False, indent=2))

        try:
            content, reasoning, tokens = self._chat_completion(self.backend_history, CHAT_TEMPERATURE)
            if reasoning:
                self.logger.debug(f"AI思维链：\n{reasoning}")
            return content, reasoning, tokens
        except Exception as e:
            self.logger.error(f"ChatAI API 异常: {e}")
            return "欸……连接不上我的大脑😵", "", None


    def _combine_with_cot(self, content: str, reasoning: str) -> str:
        """合并思维链和正式回复"""
        if not self.cfg.use_cot:
            return content
        cleaned = clean_single_square_brackets(content)
        return f"{COT_OPEN}{reasoning}{COT_SPLIT}{cleaned}" if reasoning else cleaned


    def _build_system_with_memories(self) -> str:
        """构建带相关记忆的系统提示词"""
        prompt = self.system_prompt_2
        if self.related_memories:
            prompt += "\n## 相关记忆(和最新对话有关的记忆)"
            for m in self.related_memories:
                prompt += f"\n{m['date']}: {m['content']}"
        return prompt


    def process_user_message(self, user_input: str, play_tts: bool = True) -> tuple[str, bool]:
        """处理用户消息并返回 AI 回复"""
        if not self.use_chatai:
            return f"ChatAI不可用 {user_input}", False

        self.related_memories = self._select_related_memories(self.last_ai_response, user_input)
        cleaned_input = clean_brackets(user_input)
        self._append_message("user", cleaned_input)
        self.logger.debug(f"用户消息: {cleaned_input}")

        if self.related_memories:
            self.logger.debug(
                f"匹配记忆({len(self.related_memories)}条): "
                f"{[m['matched_essence'] for m in self.related_memories]}"
            )

        content, reasoning, tokens = self._call_chatai()
        content = content.strip()
        reasoning = reasoning.strip() if reasoning else ""

        combined = self._combine_with_cot(content, reasoning)
        self.last_ai_response = content

        cleaned_combined = clean_brackets(combined)
        self._append_message("assistant", cleaned_combined)

        should_exit = EXIT_FLAG in content
        if self.tts_success and play_tts:
            self.process_ai_response_tts(content)

        self._save_short_term_memory()

        if should_exit:
            self.trigger_exit_summary()

        # 长期记忆在退出时才进行写入
        self.logger.info(f"Token: {tokens} | 条数: {len(self.backend_history)}")

        return content, should_exit


    def process_ai_response_tts(self, ai_response: str) -> bool:
        """提取对话并执行TTS"""
        if not self.tts_success:
            return False

        dialogue = self._extract_dialogue(ai_response)
        if not dialogue:
            return EXIT_FLAG in ai_response

        translated = self._translate_to_japanese(dialogue)
        text = translated or dialogue
        return self._text_to_speech(text)


    def _extract_dialogue(self, text: str) -> str:
        """从AI回复中提取可读内容"""
        match = re.search(r"content:\s*(.*?)(?=\n\w+:|\Z)", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

        prev = None
        while prev != text:
            prev = text
            text = re.sub(r"（.*?）", "", text, flags=re.DOTALL)
            text = re.sub(r"\(.*?\)", "", text, flags=re.DOTALL)

        cleaned = re.sub(r"\s+", " ", text.strip())
        cleaned = cleaned.replace("...", "……")
        cleaned = re.sub(r"[Zz]{3,}", "", cleaned)
        return cleaned


    def _get_translate_service(self) -> Service:
        """懒加载火山翻译，复用连接"""
        if self._translate_svc is None:
            service_info = ServiceInfo(
                "translate.volcengineapi.com",
                {"Content-Type": "application/json"},
                Credentials(self.cfg.volc_access_key, self.cfg.volc_secret_key,
                            "translate", "cn-north-1"),
                5, 5,
            )
            api_info = {
                "translate": ApiInfo("POST", "/",
                                     {"Action": "TranslateText", "Version": "2020-06-01"},
                                     {}, {})
            }
            self._translate_svc = Service(service_info, api_info)
        return self._translate_svc


    def _translate_to_japanese(self, text: str) -> Optional[str]:
        """将文本翻译为日语，超时自动重试一次"""
        if not self.cfg.use_translation:
            return text

        for attempt in range(2):
            try:
                service = self._get_translate_service()
                body = {"TargetLanguage": "ja", "TextList": [text], "SourceLanguage": "zh"}
                resp = json.loads(service.json("translate", {}, json.dumps(body)))
                if "TranslationList" in resp and resp["TranslationList"]:
                    return resp["TranslationList"][0]["Translation"]
                self.logger.error(f"翻译API返回异常: {json.dumps(resp, ensure_ascii=False)}")
                return None
            except Exception as e:
                if attempt == 0 and "timed out" in str(e).lower():
                    self.logger.warning("翻译超时，重试中……")
                    continue
                self.logger.error(f"翻译异常: {e}")
                return None
        return None


    def _text_to_speech(self, text: str) -> bool:
        """调用 GPT-SoVITS 并播放语音"""
        try:
            request_data = {
                "ref_audio_path": self.cfg.tts_ref_audio,
                "prompt_text": self.cfg.tts_prompt_text,
                "prompt_lang": self.cfg.tts_prompt_lang,
                "text_lang": self.cfg.tts_text_lang,
                "top_k": 50,
                "top_p": 0.95,
                "temperature": 1.0,
                "batch_size": 40,
                "parallel_infer": True,
                "split_bucket": True,
                "super_sampling": True,
                "text": text,
            }
            self.logger.debug(f"TTS文本: {text}")
            response = requests.post(TTS_API_URL, json=request_data, timeout=60)

            if response.status_code != 200:
                self.logger.error(f"TTS错误: HTTP {response.status_code}")
                return False

            audio_path = os.path.join(DEBUG_DIR, f"response_{int(time.time())}.wav")
            with open(audio_path, "wb") as f:
                f.write(response.content)

            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            return True

        except Exception as e:
            error_msg = str(e).lower()
            tb = traceback.format_exc()
            with open(os.path.join(DEBUG_DIR, "TTS_Error.log"), "w", encoding="utf-8") as f:
                f.write(tb)

            if any(kw in error_msg for kw in ("connection refused", "max retries", "errno 111", "errno 10061")):
                self.logger.error("GPT-SoVITS 服务未运行")
            else:
                self.logger.error(f"GPT-SoVITS 异常: {e}")
            return False


    def trigger_exit_summary(self):
        """执行退出总结流程"""
        self.logger.info("触发退出流程，开始递归总结")
        self._add_time_to_memory()
        self._request_summary()
        self._remove_summary_from_short_term()
        self._save_long_term_memory()


    def _add_time_to_memory(self):
        """向短期记忆添加时间标记"""
        try:
            tag = TIME_TAG_FMT.format(get_timeinfo_2())
            for hist in (self.backend_history, self.backend_long_history):
                if len(hist) >= 2 and "<OOC>" not in hist[-2].get("content", ""):
                    hist[-2]["content"] += tag
            self._save_short_term_memory()
        except Exception as e:
            self.logger.warning(f"添加时间信息失败: {e}")


    def _request_summary(self) -> Optional[str]:
        """请求对话总结并保存记忆"""
        try:
            summary_history = self._get_summary_history()
            self._save_debug("dialogue_summary_messages", summary_history)

            summary_request = {"role": "user", "content": PromptLoader.load("Summary_Request.txt")}
            summary_history.append(summary_request)
            current_summary, _ = self._call_chatai_for_summary(summary_history)
            self._save_debug("dialogue_summary_result", current_summary)

            has_old = any(self.memory_core[cat] for cat in MEMORY_CATEGORIES)
            if not has_old:
                self._save_memory_core(current_summary)
                self.logger.info("总结完成（无旧记忆）")
                return current_summary

            recent_diary = self._get_recent_diary(2)
            old_memory_json = json.dumps({
                "diary": recent_diary,
                "promise": self.memory_core["promise"],
                "preference": self.memory_core["preference"],
                "plan": self.memory_core["plan"],
                "motivation": self.memory_core["motivation"],
                "pivotal_memory": self.memory_core["pivotal_memory"],
            }, ensure_ascii=False)

            recursive_user = PromptLoader.render(
                "Summary_Recursive.txt",
                old_memory_json=old_memory_json,
                short_date=get_timeinfo_3(),
                current_summary=current_summary,
            )
            recursive_system = PromptLoader.load("Summary_System.txt")

            recursive_messages = [
                {"role": "system", "content": recursive_system},
                {"role": "user", "content": recursive_user},
            ]
            self._save_debug("recursive_summary_messages", recursive_messages)

            recursive_result, _ = self._call_chatai_for_summary(recursive_messages)
            self._save_debug("recursive_summary_result", recursive_result)
            self._save_memory_core(recursive_result)
            self.logger.info("递归总结完成")
            return recursive_result

        except Exception as e:
            self.logger.error(f"获取总结失败: {e}")
            return None


    def _get_summary_history(self) -> list[dict]:
        """构建总结用历史消息"""
        memory_for_summary = self._format_memory_for_prompt(2)
        sys_prompt = self.system_prompt_1 + "\n你的记忆:\n" + memory_for_summary
        dialogue = self.backend_long_history[-self.cfg.summary_history_length:]
        return [{"role": "system", "content": sys_prompt}] + dialogue


    def _call_chatai_for_summary(self, messages: list[dict]) -> tuple[str, Optional[int]]:
        """调用AI进行总结"""
        try:
            content, _, tokens = self._chat_completion(
                messages,
                SUMMARY_TEMPERATURE,
                response_format={"type": "json_object"},
            )
            return content, tokens
        except Exception as e:
            self.logger.error(f"总结API调用异常: {e}")
            return "{}", None


    def _remove_summary_from_short_term(self):
        """从短期记忆中删除总结请求与结果"""
        try:
            if not os.path.exists(SHORT_TERM_MEMORY_FILE):
                return
            with open(SHORT_TERM_MEMORY_FILE, "r", encoding="utf-8") as f:
                stm = json.load(f)
            if len(stm) >= 2:
                last_two = stm[-2:]
                has_req = any("请以第一人称总结以上对话" in m.get("content", "") for m in last_two)
                has_resp = any(m.get("role") == "assistant" for m in last_two)
                if has_req and has_resp:
                    stm = stm[:-2]
                    with open(SHORT_TERM_MEMORY_FILE, "w", encoding="utf-8") as f:
                        json.dump(stm, f, ensure_ascii=False, indent=4)
                    self.logger.info("已从短期记忆中删除总结消息")
        except Exception as e:
            self.logger.warning(f"删除总结消息失败: {e}")


    def _test_chatai_service(self) -> bool:
        """测试 ChatAI 服务(开场白)"""
        # 测试AI连通性也是作为开场白方法，确保在用户实际发送信息前不进行写入到后端历史、后端长历史即符合预期
        self.logger.info("测试ChatAI……")
        try:
            time_info = get_timeinfo_2()
            has_memory = (
                os.path.exists(SHORT_TERM_MEMORY_FILE)
                or os.path.exists(os.path.join(MEMORY_CORE_DIR, "Memory_Core_diary.json"))
            )

            if has_memory:
                test_content = (
                    f"{BOOT_MSG}，如果时间跨度较小则侧重上下文推理，"
                    f"否则应该重点推理该跨度时间内可能做的事情，比如一些日常；"
                    f"此次回复不要带'{EXIT_FLAG}' | {time_info}</OOC>"
                )
            else:
                test_content = (
                    f"<OOC>你是用户网购的实验性仿生人，使命是实现用户愿望。"
                    f"现在是你和用户第一次见面，你刚刚从充电舱中醒来，请和用户打招呼吧。"
                    f"很多事物对亚托莉来说是新奇的，她会好奇，会偷偷打量周围的事物。"
                    f"另外注意人称，回复自称为`我` | {time_info}</OOC>"
                )

            self._append_message("user", clean_brackets(test_content))

            content, reasoning, tokens = self._call_chatai()
            combined = self._combine_with_cot(
                content.strip(), reasoning.strip() if reasoning else ""
            )
            self._append_message("assistant", clean_brackets(combined))

            self.logger.info(f"ChatAI连接正常 | Token: {tokens}")
            return True
        except Exception as e:
            self.logger.error(f"ChatAI API 错误: {e}")
            return False


    def _test_tts_service(self) -> bool:
        """TTS服务检测"""
        self.logger.info("测试TTS服务……")
        try:
            if not os.access(DEBUG_DIR, os.W_OK):
                self.logger.error("TTS输出文件夹不可写")
                return False
            requests.get(TTS_API_URL, timeout=3)
            self.logger.info("TTS服务连接正常")
            return True
        except requests.ConnectionError:
            self.logger.warning("TTS服务未运行，将以静音模式工作")
            return False
        except Exception as e:
            self.logger.warning(f"TTS检测异常: {e}")
            return False


    def _generate_opening_line(self) -> str:
        """生成开场白"""
        if not self.use_chatai:
            return "欸……连接不上我的大脑😵"
        last = self.backend_history[-1]["content"]
        if self.cfg.use_cot and last.startswith(COT_OPEN) and COT_SPLIT in last:
            return last.split(COT_SPLIT, 1)[1]
        return last


    def _save_debug(self, name: str, data):
        """保存调试数据"""
        try:
            path = os.path.join(DEBUG_DIR, f"{name}.json")
            payload = {
                "type": name,
                "timestamp": int(time.time()),
                "formatted_time": get_timeinfo_1(),
                "data": data,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.logger.warning(f"保存调试数据失败: {e}")


    def get_opening_line(self) -> str:
        """获取开场白"""
        return self.opening_line


# 通用后台 Worker
class Worker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except SystemExit:
            self.failed.emit("后端配置错误，已退出")
        except Exception as e:
            logger.exception("后台任务失败")
            self.failed.emit(str(e))


# 前端界面
def blur_pixmap(pixmap: QPixmap, radius: float) -> QPixmap:
    """对 QPixmap 进行高斯模糊"""
    if pixmap.isNull():
        return pixmap
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(pixmap)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    result = QPixmap(pixmap.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter, QRectF(result.rect()), QRectF(pixmap.rect()))
    painter.end()
    return result


def parse_yaml_response(raw: str) -> dict:
    """解析 AI 返回的 YAML 内容"""
    result = {"scene": "", "content": raw, "option1": "", "option2": ""}
    try:
        # 若带思维链则先剥离，避免 YAML 解析失败
        if raw.startswith(COT_OPEN) and COT_SPLIT in raw:
            raw = raw.split(COT_SPLIT, 1)[1]

        clean = re.sub(r'```(?:yaml)?\s*|\s*```', '', raw).strip()
        data = yaml.safe_load(clean)
        if isinstance(data, dict):
            result["scene"] = str(data.get("scene") or "")
            result["content"] = str(data.get("content") or raw)
            result["option1"] = str(data.get("option1") or "")
            result["option2"] = str(data.get("option2") or "")
    except Exception:
        pass
    result["content"] = re.sub(r'[（(][^）)]*\.gif[）)]', '', result["content"]).strip()
    return result


class SceneRenderer:
    """场景渲染器"""
    # 合成 背景(scene) + 立绘(Doll)
    def __init__(self, bg_path: str, char_path: str):
        self.bg_pixmap = QPixmap(bg_path)  # 背景层：scene
        self.char_pixmap = QPixmap(char_path)  # 立绘层：Doll


    def set_background(self, bg_path: str) -> bool:
        """切换背景图；成功返回 True"""
        pixmap = QPixmap(bg_path)
        if pixmap.isNull():
            return False
        self.bg_pixmap = pixmap
        return True


    def render(self, width: int, height: int) -> QPixmap:
        """渲染背景与立绘"""
        # 渲染顺序：先背景(scene)，再立绘(Doll)
        canvas = QPixmap(width, height)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 背景：进行等比缩放并居中裁剪
        if not self.bg_pixmap.isNull():
            scaled_bg = self.bg_pixmap.scaled(
                width, height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (width - scaled_bg.width()) // 2
            y = (height - scaled_bg.height()) // 2
            painter.drawPixmap(x, y, scaled_bg)

        # 立绘：底部居中
        if not self.char_pixmap.isNull():
            target_h = int(height * 0.75 * 1.10)
            scaled_char = self.char_pixmap.scaledToHeight(
                target_h, Qt.TransformationMode.SmoothTransformation
            )
            cx = (width - scaled_char.width()) // 2
            cy = height - scaled_char.height()
            painter.drawPixmap(cx, cy, scaled_char)

        painter.end()
        return canvas


class GlassDialog(QWidget):
    """特殊毛玻璃对话框"""
    # 渲染AI 回复界面、用户回复界面、思考动画、选项与输入
    clicked_advance = pyqtSignal()
    option_selected = pyqtSignal(str)
    return_to_ai_display = pyqtSignal()

    # 统一渲染样式：
    # - 板块样式：无色100%透明、圆角20、模糊半径10、级联模糊3次、1像素纯白色描边
    # - 按钮样式：无色100%透明、圆角13、模糊半径10、级联模糊3次、1像素纯白色描边
    # - 字体样式：黑色、字号14
    CORNER_RADIUS = 20
    BLUR_RADIUS = 10
    BLUR_CASCADE = 3
    TEXT_SIZE = 14
    SCENE_TEXT_SIZE = 11  # 场景小字号特殊处理

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._state = "ai_display"
        self._options = ("", "")
        self._thinking_prefix = "思考中"
        self._current_scene = ""  # 当前场景，供用户回复界面复用
        self._blur_cache_key = None
        self._blur_cache = None
        self._build_ui()


    def _build_ui(self):
        """构建对话框 UI"""
        # 渲染头部、分割线、内容区、选项、输入框
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 14, 24, 18)
        layout.setSpacing(6)

        # 头部容器：角色名 + 场景名
        self.header_widget = QWidget()
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        self.name_label = QLabel("亚托莉")
        self.name_label.setFont(QFont(FONT_FAMILY, self.TEXT_SIZE, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: black; background: transparent;")

        self.scene_label = QLabel("")
        self.scene_label.setFont(QFont(FONT_FAMILY, self.SCENE_TEXT_SIZE))
        self.scene_label.setStyleSheet("color: rgba(0,0,0,0.55); background: transparent;")

        header_layout.addWidget(self.name_label)
        header_layout.addWidget(self.scene_label)
        layout.addWidget(self.header_widget)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: rgba(0,0,0,0.3); border: none;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # 内容区：消息、选项、输入框
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 6, 0, 0)
        self.content_layout.setSpacing(8)
        layout.addWidget(self.content_widget, 1)

        # AI 消息文本
        self.msg_label = QLabel()
        self.msg_label.setWordWrap(True)
        self.msg_label.setFont(QFont(FONT_FAMILY, self.TEXT_SIZE))
        self.msg_label.setStyleSheet("color: black; background: transparent;")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.msg_label)

        # 用户选项：两个选项(option) + 自定义输入入口
        self.opt1_label = QLabel()
        self.opt2_label = QLabel()
        self.custom_label = QLabel("我想说……")
        for lab in (self.opt1_label, self.opt2_label, self.custom_label):
            lab.setFont(QFont(FONT_FAMILY, self.TEXT_SIZE))
            lab.setStyleSheet(
                "color: black; background: rgba(255,255,255,0.25);"
                "padding: 8px 12px; border-radius: 8px;"
            )
            lab.setCursor(Qt.CursorShape.PointingHandCursor)
            lab.hide()
        self.opt1_label.mousePressEvent = lambda _: self._emit_option(0)
        self.opt2_label.mousePressEvent = lambda _: self._emit_option(1)
        self.custom_label.mousePressEvent = lambda _: self._switch_to_input()
        self.content_layout.addWidget(self.opt1_label)
        self.content_layout.addWidget(self.opt2_label)
        self.content_layout.addWidget(self.custom_label)

        # 自定义输入框
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("请输入文本")
        self.input_edit.setFont(QFont(FONT_FAMILY, self.TEXT_SIZE))
        self.input_edit.setStyleSheet(
            f'QTextEdit {{ background: transparent; border: none; '
            f'color: black; font-family: "{FONT_FAMILY}"; font-size: {self.TEXT_SIZE}pt; }}'
        )
        self.input_edit.setMaximumHeight(90)
        self.input_edit.hide()
        self.content_layout.addWidget(self.input_edit)

        # 思考动画定时器
        self._thinking_timer = QTimer(self)
        self._thinking_timer.timeout.connect(self._update_thinking_animation)
        self._thinking_dots = 0


    def _set_state(self, state, *, name, align, msg_visible=False,
                   options_visible=False, input_visible=False, scene=None):
        """统一切换对话框状态"""
        self.stop_thinking()
        self._state = state
        self.name_label.setText(name)
        self.name_label.setAlignment(align)
        # 场景标签与名字标签使用同一对齐方式：AI 左对齐，用户右对齐
        self.scene_label.setAlignment(align)
        if not scene:
            self.scene_label.hide()
        else:
            self.scene_label.setText(scene)
            self.scene_label.show()
        self.msg_label.setVisible(msg_visible)
        self.opt1_label.setVisible(options_visible)
        self.opt2_label.setVisible(options_visible)
        self.custom_label.setVisible(options_visible)
        self.input_edit.setVisible(input_visible)
        self.update()


    def show_ai_message(self, content: str, scene: str = ""):
        """显示AI消息"""
        # AI回复界面
        self._current_scene = scene or self._current_scene
        self._set_state(
            "ai_display",
            name="亚托莉",
            align=Qt.AlignmentFlag.AlignLeft,
            msg_visible=True,
            scene=scene,
        )
        self.msg_label.setText(content)


    def show_options(self, opt1: str, opt2: str):
        """用户回复界面"""
        # 显示选项并同步AI阶段的"scene"
        self._options = (opt1, opt2)
        self.opt1_label.setText(opt1)
        self.opt2_label.setText(opt2)
        self._set_state(
            "opt_display",
            name="我",
            align=Qt.AlignmentFlag.AlignRight,
            options_visible=True,
            scene=self._current_scene,
        )


    def _switch_to_input(self):
        """切换输入状态"""
        # 显示输入框并显示"scene"
        self._set_state(
            "input",
            name="我",
            align=Qt.AlignmentFlag.AlignRight,
            input_visible=True,
            scene=self._current_scene,
        )
        self.input_edit.setFocus()


    def show_thinking(self, scene: str = "", prefix: str = "思考中"):
        """思考阶段动画"""
        if scene:
            self._current_scene = scene
        self._thinking_prefix = prefix
        self._set_state(
            "thinking",
            name="亚托莉",
            align=Qt.AlignmentFlag.AlignLeft,
            msg_visible=True,
            scene=scene or self._current_scene,
        )
        self.msg_label.setText(f"（{prefix}……）")
        self._thinking_dots = 0
        self._thinking_timer.start(300)


    def show_summarizing(self, scene: str = ""):
        """整理记忆动画"""
        self.show_thinking(scene, prefix="正在整理记忆")


    def stop_thinking(self):
        """停止思考动画"""
        if hasattr(self, "_thinking_timer"):
            self._thinking_timer.stop()


    def _update_thinking_animation(self):
        """更新思考动画的省略号数量"""
        self._thinking_dots = (self._thinking_dots + 1) % 7
        dots = "." * self._thinking_dots
        self.msg_label.setText(f"（{self._thinking_prefix}{dots}）")
        self.update()


    def _emit_option(self, idx: int):
        """发出选项选择信号"""
        self.option_selected.emit(self._options[idx])


    def get_input_text(self) -> str:
        """获取输入框文本"""
        return self.input_edit.toPlainText().strip()


    def clear_input(self):
        """清空输入框"""
        self.input_edit.clear()


    def keyPressEvent(self, event):
        """处理按键事件"""
        # ESC 从用户回复界面返回 AI 显示
        if event.key() == Qt.Key.Key_Escape and self._state in ("opt_display", "input"):
            self.return_to_ai_display.emit()
        else:
            super().keyPressEvent(event)


    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        # AI显示状态下，左键点击推进到用户回复界面
        if event.button() == Qt.MouseButton.LeftButton and self._state == "ai_display":
            self.clicked_advance.emit()
        super().mousePressEvent(event)


    def paintEvent(self, event):
        """绘制特殊玻璃对话框"""
        # 从主窗口场景截取并模糊
        window = self.window()
        scene_pixmap = getattr(window, "_scene_composite", None)
        if scene_pixmap is None or scene_pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pos = self.mapTo(window, QPoint(0, 0))
        margin = 2
        rx = max(0, pos.x() - margin)
        ry = max(0, pos.y() - margin)
        rw = min(scene_pixmap.width() - rx, self.width() + margin * 2)
        rh = min(scene_pixmap.height() - ry, self.height() + margin * 2)

        # 模糊缓存：场景、位置、尺寸不变时直接复用
        key = (scene_pixmap.cacheKey(), int(rx), int(ry), int(rw), int(rh))
        if self._blur_cache_key == key and self._blur_cache is not None:
            region = self._blur_cache
        else:
            region = scene_pixmap.copy(int(rx), int(ry), int(rw), int(rh))
            for _ in range(self.BLUR_CASCADE):
                region = blur_pixmap(region, self.BLUR_RADIUS)
            self._blur_cache_key = key
            self._blur_cache = region

        # 圆角裁剪并绘制模糊背景
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.CORNER_RADIUS, self.CORNER_RADIUS)
        painter.setClipPath(path)
        painter.drawPixmap(-margin, -margin, region)

        # 玻璃边框
        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawRoundedRect(QRectF(self.rect()), self.CORNER_RADIUS, self.CORNER_RADIUS)
        super().paintEvent(event)


class ContextMask(QWidget):
    """初始化上下文遮罩"""
    # 半透明黑底，滚动显示历史消息

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)

        # 滚动区域：矩形容器，容纳历史消息
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.15);
                width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.5);
                border-radius: 4px; min-height: 30px;
            }
        """)
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(14)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.content)
        layout.addWidget(scroll)


    def update_history(self, history: list):
        """更新上下文历史显示"""
        # 清空旧控件
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for msg in history:
            role = msg.get("role", "")
            text = msg.get("content", "")
            if role == "system":
                continue
            lab = QLabel()
            lab.setWordWrap(True)
            lab.setFont(QFont(FONT_FAMILY, 14))
            if role == "user":
                lab.setText(f"<b>我：</b>{text}")
            else:
                lab.setText(f"<b>亚托莉：</b>{text}")
            lab.setStyleSheet("color: white; background: transparent;")
            lab.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.content_layout.addWidget(lab)


    def paintEvent(self, event):
        """绘制半透明黑色遮罩"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))


class VisualNovelFrontend(QMainWindow):
    """初始化视觉小说前端"""
    # 最底部背景(scene)、立绘(Doll)、毛玻璃对话框、上下文遮罩

    def __init__(self, backend=None):
        super().__init__()
        self.backend = backend
        self.setWindowTitle("ATRI_Chat · 视觉小说模式")
        self.setFont(QFont(FONT_FAMILY, 14))
        self.resize(1280, 720)
        self.setMinimumSize(800, 450)

        self.ui_busy = False
        self._current_ai_response = ""
        self.frontend_history: list[dict] = []
        self._pending_options = ("", "")
        self._workers = []  # 持有后台线程/Worker，防止被 GC

        # 场景索引
        self.scene_index = {}
        try:
            for f in os.listdir(SCENE_DIR):
                if f.lower().endswith(".png"):
                    stem = os.path.splitext(f)[0]
                    self.scene_index[stem] = os.path.join(SCENE_DIR, f)
        except Exception as e:
            logger.warning(f"构建场景索引失败: {e}")

        # 提取上一段对话的"scene"
        self._current_scene = self._get_last_scene() or SCENE_FALLBACK_NAME

        # 场景渲染器：背景(scene) + 立绘(Doll)
        self.scene_renderer = SceneRenderer(
            bg_path=DEFAULT_BG_PATH,
            char_path=DEFAULT_CHAR_PATH,
        )
        self._scene_composite = QPixmap()

        # 布局防抖定时器
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(30)
        self._layout_timer.timeout.connect(self._update_layout)

        self._build_ui()
        self._setup_shortcuts()

        if self.backend is None:
            # 后端尚未就绪时，先展示思考阶段动画，并尝试切换到上一段对话的场景
            self.dialog.show_thinking(self._current_scene, prefix="思考中")
            QTimer.singleShot(120, lambda: self._apply_scene_background(self._current_scene))
        else:
            self._show_opening()

        QTimer.singleShot(80, self._update_layout)


    def _build_ui(self):
        """构建前端UI"""
        # 中央透明容器 + 毛玻璃对话框 + 上下文遮罩
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        central.setAutoFillBackground(False)
        self.setCentralWidget(central)

        self.dialog = GlassDialog(central)
        self.dialog.clicked_advance.connect(self._on_advance)
        self.dialog.option_selected.connect(self._on_option_select)
        self.dialog.return_to_ai_display.connect(self._on_esc_return)

        self.context_mask = ContextMask(self)


    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+Enter 发送
        # Ctrl+/ 切换上下文
        QShortcut(
            QKeySequence(Qt.Key.Key_Return | Qt.KeyboardModifier.ControlModifier),
            self, activated=self._send_message
        )
        QShortcut(
            QKeySequence(Qt.Key.Key_Slash | Qt.KeyboardModifier.ControlModifier),
            self, activated=self._toggle_context
        )


    def _run_worker(self, fn, on_success, on_failed=None, *args, **kwargs):
        """统一创建后台线程任务，并持有引用防止 GC"""
        worker = Worker(fn, *args, **kwargs)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        if on_failed:
            worker.failed.connect(on_failed)
        else:
            worker.failed.connect(lambda err: logger.error(err))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self._workers.append((worker, thread))

        def cleanup():
            try:
                self._workers.remove((worker, thread))
            except ValueError:
                pass

        thread.finished.connect(cleanup)
        thread.start()
        return worker, thread


    def _get_last_scene(self) -> str:
        """从短期记忆文件里最后一条 assistant 消息中解析 scene"""
        try:
            if not os.path.exists(SHORT_TERM_MEMORY_FILE):
                return ""
            with open(SHORT_TERM_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return ""
            for msg in reversed(data):
                if msg.get("role") == "assistant":
                    parsed = parse_yaml_response(msg.get("content", ""))
                    if parsed["scene"]:
                        return parsed["scene"]
        except Exception as e:
            logger.warning(f"提取上一段对话场景失败: {e}")
        return ""


    def on_backend_ready(self, backend):
        """后端初始化完成后调用"""
        self.backend = backend
        self._show_opening()


    def on_backend_failed(self, err: str):
        """后端初始化失败回调"""
        self.dialog.show_ai_message(f"后端加载失败：{err}", self._current_scene)
        self.ui_busy = False


    def _apply_scene_background(self, scene_name: str) -> None:
        """根据 scene 字段切换背景"""
        # 解析失败或文件不存在时不切换
        if not scene_name:
            return
        scene_name = os.path.splitext(scene_name)[0]  # 去掉扩展名
        path = self.scene_index.get(scene_name)
        if path and self.scene_renderer.set_background(path):
            self._update_layout()
            logger.info(f"场景已切换: {scene_name}")
        else:
            logger.warning(f"未找到匹配的场景文件: {scene_name}.png")


    def _apply_ai_response(self, response: str):
        """应用 AI 回复到界面"""
        # 解析 scene、content、选项
        parsed = parse_yaml_response(response)
        if parsed["scene"]:
            self._current_scene = parsed["scene"]
            self._apply_scene_background(parsed["scene"])
        self.dialog.show_ai_message(parsed["content"], self._current_scene)
        self._pending_options = (parsed["option1"], parsed["option2"])
        self._current_ai_response = response


    def _show_opening(self):
        """显示开场白"""
        if not self.backend:
            self.dialog.show_ai_message("……", self._current_scene)
            return
        opening = self.backend.get_opening_line()
        self.frontend_history.append({"role": "assistant", "content": opening})
        self._apply_ai_response(opening)


    def _on_advance(self):
        """处理点击推进"""
        # AI 显示界面点击推进，有选项则显示选项，否则切到输入
        opt1, opt2 = getattr(self, "_pending_options", ("", ""))
        if opt1 or opt2:
            self.dialog.show_options(opt1, opt2)
        else:
            self.dialog._switch_to_input()


    def _on_option_select(self, text: str):
        """处理选项选择"""
        self.dialog.input_edit.setPlainText(text)
        self._send_message()


    def _on_esc_return(self):
        """按 ESC 返回 AI 显示界面"""
        if self._current_ai_response:
            parsed = parse_yaml_response(self._current_ai_response)
            self.dialog.show_ai_message(parsed["content"], self._current_scene)


    def _handle_command(self, text: str):
        """处理斜杠指令"""
        # "/exit"退出并总结
        cmd = text.strip().lower()
        if cmd == "/exit":
            if self.ui_busy:
                return
            self.ui_busy = True
            self.dialog.show_summarizing(self._current_scene)
            self._run_worker(
                self.backend.trigger_exit_summary,
                lambda _: self._on_summary_done(),
                lambda err: self._on_ai_error(f"总结失败: {err}")
            )
        else:
            self.dialog.show_ai_message(f"未知指令：{text}", self._current_scene)


    def _on_summary_done(self):
        """总结完成回调"""
        self.ui_busy = False
        self.dialog.show_ai_message("记忆整理完成，再见～", self._current_scene)
        QTimer.singleShot(1500, QApplication.instance().quit)


    def _send_message(self):
        """发送用户消息"""
        text = self.dialog.get_input_text()
        if not text or self.ui_busy:
            return

        if text.startswith("/"):
            self.dialog.clear_input()
            self._handle_command(text)
            return

        self.frontend_history.append({"role": "user", "content": text})
        self.dialog.clear_input()
        self.ui_busy = True

        thinking_prefix = "思考中"
        if self.backend and getattr(self.backend, "cfg", None):
            model_name = str(getattr(self.backend.cfg, "model", "")).lower()
            # 大肥鱼彩蛋
            if "deepseek" in model_name and random.randint(1, 20) == 1:
                thinking_prefix = "🐳海底级思考中"
        self.dialog.show_thinking(self._current_scene, prefix=thinking_prefix)

        self._run_worker(
            self.backend.process_user_message,
            self._on_ai_response,
            self._on_ai_error,
            text,
            False,  # play_tts=False，TTS 由前端单独线程播放
        )


    def _on_ai_response(self, result):
        """处理 AI 回复"""
        response, should_exit = result
        self.frontend_history.append({"role": "assistant", "content": response})
        self._apply_ai_response(response)
        self.ui_busy = False
        self._start_tts(response)
        if should_exit:
            QTimer.singleShot(2000, QApplication.instance().quit)


    def _on_ai_error(self, err: str):
        """处理 AI 错误"""
        self.dialog.show_ai_message(err, self._current_scene)
        self.ui_busy = False


    def _start_tts(self, text: str):
        """启动 TTS 播放线程"""
        if not self.backend or not getattr(self.backend, "tts_success", False):
            return
        self._run_worker(
            self.backend.process_ai_response_tts,
            lambda _: None,
            lambda err: logger.error(f"TTS 播放失败: {err}"),
            text
        )


    def _toggle_context(self):
        """切换上下文面板"""
        if self.context_mask.isVisible():
            self.context_mask.hide()
        else:
            self.context_mask.update_history(self.frontend_history)
            self.context_mask.show()
            self.context_mask.raise_()


    def resizeEvent(self, event):
        """窗口大小变化"""
        # 保持 16:9，并及时更新布局
        size = event.size()
        w, h = size.width(), size.height()
        ratio = 16 / 9
        if abs(w / h - ratio) > 0.01:
            if w / h > ratio:
                self.resize(int(h * ratio), h)
            else:
                self.resize(w, int(w / ratio))
            return
        self._update_layout()
        super().resizeEvent(event)


    def _update_layout(self):
        """更新布局"""
        w, h = self.width(), self.height()

        # 背景(scene) + 立绘(Doll)
        self._scene_composite = self.scene_renderer.render(w, h)

        # 对话框：底部居中，宽 90%，高 32%
        mx = int(w * 0.05)
        mb = int(h * 0.03)
        dw = w - mx * 2
        dh = int(h * 0.32)
        self.dialog.setGeometry(mx, h - mb - dh, dw, dh)

        # 上下文遮罩：全屏
        self.context_mask.setGeometry(0, 0, w, h)

        # 及时重绘
        self.update()
        # 让对话框的模糊缓存失效并重绘
        self.dialog.update()


    def paintEvent(self, event):
        """主窗口绘制"""
        if not self._scene_composite.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(0, 0, self._scene_composite)
        super().paintEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_FAMILY, 14))

    # 先显示 UI 并进入思考阶段，后端在后台线程初始化
    window = VisualNovelFrontend(backend=None)
    window.show()

    init_thread = QThread()
    init_worker = Worker(BackendService)
    init_worker.moveToThread(init_thread)

    init_thread.started.connect(init_worker.run)
    init_worker.finished.connect(window.on_backend_ready)
    init_worker.failed.connect(window.on_backend_failed)
    init_worker.finished.connect(init_thread.quit)
    init_worker.failed.connect(init_thread.quit)
    init_thread.finished.connect(init_thread.deleteLater)

    # 保持引用，避免被 GC
    window._init_worker = init_worker
    window._init_thread = init_thread

    init_thread.start()

    sys.exit(app.exec())