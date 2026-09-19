# ATRI_Chat_Setting.py - ATRI_Chat设置工具
# 版本：v1.5.5
# 更新时间：2026.09.10


import sys
import os
import ATRI_Crypto
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QMessageBox, QLabel,
    QScrollArea, QComboBox, QHBoxLayout, QFrame, QInputDialog,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QPoint, QRectF
from PyQt6.QtGui import (
    QColor, QPixmap, QPainter, QPainterPath, QPen, QBrush,
)


#  日志系统
LOG_LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
# 全局日志等级，"ATRI_Chat_Setting.py"不读取配置文件"./Data/Data[1].bin"中的日志等级，而是代码硬编码等级
_log_threshold: int = LOG_LEVELS["DEBUG"]


def set_log_level(level: str) -> None:
    """设置全局日志等级，并过滤低等级日志"""
    global _log_threshold
    _log_threshold = LOG_LEVELS.get(level.upper(), LOG_LEVELS["INFO"])


def _log(level: str, msg) -> None:
    """底层日志输出，按等级过滤，多行拆分打印"""
    if LOG_LEVELS.get(level, 0) < _log_threshold:
        return
    for line in str(msg).split("\n"):
        print(f"[{level}] {line}")


def log_debug(msg): _log("DEBUG", msg)
def log_info(msg):  _log("INFO", msg)
def log_warn(msg):  _log("WARNING", msg)
def log_error(msg): _log("ERROR", msg)


#  路径常量
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "Data")
CONFIG_FILE   = os.path.join(DATA_DIR, "Data[1].bin")
BG_IMAGE_PATH = os.path.join(BASE_DIR, "Resources", "Subject", "Background[2].png")
BG_TARGET_HEIGHT = 777


#  样式常量(毛玻璃统一参数)
CARD_CORNER       = 20        # 板块圆角半径
BUTTON_CORNER     = 13        # 按钮圆角半径
BLUR_RADIUS       = 10        # 单次模糊半径
BLUR_TIMES        = 3         # 级联模糊次数
FONT_SIZE_PX      = 14        # 全局字号


#  默认配置
DEFAULT_CONFIG: dict = {
    "PROVIDER":                   "深度求索",
    "MODEL":                      "deepseek-v4-flash",
    "CHAT_API_KEY":               "",
    "CHAT_API_KEY2":              "",
    "TRANSLATION_ENGINE":         "火山引擎",
    "VOLC_ACCESS_KEY":            "",
    "VOLC_SECRET_KEY":            "",
    "MAX_HISTORY_MESSAGES":       20,
    "SHORT_TERM_MEMORY_MESSAGES": 10,
    "SUMMARY_HISTORY_LENGTH":     30,
    "MEMORY_DAYS":                3,
    "USE_TRANSLATION":            False,
    "USE_COT":                    False,
    "LOG_LEVEL":                  "INFO",
}


def default_config() -> dict:
    """返回默认配置的浅拷贝"""
    log_debug(f"生成默认配置：{list(DEFAULT_CONFIG.keys())}")
    return dict(DEFAULT_CONFIG)


#  配置元数据
CONFIG_DESCRIPTIONS: dict[str, str] = {
    "PROVIDER":                 "模型服务提供商，选择后会自动切换模型列表和 API 密钥",
    "MODEL":                    "模型名称，使用的语言模型",
    "CHAT_API_KEY":             "深度求索 API Key",
    "CHAT_API_KEY2":            "智谱 API Key",
    "TRANSLATION_ENGINE":       "翻译服务引擎，目前仅支持火山引擎",
    "VOLC_ACCESS_KEY":          "Access Key ID",
    "VOLC_SECRET_KEY":          "Secret Access Key",
    "MAX_HISTORY_MESSAGES":     "最大上下文条数，后端历史条数，填整数",
    "SHORT_TERM_MEMORY_MESSAGES": "加载短期记忆条数，启动时加载到后端历史的条数，填整数",
    "SUMMARY_HISTORY_LENGTH":   "最大对话总结条数，后端长历史条数，填整数",
    "MEMORY_DAYS":              "加载记忆天数，填整数",
    "USE_TRANSLATION":          "是否启用翻译功能",
    "USE_COT":                  "是否使用思维链",
    "LOG_LEVEL":                "日志输出等级",
}

