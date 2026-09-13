#!/usr/bin/env python3
"""TOUCHaDESKTOP control GUI — no terminal fiddling.

Drives the TOUCHaDESKTOP streamer directly (start/stop/restart with the chosen
flags), shows its live log with an input-line filter for keyboard diagnosis,
streams the Quest logcat on demand, and remembers settings in
~/.toucha/gui.json.

Usage:
    python3 toucha_gui.py [--smoke]   # --smoke: offscreen self-test, no display
"""
import json
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox, QSlider,
    QGroupBox, QFormLayout, QPlainTextEdit, QLineEdit, QFileDialog,
    QTabWidget, QSplitter,
)
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer
from PyQt6.QtGui import QFont, QIcon, QTextCursor

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
# Binary resolution order: sandbox install first (Flatpak /app), then the
# release folder next to this script (~/.local install), then dev paths.
def _default_binary():
    for cand in (Path("/app/bin/TOUCHaDESKTOP"),
                 HERE / "TOUCHaDESKTOP",
                 Path.home() / ".local" / "bin" / "TOUCHaDESKTOP",
                 REPO / "build" / "TOUCHaDESKTOP",
                 REPO / "build" / "toucha-streamer"):
        if cand.exists():
            return cand
    return HERE / "TOUCHaDESKTOP"
DEFAULT_BINARY = _default_binary()
CONFIG_FILE = Path.home() / ".toucha" / "gui.json"

# Release version shown in the window title (bump per release).
APP_VERSION = "0.2.5-beta"


def resolve_icon():
    """App icon: next to this script, else sandbox/native install spots."""
    for cand in (HERE / "toucha_icon.png",
                 Path("/app/share/icons/hicolor/256x256/apps/"
                      "com.toucha.Streamer.png"),
                 Path.home() / ".local" / "share" / "TOUCHaDESKTOP" /
                 "toucha_icon.png"):
        if cand.exists():
            return cand
    return HERE / "toucha_icon.png"


ICON_FILE = resolve_icon()

# Substrings shown when the "input lines only" filter is on (keyboard/input
# diagnosis without terminal scrolling).
INPUT_KEYS = ("input", "keyboard", "uinput", "xkb", "eis", "pointer=",
              "held", "watchdog", "quest", "ime")


class TouchAGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TOUCHaDESKTOP {APP_VERSION}")
        if ICON_FILE.exists():
            self.setWindowIcon(QIcon(str(ICON_FILE)))
        self.resize(1000, 900)
        self.proc = None
        self.quest_proc = None
        self.log_lines = []

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # --- binary row (always visible) ---
        bin_row = QHBoxLayout()
        bin_row.addWidget(QLabel("Streamer binary:"))
        self.binary_edit = QLineEdit(str(DEFAULT_BINARY))
        self.binary_edit.setFont(QFont("SF Mono", 11))
        bin_row.addWidget(self.binary_edit, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_binary)
        bin_row.addWidget(browse)
        layout.addLayout(bin_row)

        # --- status + buttons (always visible) ---
        top_row = QHBoxLayout()
        self.status_label = QLabel("● stopped")
        self.status_label.setFont(QFont("SF Pro Text", 14, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #86868b;")
        top_row.addWidget(self.status_label)
        self.version_label = QLabel(APP_VERSION)
        self.version_label.setFont(QFont("SF Mono", 11))
        self.version_label.setStyleSheet("color: #86868b;")
        top_row.addWidget(self.version_label)
        top_row.addStretch(1)
        self.start_btn = self._btn("Start", "#007AFF", self.start_streamer)
        self.stop_btn = self._btn("Stop", "#FF3B30", self.stop_streamer)
        self.restart_btn = self._btn("Restart", "#FF9500", self.restart_streamer)
        self.stop_btn.setEnabled(False)
        for b in (self.start_btn, self.stop_btn, self.restart_btn):
            top_row.addWidget(b)
        layout.addLayout(top_row)

        # --- tabs ---
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.page_main = QWidget()
        self.main_layout = QVBoxLayout(self.page_main)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)
        self.page_adv = QWidget()
        self.adv_layout = QVBoxLayout(self.page_adv)
        self.adv_layout.setContentsMargins(8, 8, 8, 8)
        self.adv_layout.setSpacing(8)
        self.adv_layout.addStretch(1)
        self.tabs.addTab(self.page_main, "Streamer")
        self.tabs.addTab(self.page_adv, "Advanced")

        self.build_main_page()
        self.build_adv_page()

        for w in (self.source_combo, self.audio_combo, self.codec_combo,
                  self.backend_combo, self.mode_combo, self.monitors_spin,
                  self.fps_spin, self.port_spin, self.bitrate_slider,
                  self.width_spin, self.height_spin, self.keyint_spin,
                  self.abitrate_spin, self.order_edit, self.input_chk,
                  self.disc_chk, self.hw_chk, self.dbg_chk,
                  self.noportal_chk, self.norestore_chk, self.binary_edit):
            if hasattr(w, "currentTextChanged"):
                w.currentTextChanged.connect(self.update_cmd)
            elif hasattr(w, "valueChanged"):
                w.valueChanged.connect(self.update_cmd)
            elif hasattr(w, "toggled"):
                w.toggled.connect(self.update_cmd)
            elif hasattr(w, "textChanged"):
                w.textChanged.connect(self.update_cmd)
        self.load_config()
        self.update_cmd()

    # --- main page ---
    def build_main_page(self):
        # Controls live in the splitter's top half so the log below always
        # keeps usable space (and stays user-resizable).
        top = QWidget()
        layout = QVBoxLayout(top)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        # --- presets ---
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:"))
        for name, fn in (("Test pattern", self.preset_test),
                         ("3× portal", self.preset_portal3),
                         ("Input debug", self.preset_debug)):
            b = QPushButton(name)
            b.clicked.connect(fn)
            preset_row.addWidget(b)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        # --- basic options ---
        opts = QGroupBox("Options")
        form = QFormLayout()
        form.setSpacing(8)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["portal", "test"])
        form.addRow("Source:", self.source_combo)

        self.monitors_spin = QSpinBox()
        self.monitors_spin.setRange(1, 8)
        self.monitors_spin.setValue(3)
        form.addRow("Monitors:", self.monitors_spin)

        self.audio_combo = QComboBox()
        self.audio_combo.addItems(["system", "mic", "test", "none"])
        form.addRow("Audio:", self.audio_combo)

        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["hevc", "h264"])
        form.addRow("Codec:", self.codec_combo)

        brow = QHBoxLayout()
        self.bitrate_label = QLabel("8000 kbps")
        self.bitrate_label.setFixedWidth(90)
        self.bitrate_slider = QSlider(Qt.Orientation.Horizontal)
        self.bitrate_slider.setRange(1000, 16000)
        self.bitrate_slider.setValue(8000)
        self.bitrate_slider.valueChanged.connect(
            lambda v: self.bitrate_label.setText(f"{v} kbps"))
        brow.addWidget(self.bitrate_label)
        brow.addWidget(self.bitrate_slider)
        form.addRow("Bitrate:", brow)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 120)
        self.fps_spin.setValue(72)
        form.addRow("FPS:", self.fps_spin)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8778)
        form.addRow("Port:", self.port_spin)

        flags = QHBoxLayout()
        self.input_chk = QCheckBox("Remote input")
        self.input_chk.setChecked(True)
        self.disc_chk = QCheckBox("Discovery")
        self.disc_chk.setChecked(True)
        for c in (self.input_chk, self.disc_chk):
            flags.addWidget(c)
        flags.addStretch(1)
        form.addRow("Flags:", flags)
        opts.setLayout(form)
        layout.addWidget(opts)

        # --- command preview (single line; full text in tooltip) ---
        self.cmd_label = QLabel("")
        self.cmd_label.setFont(QFont("SF Mono", 10))
        self.cmd_label.setStyleSheet("color: #86868b;")
        self.cmd_label.setWordWrap(False)
        layout.addWidget(self.cmd_label)

        # --- log tools (Quest log stays here, next to the log it fills) ---
        log_row = QHBoxLayout()
        self.quest_btn = QPushButton("Quest log")
        self.quest_btn.setCheckable(True)
        self.quest_btn.setToolTip(
            "Stream `adb logcat -s RemoteInput` from the connected Quest "
            "into this view (typing/pinch diagnostics, no terminal).")
        self.quest_btn.toggled.connect(self.toggle_quest_log)
        log_row.addWidget(self.quest_btn)
        log_row.addStretch(1)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_log)
        save_btn = QPushButton("Save log…")
        save_btn.clicked.connect(self.save_log)
        log_row.addWidget(clear_btn)
        log_row.addWidget(save_btn)
        layout.addLayout(log_row)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("SF Mono", 11))
        self.log_view.setMaximumBlockCount(5000)
        self.log_view.setMinimumHeight(220)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(top)
        self.splitter.addWidget(self.log_view)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([340, 460])
        self.main_layout.addWidget(self.splitter, 1)

    # --- advanced page ---
    def build_adv_page(self):
        layout = self.adv_layout
        adv = QGroupBox("Streamer flags")
        form = QFormLayout()
        form.setSpacing(8)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(640, 3840)
        self.width_spin.setValue(1920)
        form.addRow("Width:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(360, 2160)
        self.height_spin.setValue(1080)
        form.addRow("Height:", self.height_spin)

        self.keyint_spin = QSpinBox()
        self.keyint_spin.setRange(1, 10)
        self.keyint_spin.setValue(2)
        self.keyint_spin.setSuffix(" s")
        form.addRow("Keyframe interval:", self.keyint_spin)

        self.order_edit = QLineEdit()
        self.order_edit.setPlaceholderText("x,y;x,y;… (empty = auto sort)")
        self.order_edit.setFont(QFont("SF Mono", 11))
        form.addRow("Monitor order:", self.order_edit)

        self.abitrate_spin = QSpinBox()
        self.abitrate_spin.setRange(16, 320)
        self.abitrate_spin.setValue(96)
        self.abitrate_spin.setSuffix(" kbps")
        form.addRow("Audio bitrate:", self.abitrate_spin)

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["auto", "uinput", "portal"])
        form.addRow("Input backend:", self.backend_combo)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["physical", "virtual"])
        form.addRow("Monitor mode:", self.mode_combo)

        advflags = QHBoxLayout()
        self.hw_chk = QCheckBox("Software encode")
        self.noportal_chk = QCheckBox("No portal input")
        self.norestore_chk = QCheckBox("No restore")
        for c in (self.hw_chk, self.noportal_chk, self.norestore_chk):
            advflags.addWidget(c)
        advflags.addStretch(1)
        form.addRow("Flags:", advflags)
        adv.setLayout(form)
        # Insert before the bottom stretch.
        layout.insertWidget(0, adv)

        dbg = QGroupBox("Debug")
        dform = QFormLayout()
        dform.setSpacing(8)
        self.dbg_chk = QCheckBox("Input debug (TOUCHA_INPUT_DEBUG=1)")
        dform.addRow("", self.dbg_chk)
        self.filter_chk = QCheckBox("Input lines only")
        self.filter_chk.setToolTip(
            "Show only input/keyboard lines in the Streamer tab's log view.")
        self.filter_chk.toggled.connect(self.refresh_log_view)
        dform.addRow("", self.filter_chk)
        dbg.setLayout(dform)
        layout.insertWidget(1, dbg)

    # --- helpers ---
    @staticmethod
    def _btn(text, color, slot):
        b = QPushButton(text)
        b.setFixedHeight(38)
        b.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: white; "
            "border: none; border-radius: 8px; padding: 8px; }}")
        b.clicked.connect(slot)
        return b

    def browse_binary(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "TOUCHaDESKTOP binary", str(HERE))
        if path:
            self.binary_edit.setText(path)

    def build_argv(self):
        argv = [self.binary_edit.text().strip(),
                "--source", self.source_combo.currentText(),
                "--monitors", str(self.monitors_spin.value()),
                "--audio", self.audio_combo.currentText(),
                "--codec", self.codec_combo.currentText(),
                "--bitrate", str(self.bitrate_slider.value()),
                "--fps", str(self.fps_spin.value()),
                "--port", str(self.port_spin.value()),
                "--width", str(self.width_spin.value()),
                "--height", str(self.height_spin.value()),
                "--keyint", str(self.keyint_spin.value()),
                "--audio-bitrate", str(self.abitrate_spin.value()),
                "--input-backend", self.backend_combo.currentText(),
                "--monitor-mode", self.mode_combo.currentText()]
        if self.order_edit.text().strip():
            argv += ["--monitor-order", self.order_edit.text().strip()]
        if not self.input_chk.isChecked():
            argv.append("--no-input")
        if not self.disc_chk.isChecked():
            argv.append("--no-discovery")
        if self.hw_chk.isChecked():
            argv.append("--no-hw")
        if self.noportal_chk.isChecked():
            argv.append("--no-portal-input")
        if self.norestore_chk.isChecked():
            argv.append("--no-restore")
        return argv

    def update_cmd(self, *a):
        cmd = "$ " + " ".join(self.build_argv())
        self.cmd_label.setText(cmd)
        self.cmd_label.setToolTip(cmd)
        self.save_config()

    # --- presets ---
    def _apply(self, **kw):
        if "source" in kw:
            self.source_combo.setCurrentText(kw["source"])
        if "monitors" in kw:
            self.monitors_spin.setValue(kw["monitors"])
        if "audio" in kw:
            self.audio_combo.setCurrentText(kw["audio"])
        if "codec" in kw:
            self.codec_combo.setCurrentText(kw["codec"])
        if "fps" in kw:
            self.fps_spin.setValue(kw["fps"])
        if "port" in kw:
            self.port_spin.setValue(kw["port"])
        if "hw" in kw:
            self.hw_chk.setChecked(kw["hw"])
        if "dbg" in kw:
            self.dbg_chk.setChecked(kw["dbg"])
        self.update_cmd()

    def preset_test(self):
        self._apply(source="test", monitors=1, audio="none", codec="h264",
                    fps=30, port=17878, hw=True, dbg=False)

    def preset_portal3(self):
        self._apply(source="portal", monitors=3, audio="system",
                    codec="hevc", fps=72, port=8778, hw=False, dbg=False)

    def preset_debug(self):
        self._apply(source="portal", monitors=1, audio="system",
                    codec="hevc", fps=72, port=8778, hw=False, dbg=True)

    # --- process ---
    def start_streamer(self):
        if self.proc is not None:
            return
        binary = self.binary_edit.text().strip()
        if not (binary and os.path.isfile(binary) and os.access(binary, os.X_OK)):
            self.append_log("[gui] not executable: " + binary + " (run `make streamer` first)")
            return
        argv = self.build_argv()
        self.append_log("[gui] $ " + " ".join(argv))
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self.on_output)
        self.proc.readyReadStandardError.connect(self.on_output)
        self.proc.finished.connect(self.on_finished)
        env = QProcessEnvironment.systemEnvironment()
        if self.dbg_chk.isChecked():
            env.insert("TOUCHA_INPUT_DEBUG", "1")
        self.proc.setProcessEnvironment(env)
        self.proc.setProgram(argv[0])
        self.proc.setArguments(argv[1:])
        self.proc.start()
        if not self.proc.waitForStarted(5000):
            self.append_log("[gui] failed to start process")
            self.proc = None
            return
        self.set_status("running", "#34C759")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_streamer(self):
        if self.proc is None:
            return
        self.append_log("[gui] stopping…")
        self.proc.terminate()
        if not self.proc.waitForFinished(3000):
            self.proc.kill()

    def restart_streamer(self):
        self.stop_streamer()
        QTimer.singleShot(500, self.start_streamer)

    def on_output(self):
        if self.proc is None:
            return
        data = bytes(self.proc.readAllStandardOutput()).decode(
            "utf-8", "replace")
        data += bytes(self.proc.readAllStandardError()).decode(
            "utf-8", "replace")
        for line in data.splitlines():
            self.append_log(line.rstrip())

    def on_finished(self, code, status):
        self.append_log(f"[gui] exited with code {code}")
        self.proc = None
        self.set_status("stopped", "#86868b")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def set_status(self, text, color):
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(f"color: {color};")

    # --- Quest device log (adb logcat, no terminal) ---
    def toggle_quest_log(self, on):
        if on:
            self.start_quest_log()
        else:
            self.stop_quest_log()

    def start_quest_log(self):
        if self.quest_proc is not None:
            return
        import shutil
        import subprocess
        if shutil.which("adb") is None:
            self.append_log("[gui] adb not found on PATH — cannot read Quest log")
            self.quest_btn.setChecked(False)
            return
        try:
            devs = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True,
                timeout=10)
        except Exception as e:
            self.append_log(f"[gui] adb devices failed: {e}")
            self.quest_btn.setChecked(False)
            return
        # Device lines look like "<serial>\tdevice"; the header + offline /
        # unauthorized entries don't count.
        attached = [l for l in devs.stdout.splitlines()[1:]
                    if l.strip().endswith("\tdevice")]
        if not attached:
            self.append_log("[gui] no Quest device attached (adb devices empty)")
            self.quest_btn.setChecked(False)
            return
        self.append_log(f"[gui] Quest log streaming ({len(attached)} device(s))…")
        self.quest_proc = QProcess(self)
        self.quest_proc.readyReadStandardOutput.connect(self.on_quest_output)
        self.quest_proc.finished.connect(self.on_quest_finished)
        self.quest_proc.setProgram("adb")
        self.quest_proc.setArguments(["logcat", "-s", "RemoteInput"])
        self.quest_proc.start()

    def stop_quest_log(self):
        qp, self.quest_proc = self.quest_proc, None
        if qp is not None:
            qp.terminate()
            if not qp.waitForFinished(2000):
                qp.kill()
        if self.quest_btn.isChecked():
            self.quest_btn.setChecked(False)

    def on_quest_output(self):
        if self.quest_proc is None:
            return
        data = bytes(self.quest_proc.readAllStandardOutput()).decode(
            "utf-8", "replace")
        for line in data.splitlines():
            self.append_log("[quest] " + line.rstrip())

    def on_quest_finished(self, code, status):
        self.append_log(f"[gui] Quest log stopped (code {code})")
        self.quest_proc = None
        if self.quest_btn.isChecked():
            self.quest_btn.setChecked(False)

    def closeEvent(self, event):
        self.stop_quest_log()
        if self.proc is not None:
            self.stop_streamer()
            self.proc.waitForFinished(3000)
        super().closeEvent(event)

    # --- log ---
    def append_log(self, line):
        self.log_lines.append(line)
        if len(self.log_lines) > 8000:
            del self.log_lines[:1000]
        if self.passes_filter(line):
            self.log_view.appendPlainText(line)

    def passes_filter(self, line):
        if not self.filter_chk.isChecked():
            return True
        if line.startswith("[gui]"):
            return True
        low = line.lower()
        return any(k in low for k in INPUT_KEYS)

    def refresh_log_view(self):
        self.log_view.clear()
        for line in self.log_lines[-2000:]:
            if self.passes_filter(line):
                self.log_view.appendPlainText(line)

    def clear_log(self):
        self.log_lines.clear()
        self.log_view.clear()

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save streamer log", str(Path.home() / "TOUCHaDESKTOP.log"),
            "Log files (*.log);;All files (*)")
        if path:
            with open(path, "w") as f:
                f.write("\n".join(self.log_lines) + "\n")
            self.append_log(f"[gui] log saved to {path}")

    # --- config ---
    def save_config(self):
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump({
                    "binary": self.binary_edit.text(),
                    "source": self.source_combo.currentText(),
                    "monitors": self.monitors_spin.value(),
                    "audio": self.audio_combo.currentText(),
                    "codec": self.codec_combo.currentText(),
                    "bitrate": self.bitrate_slider.value(),
                    "fps": self.fps_spin.value(),
                    "port": self.port_spin.value(),
                    "input": self.input_chk.isChecked(),
                    "discovery": self.disc_chk.isChecked(),
                    "sw": self.hw_chk.isChecked(),
                    "dbg": self.dbg_chk.isChecked(),
                    "width": self.width_spin.value(),
                    "height": self.height_spin.value(),
                    "keyint": self.keyint_spin.value(),
                    "order": self.order_edit.text(),
                    "abitrate": self.abitrate_spin.value(),
                    "backend": self.backend_combo.currentText(),
                    "mode": self.mode_combo.currentText(),
                    "noportal": self.noportal_chk.isChecked(),
                    "norestore": self.norestore_chk.isChecked(),
                    "filter": self.filter_chk.isChecked(),
                    "split": list(self.splitter.sizes()),
                }, f, indent=2)
        except OSError:
            pass

    def load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                c = json.load(f)
        except (OSError, ValueError):
            return
        self.binary_edit.setText(c.get("binary", str(DEFAULT_BINARY)))
        self.source_combo.setCurrentText(c.get("source", "portal"))
        self.monitors_spin.setValue(c.get("monitors", 3))
        self.audio_combo.setCurrentText(c.get("audio", "system"))
        self.codec_combo.setCurrentText(c.get("codec", "hevc"))
        self.bitrate_slider.setValue(c.get("bitrate", 8000))
        self.fps_spin.setValue(c.get("fps", 72))
        self.port_spin.setValue(c.get("port", 8778))
        self.input_chk.setChecked(c.get("input", True))
        self.disc_chk.setChecked(c.get("discovery", True))
        self.hw_chk.setChecked(c.get("sw", False))
        self.dbg_chk.setChecked(c.get("dbg", False))
        self.width_spin.setValue(c.get("width", 1920))
        self.height_spin.setValue(c.get("height", 1080))
        self.keyint_spin.setValue(c.get("keyint", 2))
        self.order_edit.setText(c.get("order", ""))
        self.abitrate_spin.setValue(c.get("abitrate", 96))
        self.backend_combo.setCurrentText(c.get("backend", "auto"))
        self.mode_combo.setCurrentText(c.get("mode", "physical"))
        self.noportal_chk.setChecked(c.get("noportal", False))
        self.norestore_chk.setChecked(c.get("norestore", False))
        self.filter_chk.setChecked(c.get("filter", False))
        split = c.get("split")
        if (isinstance(split, list) and len(split) == 2 and
                all(isinstance(v, int) and v > 0 for v in split)):
            self.splitter.setSizes(split)


