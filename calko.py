"""
Calko 2.3 — Capa de calco flotante always-on-top
Modo claro/oscuro · Toolbar en dos filas · Sesiones .calko
Windows / Mac / Linux
"""

import sys, os, json, ctypes, math, base64
from pathlib import Path

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSlider, QSpinBox,
    QFileDialog, QMessageBox, QMenu, QLabel, QPushButton,
    QComboBox, QSizePolicy, QSystemTrayIcon, QHBoxLayout,
    QVBoxLayout, QFrame,
)
from PyQt6.QtCore  import Qt, QTimer, QSize, QRectF, pyqtSignal, QRect, QEvent, QPoint
from PyQt6.QtGui   import (
    QPixmap, QPainter, QPen, QColor, QKeySequence,
    QShortcut, QAction, QCursor, QImageReader, QIcon,
)

try:
    import qtawesome as qta
    _QTA = True
except ImportError:
    _QTA = False

try:
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtCore import QByteArray
    _SVG = True
except ImportError:
    _SVG = False


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME    = "Calko"
APP_VERSION = "2.3"
CONFIG_DIR  = Path.home() / ".calko"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSION_EXT = ".calko"
CONFIG_DIR.mkdir(exist_ok=True)

DEFAULT_CFG = {
    "opacity": 0.5, "last_image": None, "recent_images": [],
    "window_x": 120, "window_y": 80, "window_w": 680, "window_h": 560,
    "flip_h": False, "flip_v": False, "rotation": 0, "tint": "none",
    "theme": "dark",
}

TINTS = {
    "none":  None,
    "warm":  QColor(255, 190,  80, 45),
    "cold":  QColor( 80, 150, 255, 45),
    "green": QColor( 80, 210, 120, 45),
    "red":   QColor(255,  70,  70, 45),
}

FORMATS = (
    "Imágenes (*.png *.jpg *.jpeg *.gif *.webp "
    "*.bmp *.tiff *.tif *.svg *.eps *.ico)"
)
SESSION_FILTER = f"Sesión Calko (*{SESSION_EXT})"

ASPECT_RATIOS = {
    "Libre": None,
    "1:1":   (1,  1),
    "16:9":  (16, 9),
    "9:16":  (9,  16),
    "4:3":   (4,  3),
    "3:2":   (3,  2),
    "2:3":   (2,  3),
}

MIN_OP, MAX_OP = 0.10, 0.80
MAX_RECENT = 8


# ═══════════════════════════════════════════════════════════════════════════════
#  TEMAS
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "dark": {
        "B0": "#080c12", "B1": "#0b1018", "B2": "#0e1520",
        "B3": "#152030", "B4": "#1c2d42", "B5": "#233850",
        "BA": "#3a8fd4", "BB": "#5aaee8",
        "BT": "#c8ddf0", "BM": "#6a8aaa", "BD": "#182030",
        "C_BORDER_E": (70,  155, 255, 200),
        "C_BORDER_L": (255, 145,  35, 160),
        "C_DOT_E":    (60,  200, 100),
        "C_DOT_L":    (255, 125,  25),
        "logo": "logo-calko.png",
    },
    "light": {
        "B0": "#dde8f5", "B1": "#e8f0f8", "B2": "#f0f5fc",
        "B3": "#dce8f5", "B4": "#c8daea", "B5": "#aec8e0",
        "BA": "#1a6aaa", "BB": "#2a80c8",
        "BT": "#0a1828", "BM": "#3a5878", "BD": "#b8cce0",
        "C_BORDER_E": (26,  106, 170, 220),
        "C_BORDER_L": (200, 100,  20, 180),
        "C_DOT_E":    (30,  150,  60),
        "C_DOT_L":    (200,  90,  10),
        "logo": "logo-calko.png",
    },
}

T: dict = THEMES["dark"]


def apply_theme(name: str):
    global T
    T = THEMES.get(name, THEMES["dark"])


def ico(name: str, color: str = None) -> QIcon:
    c = color or T["BT"]
    if _QTA:
        return qta.icon(name, color=c, options=[{"scale_factor": 0.85}])
    return QIcon()