PROVIDER_MODELS: dict[str, list[str]] = {
    "深度求索": ["deepseek-v4-flash", "deepseek-v4-pro"],
    "智谱":     ["GLM-4.7", "GLM-5.1", "GLM-5.2", "GLM-5.3"],
}
TRANSLATION_ENGINES = ["火山引擎"]

LOG_LEVEL_OPTIONS   = ["DEBUG", "INFO", "WARNING", "ERROR"]

_PROVIDER_KEY_VIS: dict[str, tuple[bool, bool]] = {
    "深度求索": (True,  False),
    "智谱":     (False, True),
}


#  模糊工具
def blur_pixmap(pixmap: QPixmap, radius: int) -> QPixmap:
    """对 QPixmap 做一次高斯模糊并返回同尺寸新图"""
    if pixmap is None or pixmap.isNull() or radius <= 0:
        return pixmap

    w, h = pixmap.width(), pixmap.height()
    margin = radius * 2 + 2
    scene = QGraphicsScene()
    scene.setSceneRect(-margin, -margin,
                       w + 2 * margin,
                       h + 2 * margin)
    item = QGraphicsPixmapItem(pixmap)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius)
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)

    result = QPixmap(w + 2 * margin, h + 2 * margin)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter)
    painter.end()
    return result.copy(margin, margin, w, h)


def cascade_blur(pixmap: QPixmap, radius: int, times: int) -> QPixmap:
    """级联模糊：连续多次执行小半径模糊，用于替代单次大半径模糊"""
    log_debug(f"开始级联模糊：radius={radius} times={times}")
    for _ in range(max(times, 0)):
        pixmap = blur_pixmap(pixmap, radius)
    log_debug("级联模糊结束")
    return pixmap


#  毛玻璃控件
class FrostedMixin:
    """毛玻璃绘制公共逻辑"""

    _corner: int = CARD_CORNER

    def _init_frosted(self, bg_provider) -> None:
        """绑定背景提供者并开启透明属性"""
        self._bg_provider = bg_provider
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        log_debug(f"Frosted 初始化：{type(self).__name__} corner={self._corner}")


    def _draw_frosted_bg(self, painter: QPainter) -> None:
        """从预模糊背景中裁剪当前区域并绘制(无任何着色)"""
        bg = self._bg_provider()
        if bg is None or bg.isNull():
            log_debug("毛玻璃背景为空，跳过绘制")
            return
        pos = self.mapTo(self.window(), QPoint(0, 0))
        region = bg.copy(pos.x(), pos.y(), self.width(), self.height())
        if region.isNull():
            log_debug(f"毛玻璃裁剪区域为空：pos=({pos.x()},{pos.y()}) "
                      f"size=({self.width()}x{self.height()})")
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._corner, self._corner)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, region)
        painter.setClipping(False)


    def _draw_border(self, painter: QPainter) -> None:
        """绘制白色描边"""
        pen = QPen(QColor(255, 255, 255), 1)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.drawRoundedRect(r, self._corner, self._corner)


    def _paint_frosted(self, painter: QPainter,
                       overlay: QColor | None = None) -> None:
        """毛玻璃背景、可选叠加层和边框"""
        self._draw_frosted_bg(painter)
        if overlay is not None:
            painter.fillRect(self.rect(), overlay)
            painter.setClipping(False)
        self._draw_border(painter)