def run_smoke(app):
    """Offscreen self-test: boot the window, run the test preset, check the
    log flows, stop; exercise the Advanced tab argv. Prints SMOKE_OK or
    raises. Takes the existing QApplication (creating a second one hangs)."""
    import time
    w = TouchAGui()
    assert w.tabs.count() == 2, "expected Streamer + Advanced tabs"
    assert APP_VERSION and APP_VERSION in w.windowTitle(), w.windowTitle()
    assert w.version_label.text() == APP_VERSION
    assert ICON_FILE.exists(), f"app icon missing: {ICON_FILE}"
    assert not QIcon(str(ICON_FILE)).isNull(), "app icon failed to load"
    w.show()
    app.processEvents()
    assert w.log_view.viewport().height() > 150, \
        f"log view squeezed: {w.log_view.viewport().height()}px"
    w.preset_test()
    assert "--source" in w.cmd_label.text() and "test" in w.cmd_label.text()
    # Advanced tab: flip an advanced flag, check argv + config round-trip.
    w.tabs.setCurrentIndex(1)
    app.processEvents()
    w.width_spin.setValue(1280)
    w.noportal_chk.setChecked(True)
    assert "--width 1280" in w.cmd_label.text(), w.cmd_label.text()
    assert "--no-portal-input" in w.cmd_label.text(), w.cmd_label.text()
    w.filter_chk.setChecked(True)
    assert w.passes_filter("[toucha][monitor 0] INPUT k 99 1")
    assert not w.passes_filter("[toucha][encoder] x264 ready")
    w.tabs.setCurrentIndex(0)
    w.start_streamer()
    assert w.proc is not None, "process did not start"
    deadline = time.time() + 25
    while time.time() < deadline:
        app.processEvents()
        if any("capture" in l for l in w.log_lines):
            break
        time.sleep(0.2)
    assert any("capture" in l for l in w.log_lines), \
        f"no capture line in log: {w.log_lines[-5:]}"
    assert any("toucha" in l for l in w.log_lines), "no toucha log output"
    w.stop_streamer()
    deadline = time.time() + 10
    while w.proc is not None and time.time() < deadline:
        app.processEvents()
        time.sleep(0.2)
    assert w.proc is None, "process did not stop"
    # Quest log without a device must degrade gracefully (no adb device here).
    w.quest_btn.setChecked(True)
    deadline = time.time() + 15
    while w.quest_proc is not None and time.time() < deadline:
        app.processEvents()
        time.sleep(0.2)
    assert w.quest_proc is None, "quest log should not run without a device"
    assert any("no Quest device" in l or "adb" in l for l in w.log_lines), \
        f"no graceful quest-log message: {w.log_lines[-5:]}"
    print("SMOKE_OK")
    return 0


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if "--smoke" in sys.argv:
        return run_smoke(app)
    window = TouchAGui()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
