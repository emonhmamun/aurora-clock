"""Aurora Clock - settings window (live preview, all options)."""
# Aurora Clock - a lightweight desktop clock overlay for Windows.
# Copyright (C) 2026 Emon Hasan Mamun
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from . import alerts as AL
from . import autostart, contrast, faces, fonts, themes, timezones, winutil
from . import sessions as S
from .config import APP_DISPLAY_NAME, APP_VERSION


class _NoWheel(QWidget):
    """Event filter: a mouse wheel over a combo/spin/slider scrolls the page
    instead of silently changing the value (a classic settings-window trap)."""

    def eventFilter(self, obj, ev):  # noqa: N802
        from PySide6.QtCore import QEvent
        if ev.type() == QEvent.Wheel and not obj.hasFocus():
            ev.ignore()
            return True
        return False


_NO_WHEEL = None


def _guard_wheel(root: QWidget) -> None:
    global _NO_WHEEL
    if _NO_WHEEL is None:
        _NO_WHEEL = _NoWheel()
    for cls in (QComboBox, QSpinBox, QSlider, QDoubleSpinBox):
        for w in root.findChildren(cls):
            w.setFocusPolicy(Qt.StrongFocus)
            w.installEventFilter(_NO_WHEEL)


def _scrollable(inner: QWidget) -> QScrollArea:
    """Put a tab page inside a scroll area so nothing is ever cut off."""
    if isinstance(inner, QScrollArea):          # already scrollable
        inner.setFrameShape(QFrame.NoFrame)
        if inner.widget() is not None:
            _guard_wheel(inner.widget())
        return inner
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    sa.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    _guard_wheel(inner)
    sa.setWidget(inner)
    return sa