def make_icon(theme: str = "dark") -> QIcon:
    logo_name = THEMES[theme].get("logo", "logo-calko.png")
    path = Path(__file__).parent / logo_name
    
    if path.exists():
        return QIcon(str(path))
        
    px = QPixmap(48, 48)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QColor(14, 21, 32) if theme == "dark" else QColor(220, 235, 250)
    p.setBrush(bg)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 44, 44)
    p.setPen(QPen(QColor(125, 212, 255), 5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRect(8, 8, 32, 32), 45 * 16, 270 * 16)
    p.end()
    return QIcon(px)


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG / SESIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def load_cfg():
    try:
        with open(CONFIG_FILE) as f:
            d = json.load(f)
        c = DEFAULT_CFG.copy(); c.update(d)
        return c
    except Exception:
        return DEFAULT_CFG.copy()

def save_cfg(c):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(c, f, indent=2)
    except Exception:
        pass

def add_recent(c, path):
    r = c.get("recent_images", [])
    if path in r: r.remove(path)
    r.insert(0, path)
    c["recent_images"] = r[:MAX_RECENT]

def session_to_dict(win) -> dict:
    g = win.geometry(); cv = win._cv
    return {
        "version": APP_VERSION, "image_path": win._path,
        "opacity": win._op, "zoom": cv._zoom,
        "offset_x": cv._cx, "offset_y": cv._cy,
        "flip_h": win._fh, "flip_v": win._fv,
        "rotation": int(win._rot), "tint": win._tint,
        "window_x": g.x(), "window_y": g.y(),
        "window_w": g.width(), "window_h": g.height(),
    }

def session_from_dict(win, d: dict):
    if d.get("image_path") and Path(d["image_path"]).exists():
        win.load_path(d["image_path"])
    win._set_op(d.get("opacity", 0.5))
    win._fh = d.get("flip_h", False)
    win._fv = d.get("flip_v", False)
    win._rot = float(d.get("rotation", 0))
    win._set_tint(d.get("tint", "none"))
    win._cv._zoom = d.get("zoom", 1.0)
    win._cv._cx   = d.get("offset_x", win._cv.width()  / 2)
    win._cv._cy   = d.get("offset_y", win._cv.height() / 2)
    win._cv.set_flip(win._fh, win._fv)
    win._cv.set_angle(win._rot)
    win._cv.update()
    win._tb.set_rotation(int(win._rot))
    win.setGeometry(
        d.get("window_x", win.x()), d.get("window_y", win.y()),
        d.get("window_w", win.width()), d.get("window_h", win.height()),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  ESTILOS
# ═══════════════════════════════════════════════════════════════════════════════

def _svg_arrow(color, up=True):
    pts = "3,10 8,4 13,10" if up else "3,6 8,12 13,6"
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16'><polygon points='{pts}' fill='{color}'/></svg>"
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"

def _styles():
    arr_up = _svg_arrow(T['BT'], True)
    arr_dn = _svg_arrow(T['BT'], False)
    
    return {
        "btn": (
            f"QPushButton {{ background:{T['B3']}; color:{T['BT']}; border:1px solid {T['BD']}; "
            f"border-radius:4px; padding:2px 8px; font-size:12px; min-height:24px; }}"
            f"QPushButton:hover {{ background:{T['B4']}; border-color:{T['BA']}; }}"
            f"QPushButton:pressed {{ background:{T['B5']}; }}"
        ),
        "spin": (
            f"QSpinBox {{ background:{T['B3']}; color:{T['BT']}; border:1px solid {T['BD']}; "
            f"border-radius:4px; padding:1px 4px; font-size:12px; min-height:24px; min-width:62px; }}"
            f"QSpinBox::up-button, QSpinBox::down-button {{ background:{T['B4']}; border:none; width:16px; }}"
            f"QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background:{T['BA']}; }}"
            f"QSpinBox::up-arrow {{ image: url(\"{arr_up}\"); }}"
            f"QSpinBox::down-arrow {{ image: url(\"{arr_dn}\"); }}"
        ),
        "slider": (
            f"QSlider::groove:horizontal {{ height:4px; background:{T['B4']}; border-radius:2px; }}"
            f"QSlider::handle:horizontal {{ width:14px; height:14px; margin:-5px 0; background:{T['BB']}; border-radius:7px; }}"
            f"QSlider::sub-page:horizontal {{ background:{T['BA']}; border-radius:2px; }}"
        ),
        "combo": (
            f"QComboBox {{ background:{T['B3']}; color:{T['BT']}; border:1px solid {T['BD']}; "
            f"border-radius:4px; padding:2px 6px; font-size:11px; min-height:24px; }}"
            f"QComboBox::drop-down {{ border:none; width:18px; }}"
            f"QComboBox QAbstractItemView {{ background:{T['B1']}; color:{T['BT']}; border:1px solid {T['BD']}; "
            f"selection-background-color:{T['B5']}; }}"
        ),
        "menu": (
            f"QMenuBar {{ background:transparent; color:{T['BM']}; font-size:12px; "
            f"padding:1px 4px; border-bottom:1px solid {T['BD']}; }}"
            f"QMenuBar::item {{ padding:3px 8px; border-radius:3px; }}"
            f"QMenuBar::item:selected {{ background:{T['B4']}; }}"
            f"QMenu {{ background:{T['B1']}; color:{T['BT']}; border:1px solid {T['BD']}; border-radius:6px; padding:4px; }}"
            f"QMenu::item {{ padding:6px 22px; border-radius:4px; }}"
            f"QMenu::item:selected {{ background:{T['B5']}; }}"
            f"QMenu::separator {{ height:1px; background:{T['BD']}; margin:3px 8px; }}"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  CANVAS
# ═══════════════════════════════════════════════════════════════════════════════

class Canvas(QWidget):
    sig_zoom = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._px = None; self._zoom = 1.0; self._angle = 0.0
        self._flip_h = False; self._flip_v = False
        self._opacity = 0.5; self._tint = None; self._mode = "edit"
        self._cx = 300.0; self._cy = 270.0
        self._pan = False; self._pan_gx = 0.0; self._pan_gy = 0.0
        self._pan_cx0 = 0.0; self._pan_cy0 = 0.0

    def set_mode(self, m):    self._mode = m;    self.update()
    def set_opacity(self, v): self._opacity = v; self.update()
    def set_tint(self, c):    self._tint = c;    self.update()
    def set_angle(self, a):   self._angle = a;   self.update()
    def set_flip(self, h, v): self._flip_h = h;  self._flip_v = v; self.update()

    def load(self, px):
        self._px = px; self._zoom = 1.0; self._angle = 0.0
        w, h = self.width(), self.height()
        self._cx = w / 2 if w > 0 else 300
        self._cy = h / 2 if h > 0 else 270
        self.update(); self.sig_zoom.emit(1.0)

    def fit(self):
        if not self._px: return
        rad = math.radians(self._angle)
        ca, sa = abs(math.cos(rad)), abs(math.sin(rad))
        pw, ph = self._px.width(), self._px.height()
        ew = pw * ca + ph * sa; eh = pw * sa + ph * ca
        if ew > 0 and eh > 0:
            self._zoom = min(self.width() / ew, self.height() / eh) * 0.95
        self._cx = self.width() / 2; self._cy = self.height() / 2
        self.update(); self.sig_zoom.emit(self._zoom)

    def reset(self):
        self._zoom = 1.0
        self._cx = self.width() / 2; self._cy = self.height() / 2
        self.update(); self.sig_zoom.emit(1.0)

    def shift_cy(self, amount: float):
        self._cy += amount

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(0, 0, w, h, Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self._mode == "edit":
            pen = QPen(QColor(*T["C_BORDER_E"])); pen.setWidth(2)
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(1, 1, w - 2, h - 2, 5, 5)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(*T["C_DOT_E"]))
            p.drawEllipse(w - 14, 6, 8, 8)
        else:
            pen = QPen(QColor(*T["C_BORDER_L"])); pen.setWidth(1)
            pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(1, 1, w - 2, h - 2)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(*T["C_DOT_L"]))
            p.drawEllipse(w - 14, 6, 8, 8)

        if self._px and not self._px.isNull():
            pw, ph = self._px.width(), self._px.height()
            p.save()
            p.translate(self._cx, self._cy)
            if self._angle: p.rotate(self._angle)
            sx = -self._zoom if self._flip_h else self._zoom
            sy = -self._zoom if self._flip_v else self._zoom
            p.scale(sx, sy)
            p.setOpacity(self._opacity)
            dst = QRectF(-pw / 2, -ph / 2, float(pw), float(ph))
            p.drawPixmap(dst, self._px, QRectF(self._px.rect()))
            if self._tint:
                p.setOpacity(1.0); p.fillRect(dst, self._tint)
            p.restore()
        else:
            p.setOpacity(0.12); p.fillRect(0, 0, w, h, QColor(T["B3"]))
            p.setOpacity(0.55); p.setPen(QColor(T["BM"]))
            font = p.font(); font.setPointSize(11); p.setFont(font)
            lines = ["Arrastra una imagen aquí",
                     "Ctrl+O  →  Abrir desde el ordenador",
                     "Ctrl+V  →  Pegar desde portapapeles"]
            lh = 32; y0 = (h - 3 * lh) // 2
            for i, line in enumerate(lines):
                p.drawText(0, y0 + i * lh, w, lh,
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, line)
        p.end()

    def wheelEvent(self, e):
        if self._mode == "lock" or not self._px: return
        factor = 1.12 if e.angleDelta().y() > 0 else (1.0 / 1.12)
        new_z  = max(0.02, min(40.0, self._zoom * factor))
        mx, my = e.position().x(), e.position().y()
        ratio  = new_z / self._zoom
        self._cx = mx - (mx - self._cx) * ratio
        self._cy = my - (my - self._cy) * ratio
        self._zoom = new_z; self.update(); self.sig_zoom.emit(self._zoom)

    def mousePressEvent(self, e):
        if self._mode == "lock": return
        if e.button() == Qt.MouseButton.LeftButton:
            self._pan = True
            gp = e.globalPosition()
            self._pan_gx, self._pan_gy   = gp.x(), gp.y()
            self._pan_cx0, self._pan_cy0 = self._cx, self._cy
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._mode == "lock": return
        if self._pan and (e.buttons() & Qt.MouseButton.LeftButton):
            gp = e.globalPosition()
            self._cx = self._pan_cx0 + gp.x() - self._pan_gx
            self._cy = self._pan_cy0 + gp.y() - self._pan_gy
            self.update()
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, e):
        self._pan = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path:
                win = self.window()
                if hasattr(win, "load_path"): win.load_path(path)
                break

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self._px:
            self._cx = self.width() / 2; self._cy = self.height() / 2


# ═══════════════════════════════════════════════════════════════════════════════
#  TOOLBAR
# ═══════════════════════════════════════════════════════════════════════════════

class ToolBar(QFrame):
    sig_opacity  = pyqtSignal(float)
    sig_flip_h   = pyqtSignal()
    sig_flip_v   = pyqtSignal()
    sig_rotation = pyqtSignal(int)
    sig_fit      = pyqtSignal()
    sig_reset    = pyqtSignal()
    sig_ar       = pyqtSignal(str)
    sig_tint     = pyqtSignal(str)
    sig_mode     = pyqtSignal()

    def __init__(self, opacity=0.5, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbar_frame")
        self._opacity_val = opacity
        self._build()

    def _build(self, opacity=None):
        if opacity is not None:
            self._opacity_val = opacity
            
        s = _styles()
        self.setStyleSheet(f"#toolbar_frame {{ background-color: {T['B2']}; }}")

        outer = self.layout()
        if outer is None:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(6, 4, 6, 4)
            outer.setSpacing(10)
        else:
            def clear_lyt(lay):
                while lay.count():
                    item = lay.takeAt(0)
                    if item.widget(): item.widget().deleteLater()
                    elif item.layout():
                        clear_lyt(item.layout())
                        item.layout().deleteLater()
            clear_lyt(outer)

        def lbl(t):
            w = QLabel(t)
            w.setStyleSheet(f"color:{T['BM']}; font-size:11px;")
            w.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            return w

        def ibtn(icon_name, tip, fn, color=None, text="", fixed_w=None):
            b = QPushButton()
            b.setToolTip(tip)
            b.setIcon(ico(icon_name, color or T["BT"]))
            b.setIconSize(QSize(14, 14))
            b.setStyleSheet(s["btn"])
            if text:
                b.setText(f"  {text}")
                if fixed_w: b.setFixedWidth(fixed_w)
            else:
                b.setFixedSize(28, 26)
            b.clicked.connect(fn)
            return b

        def sep():
            f = QFrame(); f.setFrameShape(QFrame.Shape.VLine)
            f.setFixedSize(1, 18); f.setStyleSheet(f"color:{T['BD']};")
            return f

        row1 = QHBoxLayout(); row1.setContentsMargins(0, 0, 0, 0); row1.setSpacing(3)
        row1.addWidget(lbl("Opac."))
        self._sl = QSlider(Qt.Orientation.Horizontal)
        self._sl.setRange(int(MIN_OP * 100), int(MAX_OP * 100))
        self._sl.setValue(int(self._opacity_val * 100))
        self._sl.setMinimumWidth(55); self._sl.setMaximumWidth(95)
        self._sl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._sl.setStyleSheet(s["slider"])
        self._sl.valueChanged.connect(lambda v: self.sig_opacity.emit(v / 100.0))
        row1.addWidget(self._sl)

        self._lbl_op = QLabel(f"{int(self._opacity_val * 100)}%")
        self._lbl_op.setFixedWidth(28); self._lbl_op.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_op.setStyleSheet(f"color:{T['BM']}; font-size:11px;")
        row1.addWidget(self._lbl_op); row1.addWidget(sep())

        row1.addWidget(ibtn("fa6s.left-right", "Espejo horizontal (H)", self.sig_flip_h.emit))
        row1.addWidget(ibtn("fa6s.up-down",    "Espejo vertical (V)",   self.sig_flip_v.emit))
        row1.addWidget(sep())

        row1.addWidget(ibtn("fa6s.expand",           "Ajustar a ventana (Ctrl+F)",    self.sig_fit.emit))
        row1.addWidget(ibtn("fa6s.magnifying-glass", "Tamaño original 100% (Ctrl+0)", self.sig_reset.emit))

        self._lbl_z = QLabel("100%")
        self._lbl_z.setFixedWidth(34); self._lbl_z.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_z.setStyleSheet(f"color:{T['BM']}; font-size:11px;")
        row1.addWidget(self._lbl_z); row1.addWidget(sep())

        self._btn_mode = QPushButton()
        self._btn_mode.setToolTip("Activar modo calco — Tab / F8\nVolver a edición — Tab / F7")
        self._btn_mode.setStyleSheet(s["btn"])
        self._btn_mode.setIcon(ico("fa6s.lock", T["BB"]))
        self._btn_mode.setIconSize(QSize(13, 13))
        self._btn_mode.setText("  Bloquear  [Tab]")
        self._btn_mode.setFixedWidth(135)
        self._btn_mode.clicked.connect(self.sig_mode.emit)
        row1.addWidget(self._btn_mode); row1.addStretch()

        row2 = QHBoxLayout(); row2.setContentsMargins(0, 0, 0, 0); row2.setSpacing(3)
        rot_ico = QLabel()
        rot_ico.setPixmap(ico("fa6s.rotate-right", T["BM"]).pixmap(QSize(12, 12)))
        rot_ico.setFixedSize(16, 24); rot_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(rot_ico)

        self._spin = QSpinBox()
        self._spin.setRange(0, 359); self._spin.setSuffix("°")
        self._spin.setWrapping(True); self._spin.setValue(0)
        self._spin.setFixedWidth(60); self._spin.setStyleSheet(s["spin"])
        self._spin.setToolTip("Rotación en grados")
        self._spin.valueChanged.connect(self.sig_rotation.emit)
        row2.addWidget(self._spin); row2.addWidget(sep())

        ar_ico = QLabel()
        ar_ico.setPixmap(ico("fa6s.crop", T["BM"]).pixmap(QSize(12, 12)))
        ar_ico.setFixedSize(16, 24); ar_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(ar_ico)

        self._cb = QComboBox()
        for k in ASPECT_RATIOS: self._cb.addItem(k)
        self._cb.setMinimumWidth(70); self._cb.setMaximumWidth(110)
        self._cb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._cb.setStyleSheet(s["combo"]); self._cb.setToolTip("Proporción de la ventana")
        self._cb.currentTextChanged.connect(self.sig_ar.emit)
        row2.addWidget(self._cb); row2.addWidget(sep())

        row2.addWidget(ibtn("fa6s.palette", "Filtro de color", self._open_tint_menu))
        row2.addStretch()

        outer.addLayout(row1)
        outer.addLayout(row2)

    def _open_tint_menu(self):
        m = QMenu(self); m.setStyleSheet(_styles()["menu"])
        for label, key in [("Sin tinte","none"),("Cálido (amarillo)","warm"),
                            ("Frío (azul)","cold"),("Verde","green"),("Rojo","red")]:
            a = m.addAction(label); a.setData(key)
        chosen = m.exec(QCursor.pos())
        if chosen: self.sig_tint.emit(chosen.data())

    def set_opacity(self, v):
        self._sl.blockSignals(True); self._sl.setValue(int(v * 100)); self._sl.blockSignals(False)
        self._lbl_op.setText(f"{int(v * 100)}%")

    def set_zoom_label(self, z):
        self._lbl_z.setText(f"{int(z * 100)}%")

    def set_mode_button(self, mode: str):
        self._btn_mode.setStyleSheet(_styles()["btn"])
        if mode == "lock":
            self._btn_mode.setIcon(ico("fa6s.lock-open", "#ffa040"))
            self._btn_mode.setText("  Editar  [Tab]")
        else:
            self._btn_mode.setIcon(ico("fa6s.lock", T["BB"]))
            self._btn_mode.setText("  Bloquear  [Tab]")

    def set_rotation(self, v: int):
        self._spin.blockSignals(True); self._spin.setValue(v); self._spin.blockSignals(False)

    def refresh_theme(self):
        self._opacity_val = self._sl.value() / 100.0
        self._build()


# ═══════════════════════════════════════════════════════════════════════════════
#  TITLEBAR
# ═══════════════════════════════════════════════════════════════════════════════

class TitleBar(QFrame):
    sig_close    = pyqtSignal()
    sig_minimize = pyqtSignal()

    def __init__(self, title: str, icon: QIcon, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar_frame")
        self.setFixedHeight(28)
        self._title = title; self._icon = icon
        self._build()

    def _build(self):
        self.setStyleSheet(f"#titleBar_frame {{ background-color: {T['B0']}; }}")
        row = self.layout()
        if row is None:
            row = QHBoxLayout(self)
            row.setContentsMargins(8, 0, 4, 0); row.setSpacing(6)
        else:
            while row.count():
                item = row.takeAt(0)
                if w := item.widget(): w.deleteLater()

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(18, 18)
        icon_lbl.setPixmap(self._icon.pixmap(18, 18))
        icon_lbl.setScaledContents(False)
        row.addWidget(icon_lbl)

        self._lbl = QLabel(self._title)
        self._lbl.setStyleSheet(f"color:{T['BM']}; font-size:11px; background:transparent;")
        row.addWidget(self._lbl); row.addStretch()

        for icon_name, tip, sig, color in [
            ("fa6s.minus", "Minimizar", self.sig_minimize, T["BM"]),
            ("fa6s.xmark", "Cerrar",    self.sig_close,    "#e05555"),
        ]:
            b = QPushButton(); b.setFixedSize(24, 20); b.setToolTip(tip)
            b.setIcon(ico(icon_name, color)); b.setIconSize(QSize(11, 11))
            b.setStyleSheet("QPushButton{background:transparent;border:none;}"
                            "QPushButton:hover{background:rgba(128,128,128,0.15);border-radius:3px;}")
            b.clicked.connect(sig.emit); row.addWidget(b)

    def set_title(self, t: str):
        self._title = t; self._lbl.setText(t)

    def refresh_theme(self, icon: QIcon):
        self._icon = icon; self._build()

    def mousePressEvent(self, e):
        # ¡DELEGAMOS EL ARRASTRE AL SISTEMA OPERATIVO DE FORMA NATIVA!
        if e.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(e.position().toPoint())
            if isinstance(child, QPushButton): return
            
            window = self.window().windowHandle()
            if window:
                window.startSystemMove()
            e.accept()

    def mouseDoubleClickEvent(self, e):
        if self.window().isMaximized(): self.window().showNormal()
        else: self.window().showMaximized()


# ═══════════════════════════════════════════════════════════════════════════════
#  MENUBAR WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class MenuBarWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("menuBar_frame"); self.setFixedHeight(26)
        self._menus: dict[str, QMenu] = {}; self._recent_menu = None
        self._refresh_style()
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(4, 0, 4, 0); self._row.setSpacing(0)
        self._row.addStretch()

    def _refresh_style(self):
        self.setStyleSheet(f"#menuBar_frame {{ background-color: {T['B1']}; }}")

    def _make_btn(self, label: str, icon_name: str = None) -> QPushButton:
        b = QPushButton(label)
        if icon_name and _QTA:
            b.setIcon(ico(icon_name, T["BM"])); b.setIconSize(QSize(12, 12))
        b.setStyleSheet(
            f"QPushButton{{background:transparent;color:{T['BM']};border:none;"
            f"padding:2px 10px;font-size:12px;}}"
            f"QPushButton:hover{{background:{T['B4']};border-radius:3px;}}"
            f"QPushButton:pressed{{background:{T['B5']};}}"
        )
        return b

    def clear_menus(self):
        while self._row.count():
            item = self._row.takeAt(0)
            if w := item.widget(): w.deleteLater()
        self._row.addStretch()
        self._menus.clear()
        self._recent_menu = None

    def add_menu(self, label: str, items: list, icon_name: str = None):
        s = _styles()
        m = QMenu(label, self); m.setStyleSheet(s["menu"])
        self._menus[label] = m
        for item in items:
            if item is None:
                m.addSeparator()
            elif item[0] == "_recent":
                self._recent_menu = QMenu("Imágenes recientes", m)
                self._recent_menu.setStyleSheet(s["menu"])
                if _QTA: self._recent_menu.setIcon(ico("fa6s.clock-rotate-left", T["BM"]))
                m.addMenu(self._recent_menu)
            else:
                text, fn = item[0], item[1]
                checkable = len(item) > 2 and item[2] is True
                icon_key  = item[3] if len(item) > 3 else None
                a = QAction(text, self)
                if icon_key and _QTA: a.setIcon(ico(icon_key, T["BM"]))
                if checkable: a.setCheckable(True); a.setChecked(True)
                if fn:
                    if checkable: a.triggered.connect(fn)
                    else: a.triggered.connect(lambda _=False, f=fn: f())
                m.addAction(a)
        btn = self._make_btn(label, icon_name)
        self._row.insertWidget(self._row.count() - 1, btn)
        btn.clicked.connect(lambda: m.exec(btn.mapToGlobal(btn.rect().bottomLeft())))

    def refresh_recent(self, paths: list, load_fn):
        if self._recent_menu is None: return
        self._recent_menu.clear()
        if not paths:
            self._recent_menu.addAction("(vacío)").setEnabled(False); return
        for p in paths:
            a = self._recent_menu.addAction(Path(p).name)
            a.triggered.connect(lambda _=False, pp=p: load_fn(pp))


# ═══════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class CalkoWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.cfg   = load_cfg()
        self._path = None
        self._op   = self.cfg.get("opacity", 0.5)
        self._fh   = self.cfg.get("flip_h",  False)
        self._fv   = self.cfg.get("flip_v",  False)
        self._rot  = float(self.cfg.get("rotation", 0))
        self._tint = self.cfg.get("tint", "none")
        self._mode = "edit"
        self._theme = self.cfg.get("theme", "dark")
        self._session_path = None
        self._EDGE = 12

        apply_theme(self._theme)
        self._build()

        self.setGeometry(
            self.cfg.get("window_x", 120), self.cfg.get("window_y", 80),
            self.cfg.get("window_w", 680), self.cfg.get("window_h", 560),
        )

        last = self.cfg.get("last_image")
        if last and Path(last).exists():
            r = QMessageBox.question(self, APP_NAME,
                f"¿Retomar la última imagen?\n{Path(last).name}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self.load_path(last)

        for w in [self, self._cv, self._title_bar, self._menubar_widget, self._tb]:
            w.setMouseTracking(True)
            self.installEventFilter(self) if w is self else w.installEventFilter(self)

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(340, 200)

        self._icon = make_icon(self._theme)
        self.setWindowIcon(self._icon)

        container = QWidget(self)
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)

        self._title_bar = TitleBar(APP_NAME, self._icon, self)
        self._title_bar.sig_close.connect(self.close)
        self._title_bar.sig_minimize.connect(self.showMinimized)
        layout.addWidget(self._title_bar)

        self._menubar_widget = MenuBarWidget(self)
        layout.addWidget(self._menubar_widget)

        self._tb = ToolBar(self._op, self)
        layout.addWidget(self._tb)

        self._cv = Canvas(self)
        self._cv.sig_zoom.connect(self._tb.set_zoom_label)
        layout.addWidget(self._cv, stretch=1)

        self.setCentralWidget(container)
        self._wire_toolbar()
        self._build_menus()
        self._build_shortcuts()
        self._build_tray()

    def _wire_toolbar(self):
        self._tb.sig_opacity.connect(self._set_op)
        self._tb.sig_flip_h.connect(self._flip_h)
        self._tb.sig_flip_v.connect(self._flip_v)
        self._tb.sig_rotation.connect(self._on_rot)
        self._tb.sig_fit.connect(self._cv.fit)
        self._tb.sig_reset.connect(self._cv.reset)
        self._tb.sig_ar.connect(self._apply_ar)
        self._tb.sig_tint.connect(self._set_tint)
        self._tb.sig_mode.connect(self._toggle_mode)

    def _build_menus(self):
        mb = self._menubar_widget
        mb.add_menu("Archivo", [
            ("Cargar imagen...  Ctrl+O",    self._open,           False, "fa6s.folder-open"),
            ("Pegar portapapeles  Ctrl+V",  self._paste,          False, "fa6s.clipboard"),
            ("Captura de pantalla  Ctrl+P", self._screenshot,     False, "fa6s.camera"),
            None,
            ("_recent", None),
            None,
            ("Guardar sesión  Ctrl+S",      self._save_session,   False, "fa6s.floppy-disk"),
            ("Guardar sesión como...",       self._saveas_session, False, "fa6s.floppy-disk"),
            ("Abrir sesión...",              self._open_session,   False, "fa6s.folder-open"),
            None,
            ("Siempre encima",              self._toggle_top,     True),
            ("Minimizar a bandeja",          self._to_tray,        False, "fa6s.minimize"),
            None,
            ("Salir  Ctrl+W",              self.close,             False, "fa6s.right-from-bracket"),
        ], icon_name="fa6s.folder-open")
        mb.add_menu("Vista", [
            ("Ajustar a ventana  Ctrl+F",    self._cv.fit,         False, "fa6s.expand"),
            ("Tamaño original 100%  Ctrl+0", self._cv.reset,       False, "fa6s.magnifying-glass"),
            None,
            *[(f"Ventana {l}", lambda _=False, ll=l: self._apply_ar(ll))
              for l, r in ASPECT_RATIOS.items() if r],
            None,
            ("Modo oscuro",  lambda: self._set_theme("dark"),  False, "fa6s.moon"),
            ("Modo claro",   lambda: self._set_theme("light"), False, "fa6s.sun"),
        ], icon_name="fa6s.expand")
        mb.add_menu("Imagen", [
            ("Espejo horizontal  H",     self._flip_h,              False, "fa6s.left-right"),
            ("Espejo vertical  V",       self._flip_v,              False, "fa6s.up-down"),
            None,
            ("Sin tinte",                lambda: self._set_tint("none"),  False, "fa6s.circle-xmark"),
            ("Tinte cálido (amarillo)",  lambda: self._set_tint("warm"),  False, "fa6s.circle"),
            ("Tinte frío (azul)",        lambda: self._set_tint("cold"),  False, "fa6s.circle"),
            ("Tinte verde",              lambda: self._set_tint("green"), False, "fa6s.circle"),
            ("Tinte rojo",               lambda: self._set_tint("red"),   False, "fa6s.circle"),
        ], icon_name="fa6s.image")
        mb.add_menu("Ayuda", [
            (f"Acerca de {APP_NAME}", self._about, False, "fa6s.circle-info"),
        ], icon_name="fa6s.circle-question")
        self._refresh_recent()

    def _build_shortcuts(self):
        def sc(k, fn): QShortcut(QKeySequence(k), self).activated.connect(fn)
        sc("F7",           lambda: self._apply_mode("edit"))
        sc("F8",           lambda: self._apply_mode("lock"))
        sc("Tab",          self._toggle_mode)
        sc("Escape",       lambda: self._apply_mode("edit"))
        sc("Ctrl+O",       self._open)
        sc("Ctrl+V",       self._paste)
        sc("Ctrl+W",       self.close)
        sc("Ctrl+F",       self._cv.fit)
        sc("Ctrl+0",       self._cv.reset)
        sc("Ctrl+P",       self._screenshot)
        sc("Ctrl+S",       self._save_session)
        sc("Ctrl+Shift+S", self._saveas_session)
        sc("H",            self._flip_h)
        sc("V",            self._flip_v)
        sc("+",            lambda: self._step_op(+0.05))
        sc("-",            lambda: self._step_op(-0.05))
        sc("=",            lambda: self._step_op(+0.05))

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable(): return
        self._tray = QSystemTrayIcon(self._icon, self)
        self._tray.setToolTip(APP_NAME)
        m = QMenu()
        m.addAction("Mostrar Calko", self._from_tray)
        m.addAction("Salir", self.close)
        self._tray.setContextMenu(m)
        self._tray.activated.connect(
            lambda r: self._from_tray() if r == QSystemTrayIcon.ActivationReason.Trigger else None)

    # ── tema ──────────────────────────────────────────────────────────────────

    def _set_theme(self, name: str):
        self._theme = name
        apply_theme(name)
        self._icon = make_icon(name)
        self.setWindowIcon(self._icon)
        self._title_bar.refresh_theme(self._icon)
        self._menubar_widget.clear_menus()
        self._menubar_widget._refresh_style()
        self._build_menus()
        cur_op = self._op; cur_rot = int(self._rot)
        self._tb.refresh_theme()
        self._wire_toolbar()
        self._tb.set_opacity(cur_op)
        self._tb.set_rotation(cur_rot)
        self._cv.update()

    # ── sesiones ──────────────────────────────────────────────────────────────

    def _save_session(self):
        if self._session_path: self._write_session(self._session_path)
        else: self._saveas_session()

    def _saveas_session(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar sesión Calko", "", SESSION_FILTER)
        if path:
            if not path.endswith(SESSION_EXT): path += SESSION_EXT
            self._session_path = path; self._write_session(path)

    def _open_session(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir sesión Calko", "", SESSION_FILTER)
        if path: self._load_session(path)

    def _write_session(self, path: str):
        try:
            with open(path, "w") as f: json.dump(session_to_dict(self), f, indent=2)
            self._title_bar.set_title(f"{APP_NAME}  —  {Path(path).name}")
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"No se pudo guardar:\n{ex}")

    def _load_session(self, path: str):
        try:
            with open(path) as f: d = json.load(f)
            self._session_path = path
            session_from_dict(self, d)
            self._title_bar.set_title(f"{APP_NAME}  —  {Path(path).name}")
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"No se pudo abrir la sesión:\n{ex}")

    # ── modos ─────────────────────────────────────────────────────────────────

    def _toggle_mode(self):
        self._apply_mode("lock" if self._mode == "edit" else "edit")

    def _apply_mode(self, mode: str):
        if self._mode == mode: return
        self._mode = mode
        self._cv.set_mode(mode)
        self._tb.set_mode_button(mode)
        bars_h = self._title_bar.height() + self._menubar_widget.height() + self._tb.height()
        if mode == "lock":
            self._title_bar.hide(); self._menubar_widget.hide(); self._tb.hide()
            self._cv.shift_cy(bars_h); self._enable_ct(True)
        else:
            self._title_bar.show(); self._menubar_widget.show(); self._tb.show()
            self._cv.shift_cy(-bars_h); self._enable_ct(False)

    def _enable_ct(self, on: bool):
        if sys.platform == "win32":
            hwnd = int(self.winId()); GWL = -20; LAY = 0x80000; TRA = 0x20
            s = ctypes.windll.user32.GetWindowLongW(hwnd, GWL)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL, (s | LAY | TRA) if on else ((s & ~TRA) | LAY))
        else:
            f = self.windowFlags()
            f = (f | Qt.WindowType.WindowTransparentForInput) if on \
                else (f & ~Qt.WindowType.WindowTransparentForInput)
            self.setWindowFlags(f | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
            self.show()

    # ── EVENT FILTER: REDIMENSIONADO NATIVO ───────────────────────────────────

    def eventFilter(self, obj, event):
        if self._mode == "lock": return super().eventFilter(obj, event)
        et = event.type()
        
        if et in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            pos  = self.mapFromGlobal(event.globalPosition().toPoint())
            edge = self._detect_edge(pos)
            
            if isinstance(obj, (QPushButton, QSlider, QSpinBox, QComboBox, QMenu, QAction)):
                return super().eventFilter(obj, event)
                
            if edge:
                cursors = {
                    "right": Qt.CursorShape.SizeHorCursor,  "left":  Qt.CursorShape.SizeHorCursor,
                    "bottom": Qt.CursorShape.SizeVerCursor, "top":   Qt.CursorShape.SizeVerCursor,
                    "bottom-right": Qt.CursorShape.SizeFDiagCursor, "top-left":    Qt.CursorShape.SizeFDiagCursor,
                    "bottom-left":  Qt.CursorShape.SizeBDiagCursor, "top-right":   Qt.CursorShape.SizeBDiagCursor,
                }
                if obj.cursor().shape() != cursors[edge]: obj.setCursor(cursors[edge])
            else:
                if obj == self._cv:
                    obj.setCursor(Qt.CursorShape.ClosedHandCursor if self._cv._pan else Qt.CursorShape.OpenHandCursor)
                elif obj.cursor().shape() != Qt.CursorShape.ArrowCursor:
                    obj.unsetCursor()
                    
        elif et == QEvent.Type.MouseButtonPress:
            if getattr(event, "button", lambda: None)() == Qt.MouseButton.LeftButton:
                pos  = self.mapFromGlobal(event.globalPosition().toPoint())
                edge = self._detect_edge(pos)
                if edge:
                    if isinstance(obj, (QPushButton, QSlider, QSpinBox, QComboBox)):
                        return super().eventFilter(obj, event)
                        
                    # ¡DELEGAMOS EL ESTIRAMIENTO AL SISTEMA OPERATIVO!
                    edges = None
                    if "top" in edge: edges = Qt.Edge.TopEdge if edges is None else edges | Qt.Edge.TopEdge
                    if "bottom" in edge: edges = Qt.Edge.BottomEdge if edges is None else edges | Qt.Edge.BottomEdge
                    if "left" in edge: edges = Qt.Edge.LeftEdge if edges is None else edges | Qt.Edge.LeftEdge
                    if "right" in edge: edges = Qt.Edge.RightEdge if edges is None else edges | Qt.Edge.RightEdge
                    
                    window = self.windowHandle()
                    if window and edges is not None:
                        window.startSystemResize(edges)
                    return True
                    
        return super().eventFilter(obj, event)

    def _detect_edge(self, pos: QPoint) -> str | None:
        e = self._EDGE; x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        if x < 0 or x > w or y < 0 or y > h: return None
        on_r = x >= w-e; on_b = y >= h-e; on_l = x <= e; on_t = y <= e
        if on_b and on_r: return "bottom-right"
        if on_b and on_l: return "bottom-left"
        if on_t and on_r: return "top-right"
        if on_t and on_l: return "top-left"
        if on_r: return "right"
        if on_b: return "bottom"
        if on_l: return "left"
        if on_t: return "top"
        return None

    # ── imagen ────────────────────────────────────────────────────────────────

    def _open(self):
        p, _ = QFileDialog.getOpenFileName(self, "Cargar imagen", "", FORMATS)
        if p: self.load_path(p)

    def _paste(self):
        img = QApplication.clipboard().image()
        if not img.isNull():
            self._path = None; self._cv.load(QPixmap.fromImage(img)); self._sync()
        else:
            QMessageBox.information(self, APP_NAME, "No hay imagen en el portapapeles.")

    def load_path(self, path: str):
        r = QImageReader(path); r.setAutoTransform(True); img = r.read()
        if img.isNull():
            QMessageBox.warning(self, APP_NAME, f"No se pudo cargar:\n{path}"); return
        self._path = path; add_recent(self.cfg, path); self.cfg["last_image"] = path
        self._refresh_recent(); self._cv.load(QPixmap.fromImage(img)); self._sync()
        name = Path(path).name
        self.setWindowTitle(f"{APP_NAME}  —  {name}")
        self._title_bar.set_title(f"{APP_NAME}  —  {name}")

    def _screenshot(self):
        self.hide(); QTimer.singleShot(350, self._do_shot)

    def _do_shot(self):
        px = QApplication.primaryScreen().grabWindow(0)
        self._path = None; self._cv.load(px); self._sync(); self.show()

    def _sync(self):
        self._cv.set_opacity(self._op); self._cv.set_flip(self._fh, self._fv)
        self._cv.set_angle(self._rot); self._cv.set_tint(TINTS.get(self._tint))

    # ── controles ─────────────────────────────────────────────────────────────

    def _set_op(self, v):
        self._op = max(MIN_OP, min(MAX_OP, v))
        self._tb.set_opacity(self._op); self._cv.set_opacity(self._op)

    def _step_op(self, d): self._set_op(self._op + d)

    def _flip_h(self): self._fh = not self._fh; self._cv.set_flip(self._fh, self._fv)
    def _flip_v(self): self._fv = not self._fv; self._cv.set_flip(self._fh, self._fv)

    def _on_rot(self, v): self._rot = float(v); self._cv.set_angle(self._rot)

    def _apply_ar(self, label):
        ratio = ASPECT_RATIOS.get(label)
        if ratio: self.resize(self.width(), max(200, int(self.width() * ratio[1] / ratio[0])))

    def _set_tint(self, key): self._tint = key; self._cv.set_tint(TINTS.get(key))

    def _toggle_top(self, checked=None):
        f = self.windowFlags()
        has = bool(f & Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags((f & ~Qt.WindowType.WindowStaysOnTopHint) if has
                            else (f | Qt.WindowType.WindowStaysOnTopHint))
        self.show()

    def _to_tray(self):
        if hasattr(self, "_tray"):
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self._tray.show(); self.hide()
        else: self.showMinimized()

    def _from_tray(self):
        QApplication.instance().setQuitOnLastWindowClosed(True)
        self.show(); self.raise_(); self.activateWindow()

    def _refresh_recent(self):
        if hasattr(self, "_menubar_widget"):
            self._menubar_widget.refresh_recent(self.cfg.get("recent_images", []), self.load_path)

    def _about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle(f"Acerca de {APP_NAME}")
        msg.setIconPixmap(self._icon.pixmap(48, 48))
        msg.setText(f"<b style='font-size:15px'>{APP_NAME} {APP_VERSION}</b>")
        msg.setInformativeText(
            f"<p style='color:{T['BM']};font-size:12px;line-height:1.6'>"
            "Calko es una capa de calco flotante always-on-top para artistas digitales. "
            "Carga una imagen de referencia y úsala como guía transparente mientras "
            "dibujas en Photoshop, Procreate, Krita, Clip Studio o cualquier otro programa."
            "</p>"
            f"<p style='font-size:12px;color:{T['BT']}'>"
            "<b>Atajos principales:</b><br>"
            "Tab / F7 / F8 → Alternar modo edición/calco<br>"
            "Ctrl+O → Abrir | Ctrl+V → Pegar | Ctrl+P → Captura<br>"
            "Ctrl+S → Guardar sesión | Ctrl+Shift+S → Guardar como<br>"
            "Scroll → Zoom al puntero | Arrastrar → Mover imagen<br>"
            "H / V → Espejo | +/- → Opacidad"
            "</p>"
            f"<p style='font-size:11px;color:{T['BM']}'>"
            f"Código fuente: <a href='https://github.com/sukiisanz/calko' style='color:{T['BB']}'>"
            "github.com/sukiisanz/calko</a></p>"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setStyleSheet(
            f"QMessageBox{{background:{T['B1']};}}"
            f"QMessageBox QLabel{{color:{T['BT']};font-size:12px;}}"
            f"QPushButton{{background:{T['B3']};color:{T['BT']};border:1px solid {T['BD']};"
            f"border-radius:4px;padding:4px 18px;}}"
            f"QPushButton:hover{{background:{T['B4']};border-color:{T['BA']};}}"
        )
        msg.exec()

    # ── cierre ────────────────────────────────────────────────────────────────

    def closeEvent(self, e):
        g = self.geometry()
        self.cfg.update({
            "opacity": self._op, "last_image": self._path,
            "window_x": g.x(), "window_y": g.y(),
            "window_w": g.width(), "window_h": g.height(),
            "flip_h": self._fh, "flip_v": self._fv,
            "rotation": int(self._rot), "tint": self._tint,
            "theme": self._theme, "mode": "edit",
        })
        save_cfg(self.cfg)
        if hasattr(self, "_tray"): self._tray.hide()
        e.accept()

    def keyPressEvent(self, e):
        k = e.key()
        if   k == Qt.Key.Key_F7:     self._apply_mode("edit")
        elif k == Qt.Key.Key_F8:     self._apply_mode("lock")
        elif k == Qt.Key.Key_Escape: self._apply_mode("edit")
        else:                        super().keyPressEvent(e)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(True)

    win = CalkoWindow()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.endswith(SESSION_EXT) and Path(arg).exists():
            win._load_session(arg)
        elif Path(arg).exists():
            win.load_path(arg)

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()