class FrostedCard(QFrame, FrostedMixin):
    """毛玻璃板块"""
    # 板块样式：无色100%透明、圆角20、模糊半径10、级联模糊3次、1像素纯白色描边
    _corner = CARD_CORNER

    def __init__(self, bg_provider, parent=None):
        super().__init__(parent)
        self._init_frosted(bg_provider)
        self.setStyleSheet(
            "QFrame { background: transparent; border: none; }"
            "QLabel { background: transparent; }"
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_frosted(painter)
        painter.end()


class FrostedButton(QPushButton, FrostedMixin):
    """毛玻璃按钮"""
    # 按钮样式：无色100%透明、圆角13、模糊半径10、级联模糊3次、1像素纯白色描边
    _corner = BUTTON_CORNER

    def __init__(self, text: str, bg_provider, parent=None):
        super().__init__(text, parent)
        self._init_frosted(bg_provider)
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setMinimumWidth(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")


    def enterEvent(self, e):
        self._hovered = True
        self.update()


    def leaveEvent(self, e):
        self._hovered = False
        self.update()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        overlay = None
        if self.isDown():
            overlay = QColor(0, 0, 0, 45)
        elif self._hovered:
            overlay = QColor(255, 255, 255, 55)
        self._paint_frosted(painter, overlay)
        # 字体样式：黑色、字号14
        font = painter.font()
        font.setBold(True)
        font.setPointSize(FONT_SIZE_PX)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


def get_global_stylesheet(font_family: str) -> str:
    """生成全局样式表"""
    return f"""
QWidget {{
    font-family: '{font_family}';
    font-size: {FONT_SIZE_PX}px;
    color: #000000;
}}
QLabel {{ color: #000000; }}
QToolTip {{
    background-color: rgba(255,255,255,245);
    color: #000000;
    border: 1px solid #DCDFE6;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 13px;
}}
QLineEdit {{
    border: 1px solid rgba(255,255,255,0.9);
    padding: 6px 8px;
    background-color: rgba(255,255,255,0.72);
    border-radius: 6px;
    color: #000000;
    font-size: {FONT_SIZE_PX}px;
    selection-background-color: #409EFF;
}}
QLineEdit:focus {{
    border: 1px solid #409EFF;
    background-color: rgba(255,255,255,0.9);
}}
QComboBox {{
    border: 1px solid rgba(255,255,255,0.9);
    padding: 6px 8px;
    background-color: rgba(255,255,255,0.72);
    border-radius: 6px;
    color: #000000;
    font-size: {FONT_SIZE_PX}px;
}}
QComboBox:focus {{
    border: 1px solid #409EFF;
    background-color: rgba(255,255,255,0.9);
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #000000;
    margin-right: 5px;
}}
QComboBox QAbstractItemView {{
    border: 1px solid #E4E7ED;
    background-color: rgba(255,255,255,0.95);
    selection-background-color: #F5F7FA;
    selection-color: #000000;
    outline: none;
}}
QCheckBox {{ spacing: 8px; color: #000000; font-size: {FONT_SIZE_PX}px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid rgba(255,255,255,0.95);
    border-radius: 3px;
    background-color: rgba(255,255,255,0.8);
}}
QCheckBox::indicator:hover {{ border-color: #409EFF; }}
QCheckBox::indicator:checked {{
    background-color: #409EFF;
    border-color: #409EFF;
}}
QScrollBar:vertical {{
    border: none; background: transparent;
    width: 8px; margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: rgba(0,0,0,0.35);
    min-height: 20px; border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(0,0,0,0.55); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""


def get_platform_font() -> str:
    """获取平台默认字体族名"""
    p = sys.platform
    if p.startswith("win"):
        return "Microsoft YaHei"
    elif p.startswith("linux"):
        return "Inter"
    return "Noto Sans"


#  主窗口
class ConfigWindow(QMainWindow):
    """ATRI Chat 配置主窗口"""

    def __init__(self):
        super().__init__()
        log_debug("ConfigWindow 初始化开始")
        self.setWindowTitle("ATRI_Chat_Setting")
        self.config_data: dict = {}
        self.widgets: dict = {}
        self.bg_pixmap: QPixmap | None = None
        self.bottom_bg: QPixmap | None = None
        self.blurred_bg: QPixmap | None = None
        self.frosted_widgets: list = []
        self._super_password: str | None = None
        self._machine_key_valid: bool = False

        self._connect_crypto_signals()
        self.init_ui()
        self._load_background()
        self._build_bottom_background()
        self._lock_window_size()
        self.load_config()
        log_debug("ConfigWindow 初始化结束")


    # 加解密信号
    def _connect_crypto_signals(self):
        """连接 ATRI_Crypto 抛出的各加密异常信号"""
        log_debug("连接 ATRI_Crypto 信号")
        sig = ATRI_Crypto.crypto_signals
        sig.sig_no_super_password.connect(self._on_no_super_password)
        sig.sig_machine_decrypt_failed.connect(self._on_machine_decrypt_failed)
        sig.sig_super_fail_limit.connect(self._on_super_fail_limit)


    def _on_no_super_password(self):
        """未设置超级密码时的回调"""
        log_warn("检测到超级密码未设置")
        self._prompt_bind_super_password()


    def _on_machine_decrypt_failed(self):
        """机器码解密失败时的回调"""
        log_warn("机器码解密失败，尝试超级密码恢复")
        self._prompt_super_password_recovery()


    def _on_super_fail_limit(self):
        """超级密码连续失败触发的锁定回调"""
        log_error("超级密码连续失败 3 次，配置文件已删除")
        QMessageBox.critical(
            self, "安全锁定",
            "超级密码连续输入错误 3 次，配置文件已被删除\n请重新配置",
        )


    # 超级密码交互
    def _prompt_bind_super_password(self):
        """首次使用时引导用户设置超级密码，含二次确认"""
        while True:
            pwd, ok = QInputDialog.getText(
                self, "设置超级密码",
                "首次使用，请设置超级密码用于数据恢复：\n"
                "（超级密码用于在机器码变更时恢复配置，请牢记）",
                QLineEdit.EchoMode.Password,
            )
            if not ok:
                log_warn("用户取消了超级密码设置")
                return
            if len(pwd) < 6:
                log_debug(f"超级密码长度不足：len={len(pwd)}")
                QMessageBox.warning(self, "提示", "超级密码长度不能少于 6 位")
                continue
            pwd2, ok2 = QInputDialog.getText(
                self, "确认超级密码",
                "请再次输入超级密码以确认：",
                QLineEdit.EchoMode.Password,
            )
            if not ok2:
                log_debug("用户在确认步骤取消")
                continue
            if pwd != pwd2:
                log_debug("两次输入的超级密码不一致")
                QMessageBox.warning(self, "提示", "两次输入的超级密码不一致，请重试")
                continue
            self._super_password = pwd
            log_info("超级密码绑定成功")
            return


    def _prompt_super_password_recovery(self):
        """机器码失效时，引导用户用超级密码恢复配置"""
        reply = QMessageBox.question(
            self, "机器码验证失败",
            "当前机器码与配置文件不匹配\n\n"
            "是否使用超级密码解密并重新绑定当前机器码",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.No:
            log_warn("用户选择不使用超级密码恢复")
            return
        pwd, ok = QInputDialog.getText(
            self, "超级密码验证",
            "请输入超级密码以解密配置：",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not pwd:
            log_warn("用户取消了超级密码输入")
            return
        try:
            config = ATRI_Crypto.decrypt_with_super_password(CONFIG_FILE, pwd)
            self.config_data = config
            self._super_password = pwd
            ATRI_Crypto.rebind_machine_key(CONFIG_FILE, config, super_password=pwd)
            log_info("超级密码验证成功，已重新绑定当前机器码")
            QMessageBox.information(self, "恢复成功",
                                    "配置已通过超级密码恢复并重新绑定当前机器")
        except RuntimeError as e:
            log_error(f"超级密码验证失败: {e}")
            QMessageBox.warning(self, "验证失败", str(e))
        except FileNotFoundError:
            log_error("配置文件不存在")


    # 背景
    def _load_background(self):
        """加载背景图片并按目标高度等比缩放"""
        log_debug(f"尝试加载背景图：{BG_IMAGE_PATH}")
        if not os.path.exists(BG_IMAGE_PATH):
            log_warn(f"背景图片不存在：{BG_IMAGE_PATH}")
            return
        pixmap = QPixmap(BG_IMAGE_PATH)
        if pixmap.isNull():
            log_warn("背景图片加载失败，图片文件可能损坏")
            return
        ratio = BG_TARGET_HEIGHT / pixmap.height()
        target_w = int(pixmap.width() * ratio)
        self.bg_pixmap = pixmap.scaled(
            target_w, BG_TARGET_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        log_info(f"背景图加载成功：原 {pixmap.width()}x{pixmap.height()} "
                 f"-> {self.bg_pixmap.width()}x{self.bg_pixmap.height()}")


    def _build_bottom_background(self):
        """构建底部背景与毛玻璃层"""
        if self.bg_pixmap is None or self.bg_pixmap.isNull():
            log_debug("背景图为空，跳过底部背景构建")
            self.bottom_bg = None
            self.blurred_bg = None
            return
        self.bottom_bg = self.bg_pixmap
        log_debug(f"生成预模糊层：radius={BLUR_RADIUS} times={BLUR_TIMES}")
        self.blurred_bg = cascade_blur(self.bg_pixmap, BLUR_RADIUS, BLUR_TIMES)
        log_info("底部背景 & 预模糊背景已生成")


    def _lock_window_size(self):
        """按背景图尺寸锁死窗口大小"""
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            self.setFixedSize(self.bg_pixmap.size())
            log_info(f"窗口已锁死，尺寸：{self.width()}x{self.height()}")
        else:
            log_debug("无背景图，跳过窗口尺寸锁定")


    def paintEvent(self, event):
        """窗口底图绘制"""
        # 优先底部原图，否则纯色兜底
        painter = QPainter(self)
        if self.bottom_bg and not self.bottom_bg.isNull():
            painter.drawPixmap(0, 0, self.bottom_bg)
        elif self.bg_pixmap and not self.bg_pixmap.isNull():
            painter.drawPixmap(0, 0, self.bg_pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#F5F7FA"))
        painter.end()
        super().paintEvent(event)


    def _refresh_frosted_widgets(self):
        """滚动时重绘所有毛玻璃控件，使其裁剪区域跟随"""
        for w in self.frosted_widgets:
            w.update()


    # UI 构建
    def init_ui(self):
        """构建主界面"""
        log_debug("开始构建 UI")
        main_layout = self._setup_main_container()
        self._build_header(main_layout)
        container_layout = self._build_scroll_area(main_layout)
        self._build_llm_card(container_layout)
        self._build_trans_card(container_layout)
        self._build_main_card(container_layout)
        self._build_hint(container_layout)
        self._build_bottom_buttons(container_layout)
        container_layout.addStretch()
        log_debug("UI 构建完成")


    def _setup_main_container(self) -> QVBoxLayout:
        """初始化中央部件与主布局"""
        central = QWidget()
        self.setCentralWidget(central)
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(14)
        log_debug("主容器初始化完成")
        return layout


    def _form_label(self, text: str, tooltip: str = "") -> QLabel:
        """表单标签"""
        # 加粗黑字 + 悬停说明(缺省从描述表按 key 取)
        lbl = QLabel(text)
        lbl.setToolTip(tooltip or CONFIG_DESCRIPTIONS.get(text, ""))
        lbl.setStyleSheet(
            "color:#000; font-weight:bold; background:transparent;"
            f"font-size:{FONT_SIZE_PX}px;"
        )
        return lbl


    def _build_header(self, parent_layout: QVBoxLayout):
        """顶部标题毛玻璃板块"""
        log_debug("构建顶部标题板块")
        card = FrostedCard(lambda: self.blurred_bg)
        card.setFixedHeight(66)
        self.frosted_widgets.append(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(0)
        title = QLabel("ATRI Chat设置")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:#000; background:transparent; border:none;"
            "font-weight:bold; font-size:20px;"
        )
        lay.addWidget(title)
        parent_layout.addWidget(card)


    def _build_scroll_area(self, parent_layout: QVBoxLayout) -> QVBoxLayout:
        """创建滚动区域，返回内部容器布局"""
        log_debug("构建滚动区")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("background-color:transparent; border:none;")
        scroll.viewport().setStyleSheet("background-color:transparent;")
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        scroll.verticalScrollBar().valueChanged.connect(self._refresh_frosted_widgets)
        parent_layout.addWidget(scroll)

        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(16)
        c_layout.setContentsMargins(6, 6, 6, 6)
        scroll.setWidget(container)
        return c_layout


    def _make_card(self, title_text: str):
        """创建带标题的毛玻璃卡片，返回 (card, card_layout)"""
        log_debug(f"创建毛玻璃卡片：{title_text}")
        card = FrostedCard(lambda: self.blurred_bg)
        self.frosted_widgets.append(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 12, 18, 14)
        lay.setSpacing(8)
        lbl = QLabel(title_text)
        lbl.setStyleSheet(
            "font-size:15px; font-weight:bold; color:#000;"
            "background:transparent; border:none;"
            "border-bottom:1px solid rgba(255,255,255,0.7);"
            "padding-bottom:6px;"
        )
        lay.addWidget(lbl)
        return card, lay


    def _make_form_card(self, title: str):
        """创建带 QFormLayout 的毛玻璃卡片，返回 (card, form_layout)"""
        card, card_lay = self._make_card(title)
        fl = QFormLayout()
        fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fl.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        fl.setSpacing(12)
        fl.setContentsMargins(0, 8, 0, 0)
        card_lay.addLayout(fl)
        return card, fl


    def _build_llm_card(self, parent_layout: QVBoxLayout):
        """语言模型配置卡片"""
        log_debug("构建语言模型配置卡片")
        card, fl = self._make_form_card("语言模型配置")

        self.combo_provider = QComboBox()
        self.combo_provider.addItems(list(PROVIDER_MODELS.keys()))
        self.combo_provider.setToolTip(CONFIG_DESCRIPTIONS["PROVIDER"])
        self.combo_provider.currentIndexChanged.connect(self.on_provider_changed)
        fl.addRow(QLabel("模型提供商"), self.combo_provider)

        self.combo_model = QComboBox()
        self.combo_model.setToolTip(CONFIG_DESCRIPTIONS["MODEL"])
        fl.addRow(QLabel("模型名称"), self.combo_model)

        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.setPlaceholderText("请输入密钥")
        self.label_api_key = QLabel("DeepSeek Key")
        self.label_api_key.setToolTip(CONFIG_DESCRIPTIONS["CHAT_API_KEY"])
        fl.addRow(self.label_api_key, self.input_api_key)

        self.input_api_key2 = QLineEdit()
        self.input_api_key2.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key2.setPlaceholderText("请输入密钥")
        self.label_api_key2 = QLabel("Z.AI Key")
        self.label_api_key2.setToolTip(CONFIG_DESCRIPTIONS["CHAT_API_KEY2"])
        fl.addRow(self.label_api_key2, self.input_api_key2)

        parent_layout.addWidget(card)


    def _build_trans_card(self, parent_layout: QVBoxLayout):
        """翻译服务配置卡片"""
        log_debug("构建翻译服务配置卡片")
        card, fl = self._make_form_card("翻译服务配置")

        self.combo_trans_engine = QComboBox()
        self.combo_trans_engine.addItems(TRANSLATION_ENGINES)
        self.combo_trans_engine.setToolTip(CONFIG_DESCRIPTIONS["TRANSLATION_ENGINE"])
        fl.addRow(QLabel("翻译引擎"), self.combo_trans_engine)

        self.input_volc_ak = QLineEdit()
        self.input_volc_ak.setPlaceholderText("请输入火山引擎 Access Key ID")
        self.input_volc_ak.setToolTip(CONFIG_DESCRIPTIONS["VOLC_ACCESS_KEY"])
        fl.addRow(QLabel("Access Key ID"), self.input_volc_ak)

        self.input_volc_sk = QLineEdit()
        self.input_volc_sk.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_volc_sk.setPlaceholderText("请输入火山引擎 Secret Access Key")
        self.input_volc_sk.setToolTip(CONFIG_DESCRIPTIONS["VOLC_SECRET_KEY"])
        fl.addRow(QLabel("Secret Key"), self.input_volc_sk)

        parent_layout.addWidget(card)


    def _build_main_card(self, parent_layout: QVBoxLayout):
        """主服务配置卡片"""
        log_debug("构建主服务配置卡片")
        card, fl = self._make_form_card("主服务配置")

        int_keys  = [
            "MAX_HISTORY_MESSAGES", "SHORT_TERM_MEMORY_MESSAGES",
            "SUMMARY_HISTORY_LENGTH", "MEMORY_DAYS",
        ]
        bool_keys = ["USE_TRANSLATION", "USE_COT"]

        for key in int_keys + bool_keys:
            desc = CONFIG_DESCRIPTIONS.get(key, "")
            lbl = self._form_label(key, desc)
            if key in bool_keys:
                w = QCheckBox()
                w.setToolTip(desc + " (勾选为 True)")
                w.setStyleSheet("background:transparent; color:#000;")
            else:
                w = QLineEdit()
                w.setToolTip(desc)
                w.setPlaceholderText(desc)
            self.widgets[key] = w
            fl.addRow(lbl, w)

        lbl_log = self._form_label("LOG_LEVEL", CONFIG_DESCRIPTIONS["LOG_LEVEL"])
        self.combo_log_level = QComboBox()
        self.combo_log_level.addItems(LOG_LEVEL_OPTIONS)
        self.combo_log_level.setToolTip(CONFIG_DESCRIPTIONS["LOG_LEVEL"])
        fl.addRow(lbl_log, self.combo_log_level)

        parent_layout.addWidget(card)


    def _build_hint(self, parent_layout: QVBoxLayout):
        """底部提示文字"""
        hint = QLabel("将鼠标悬停在参数名称上可查看详细说明")
        hint.setStyleSheet("color:#000; font-size:12px; background:transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        parent_layout.addWidget(hint)

    def _build_bottom_buttons(self, parent_layout: QVBoxLayout):
        """底部按钮区"""
        log_debug("构建底部按钮区")
        bw = QWidget()
        bw.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        bl = QHBoxLayout(bw)
        bl.setSpacing(14); bl.setContentsMargins(0, 4, 0, 4)

        save_btn = FrostedButton("保存配置", lambda: self.blurred_bg)
        save_btn.clicked.connect(self.save_config)
        self.frosted_widgets.append(save_btn)

        close_btn = FrostedButton("退出", lambda: self.blurred_bg)
        close_btn.clicked.connect(self.close)
        self.frosted_widgets.append(close_btn)

        bl.addWidget(save_btn)
        bl.addWidget(close_btn)
        parent_layout.addWidget(bw)


    # Provider 切换
    def on_provider_changed(self, index: int):
        """切换提供商时刷新模型列表与可见的 Key 输入框"""
        provider = self.combo_provider.currentText()
        log_debug(f"Provider 切换：index={index} provider={provider}")
        self.combo_model.clear()
        self.combo_model.addItems(PROVIDER_MODELS.get(provider, []))
        for visible, label, edit in zip(
            _PROVIDER_KEY_VIS.get(provider, (False, False)),
            (self.label_api_key, self.label_api_key2),
            (self.input_api_key, self.input_api_key2),
        ):
            label.setVisible(visible)
            edit.setVisible(visible)


    # 配置加载
    @staticmethod
    def _select_combo(combo: QComboBox, text: str, fallback: int = 0) -> None:
        """按文本选择 QComboBox 项，未找到时回退到 fallback 索引"""
        idx = combo.findText(text)
        combo.setCurrentIndex(idx if idx >= 0 else fallback)


    def load_config(self):
        """加载配置文件并按状态分派到机器码、超级密码解密路径"""
        log_info("正在加载配置文件……")
        defaults = default_config()
        status = ATRI_Crypto.check_super_password(CONFIG_FILE)
        log_debug(f"配置状态：{status}")

        if not status["file_exists"]:
            log_warn("配置文件不存在，将使用默认配置")
            self.config_data = defaults
            self._super_password = None
        elif not status["has_super"]:
            log_debug("配置文件未绑定超级密码，触发绑定信号")
            ATRI_Crypto.crypto_signals.sig_no_super_password.emit()
            self._try_machine_decrypt(defaults)
        elif status["can_machine_decrypt"]:
            log_debug("机器码可用，尝试机器码解密")
            self._try_machine_decrypt(defaults)
        else:
            log_debug("机器码不可用，触发恢复信号")
            ATRI_Crypto.crypto_signals.sig_machine_decrypt_failed.emit()
            if not self.config_data:  # 恢复流程可能已填充
                self.config_data = defaults

        self._apply_config_to_ui()


    def _try_machine_decrypt(self, defaults: dict):
        """尝试用机器码解密，成功则标记 _machine_key_valid"""
        try:
            loaded = ATRI_Crypto.load_and_decrypt(CONFIG_FILE)
            self.config_data = {**defaults, **loaded}
            self._machine_key_valid = True  # 标记机器码可用
            log_info(f"配置文件解密并加载成功：{len(loaded)} 个键")
        except Exception as e:
            log_error(f"配置文件解密失败：{e}")
            self.config_data = defaults


    def _apply_config_to_ui(self):
        """将 self.config_data 中的值回填到 UI 控件"""
        log_debug("开始将配置回填到 UI")
        d = self.config_data

        # Provider / Model
        self._select_combo(self.combo_provider, d.get("PROVIDER", "深度求索"))
        self.on_provider_changed(self.combo_provider.currentIndex())
        self._select_combo(self.combo_model, d.get("MODEL", ""))

        # Keys
        self.input_api_key.setText(d.get("CHAT_API_KEY", ""))
        self.input_api_key2.setText(d.get("CHAT_API_KEY2", ""))
        self.input_volc_ak.setText(d.get("VOLC_ACCESS_KEY", ""))
        self.input_volc_sk.setText(d.get("VOLC_SECRET_KEY", ""))

        # Translation engine
        self._select_combo(self.combo_trans_engine, d.get("TRANSLATION_ENGINE", "火山引擎"))

        # 通用控件
        for key, widget in self.widgets.items():
            val = d.get(key)
            if val is None:
                continue
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            else:
                widget.setText(str(val))

        # 日志等级
        lv = d.get("LOG_LEVEL", "INFO")
        self._select_combo(self.combo_log_level, lv)
        set_log_level(lv)
        log_debug(f"配置回填完成，日志等级：{lv}")


    # 配置保存
    def save_config(self):
        """从 UI 收集数据 -> 校验 -> 加密保存到 CONFIG_FILE"""
        log_info("正在保存配置文件……")
        new_data: dict = {
            "PROVIDER":           self.combo_provider.currentText(),
            "MODEL":              self.combo_model.currentText(),
            "CHAT_API_KEY":       self.input_api_key.text().strip(),
            "CHAT_API_KEY2":      self.input_api_key2.text().strip(),
            "TRANSLATION_ENGINE": self.combo_trans_engine.currentText(),
            "VOLC_ACCESS_KEY":    self.input_volc_ak.text().strip(),
            "VOLC_SECRET_KEY":    self.input_volc_sk.text().strip(),
            "LOG_LEVEL":          self.combo_log_level.currentText(),
        }
        for key, widget in self.widgets.items():
            if isinstance(widget, QCheckBox):
                new_data[key] = widget.isChecked()
            else:
                text = widget.text().strip()
                try:
                    new_data[key] = int(text)
                except ValueError:
                    log_error(f"参数 {key} 需要是整数，当前值为：{text}")
                    QMessageBox.warning(
                        self, "格式错误",
                        f"参数 {key} 需要是整数，当前值为：{text}",
                    )
                    return

        self.config_data.pop("GALGAME", None)
        self.config_data.update(new_data)
        log_debug(f"待保存键数量：{len(new_data)}")

        # 仅在超级密码未设置，且机器码不可用时才提示
        if self._super_password is None and not self._machine_key_valid:
            log_debug("尚未绑定超级密码，触发绑定流程")
            self._prompt_bind_super_password()

        try:
            log_info("正在序列化并加密配置……")
            ATRI_Crypto.encrypt_and_save(
                self.config_data, CONFIG_FILE,
                super_password=self._super_password,
            )
            set_log_level(new_data.get("LOG_LEVEL", "INFO"))
            log_info("配置已加密保存")
            QMessageBox.information(self, "成功", "配置已加密保存")
        except RuntimeError as e:
            log_error(f"无法获取机器指纹：{e}")
            QMessageBox.critical(self, "保存失败", f"无法获取机器指纹：{e}")
        except Exception as e:
            log_error(f"无法写入或加密文件：{e}")
            QMessageBox.critical(self, "保存失败", f"无法写入或加密文件：{e}")


#  入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(get_global_stylesheet(get_platform_font()))
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec())