class PreviewWidget(QWidget):
    """Live preview. The backdrop can be switched so you can check that the
    clock stays readable on a dark, light or busy wallpaper."""

    BACKDROPS = ["theme", "dark", "light", "photo", "checker"]

    def __init__(self, get_settings, app_ctx, parent=None):
        super().__init__(parent)
        self.get_settings = get_settings
        self.app = app_ctx
        self.backdrop = "theme"
        self.setMinimumHeight(170)
        t = QTimer(self); t.timeout.connect(self.update); t.start(50)

    def _paint_backdrop(self, p, pal):
        from PySide6.QtGui import QBrush, QColor, QLinearGradient
        r = self.rect()
        if self.backdrop == "theme":
            p.fillRect(r, QColor(pal["bg"]))
        elif self.backdrop == "dark":
            p.fillRect(r, QColor("#0A0A0C"))
        elif self.backdrop == "light":
            p.fillRect(r, QColor("#F2F4F7"))
        elif self.backdrop == "photo":
            g = QLinearGradient(0, 0, r.width(), r.height())
            for pos, col in ((0.0, "#2B5876"), (0.35, "#8E9EAB"),
                             (0.6, "#D7A86E"), (0.85, "#2F2F38"), (1.0, "#E9E4D4")):
                g.setColorAt(pos, QColor(col))
            p.fillRect(r, QBrush(g))
            p.setPen(Qt.NoPen)
            for i in range(9):
                c = QColor("#FFFFFF" if i % 2 else "#000000"); c.setAlphaF(0.10)
                p.setBrush(QBrush(c))
                p.drawEllipse(r.width() * i / 9.0 - 30, (i % 3) * r.height() / 3.0, 120, 90)
        else:
            sq = 14
            p.fillRect(r, QColor("#9AA3AD"))
            p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor("#D9DEE3")))
            for y in range(0, r.height(), sq):
                for x in range(0, r.width(), sq):
                    if ((x // sq) + (y // sq)) % 2 == 0:
                        p.drawRect(x, y, sq, sq)

    def paintEvent(self, _e):
        s = self.get_settings()
        if not s:
            return
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        pal = themes.palette(s.get("theme", "aurora"), s.get("custom_colors"))
        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        self._paint_backdrop(p, pal)
        now_utc = self.app.timesync.now_utc()
        now = timezones.localize(now_utc, s.get("timezone", ""))
        label = s.get("label") or timezones.city_label(s.get("timezone", ""))
        sts = None
        if s.get("face") in faces.SESSION_FACES or s.get("show_sessions", False):
            sts = self.app.session_statuses(s)
        ctx = faces.FaceContext(now=now, sub_second=now_utc.microsecond / 1e6,
                                pal=pal, settings=s, label=label,
                                now_utc=now_utc, sessions=sts)
        faces.render(p, r, ctx)
        p.end()


class SettingsDialog(QDialog):
    applied = Signal()

    def __init__(self, app_ctx, clock_id: str = "", parent=None):
        super().__init__(parent)
        self.app = app_ctx
        self.cfg = app_ctx.cfg
        self.setWindowTitle(f"{APP_DISPLAY_NAME} — Settings")
        # A real, resizable window: it can be minimised, maximised and snapped
        # like any other program (a plain QDialog cannot be minimised).
        self.setWindowFlags(Qt.Window
                            | Qt.CustomizeWindowHint
                            | Qt.WindowTitleHint
                            | Qt.WindowSystemMenuHint
                            | Qt.WindowMinimizeButtonHint
                            | Qt.WindowMaximizeButtonHint
                            | Qt.WindowCloseButtonHint)
        self.setSizeGripEnabled(True)
        self.setMinimumSize(720, 460)
        self.resize(980, 680)
        self._loading = False

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # ---- left: clock list ------------------------------------------
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Clocks</b>"))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._select_row)
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        b_add = QPushButton("Add"); b_add.clicked.connect(self._add_clock)
        b_dup = QPushButton("Duplicate"); b_dup.clicked.connect(self._dup_clock)
        b_del = QPushButton("Remove"); b_del.clicked.connect(self._del_clock)
        for b in (b_add, b_dup, b_del):
            row.addWidget(b)
        left.addLayout(row)
        b_only = QPushButton("Keep only this one")
        b_only.setToolTip("Delete every other clock — handy if you accidentally "
                          "created duplicates that sit on top of each other.")
        b_only.clicked.connect(self._keep_only)
        left.addWidget(b_only)
        b_find = QPushButton("Flash the selected clock")
        b_find.setToolTip("Blinks the selected clock so you can tell which is which.")
        b_find.clicked.connect(lambda: self.app.flash_clock(self._current_id()))
        left.addWidget(b_find)
        lw = QWidget(); lw.setLayout(left)
        lw.setMinimumWidth(170); lw.setMaximumWidth(320)

        # ---- right: tabs + preview -------------------------------------
        rightw = QWidget()
        right = QVBoxLayout(rightw)
        right.setContentsMargins(0, 0, 0, 0)
        self.preview = PreviewWidget(self._current, app_ctx)
        self.preview.setMinimumHeight(90)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        bdrow = QHBoxLayout()
        bdrow.addWidget(QLabel("Preview on:"))
        for key, lbl in (("theme", "Theme"), ("dark", "Dark"), ("light", "Light"),
                         ("photo", "Colourful"), ("checker", "Transparency")):
            b = QPushButton(lbl); b.setCheckable(True); b.setChecked(key == "theme")
            b.clicked.connect(lambda _c, k=key: self._set_backdrop(k))
            bdrow.addWidget(b)
            self._backdrop_buttons = getattr(self, "_backdrop_buttons", {})
            self._backdrop_buttons[key] = b
        bdrow.addStretch(1)
        self.b_preview = QPushButton("Hide preview")
        self.b_preview.setCheckable(True)
        self.b_preview.setToolTip("Collapse the preview to give the options more room.")
        self.b_preview.toggled.connect(self._toggle_preview)
        bdrow.addWidget(self.b_preview)
        bdw = QWidget(); bdw.setLayout(bdrow)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setUsesScrollButtons(True)
        # Every tab lives inside a scroll area, so options further down the
        # page are always reachable no matter how small the window is.
        for widget, title in ((self._tab_appearance(), "Appearance"),
                              (self._tab_visibility(), "Visibility"),
                              (self._tab_time(), "Time && Zone"),
                              (self._tab_sessions(), "Sessions"),
                              (self._tab_alerts(), "Alerts"),
                              (self._tab_behaviour(), "Behaviour"),
                              (self._tab_app(), "Application")):
            self.tabs.addTab(_scrollable(widget), title)

        # preview on top, options below - the divider can be dragged
        self._split = QSplitter(Qt.Vertical)
        top = QWidget(); tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(self.preview, 1)
        tl.addWidget(bdw)
        self._split.addWidget(top)
        self._split.addWidget(self.tabs)
        self._split.setStretchFactor(0, 0)
        self._split.setStretchFactor(1, 1)
        self._split.setSizes([200, 460])
        self._split.setChildrenCollapsible(False)
        right.addWidget(self._split, 1)

        btns = QHBoxLayout()
        self.status = QLabel("")
        self.status.setWordWrap(True)
        btns.addWidget(self.status, 1)
        hint = QLabel("Every change is saved and applied immediately.")
        hint.setStyleSheet("color:#8a949e;")
        btns.addWidget(hint)
        b_min = QPushButton("Minimise"); b_min.clicked.connect(self.showMinimized)
        btns.addWidget(b_min)
        b_close = QPushButton("Close"); b_close.setDefault(True)
        b_close.clicked.connect(self.accept)
        btns.addWidget(b_close)
        right.addLayout(btns)

        self._hsplit = QSplitter(Qt.Horizontal)
        self._hsplit.addWidget(lw)
        self._hsplit.addWidget(rightw)
        self._hsplit.setStretchFactor(1, 1)
        self._hsplit.setChildrenCollapsible(False)
        self._hsplit.setSizes([220, 760])
        root.addWidget(self._hsplit)

        self._reload_list(clock_id)
        self._refresh_status()
        self._restore_window_state()
        st = QTimer(self); st.timeout.connect(self._refresh_status); st.start(5000)

    # ------------------------------------------------------ window state --
    def _toggle_preview(self, hidden: bool) -> None:
        self.preview.setVisible(not hidden)
        self.b_preview.setText("Show preview" if hidden else "Hide preview")
        if hidden:
            self._split.setSizes([40, 640])
        else:
            self._split.setSizes([200, 460])

    def _ui_state(self) -> dict:
        return self.cfg.data.setdefault("ui", {})

    def _restore_window_state(self) -> None:
        st = self._ui_state()
        g = st.get("settings_geometry")
        if isinstance(g, list) and len(g) == 4:
            try:
                scr = self.screen().availableGeometry() if self.screen() else None
                x, y, w, h = (int(v) for v in g)
                w = max(720, min(w, 3000)); h = max(460, min(h, 2000))
                if scr:
                    x = max(scr.left() - 20, min(x, scr.right() - 200))
                    y = max(scr.top() - 10, min(y, scr.bottom() - 120))
                self.setGeometry(x, y, w, h)
            except (TypeError, ValueError):
                pass
        if st.get("settings_preview_hidden"):
            self.b_preview.setChecked(True)
        tab = st.get("settings_tab")
        if isinstance(tab, int) and 0 <= tab < self.tabs.count():
            self.tabs.setCurrentIndex(tab)

    def _save_window_state(self) -> None:
        t = getattr(self, "_save_timer", None)
        if t is not None and t.isActive():
            t.stop()
        st = self._ui_state()
        g = self.geometry()
        st["settings_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        st["settings_preview_hidden"] = bool(self.b_preview.isChecked())
        st["settings_tab"] = int(self.tabs.currentIndex())
        try:
            self.cfg.save()
        except Exception:
            pass

    def closeEvent(self, e):  # noqa: N802
        self._save_window_state()
        super().closeEvent(e)

    def done(self, code):  # noqa: D102
        self._save_window_state()
        super().done(code)

    def keyPressEvent(self, e):  # noqa: N802
        # Esc should not throw the whole window away mid-edit without saving
        # the layout, and Ctrl+W / Ctrl+Tab behave like a normal app.
        if e.key() == Qt.Key_Escape:
            self._save_window_state()
        super().keyPressEvent(e)

    # ------------------------------------------------------------- tabs ----
    def _tab_appearance(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        self.ed_name = QLineEdit(); self.ed_name.textEdited.connect(lambda v: self._set("name", v, relist=True))
        f.addRow("Clock name", self.ed_name)

        self.cb_face = QComboBox()
        for k, lbl in faces.FACE_LABELS.items():
            self.cb_face.addItem(lbl, k)
        self.cb_face.currentIndexChanged.connect(
            lambda: self._set("face", self.cb_face.currentData()))
        f.addRow("Clock face", self.cb_face)

        self.cb_theme = QComboBox()
        for k, lbl in themes.THEME_LABELS.items():
            self.cb_theme.addItem(lbl, k)
        self.cb_theme.currentIndexChanged.connect(
            lambda: self._set("theme", self.cb_theme.currentData()))
        f.addRow("Theme", self.cb_theme)

        self.cb_font = QComboBox()
        self._fill_fonts()
        self.cb_font.currentTextChanged.connect(lambda v: self._set("font_family", v))
        frow = QHBoxLayout(); frow.addWidget(self.cb_font, 1)
        b_imp = QPushButton("Load .ttf…"); b_imp.setToolTip(
            "Add your own font file — it is copied into Aurora's folder and "
            "stays available after a restart.")
        b_imp.clicked.connect(self._import_font); frow.addWidget(b_imp)
        fw = QWidget(); fw.setLayout(frow)
        f.addRow("Font", fw)

        self.sp_weight = QSpinBox(); self.sp_weight.setRange(100, 900); self.sp_weight.setSingleStep(100)
        self.sp_weight.valueChanged.connect(lambda v: self._set("font_weight", v))
        f.addRow("Font weight", self.sp_weight)

        self.cb_bg = QComboBox()
        for k, lbl in (("none", "Transparent"), ("glass", "Glass"),
                       ("panel", "Soft panel"), ("solid", "Solid")):
            self.cb_bg.addItem(lbl, k)
        self.cb_bg.currentIndexChanged.connect(lambda: self._set("background", self.cb_bg.currentData()))
        f.addRow("Background", self.cb_bg)

        self.sp_radius = QSpinBox(); self.sp_radius.setRange(0, 80)
        self.sp_radius.valueChanged.connect(lambda v: self._set("corner_radius", v))
        f.addRow("Corner radius", self.sp_radius)

        self.sl_opacity = QSlider(Qt.Horizontal); self.sl_opacity.setRange(15, 100)
        self.sl_opacity.valueChanged.connect(lambda v: self._set("opacity", v / 100.0))
        f.addRow("Opacity", self.sl_opacity)

        self.ck_shadow = QCheckBox("Glow / shadow")
        self.ck_shadow.toggled.connect(lambda v: self._set("shadow", v))
        f.addRow("", self.ck_shadow)

        colors = QHBoxLayout()
        for key, text in (("fg", "Text"), ("accent", "Accent"), ("dim", "Secondary"), ("bg", "Panel")):
            b = QPushButton(text)
            b.clicked.connect(lambda _c, k=key: self._pick_color(k))
            colors.addWidget(b)
        b_reset = QPushButton("Reset colours")
        b_reset.clicked.connect(lambda: self._set("custom_colors", {}))
        colors.addWidget(b_reset)
        cw = QWidget(); cw.setLayout(colors)
        f.addRow("Custom colours", cw)

        # quick palette swatches -----------------------------------------
        sw = QHBoxLayout()
        sw.setSpacing(4)
        for name in ("#FFFFFF", "#38E1C6", "#6C8CFF", "#FFB300", "#FF5252",
                     "#67D37A", "#FF77B0", "#A77BFF", "#00E5FF", "#F7FF4D",
                     "#FF8A3D", "#14181D"):
            b = QPushButton()
            b.setFixedSize(22, 22)
            b.setStyleSheet(f"background:{name}; border:1px solid #555; border-radius:4px;")
            b.setToolTip(f"Set the text colour to {name}")
            b.clicked.connect(lambda _c, n=name: self._quick_color("fg", n))
            sw.addWidget(b)
        sw.addStretch(1)
        sww = QWidget(); sww.setLayout(sw)
        f.addRow("Quick text colour", sww)

        # ---- gradient ---------------------------------------------------
        gb = QGroupBox("Gradient colouring")
        gf = QFormLayout(gb)
        self.ck_grad = QCheckBox("Paint the clock with a colour gradient")
        self.ck_grad.toggled.connect(lambda v: self._set("gradient_on", v))
        gf.addRow("", self.ck_grad)

        self.cb_gpreset = QComboBox()
        for key, (lbl, _c1, _c2) in faces.GRADIENT_PRESETS.items():
            self.cb_gpreset.addItem(lbl, key)
        self.cb_gpreset.currentIndexChanged.connect(self._set_gradient_preset)
        gf.addRow("Preset", self.cb_gpreset)

        self.cb_gdir = QComboBox()
        for key, lbl in faces.GRADIENT_DIRECTIONS.items():
            self.cb_gdir.addItem(lbl, key)
        self.cb_gdir.currentIndexChanged.connect(
            lambda: self._set("gradient_dir", self.cb_gdir.currentData()))
        gf.addRow("Direction", self.cb_gdir)

        grow = QHBoxLayout()
        self.b_g1 = QPushButton("Colour 1")
        self.b_g1.clicked.connect(lambda: self._pick_plain("gradient_c1"))
        self.b_g2 = QPushButton("Colour 2")
        self.b_g2.clicked.connect(lambda: self._pick_plain("gradient_c2"))
        grow.addWidget(self.b_g1); grow.addWidget(self.b_g2)
        b_swap = QPushButton("Swap"); b_swap.clicked.connect(self._swap_gradient)
        grow.addWidget(b_swap)
        gw = QWidget(); gw.setLayout(grow)
        gf.addRow("Own colours", gw)

        self.ck_gshapes = QCheckBox("Also colour hands, bars and rings")
        self.ck_gshapes.toggled.connect(lambda v: self._set("gradient_shapes", v))
        gf.addRow("", self.ck_gshapes)
        f.addRow(gb)
        return w

    def _quick_color(self, key: str, value: str) -> None:
        s = self._current()
        if not s:
            return
        custom = dict(s.get("custom_colors") or {})
        custom[key] = value
        self._set("custom_colors", custom)

    def _set_gradient_preset(self) -> None:
        key = self.cb_gpreset.currentData()
        if self._loading or not key:
            return
        s = self._current()
        if not s:
            return
        if key != "custom":
            _lbl, c1, c2 = faces.GRADIENT_PRESETS[key]
            s["gradient_c1"] = c1
            s["gradient_c2"] = c2
        self._set("gradient_preset", key)

    def _swap_gradient(self) -> None:
        s = self._current()
        if not s:
            return
        c1 = s.get("gradient_c1", "#38E1C6")
        c2 = s.get("gradient_c2", "#6C8CFF")
        s["gradient_c1"], s["gradient_c2"] = c2, c1
        s["gradient_preset"] = "custom"
        self._loading = True
        self.cb_gpreset.setCurrentIndex(max(0, self.cb_gpreset.findData("custom")))
        self._loading = False
        self._set("gradient_c1", c2)

    def _tab_time(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        self.cb_tz = QComboBox(); self.cb_tz.setEditable(True)
        self.cb_tz.addItem("System local time", "")
        self.cb_tz.insertSeparator(1)
        for z in timezones.POPULAR:
            self.cb_tz.addItem(f"{z}  ({timezones.offset_label(z)})", z)
        self.cb_tz.insertSeparator(self.cb_tz.count())
        for z in timezones.all_timezones():
            if z not in timezones.POPULAR:
                self.cb_tz.addItem(z, z)
        self.cb_tz.currentIndexChanged.connect(lambda: self._set("timezone", self.cb_tz.currentData()))
        f.addRow("Time zone", self.cb_tz)

        self.ed_label = QLineEdit(); self.ed_label.setPlaceholderText("auto (city name)")
        self.ed_label.textEdited.connect(lambda v: self._set("label", v))
        f.addRow("Label", self.ed_label)

        self.ck_24 = QCheckBox("24-hour clock"); self.ck_24.toggled.connect(lambda v: self._set("hour24", v))
        f.addRow("", self.ck_24)
        self.ck_ampm = QCheckBox("Show AM/PM"); self.ck_ampm.toggled.connect(lambda v: self._set("show_ampm", v))
        f.addRow("", self.ck_ampm)
        self.ck_label = QCheckBox("Show label"); self.ck_label.toggled.connect(lambda v: self._set("show_label", v))
        f.addRow("", self.ck_label)
        self.ck_date = QCheckBox("Show date"); self.ck_date.toggled.connect(lambda v: self._set("show_date", v))
        f.addRow("", self.ck_date)

        self.cb_datefmt = QComboBox(); self.cb_datefmt.setEditable(True)
        for fmt in ("dddd, d MMMM yyyy", "ddd dd MMM yyyy", "dd/MM/yyyy",
                    "MM/dd/yyyy", "yyyy-MM-dd", "dddd", "d MMMM"):
            self.cb_datefmt.addItem(fmt)
        self.cb_datefmt.currentTextChanged.connect(lambda v: self._set("date_format", v))
        f.addRow("Date format", self.cb_datefmt)

        self.cb_sec = QComboBox()
        for k, lbl in (("smooth", "Smooth sweep"), ("tick", "Tick (1 s)"), ("hidden", "Hidden")):
            self.cb_sec.addItem(lbl, k)
        self.cb_sec.currentIndexChanged.connect(lambda: self._set("seconds_mode", self.cb_sec.currentData()))
        f.addRow("Seconds", self.cb_sec)

        self.ck_blink = QCheckBox("Blinking colon")
        self.ck_blink.toggled.connect(lambda v: self._set("blink_colon", v))
        f.addRow("", self.ck_blink)

        # --- network time -------------------------------------------------
        box = QGroupBox("Internet time synchronisation (NTP)")
        bf = QFormLayout(box)
        self.ck_sync = QCheckBox("Keep the displayed time accurate automatically")
        self.ck_sync.toggled.connect(self._toggle_sync)
        bf.addRow("", self.ck_sync)
        self.sp_interval = QSpinBox(); self.sp_interval.setRange(5, 1440); self.sp_interval.setSuffix(" min")
        self.sp_interval.valueChanged.connect(self._set_interval)
        bf.addRow("Check every", self.sp_interval)
        self.lbl_sync = QLabel("—"); self.lbl_sync.setWordWrap(True)
        bf.addRow("Status", self.lbl_sync)
        b = QPushButton("Sync now"); b.clicked.connect(self.app.timesync.sync_now)
        bf.addRow("", b)
        f.addRow(box)
        return w

    def _tab_behaviour(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)

        self.ck_editmode = QCheckBox("Edit mode — allow clocks to be dragged and resized")
        self.ck_editmode.setToolTip(
            "When this is OFF no clock can be moved by the mouse, no matter what. "
            "Turn it on only while you are arranging your layout.")
        self.ck_editmode.toggled.connect(self._toggle_edit_mode)
        f.addRow("<b>Master lock</b>", self.ck_editmode)
        self.ck_lockdef = QCheckBox("New clocks start locked")
        self.ck_lockdef.toggled.connect(self._toggle_lockdef)
        f.addRow("", self.ck_lockdef)
        f.addRow(QLabel("<i>Your clocks are protected twice: the master "
                        "<b>Edit mode</b> switch above, plus a per-clock lock below. "
                        "A clock moves only when both allow it.</i>"))

        self.ck_lock = QCheckBox("Lock this clock's position and size")
        self.ck_lock.toggled.connect(lambda v: self._set("locked", v)); f.addRow("", self.ck_lock)
        self.ck_ct = QCheckBox("Click-through (mouse passes to the window behind)")
        self.ck_ct.toggled.connect(lambda v: self._set("click_through", v)); f.addRow("", self.ck_ct)
        self.cb_zmode = QComboBox()
        for k in (winutil.Z_TOP, winutil.Z_NORMAL, winutil.Z_BOTTOM, winutil.Z_DESKTOP):
            self.cb_zmode.addItem(winutil.Z_LABELS[k], k)
        self.cb_zmode.currentIndexChanged.connect(self._set_zmode)
        f.addRow("<b>Screen layer</b>", self.cb_zmode)
        f.addRow(QLabel(
            "<i><b>Always on top</b> — the clock floats over Chrome, games and every "
            "other window.<br>"
            "<b>Background</b> — the clock hides behind whatever you are working in and "
            "reappears the moment you minimise it.<br>"
            "<b>On the wallpaper</b> — the clock becomes part of the desktop itself, so "
            "even “Show desktop” leaves it on screen.</i>"))
        self.ck_fs = QCheckBox("Hide automatically over full-screen apps and games")
        self.ck_fs.toggled.connect(lambda v: self._set("hide_when_fullscreen", v)); f.addRow("", self.ck_fs)
        self.ck_enabled = QCheckBox("Show this clock")
        self.ck_enabled.toggled.connect(lambda v: self._set("enabled", v, relist=True)); f.addRow("", self.ck_enabled)

        geo = QHBoxLayout()
        self.sp_x = QSpinBox(); self.sp_y = QSpinBox()
        self.sp_w = QSpinBox(); self.sp_h = QSpinBox()
        for sp, key in ((self.sp_x, "x"), (self.sp_y, "y")):
            sp.setRange(-20000, 20000); sp.valueChanged.connect(lambda v, k=key: self._set(k, v))
            geo.addWidget(QLabel(key.upper())); geo.addWidget(sp)
        for sp, key in ((self.sp_w, "width"), (self.sp_h, "height")):
            sp.setRange(60, 10000); sp.valueChanged.connect(lambda v, k=key: self._set(k, v))
            geo.addWidget(QLabel(key[0].upper())); geo.addWidget(sp)
        gw = QWidget(); gw.setLayout(geo)
        f.addRow("Geometry", gw)

        # ---- size presets & scale -------------------------------------
        szrow = QHBoxLayout()
        for label, (w_, h_) in (("S", (260, 110)), ("M", (420, 180)),
                                ("L", (640, 260)), ("XL", (900, 360)),
                                ("Square", (320, 320))):
            b = QPushButton(label)
            b.clicked.connect(lambda _c, a=w_, bb=h_: self._set_size(a, bb))
            szrow.addWidget(b)
        b = QPushButton("Fit face"); b.setToolTip("Use the best shape for the selected clock face")
        b.clicked.connect(self._fit_face); szrow.addWidget(b)
        szw = QWidget(); szw.setLayout(szrow)
        f.addRow("Size presets", szw)

        self.sl_scale = QSlider(Qt.Horizontal); self.sl_scale.setRange(15, 500)
        self.sl_scale.setToolTip("Scale the clock while keeping its proportions")
        self.sl_scale.valueChanged.connect(self._scale_changed)
        f.addRow("Scale", self.sl_scale)

        # ---- 9-point snapping ------------------------------------------
        grid = QVBoxLayout()
        for row_keys in (("tl", "tc", "tr"), ("cl", "c", "cr"), ("bl", "bc", "br")):
            rr = QHBoxLayout()
            for k in row_keys:
                b = QPushButton({"tl": "↖", "tc": "↑", "tr": "↗",
                                 "cl": "←", "c": "●", "cr": "→",
                                 "bl": "↙", "bc": "↓", "br": "↘"}[k])
                b.setFixedWidth(42)
                b.clicked.connect(lambda _c, kk=k: self.app.snap(self._current_id(), kk))
                rr.addWidget(b)
            rr.addStretch(1)
            grid.addLayout(rr)
        gw2 = QWidget(); gw2.setLayout(grid)
        f.addRow("Snap to", gw2)

        self.sp_margin = QSpinBox(); self.sp_margin.setRange(0, 400); self.sp_margin.setSuffix(" px")
        self.sp_margin.valueChanged.connect(lambda v: self._set("snap_margin", v))
        f.addRow("Snap margin", self.sp_margin)

        self.cb_monitor = QComboBox()
        self.cb_monitor.currentIndexChanged.connect(self._move_to_monitor)
        f.addRow("Monitor", self.cb_monitor)

        f.addRow(QLabel(
            "<i>Tips (edit mode only): drag to move · drag an edge to resize · Ctrl+wheel resize · "
            "Alt+wheel opacity · double-click opens settings · right-click for the menu · "
            "arrow keys nudge.</i>"))
        return w

    def _tab_app(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        self.ck_auto = QCheckBox("Start Aurora Clock automatically when Windows starts")
        self.ck_auto.toggled.connect(self._toggle_autostart)
        f.addRow("", self.ck_auto)
        self.ck_tray = QCheckBox("Show tray icon")
        self.ck_tray.toggled.connect(self._toggle_tray)
        f.addRow("", self.ck_tray)
        self.cb_perf = QComboBox()
        for k, lbl in (("low", "Power saver — lowest CPU, 1 redraw per second"),
                       ("balanced", "Balanced — recommended"),
                       ("smooth", "Smooth — silkiest analog second hand")):
            self.cb_perf.addItem(lbl, k)
        self.cb_perf.currentIndexChanged.connect(self._set_perf)
        f.addRow("Performance", self.cb_perf)
        f.addRow(QLabel("<i>Aurora only redraws a clock when something actually "
                        "changes, so a digital clock costs about 1 repaint per "
                        "second. Only a sweeping analog second hand animates.</i>"))

        self.sp_watchdog = QSpinBox(); self.sp_watchdog.setRange(1, 30); self.sp_watchdog.setSuffix(" s")
        self.sp_watchdog.setToolTip("How often Aurora checks that the clock is still "
                                    "on screen and in the right layer.")
        self.sp_watchdog.valueChanged.connect(self._set_watchdog)
        f.addRow("Self-check every", self.sp_watchdog)
        f.addRow(QLabel(f"<b>{APP_DISPLAY_NAME}</b> v{APP_VERSION}"))
        f.addRow(QLabel(f"Settings file:<br><code>{self.cfg.path}</code>"))
        return w

    # ------------------------------------------------------------ helpers --
    def _current_id(self) -> str:
        i = self.list.currentRow()
        if 0 <= i < len(self.cfg.clocks):
            return self.cfg.clocks[i]["id"]
        return ""

    def _current(self):
        i = self.list.currentRow()
        if 0 <= i < len(self.cfg.clocks):
            return self.cfg.clocks[i]
        return None

    def _reload_list(self, select_id: str = "") -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for c in self.cfg.clocks:
            tag = "" if c.get("enabled", True) else "  (hidden)"
            self.list.addItem(QListWidgetItem(f"{c['name']}{tag}"))
        self.list.blockSignals(False)
        idx = 0
        for i, c in enumerate(self.cfg.clocks):
            if c["id"] == select_id:
                idx = i
                break
        self.list.setCurrentRow(idx)

    def _select_row(self, _i: int) -> None:
        self._load_fields()

    def _load_fields(self) -> None:
        s = self._current()
        if not s:
            return
        self._loading = True
        try:
            self.ed_name.setText(s["name"])
            self.cb_face.setCurrentIndex(max(0, self.cb_face.findData(s.get("face"))))
            self.cb_theme.setCurrentIndex(max(0, self.cb_theme.findData(s.get("theme"))))
            fi = self.cb_font.findText(s.get("font_family", "Segoe UI"))
            if fi >= 0:
                self.cb_font.setCurrentIndex(fi)
            self.sp_weight.setValue(int(s.get("font_weight", 300)))
            self.cb_bg.setCurrentIndex(max(0, self.cb_bg.findData(s.get("background", "none"))))
            self.sp_radius.setValue(int(s.get("corner_radius", 18)))
            self.sl_opacity.setValue(int(float(s.get("opacity", 0.92)) * 100))
            self.ck_shadow.setChecked(bool(s.get("shadow", True)))
            self.ck_grad.setChecked(bool(s.get("gradient_on", False)))
            self.cb_gpreset.setCurrentIndex(
                max(0, self.cb_gpreset.findData(s.get("gradient_preset", "aurora"))))
            self.cb_gdir.setCurrentIndex(
                max(0, self.cb_gdir.findData(s.get("gradient_dir", "vertical"))))
            self.ck_gshapes.setChecked(bool(s.get("gradient_shapes", True)))
            for btn, key in ((self.b_g1, "gradient_c1"), (self.b_g2, "gradient_c2")):
                col = str(s.get(key, "#888888"))
                btn.setStyleSheet(
                    f"background:{col}; color:#000; border:1px solid #666; "
                    "border-radius:4px; padding:4px;")

            ti = self.cb_tz.findData(s.get("timezone", ""))
            self.cb_tz.setCurrentIndex(ti if ti >= 0 else 0)
            self.ed_label.setText(s.get("label", ""))
            self.ck_24.setChecked(bool(s.get("hour24")))
            self.ck_ampm.setChecked(bool(s.get("show_ampm", True)))
            self.ck_label.setChecked(bool(s.get("show_label", True)))
            self.ck_date.setChecked(bool(s.get("show_date", True)))
            self.cb_datefmt.setCurrentText(s.get("date_format", "dddd, d MMMM yyyy"))
            self.cb_sec.setCurrentIndex(max(0, self.cb_sec.findData(s.get("seconds_mode", "smooth"))))
            self.ck_blink.setChecked(bool(s.get("blink_colon")))

            self.ck_lock.setChecked(bool(s.get("locked")))
            self.ck_ct.setChecked(bool(s.get("click_through")))
            zm = s.get("z_mode") or (winutil.Z_TOP if s.get("always_on_top", True) else winutil.Z_NORMAL)
            self.cb_zmode.setCurrentIndex(max(0, self.cb_zmode.findData(zm)))
            self.sl_scale.setValue(int(float(s.get("width", 420)) / 4.2))
            self.cb_monitor.blockSignals(True)
            self._fill_monitors()
            self.cb_monitor.blockSignals(False)
            self.sp_margin.setValue(int(s.get("snap_margin", 24)))
            self.ck_fs.setChecked(bool(s.get("hide_when_fullscreen", True)))
            self.ck_enabled.setChecked(bool(s.get("enabled", True)))
            self.sp_x.setValue(int(s["x"])); self.sp_y.setValue(int(s["y"]))
            self.sp_w.setValue(int(s["width"])); self.sp_h.setValue(int(s["height"]))

            ts = self.cfg.timesync
            self.ck_sync.setChecked(bool(ts.get("enabled", True)))
            self.sp_interval.setValue(int(ts.get("interval_minutes", 60)))
            # visibility
            self.ck_fx_shadow.setChecked(bool(s.get("fx_shadow", True)))
            self.sl_sh_blur.setValue(int(float(s.get("fx_shadow_blur", 7.0)) * 10))
            self.sl_sh_op.setValue(int(float(s.get("fx_shadow_opacity", 0.8)) * 100))
            self.sl_sh_dx.setValue(int(float(s.get("fx_shadow_dx", 2.0)) * 10))
            self.sl_sh_dy.setValue(int(float(s.get("fx_shadow_dy", 2.0)) * 10))
            self.sl_out.setValue(int(float(s.get("fx_outline", 0.0)) * 10))
            self.sl_out_op.setValue(int(float(s.get("fx_outline_opacity", 0.95)) * 100))
            self.sl_glow.setValue(int(float(s.get("fx_glow", 0.0)) * 100))
            self.ck_plate.setChecked(bool(s.get("fx_plate", False)))
            self.sl_plate_op.setValue(int(float(s.get("fx_plate_opacity", 0.38)) * 100))
            self.sl_plate_rad.setValue(int(float(s.get("fx_plate_radius", 10.0))))
            self.sl_bgop.setValue(int(float(s.get("bg_opacity", 0.45)) * 100))
            self.ck_auto_c.setChecked(bool(s.get("fx_auto_contrast", False)))
            self.sl_auto_s.setValue(int(float(s.get("fx_auto_strength", 1.0)) * 100))
            wp = contrast.wallpaper_path()
            self.lbl_wall.setText(
                f"Detected: <code>{wp}</code>" if wp else
                "No wallpaper image found (a solid-colour desktop). "
                "Automatic contrast will stay neutral — use an outline instead.")

            # sessions
            self.ck_showsess.setChecked(bool(s.get("show_sessions", False)))
            self.cb_sessstyle.setCurrentIndex(
                max(0, self.cb_sessstyle.findData(s.get("session_style", "pills"))))
            self.ck_sesscd.setChecked(bool(s.get("session_countdown", True)))
            self.cb_sesssort.setCurrentIndex(
                max(0, self.cb_sesssort.findData(self.cfg.sessions_cfg.get("sort", "time"))))
            self.ck_overlap.setChecked(bool(self.cfg.sessions_cfg.get("highlight_overlap", True)))
            en = set(self.cfg.sessions_cfg.get("enabled", []))
            for k, box in self.session_boxes.items():
                box.setChecked(k in en)

            # alerts
            al = self.cfg.alerts
            self.ck_al_sess.setChecked(bool(al.get("sessions_enabled", True)))
            self.ck_al_pre.setChecked(bool(al.get("notify_pre_open", True)))
            self.sp_lead.setValue(int(al.get("lead_minutes", 15)))
            self.ck_al_open.setChecked(bool(al.get("notify_open", True)))
            self.ck_al_close.setChecked(bool(al.get("notify_close", True)))
            self.ck_al_ovl.setChecked(bool(al.get("notify_overlap", True)))
            self.cb_al_sound.setCurrentIndex(
                max(0, self.cb_al_sound.findData(al.get("sound_session", "chime"))))
            self.cb_chime.setCurrentIndex(max(0, self.cb_chime.findData(al.get("chime", "off"))))
            self.ck_quiet.setChecked(bool(al.get("chime_quiet_hours", True)))
            self.ck_banner.setChecked(bool(al.get("chime_banner", False)))
            self.ck_balloon.setChecked(bool(al.get("tray_balloon", True)))
            self._reload_alarms()

            self.ck_editmode.setChecked(bool(self.cfg.general.get("edit_mode", False)))
            self.ck_lockdef.setChecked(bool(self.cfg.general.get("lock_by_default", True)))
            self.ck_auto.setChecked(autostart.is_autostart())
            self.ck_tray.setChecked(bool(self.cfg.general.get("show_tray_icon", True)))
            self.cb_perf.setCurrentIndex(
                max(0, self.cb_perf.findData(self.cfg.general.get("performance", "balanced"))))
            self.sp_watchdog.setValue(int(self.cfg.general.get("watchdog_seconds", 3)))
        finally:
            self._loading = False

    def _save_soon(self) -> None:
        """Coalesce disk writes.

        Dragging a slider used to write settings.json on *every* pixel -
        dozens of writes a second.  Now the file is written 400 ms after the
        last change, and always on close.
        """
        t = getattr(self, "_save_timer", None)
        if t is None:
            t = QTimer(self)
            t.setSingleShot(True)
            t.timeout.connect(self.cfg.save)
            self._save_timer = t
        t.start(400)

    def _set(self, key: str, value, relist: bool = False) -> None:
        if self._loading:
            return
        s = self._current()
        if not s:
            return
        if s.get(key) == value:
            return                      # nothing changed - no repaint, no write
        s[key] = value
        self._save_soon()
        self.app.refresh_clock(s["id"])
        if relist:
            cur = s["id"]
            self._reload_list(cur)
        self.preview.update()

    def _pick_color(self, key: str) -> None:
        s = self._current()
        if not s:
            return
        from PySide6.QtGui import QColor
        pal = themes.palette(s.get("theme", "aurora"), s.get("custom_colors"))
        col = QColorDialog.getColor(QColor(pal[key]), self, f"Choose {key} colour")
        if col.isValid():
            custom = dict(s.get("custom_colors") or {})
            custom[key] = col.name()
            self._set("custom_colors", custom)

    # app-level toggles ----------------------------------------------------
    def _toggle_sync(self, v: bool) -> None:
        if self._loading:
            return
        self.cfg.timesync["enabled"] = v
        self.cfg.save()
        if v:
            self.app.timesync.sync_now()

    def _set_interval(self, v: int) -> None:
        if self._loading:
            return
        self.cfg.timesync["interval_minutes"] = v
        self.cfg.save()

    def _toggle_autostart(self, v: bool) -> None:
        if self._loading:
            return
        ok = autostart.set_autostart(v)
        self.cfg.general["autostart"] = v
        self.cfg.save()
        if not ok:
            self.status.setText("Could not change the autostart setting.")

    def _toggle_tray(self, v: bool) -> None:
        if self._loading:
            return
        self.cfg.general["show_tray_icon"] = v
        self.cfg.save()
        self.app.update_tray_visibility()

    def _set_perf(self) -> None:
        if self._loading:
            return
        self.cfg.general["performance"] = self.cb_perf.currentData()
        self.cfg.save()
        self.app.refresh_all()

    def _set_watchdog(self, v: int) -> None:
        if self._loading:
            return
        self.cfg.general["watchdog_seconds"] = int(v)
        self.cfg.save()
        self.app.restart_watchdog()

    # list buttons ---------------------------------------------------------
    def _add_clock(self) -> None:
        c = self.app.add_clock()
        self._reload_list(c["id"])

    def _dup_clock(self) -> None:
        cid = self._current_id()
        if cid:
            c = self.app.duplicate_clock(cid)
            self._reload_list(c["id"])

    def _del_clock(self) -> None:
        cid = self._current_id()
        if cid:
            self.app.remove_clock(cid, ask=True)
            self._reload_list()

    def _keep_only(self) -> None:
        cid = self._current_id()
        if not cid or len(self.cfg.clocks) <= 1:
            return
        name = (self._current() or {}).get("name", cid)
        if QMessageBox.question(
                self, "Aurora Clock",
                f"Keep only “{name}” and delete the other "
                f"{len(self.cfg.clocks) - 1} clock(s)?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        for c in list(self.cfg.clocks):
            if c["id"] != cid:
                self.app.remove_clock(c["id"], ask=False)
        self._reload_list(cid)




    # ------------------------------------------------- layer / geometry ----
    def _set_zmode(self) -> None:
        if self._loading:
            return
        mode = self.cb_zmode.currentData()
        s = self._current()
        if not s:
            return
        s["z_mode"] = mode
        s["always_on_top"] = (mode == winutil.Z_TOP)
        self.cfg.save()
        self.app.refresh_clock(s["id"])

    def _set_size(self, w: int, h: int) -> None:
        s = self._current()
        if not s:
            return
        s["width"], s["height"] = int(w), int(h)
        self.cfg.save()
        self.app.refresh_clock(s["id"])
        self._load_fields()

    def _fit_face(self) -> None:
        s = self._current()
        if not s:
            return
        face = s.get("face", "digital")
        if face in faces.SQUARE_FACES:
            side = max(220, int((s["width"] + s["height"]) / 2))
            self._set_size(side, side)
        elif face in faces.SESSION_FACES:
            self._set_size(max(520, s["width"]), max(240, s["height"]))
        else:
            self._set_size(max(300, s["width"]), max(130, int(s["width"] * 0.42)))

    def _scale_changed(self, v: int) -> None:
        if self._loading:
            return
        s = self._current()
        if not s:
            return
        base_w, base_h = 420.0, 180.0
        ratio = (s["height"] / s["width"]) if s["width"] else (base_h / base_w)
        new_w = max(80, int(base_w * v / 100.0))
        s["width"] = new_w
        s["height"] = max(50, int(new_w * ratio))
        self.cfg.save()
        self.app.refresh_clock(s["id"])
        self.sp_w.blockSignals(True); self.sp_h.blockSignals(True)
        self.sp_w.setValue(s["width"]); self.sp_h.setValue(s["height"])
        self.sp_w.blockSignals(False); self.sp_h.blockSignals(False)

    def _fill_monitors(self) -> None:
        from PySide6.QtGui import QGuiApplication
        self.cb_monitor.clear()
        for i, sc in enumerate(QGuiApplication.screens()):
            g = sc.geometry()
            tag = " (primary)" if sc is QGuiApplication.primaryScreen() else ""
            self.cb_monitor.addItem(f"{i + 1}: {g.width()}x{g.height()}{tag}", i)

    def _move_to_monitor(self) -> None:
        if self._loading:
            return
        idx = self.cb_monitor.currentData()
        s = self._current()
        if s is None or idx is None:
            return
        from PySide6.QtGui import QGuiApplication
        screens = QGuiApplication.screens()
        if not (0 <= idx < len(screens)):
            return
        a = screens[idx].availableGeometry()
        s["x"] = a.left() + int(s.get("snap_margin", 24))
        s["y"] = a.top() + int(s.get("snap_margin", 24))
        self.cfg.save()
        self.app.refresh_clock(s["id"])
        self._load_fields()

    # -------------------------------------------------------- visibility ----
    def _set_backdrop(self, key: str) -> None:
        self.preview.backdrop = key
        for k, b in getattr(self, "_backdrop_buttons", {}).items():
            b.setChecked(k == key)
        self.preview.update()

    def _tab_visibility(self) -> QWidget:
        outer = QWidget(); v = QVBoxLayout(outer)
        v.addWidget(QLabel(
            "<b>Readability on any wallpaper.</b> The clock itself is fully "
            "transparent — these effects make the digits stand out without "
            "putting a box around them. Use the preview buttons above to check "
            "your settings against a dark, light and colourful background."))

        # ---- quick presets --------------------------------------------
        pbox = QGroupBox("Quick presets"); pl = QHBoxLayout(pbox)
        for name, label in (("clean", "Clean"), ("shadow", "Soft shadow"),
                            ("outline", "Sharp outline"), ("neon", "Neon glow"),
                            ("plate", "Contrast plate"), ("max", "Maximum")):
            b = QPushButton(label)
            b.clicked.connect(lambda _c, n=name: self._apply_fx_preset(n))
            pl.addWidget(b)
        v.addWidget(pbox)

        # ---- shadow ----------------------------------------------------
        sbox = QGroupBox("Drop shadow"); sf = QFormLayout(sbox)
        self.ck_fx_shadow = QCheckBox("Enable drop shadow")
        self.ck_fx_shadow.toggled.connect(lambda c: self._set("fx_shadow", c))
        sf.addRow("", self.ck_fx_shadow)
        self.sl_sh_blur = self._slider(0, 300, lambda v: self._set("fx_shadow_blur", v / 10.0))
        sf.addRow("Softness", self.sl_sh_blur)
        self.sl_sh_op = self._slider(0, 100, lambda v: self._set("fx_shadow_opacity", v / 100.0))
        sf.addRow("Strength", self.sl_sh_op)
        self.sl_sh_dx = self._slider(-200, 200, lambda v: self._set("fx_shadow_dx", v / 10.0))
        sf.addRow("Offset X", self.sl_sh_dx)
        self.sl_sh_dy = self._slider(-200, 200, lambda v: self._set("fx_shadow_dy", v / 10.0))
        sf.addRow("Offset Y", self.sl_sh_dy)
        b = QPushButton("Shadow colour…")
        b.clicked.connect(lambda: self._pick_plain("fx_shadow_color"))
        sf.addRow("", b)
        v.addWidget(sbox)

        # ---- outline + glow -------------------------------------------
        obox = QGroupBox("Outline and glow"); of = QFormLayout(obox)
        self.sl_out = self._slider(0, 80, lambda v: self._set("fx_outline", v / 10.0))
        of.addRow("Outline width", self.sl_out)
        self.sl_out_op = self._slider(0, 100, lambda v: self._set("fx_outline_opacity", v / 100.0))
        of.addRow("Outline strength", self.sl_out_op)
        b = QPushButton("Outline colour…")
        b.clicked.connect(lambda: self._pick_plain("fx_outline_color"))
        of.addRow("", b)
        self.sl_glow = self._slider(0, 100, lambda v: self._set("fx_glow", v / 100.0))
        of.addRow("Glow", self.sl_glow)
        b = QPushButton("Glow colour…")
        b.clicked.connect(lambda: self._pick_plain("fx_glow_color"))
        of.addRow("", b)
        v.addWidget(obox)

        # ---- plate + backdrop ------------------------------------------
        bbox = QGroupBox("Backdrop"); bf = QFormLayout(bbox)
        self.ck_plate = QCheckBox("Contrast plate behind the text only")
        self.ck_plate.toggled.connect(lambda c: self._set("fx_plate", c))
        bf.addRow("", self.ck_plate)
        self.sl_plate_op = self._slider(0, 100, lambda v: self._set("fx_plate_opacity", v / 100.0))
        bf.addRow("Plate strength", self.sl_plate_op)
        self.sl_plate_rad = self._slider(0, 40, lambda v: self._set("fx_plate_radius", float(v)))
        bf.addRow("Plate rounding", self.sl_plate_rad)
        b = QPushButton("Plate colour…")
        b.clicked.connect(lambda: self._pick_plain("fx_plate_color"))
        bf.addRow("", b)
        self.sl_bgop = self._slider(0, 100, lambda v: self._set("bg_opacity", v / 100.0))
        bf.addRow("Panel strength", self.sl_bgop)
        bf.addRow(QLabel("<i>Panel strength only applies when Appearance → "
                         "Background is Glass, Soft panel or Solid. Leave the "
                         "background on <b>Transparent</b> for a pure overlay.</i>"))
        v.addWidget(bbox)

        # ---- auto contrast ---------------------------------------------
        abox = QGroupBox("Automatic contrast"); af = QFormLayout(abox)
        self.ck_auto_c = QCheckBox("Match the text colour to my wallpaper automatically")
        self.ck_auto_c.setToolTip(
            "Aurora measures how bright your wallpaper is under this clock and "
            "switches between light and dark text, adding a matching outline.")
        self.ck_auto_c.toggled.connect(lambda c: self._set("fx_auto_contrast", c))
        af.addRow("", self.ck_auto_c)
        self.sl_auto_s = self._slider(0, 100, lambda v: self._set("fx_auto_strength", v / 100.0))
        af.addRow("How strongly", self.sl_auto_s)
        self.lbl_wall = QLabel("—"); self.lbl_wall.setWordWrap(True)
        af.addRow("Wallpaper", self.lbl_wall)
        v.addWidget(abox)
        v.addStretch(1)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(outer)
        return scroll

    def _slider(self, lo: int, hi: int, cb) -> QSlider:
        sl = QSlider(Qt.Horizontal); sl.setRange(lo, hi)
        sl.valueChanged.connect(cb)
        return sl

    def _pick_plain(self, key: str) -> None:
        s = self._current()
        if not s:
            return
        from PySide6.QtGui import QColor
        cur = QColor(s.get(key) or "#000000")
        col = QColorDialog.getColor(cur, self, "Choose a colour")
        if col.isValid():
            if key.startswith("gradient_c"):
                s["gradient_preset"] = "custom"
                self._loading = True
                self.cb_gpreset.setCurrentIndex(max(0, self.cb_gpreset.findData("custom")))
                self._loading = False
            self._set(key, col.name())
            if key.startswith("gradient_c"):
                btn = self.b_g1 if key.endswith("c1") else self.b_g2
                btn.setStyleSheet(
                    f"background:{col.name()}; color:#000; border:1px solid #666; "
                    "border-radius:4px; padding:4px;")

    FX_PRESETS = {
        "clean":   {"fx_shadow": False, "fx_outline": 0.0, "fx_glow": 0.0, "fx_plate": False},
        "shadow":  {"fx_shadow": True, "fx_shadow_blur": 9.0, "fx_shadow_opacity": 0.85,
                    "fx_shadow_dx": 2.0, "fx_shadow_dy": 3.0, "fx_outline": 0.0,
                    "fx_glow": 0.0, "fx_plate": False},
        "outline": {"fx_shadow": True, "fx_shadow_blur": 4.0, "fx_shadow_opacity": 0.55,
                    "fx_outline": 2.0, "fx_outline_color": "#000000",
                    "fx_outline_opacity": 1.0, "fx_glow": 0.0, "fx_plate": False},
        "neon":    {"fx_shadow": True, "fx_shadow_blur": 10.0, "fx_shadow_opacity": 0.6,
                    "fx_outline": 0.0, "fx_glow": 0.85, "fx_plate": False},
        "plate":   {"fx_shadow": False, "fx_outline": 0.0, "fx_glow": 0.0,
                    "fx_plate": True, "fx_plate_opacity": 0.42, "fx_plate_radius": 12.0},
        "max":     {"fx_shadow": True, "fx_shadow_blur": 12.0, "fx_shadow_opacity": 0.9,
                    "fx_outline": 2.4, "fx_outline_opacity": 1.0, "fx_glow": 0.35,
                    "fx_plate": True, "fx_plate_opacity": 0.3},
    }

    def _apply_fx_preset(self, name: str) -> None:
        s = self._current()
        if not s:
            return
        s.update(self.FX_PRESETS.get(name, {}))
        self.cfg.save()
        self.app.refresh_clock(s["id"])
        self._load_fields()
        self.preview.update()

    # --------------------------------------------------------- sessions ----
    def _tab_sessions(self) -> QWidget:
        outer = QWidget(); v = QVBoxLayout(outer)

        v.addWidget(QLabel(
            "<b>Trading sessions</b> — tick the markets you follow. "
            "Opening hours follow each market's own time zone and handle "
            "daylight saving automatically."))

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        inner = QWidget(); iv = QVBoxLayout(inner)
        self.session_boxes = {}
        enabled = set(self.cfg.sessions_cfg.get("enabled", S.DEFAULT_ENABLED))
        for group, glabel in S.GROUP_LABELS.items():
            box = QGroupBox(glabel); gl = QVBoxLayout(box)
            for key, sess in S.CATALOGUE.items():
                if sess.group != group:
                    continue
                ck = QCheckBox(f"{sess.name}  ({sess.open_t[0]:02d}:{sess.open_t[1]:02d}"
                               f"–{sess.close_t[0]:02d}:{sess.close_t[1]:02d} {sess.tz})")
                ck.setChecked(key in enabled)
                ck.toggled.connect(lambda c, k=key: self._toggle_session(k, c))
                self.session_boxes[key] = ck
                gl.addWidget(ck)
            iv.addWidget(box)
        iv.addStretch(1)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

        f = QFormLayout()
        self.ck_showsess = QCheckBox("Show a session strip on this clock")
        self.ck_showsess.toggled.connect(lambda c: self._set("show_sessions", c))
        f.addRow("", self.ck_showsess)

        self.cb_sessstyle = QComboBox()
        for k, lbl in (("pills", "Pills (compact badges)"),
                       ("timeline", "24-hour timeline"),
                       ("list", "Detailed list")):
            self.cb_sessstyle.addItem(lbl, k)
        self.cb_sessstyle.currentIndexChanged.connect(
            lambda: self._set("session_style", self.cb_sessstyle.currentData()))
        f.addRow("Strip style", self.cb_sessstyle)

        self.ck_sesscd = QCheckBox("Show countdown to open / close")
        self.ck_sesscd.toggled.connect(lambda c: self._set("session_countdown", c))
        f.addRow("", self.ck_sesscd)

        self.cb_sesssort = QComboBox()
        for k, lbl in (("time", "Market order (Sydney → New York)"),
                       ("open_first", "Open sessions first"), ("name", "Alphabetical")):
            self.cb_sesssort.addItem(lbl, k)
        self.cb_sesssort.currentIndexChanged.connect(self._set_sess_sort)
        f.addRow("Order", self.cb_sesssort)

        self.ck_overlap = QCheckBox("Highlight overlap windows (high volatility)")
        self.ck_overlap.toggled.connect(self._set_overlap)
        f.addRow("", self.ck_overlap)

        f.addRow(QLabel("<i>Tip: the faces marked ★ in Appearance "
                        "(Trader dashboard, Session timeline, Session board) are "
                        "built for this.</i>"))
        fw = QWidget(); fw.setLayout(f)
        v.addWidget(fw)
        return outer

    def _toggle_session(self, key: str, on: bool) -> None:
        if self._loading:
            return
        order = list(S.CATALOGUE.keys())
        cur = set(self.cfg.sessions_cfg.get("enabled", []))
        cur.add(key) if on else cur.discard(key)
        self.cfg.sessions_cfg["enabled"] = [k for k in order if k in cur]
        self.cfg.save()
        self.app._session_cache.clear()
        self.app.refresh_all()
        self.preview.update()

    def _set_sess_sort(self) -> None:
        if self._loading:
            return
        self.cfg.sessions_cfg["sort"] = self.cb_sesssort.currentData()
        self.cfg.save(); self.app._session_cache.clear()

    def _set_overlap(self, v: bool) -> None:
        if self._loading:
            return
        self.cfg.sessions_cfg["highlight_overlap"] = v
        for c in self.cfg.clocks:
            c["highlight_overlap"] = v
        self.cfg.save(); self.app.refresh_all()

    # ----------------------------------------------------------- alerts ----
    def _tab_alerts(self) -> QWidget:
        outer = QWidget(); v = QVBoxLayout(outer)

        box = QGroupBox("Trading session alerts"); f = QFormLayout(box)
        self.ck_al_sess = QCheckBox("Enable session alerts")
        self.ck_al_sess.toggled.connect(lambda c: self._set_alert("sessions_enabled", c))
        f.addRow("", self.ck_al_sess)
        self.ck_al_pre = QCheckBox("Warn before a session opens")
        self.ck_al_pre.toggled.connect(lambda c: self._set_alert("notify_pre_open", c))
        f.addRow("", self.ck_al_pre)
        self.sp_lead = QSpinBox(); self.sp_lead.setRange(1, 120); self.sp_lead.setSuffix(" min before")
        self.sp_lead.valueChanged.connect(lambda v: self._set_alert("lead_minutes", v))
        f.addRow("Warning time", self.sp_lead)
        self.ck_al_open = QCheckBox("Alert when a session opens")
        self.ck_al_open.toggled.connect(lambda c: self._set_alert("notify_open", c))
        f.addRow("", self.ck_al_open)
        self.ck_al_close = QCheckBox("Alert when a session closes")
        self.ck_al_close.toggled.connect(lambda c: self._set_alert("notify_close", c))
        f.addRow("", self.ck_al_close)
        self.ck_al_ovl = QCheckBox("Alert on overlap windows (London+NY etc.)")
        self.ck_al_ovl.toggled.connect(lambda c: self._set_alert("notify_overlap", c))
        f.addRow("", self.ck_al_ovl)
        self.cb_al_sound = QComboBox()
        for k in AL.SOUNDS:
            self.cb_al_sound.addItem(k.capitalize(), k)
        self.cb_al_sound.currentIndexChanged.connect(
            lambda: self._set_alert("sound_session", self.cb_al_sound.currentData()))
        srow = QHBoxLayout(); srow.addWidget(self.cb_al_sound, 1)
        bt = QPushButton("Test"); bt.clicked.connect(self.app.test_notification)
        srow.addWidget(bt)
        sw = QWidget(); sw.setLayout(srow)
        f.addRow("Alert sound", sw)
        v.addWidget(box)

        # ---- alarms table ---------------------------------------------
        abox = QGroupBox("Your alarms"); av = QVBoxLayout(abox)
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["On", "Label", "Time", "Repeat", "Time zone", "Sound"])
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        av.addWidget(self.tbl)
        row = QHBoxLayout()
        b1 = QPushButton("Add alarm"); b1.clicked.connect(self._add_alarm)
        b2 = QPushButton("Edit"); b2.clicked.connect(self._edit_alarm)
        b3 = QPushButton("Delete"); b3.clicked.connect(self._del_alarm)
        for b in (b1, b2, b3):
            row.addWidget(b)
        row.addStretch(1)
        av.addLayout(row)
        v.addWidget(abox, 1)

        # ---- chime -----------------------------------------------------
        cbox = QGroupBox("Hourly chime"); cf = QFormLayout(cbox)
        self.cb_chime = QComboBox()
        for k, lbl in (("off", "Off"), ("hour", "Every hour"),
                       ("half", "Every 30 minutes"), ("quarter", "Every 15 minutes")):
            self.cb_chime.addItem(lbl, k)
        self.cb_chime.currentIndexChanged.connect(
            lambda: self._set_alert("chime", self.cb_chime.currentData()))
        cf.addRow("Chime", self.cb_chime)
        self.ck_quiet = QCheckBox("Stay silent between 22:00 and 07:00")
        self.ck_quiet.toggled.connect(lambda c: self._set_alert("chime_quiet_hours", c))
        cf.addRow("", self.ck_quiet)
        self.ck_banner = QCheckBox("Show an on-screen banner for alerts")
        self.ck_banner.toggled.connect(lambda c: self._set_alert("chime_banner", c))
        cf.addRow("", self.ck_banner)
        self.ck_balloon = QCheckBox("Show Windows tray notifications")
        self.ck_balloon.toggled.connect(lambda c: self._set_alert("tray_balloon", c))
        cf.addRow("", self.ck_balloon)
        v.addWidget(cbox)
        return outer

    def _toggle_edit_mode(self, v: bool) -> None:
        if self._loading:
            return
        self.app.set_edit_mode(v)

    def _toggle_lockdef(self, v: bool) -> None:
        if self._loading:
            return
        self.cfg.general["lock_by_default"] = v
        self.cfg.save()

    def _set_alert(self, key: str, value) -> None:
        if self._loading:
            return
        self.cfg.alerts[key] = value
        self.cfg.save()

    def _reload_alarms(self) -> None:
        self.tbl.setRowCount(0)
        for al in self.cfg.alarms:
            r = self.tbl.rowCount(); self.tbl.insertRow(r)
            vals = ["Yes" if al.get("enabled", True) else "No",
                    al.get("label", ""), al.get("time", ""),
                    al.get("repeat", "daily"),
                    al.get("timezone", "") or "system",
                    al.get("sound", "chime")]
            for c, val in enumerate(vals):
                self.tbl.setItem(r, c, QTableWidgetItem(str(val)))

    def _add_alarm(self) -> None:
        al = AL.default_alarm()
        al["id"] = self.cfg.new_alarm_id()
        dlg = AlarmDialog(al, self)
        if dlg.exec() == QDialog.Accepted:
            self.cfg.alarms.append(dlg.alarm)
            self.cfg.save()
            self._reload_alarms()

    def _edit_alarm(self) -> None:
        r = self.tbl.currentRow()
        if not (0 <= r < len(self.cfg.alarms)):
            return
        dlg = AlarmDialog(dict(self.cfg.alarms[r]), self)
        if dlg.exec() == QDialog.Accepted:
            self.cfg.alarms[r] = dlg.alarm
            self.cfg.save()
            self._reload_alarms()

    def _del_alarm(self) -> None:
        r = self.tbl.currentRow()
        if 0 <= r < len(self.cfg.alarms):
            del self.cfg.alarms[r]
            self.cfg.save()
            self._reload_alarms()

    # ------------------------------------------------------------ fonts ----
    def _fill_fonts(self) -> None:
        self.cb_font.blockSignals(True)
        self.cb_font.clear()
        last = None
        for fam, group in fonts.ordered_families():
            if group != last:
                if self.cb_font.count():
                    self.cb_font.insertSeparator(self.cb_font.count())
                last = group
            self.cb_font.addItem(fam)
        self.cb_font.blockSignals(False)

    def _import_font(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a font file", "", "Fonts (*.ttf *.otf *.ttc)")
        if not path:
            return
        fams = fonts.import_font(path, self.cfg)
        if not fams:
            QMessageBox.warning(self, "Aurora Clock", "That font could not be loaded.")
            return
        self._fill_fonts()
        i = self.cb_font.findText(fams[0])
        if i >= 0:
            self.cb_font.setCurrentIndex(i)
        self._set("font_family", fams[0])

    def show_tab(self, name: str) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).lower().startswith(name.lower()):
                self.tabs.setCurrentIndex(i)
                return


    def _refresh_status(self) -> None:
        st = self.app.timesync.status
        if st["synced"]:
            off = st["offset_ms"]
            when = st["last_sync"].strftime("%H:%M:%S") if st["last_sync"] else "—"
            verdict = "your PC clock is accurate" if abs(off) < 1000 else \
                      "your PC clock is off — Aurora is correcting the display"
            self.lbl_sync.setText(
                f"Synced with <b>{st['server']}</b> at {when}.<br>"
                f"Offset: <b>{off:+.0f} ms</b> — {verdict}.")
        elif st["error"]:
            self.lbl_sync.setText(f"Not synced yet ({st['error']}). Showing system time.")
        else:
            self.lbl_sync.setText("Waiting for the first synchronisation…")


class AlarmDialog(QDialog):
    """Create or edit one alarm."""

    def __init__(self, alarm: dict, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.setWindowTitle("Alarm")
        self.resize(420, 300)
        f = QFormLayout(self)

        self.ed_label = QLineEdit(alarm.get("label", "Alarm"))
        f.addRow("Label", self.ed_label)

        self.te = QTimeEdit()
        self.te.setDisplayFormat("HH:mm")
        try:
            hh, mm = [int(x) for x in alarm.get("time", "09:00").split(":")[:2]]
        except ValueError:
            hh, mm = 9, 0
        self.te.setTime(QTime(hh, mm))
        f.addRow("Time", self.te)

        self.cb_rep = QComboBox()
        for k, lbl in (("once", "Once"), ("daily", "Every day"),
                       ("weekdays", "Monday – Friday"), ("weekly", "Weekly")):
            self.cb_rep.addItem(lbl, k)
        i = self.cb_rep.findData(alarm.get("repeat", "daily"))
        self.cb_rep.setCurrentIndex(max(0, i))
        f.addRow("Repeat", self.cb_rep)

        self.cb_day = QComboBox()
        for i, d in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday",
                               "Friday", "Saturday", "Sunday"]):
            self.cb_day.addItem(d, i)
        self.cb_day.setCurrentIndex(int(alarm.get("weekday", 0)))
        f.addRow("Weekday", self.cb_day)

        self.cb_tz = QComboBox()
        self.cb_tz.addItem("System / local time", "")
        for z in timezones.POPULAR:
            self.cb_tz.addItem(z, z)
        i = self.cb_tz.findData(alarm.get("timezone", ""))
        self.cb_tz.setCurrentIndex(max(0, i))
        f.addRow("Time zone", self.cb_tz)

        self.cb_sound = QComboBox()
        for k in AL.SOUNDS:
            self.cb_sound.addItem(k.capitalize(), k)
        i = self.cb_sound.findData(alarm.get("sound", "chime"))
        self.cb_sound.setCurrentIndex(max(0, i))
        srow = QHBoxLayout(); srow.addWidget(self.cb_sound, 1)
        b = QPushButton("Test"); b.clicked.connect(
            lambda: AL.play_sound(self.cb_sound.currentData()))
        srow.addWidget(b)
        sw = QWidget(); sw.setLayout(srow)
        f.addRow("Sound", sw)

        self.ck_on = QCheckBox("Enabled"); self.ck_on.setChecked(bool(alarm.get("enabled", True)))
        f.addRow("", self.ck_on)
        self.ck_banner = QCheckBox("Show on-screen banner")
        self.ck_banner.setChecked(bool(alarm.get("banner", True)))
        f.addRow("", self.ck_banner)

        row = QHBoxLayout()
        ok = QPushButton("Save"); ok.clicked.connect(self._save)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        row.addStretch(1); row.addWidget(cancel); row.addWidget(ok)
        f.addRow(row)

    def _save(self) -> None:
        self.alarm.update({
            "label": self.ed_label.text() or "Alarm",
            "time": self.te.time().toString("HH:mm"),
            "repeat": self.cb_rep.currentData(),
            "weekday": self.cb_day.currentData(),
            "timezone": self.cb_tz.currentData(),
            "sound": self.cb_sound.currentData(),
            "enabled": self.ck_on.isChecked(),
            "banner": self.ck_banner.isChecked(),
            "last_fired": "",
        })
        self.accept()
