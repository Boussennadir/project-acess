# ============================================================
# login_window.py — Login Screen & User Profile Portal
# University Identity Management System
# ============================================================

import sys
from datetime import datetime
import secrets
from datetime import timedelta

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QDialog, QGridLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QProgressBar, QComboBox,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QPixmap

from auth import (
    authenticate, change_password, get_login_history,
    analyze_password_strength, validate_password_policy,
    get_person_for_user, get_user_specific_data,
    request_sms_otp, verify_sms_otp, mark_mfa_used,
    totp_is_enabled, totp_begin_enroll, totp_verify_and_enable, totp_verify,
    secq_is_configured, secq_get_questions, secq_verify, secq_set, SECURITY_QUESTION_POOL,
    request_password_reset, reset_password_with_token,
)
from utils import TYPE_LABELS
import qrcode
from io import BytesIO

# ── Colors (match app.py theme) ─────────────────────────────
BG = "#0f0f0f"; BG2 = "#1a1a1a"; BG3 = "#252525"; BORDER = "#3a3a3a"
TEXT = "#f5f5f5"; TEXT2 = "#a0a0a0"; ORANGE = "#ff8c42"; ORANGE_DIM = "#d96d2e"
GREEN = "#66bb6a"; RED = "#e74c3c"; PURPLE = "#9b59b6"; BLUE = "#3498db"

STATUS_CLR = {"Pending": ORANGE, "Active": GREEN, "Suspended": RED, "Inactive": TEXT2, "Archived": "#505050"}


def sep():
    f = QFrame(); f.setObjectName("sep"); f.setFrameShape(QFrame.Shape.HLine); return f


def flbl(t):
    l = QLabel(t)
    l.setStyleSheet(f"color:{ORANGE};font-size:11px;font-weight:700;margin-bottom:2px;letter-spacing:1px;text-transform:uppercase;")
    return l


def errlbl():
    l = QLabel(""); l.setStyleSheet(f"color:{RED};font-size:11px;"); return l


def fw(label, widget, err=None):
    w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)
    v.addWidget(flbl(label)); v.addWidget(widget)
    if err: v.addWidget(err)
    return w


def mkbtn(text, obj="btn_p"):
    b = QPushButton(text); b.setObjectName(obj); b.setCursor(Qt.CursorShape.PointingHandCursor); return b


# ── Password Strength Widget ─────────────────────────────────
class PasswordStrengthBar(QWidget):
    def __init__(self):
        super().__init__()
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 4, 0, 0); vl.setSpacing(3)

        bar_row = QHBoxLayout(); bar_row.setSpacing(4)
        self._bars = []
        for _ in range(4):
            seg = QFrame()
            seg.setFixedHeight(5)
            seg.setStyleSheet(f"background:{BORDER};border-radius:2px;")
            bar_row.addWidget(seg)
            self._bars.append(seg)
        vl.addLayout(bar_row)

        self._lbl = QLabel("")
        self._lbl.setStyleSheet(f"font-size:11px;color:{TEXT2};")
        vl.addWidget(self._lbl)

        self._tip = QLabel("")
        self._tip.setStyleSheet(f"font-size:10px;color:{TEXT2};")
        self._tip.setWordWrap(True)
        vl.addWidget(self._tip)

    def update_strength(self, password: str):
        if not password:
            for b in self._bars:
                b.setStyleSheet(f"background:{BORDER};border-radius:2px;")
            self._lbl.setText(""); self._tip.setText(""); return

        info = analyze_password_strength(password)
        score = info["score"]
        color = info["color"]

        for i, b in enumerate(self._bars):
            if i < score:
                b.setStyleSheet(f"background:{color};border-radius:2px;")
            else:
                b.setStyleSheet(f"background:{BORDER};border-radius:2px;")

        self._lbl.setText(f"  Strength: {info['label']}")
        self._lbl.setStyleSheet(f"font-size:11px;color:{color};font-weight:700;")
        if info["tips"]:
            self._tip.setText("  💡 " + " · ".join(info["tips"]))
        else:
            self._tip.setText("  ✓ Strong password!")
            self._tip.setStyleSheet(f"font-size:10px;color:{GREEN};")


# ── Login Window ─────────────────────────────────────────────
class LoginWindow(QWidget):
    login_success_admin = pyqtSignal(dict)
    login_success_user = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("IAM — University of Batna 2  ·  Login")
        # Was fixed 480x600, but MFA panel can be clipped on smaller windows/DPI.
        # Keep a reasonable minimum, allow resize, and grow when MFA is shown.
        # Full version uses a 2-column layout (Login + MFA) so we need more width.
        self.setMinimumSize(980, 640)
        self.resize(1040, 720)
        self._pending_user = None
        self._pending_session_id = None
        self._mfa_stage = None  # "otp" | "totp" | "secq"
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        # Top bar
        top = QWidget(); top.setFixedHeight(8)
        top.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ORANGE_DIM},stop:1 {ORANGE});")
        vl.addWidget(top)

        # Center card
        center = QWidget(); center.setStyleSheet(f"background:{BG};")
        cv = QVBoxLayout(center); cv.setContentsMargins(56, 36, 56, 36); cv.setSpacing(0)

        # Logo
        logo = QLabel("🎓")
        logo.setStyleSheet("font-size:48px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(logo)

        title = QLabel("IAM System")
        title.setStyleSheet(f"font-size:22px;font-weight:700;color:{ORANGE};letter-spacing:2px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(title)

        uni = QLabel("University of Batna 2")
        uni.setStyleSheet(f"font-size:11px;color:{TEXT2};letter-spacing:3px;")
        uni.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(uni)

        cv.addSpacing(32)
        cv.addWidget(sep())
        cv.addSpacing(28)

        # Body: 2 columns (Login left, Welcome/MFA right)
        body = QWidget()
        br = QHBoxLayout(body)
        br.setContentsMargins(0, 0, 0, 0)
        br.setSpacing(22)

        # ── Left column: Login form ──────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)

        self._username = QLineEdit()
        self._username.setPlaceholderText("username or university ID")
        self._username.setMinimumHeight(48)
        lv.addWidget(flbl("Username"))
        lv.addWidget(self._username)
        lv.addSpacing(16)

        pw_row = QHBoxLayout(); pw_row.setSpacing(0)
        self._password = QLineEdit()
        self._password.setPlaceholderText("password")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setMinimumHeight(48)
        self._password.returnPressed.connect(self._do_login)

        self._show_pw = QPushButton("👁")
        self._show_pw.setFixedSize(48, 48)
        self._show_pw.setStyleSheet(f"background:{BG3};border:1px solid {BORDER};color:{TEXT2};border-radius:0 3px 3px 0;")
        self._show_pw.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_pw.setCheckable(True)
        self._show_pw.toggled.connect(self._toggle_pw)
        pw_row.addWidget(self._password); pw_row.addWidget(self._show_pw)

        lv.addWidget(flbl("Password"))
        pw_w = QWidget(); pw_w.setLayout(pw_row); lv.addWidget(pw_w)
        lv.addSpacing(6)

        self._err = QLabel("")
        self._err.setStyleSheet(f"color:{RED};font-size:12px;font-weight:600;")
        self._err.setWordWrap(True)
        self._err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.addWidget(self._err)
        lv.addSpacing(20)

        btn = mkbtn("Log-in")
        btn.setMinimumHeight(54)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{ORANGE};color:{BG};border:none;border-radius:4px;
                font-size:14px;font-weight:700;letter-spacing:1px;
            }}
            QPushButton:hover {{ background:{ORANGE_DIM}; }}
        """)
        btn.clicked.connect(self._do_login)
        self._login_btn = btn
        lv.addWidget(btn)

        fp = QPushButton("Forgot password?")
        fp.setCursor(Qt.CursorShape.PointingHandCursor)
        fp.setStyleSheet(f"background:transparent;border:none;color:{TEXT2};font-size:11px;text-decoration: underline;")
        fp.clicked.connect(self._forgot_password)
        lv.addSpacing(10)
        lv.addWidget(fp, alignment=Qt.AlignmentFlag.AlignCenter)

        lv.addStretch()

        # ── Right column: Welcome/MFA stack ───────────────────
        self._right_stack = QStackedWidget()
        self._right_stack.setMinimumWidth(420)
        self._right_stack.setStyleSheet("QStackedWidget { background: transparent; }")

        # Welcome panel (default)
        # Blend with the main background (no border, no different background).
        welcome = QWidget()
        welcome.setStyleSheet("background:transparent;border:none;")
        wv = QVBoxLayout(welcome)
        wv.setContentsMargins(22, 22, 22, 22)
        wv.setSpacing(12)

        w_title = QLabel("Welcome")
        w_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_title.setStyleSheet(
            f"background:transparent;border:none;"
            f"font-size:34px;font-weight:900;color:{ORANGE};letter-spacing:2px;"
        )

        w_msg = QLabel(
            "Welcome back! Please log in to access your account and continue to the system."
        )
        w_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_msg.setWordWrap(True)
        w_msg.setStyleSheet(
            f"background:transparent;border:none;"
            f"color:{TEXT2};font-size:12px;line-height:1.35;"
        )

        wv.addStretch()
        wv.addWidget(w_title)
        wv.addWidget(w_msg)
        wv.addStretch()
        self._right_stack.addWidget(welcome)  # index 0

        # ── MFA panel (shown after Sign In) ───────────────────
        self._mfa_box = QWidget()
        # Let it expand with window (bigger, clearer)
        self._mfa_box.setMinimumWidth(420)
        self._mfa_box.setStyleSheet(f"background:{BG2};border:1px solid {BORDER};border-radius:4px;padding:10px;")
        mvl = QVBoxLayout(self._mfa_box); mvl.setContentsMargins(10, 10, 10, 10); mvl.setSpacing(8)

        self._mfa_title = QLabel("🔐 MFA Verification")
        self._mfa_title.setStyleSheet(f"color:{ORANGE};font-size:12px;font-weight:700;")
        mvl.addWidget(self._mfa_title)

        self._mfa_hint = QLabel("")
        self._mfa_hint.setStyleSheet(f"color:{TEXT2};font-size:11px;")
        self._mfa_hint.setWordWrap(True)
        # Allow copying demo codes (e.g., "Demo SMS: 12345678")
        self._mfa_hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mvl.addWidget(self._mfa_hint)

        # Security questions setup (only shown if L4 needs it and it's not configured yet)
        # Keep this compact (no huge stacked widgets).
        self._secq_setup = QWidget()
        sqg = QGridLayout(self._secq_setup)
        sqg.setContentsMargins(0, 0, 0, 0)
        sqg.setHorizontalSpacing(10)
        sqg.setVerticalSpacing(8)

        self._sq_q1 = QComboBox(); self._sq_q1.addItems(SECURITY_QUESTION_POOL); self._sq_q1.setMinimumHeight(36)
        self._sq_a1 = QLineEdit(); self._sq_a1.setPlaceholderText("Answer 1"); self._sq_a1.setMinimumHeight(36)
        self._sq_q2 = QComboBox(); self._sq_q2.addItems(SECURITY_QUESTION_POOL); self._sq_q2.setMinimumHeight(36)
        self._sq_a2 = QLineEdit(); self._sq_a2.setPlaceholderText("Answer 2"); self._sq_a2.setMinimumHeight(36)
        self._sq_err = QLabel(""); self._sq_err.setStyleSheet(f"color:{RED};font-size:11px;font-weight:600;"); self._sq_err.setWordWrap(True)
        self._sq_save = mkbtn("Save questions", "btn_s"); self._sq_save.setMinimumHeight(40)

        sqg.addWidget(flbl("Question 1"), 0, 0)
        sqg.addWidget(self._sq_q1,         0, 1)
        sqg.addWidget(flbl("Answer 1"),    1, 0)
        sqg.addWidget(self._sq_a1,         1, 1)
        sqg.addWidget(flbl("Question 2"),  2, 0)
        sqg.addWidget(self._sq_q2,         2, 1)
        sqg.addWidget(flbl("Answer 2"),    3, 0)
        sqg.addWidget(self._sq_a2,         3, 1)
        sqg.addWidget(self._sq_err,        4, 0, 1, 2)
        sqg.addWidget(self._sq_save,       5, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)

        self._secq_setup.hide()
        mvl.addWidget(self._secq_setup)

        code_row = QHBoxLayout(); code_row.setSpacing(8)
        self._code_in = QLineEdit()
        self._code_in.setPlaceholderText("Enter code")
        self._code_in.setMinimumHeight(46)
        self._code_in.returnPressed.connect(self._verify_mfa)
        code_row.addWidget(self._code_in, 2)

        self._code_verify_btn = mkbtn("Verify", "btn_g")
        self._code_verify_btn.setMinimumHeight(46)
        self._code_verify_btn.clicked.connect(self._verify_mfa)
        code_row.addWidget(self._code_verify_btn, 1)
        mvl.addLayout(code_row)

        self._qr_lbl = QLabel("")
        self._qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_lbl.hide()
        mvl.addWidget(self._qr_lbl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        self._otp_resend_btn = mkbtn("Resend code", "btn_s")
        self._otp_resend_btn.clicked.connect(self._resend_otp)
        self._otp_cancel_btn = mkbtn("Cancel", "btn_s")
        self._otp_cancel_btn.clicked.connect(self._cancel_mfa)
        self._otp_resend_btn.setMinimumHeight(42)
        self._otp_cancel_btn.setMinimumHeight(42)
        btn_row.addWidget(self._otp_resend_btn)
        btn_row.addWidget(self._otp_cancel_btn)
        btn_row.addStretch()
        mvl.addLayout(btn_row)

        self._mfa_err = QLabel("")
        self._mfa_err.setStyleSheet(f"color:{RED};font-size:11px;font-weight:600;")
        self._mfa_err.setWordWrap(True)
        mvl.addWidget(self._mfa_err)

        self._right_stack.addWidget(self._mfa_box)  # index 1
        self._right_stack.setCurrentIndex(0)

        # Make both columns large and balanced
        br.addWidget(left, 1)
        br.addWidget(self._right_stack, 1)
        cv.addWidget(body)

        cv.addStretch()

        # Hint
        hint = QLabel("Admin login grants full access · Users see their personal profile")
        hint.setStyleSheet(f"color:#404040;font-size:10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(hint)

        vl.addWidget(center)

    def _toggle_pw(self, checked):
        self._password.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _do_login(self):
        if self._pending_user:
            # If user is already at MFA step, treat "Sign In" as no-op.
            return
        username = self._username.text().strip()
        password = self._password.text()
        self._err.setText("")

        if not username or not password:
            self._err.setText("Please enter your username and password.")
            return

        result = authenticate(username, password)
        if result["ok"]:
            user = result["user"]
            auth_level = int(user.get("auth_level") or 1)

            # Force password change on first login
            if int(user.get("must_change_pw") or 0) == 1:
                user_data = dict(user)
                p = get_person_for_user(user)
                if p:
                    user_data["first_name"] = p.get("first_name", "")
                    user_data["last_name"] = p.get("last_name", "")
                dlg = ChangePasswordDialog(user_data, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    self._password.clear()
                    return

            # MFA by level
            if auth_level >= 2:
                self._start_mfa(user)
            else:
                if user["role"] == "admin":
                    self.login_success_admin.emit(user)
                else:
                    self.login_success_user.emit(user)
                self._password.clear()
        else:
            self._err.setText(result["error"])
            self._password.clear()
            if result["locked"]:
                self._err.setStyleSheet(f"color:{RED};font-size:12px;font-weight:600;")

    def _start_mfa(self, user: dict):
        # Lock down primary inputs during MFA
        self._pending_user = user
        self._pending_session_id = user.get("session_id")
        self._mfa_stage = "otp"
        self._username.setEnabled(False)
        self._password.setEnabled(False)
        self._show_pw.setEnabled(False)
        self._login_btn.setEnabled(False)

        self._mfa_err.setText("")
        self._code_in.clear()
        self._qr_lbl.clear()
        self._qr_lbl.hide()
        if hasattr(self, "_right_stack"):
            self._right_stack.setCurrentIndex(1)
        self._begin_otp()
        self._code_in.setFocus()
        # Ensure MFA block is visible without manual resize.
        self._ensure_mfa_visible()

    def _ensure_mfa_visible(self):
        # If current height is too small to show the MFA panel cleanly, grow it.
        try:
            target_h = max(self.height(), 760)
            if self.height() < target_h:
                self.resize(self.width(), target_h)
        except Exception:
            pass

    def _begin_otp(self):
        ok, res = request_sms_otp(self._pending_user["id"])
        if not ok:
            self._mfa_title.setText("🔐 MFA — Email OTP")
            self._mfa_hint.setText("OTP required (L2+).")
            self._mfa_err.setText(res)
            return
        lvl = int(self._pending_user.get("auth_level") or 1)
        if lvl >= 4:
            self._mfa_title.setText("🔐 MFA Step 1/3 — Email OTP")
        elif lvl >= 3:
            self._mfa_title.setText("🔐 MFA Step 1/2 — Email OTP")
        else:
            self._mfa_title.setText("🔐 MFA — Email OTP")
        self._mfa_hint.setText(f"Enter 8-digit code (sent to: {res})")
        self._code_in.setMaxLength(8)
        self._code_in.setPlaceholderText("Enter 8-digit OTP")
        self._mfa_stage = "otp"

    def _resend_otp(self):
        if not self._pending_user:
            return
        self._mfa_err.setText("")
        if self._mfa_stage == "otp":
            self._begin_otp()

    def _cancel_mfa(self):
        # Reset UI back to normal login mode
        self._pending_user = None
        self._pending_session_id = None
        self._mfa_stage = None
        self._mfa_err.setText("")
        self._code_in.clear()
        self._code_in.show()
        self._code_verify_btn.show()
        self._otp_resend_btn.show()
        if hasattr(self, "_secq_setup"):
            self._secq_setup.hide()
        self._qr_lbl.clear()
        self._qr_lbl.hide()
        if hasattr(self, "_right_stack"):
            self._right_stack.setCurrentIndex(0)
        self._username.setEnabled(True)
        self._password.setEnabled(True)
        self._show_pw.setEnabled(True)
        self._login_btn.setEnabled(True)
        self._password.clear()
        self._password.setFocus()

    def _verify_mfa(self):
        if not self._pending_user:
            return
        lvl = int(self._pending_user.get("auth_level") or 1)
        code = (self._code_in.text() or "").strip()
        self._mfa_err.setText("")

        if self._mfa_stage == "otp":
            ok, err = verify_sms_otp(self._pending_user["id"], code)
            if not ok:
                self._mfa_err.setText(err)
                return
            if lvl >= 3:
                # TOTP stage
                if not totp_is_enabled(self._pending_user["id"]):
                    ok2, info = totp_begin_enroll(self._pending_user["id"])
                    if ok2:
                        qr = qrcode.QRCode(box_size=8, border=2)
                        qr.add_data(info["otpauth_uri"])
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        buf = BytesIO()
                        img.save(buf, format="PNG")
                        qimg = QImage.fromData(buf.getvalue(), "PNG")
                        self._qr_lbl.setPixmap(QPixmap.fromImage(qimg).scaledToWidth(260, Qt.TransformationMode.FastTransformation))
                        self._qr_lbl.show()
                self._mfa_title.setText("🔐 MFA Step 2/3 — TOTP" if lvl >= 4 else "🔐 MFA Step 2/2 — TOTP")
                self._mfa_hint.setText("Enter your 6-digit Authenticator code (TOTP).")
                self._code_in.clear()
                self._code_in.setMaxLength(6)
                self._code_in.setPlaceholderText("Enter 6-digit TOTP")
                self._mfa_stage = "totp"
                return

            # L2 success
            mark_mfa_used(self._pending_session_id)
            user = self._pending_user
            self._cancel_mfa()
            (self.login_success_admin if user.get("role") == "admin" else self.login_success_user).emit(user)
            return

        if self._mfa_stage == "totp":
            if not totp_is_enabled(self._pending_user["id"]):
                ok, res = totp_verify_and_enable(self._pending_user["id"], code)
                if not ok:
                    self._mfa_err.setText(res)
                    return
                bcodes = (res or {}).get("backup_codes") if isinstance(res, dict) else None
                if bcodes:
                    QMessageBox.information(self, "Backup codes", "Save these 10 backup codes (shown once):\n\n" + "\n".join(bcodes))
            else:
                ok, err = totp_verify(self._pending_user["id"], code)
                if not ok:
                    self._mfa_err.setText(err)
                    return

            if lvl >= 4:
                if not secq_is_configured(self._pending_user["id"]):
                    # Inline setup (admin accounts don't have a user Security tab)
                    self._mfa_title.setText("🔐 MFA Step 3/3 — Setup Security Questions")
                    self._mfa_hint.setText("Choose 2 questions and set answers (required for L4).")
                    self._qr_lbl.hide()
                    self._code_in.hide()
                    self._code_verify_btn.hide()
                    self._otp_resend_btn.hide()
                    self._secq_setup.show()
                    self._sq_err.setText("")

                    def do_save():
                        self._sq_err.setText("")
                        ok_s, err_s = secq_set(
                            self._pending_user["id"],
                            self._sq_q1.currentText(), self._sq_a1.text(),
                            self._sq_q2.currentText(), self._sq_a2.text(),
                        )
                        if not ok_s:
                            self._sq_err.setText(err_s or "Failed.")
                            return
                        # Verify immediately using the same answers to finish MFA
                        ok_v, err_v = secq_verify(self._pending_user["id"], self._sq_a1.text(), self._sq_a2.text())
                        if not ok_v:
                            self._sq_err.setText(err_v or "Verification failed.")
                            return
                        mark_mfa_used(self._pending_session_id)
                        user = self._pending_user
                        self._cancel_mfa()
                        (self.login_success_admin if user.get("role") == "admin" else self.login_success_user).emit(user)

                    try:
                        self._sq_save.clicked.disconnect()
                    except Exception:
                        pass
                    self._sq_save.clicked.connect(do_save)
                    return
                okq, qs = secq_get_questions(self._pending_user["id"])
                if not okq:
                    self._mfa_err.setText("Security questions not configured.")
                    return
                self._qr_lbl.hide()
                self._mfa_title.setText("🔐 MFA Step 3/3 — Security Questions")
                self._mfa_hint.setText(f"Answer both:\n1) {qs['q1']}\n2) {qs['q2']}")
                self._code_in.clear()
                self._code_in.setPlaceholderText("Answer 1 | Answer 2")
                self._code_in.setMaxLength(256)
                self._mfa_stage = "secq"
                return

            # L3 success
            mark_mfa_used(self._pending_session_id)
            user = self._pending_user
            self._cancel_mfa()
            (self.login_success_admin if user.get("role") == "admin" else self.login_success_user).emit(user)
            return

        if self._mfa_stage == "secq":
            if "|" not in code:
                self._mfa_err.setText("Format: Answer1 | Answer2")
                return
            a1, a2 = [x.strip() for x in code.split("|", 1)]
            ok, err = secq_verify(self._pending_user["id"], a1, a2)
            if not ok:
                self._mfa_err.setText(err)
                return
            mark_mfa_used(self._pending_session_id)
            user = self._pending_user
            self._cancel_mfa()
            (self.login_success_admin if user.get("role") == "admin" else self.login_success_user).emit(user)
            return

    def _forgot_password(self):
        dlg = QDialog(self); dlg.setWindowTitle("Password Reset (Demo)"); dlg.setMinimumWidth(440)
        vl = QVBoxLayout(dlg); vl.setContentsMargins(20, 20, 20, 20); vl.setSpacing(10)
        vl.addWidget(QLabel("Enter your username to request a reset token (demo shows token on-screen).", styleSheet=f"color:{TEXT2};"))
        u = QLineEdit(); u.setPlaceholderText("username"); vl.addWidget(u)
        out = QLabel("")
        out.setStyleSheet(f"color:{ORANGE};font-weight:700;")
        out.setWordWrap(True)
        out.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        vl.addWidget(out)
        def req():
            ok, res = request_password_reset(u.text().strip())
            out.setText(f"Reset token (demo): {res}" if ok else (res or "Failed."))
        btn = mkbtn("Request token", "btn_s"); btn.clicked.connect(req); vl.addWidget(btn)
        vl.addWidget(sep())
        vl.addWidget(QLabel("Complete reset:", styleSheet=f"color:{TEXT2};"))
        token_in = QLineEdit(); token_in.setPlaceholderText("token"); vl.addWidget(token_in)
        pw = QLineEdit(); pw.setEchoMode(QLineEdit.EchoMode.Password); pw.setPlaceholderText("new password"); vl.addWidget(pw)
        err = QLabel(""); err.setStyleSheet(f"color:{RED};"); err.setWordWrap(True); vl.addWidget(err)
        def apply():
            ok, e = reset_password_with_token(u.text().strip(), token_in.text().strip(), pw.text())
            if ok:
                QMessageBox.information(dlg, "Done", "Password reset successful. You can now log in.")
                dlg.accept()
            else:
                err.setText(e or "Failed.")
        row = QHBoxLayout()
        okb = mkbtn("Reset password"); okb.clicked.connect(apply)
        cb = mkbtn("Close", "btn_s"); cb.clicked.connect(dlg.reject)
        row.addWidget(okb); row.addWidget(cb); row.addStretch()
        vl.addLayout(row)
        dlg.exec()


# ── Change Password Dialog ───────────────────────────────────
class ChangePasswordDialog(QDialog):
    def __init__(self, auth_user: dict, parent=None):
        super().__init__(parent)
        self._user = auth_user
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(440)
        self._build()

    def _pw_row(self, placeholder):
        """Returns (container_widget, lineedit) with inline show/hide toggle."""
        container = QWidget(); hl = QHBoxLayout(container)
        hl.setContentsMargins(0,0,0,0); hl.setSpacing(0)
        le = QLineEdit(); le.setEchoMode(QLineEdit.EchoMode.Password)
        le.setPlaceholderText(placeholder); le.setMinimumHeight(38)
        eye = QPushButton("👁"); eye.setFixedSize(38,38); eye.setCheckable(True)
        eye.setStyleSheet(f"background:{BG3};border:1px solid {BORDER};color:{TEXT2};"
                          f"border-left:none;border-radius:0 3px 3px 0;")
        eye.setCursor(Qt.CursorShape.PointingHandCursor)
        eye.toggled.connect(lambda c,f=le: f.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        hl.addWidget(le); hl.addWidget(eye)
        return container, le

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(28, 28, 28, 28); vl.setSpacing(12)

        title = QLabel("🔑  Change Your Password")
        title.setStyleSheet(f"font-size:16px;font-weight:700;color:{ORANGE};")
        vl.addWidget(title)
        vl.addWidget(sep())

        # Current password
        old_ctn, self._old = self._pw_row("Enter your current password")
        vl.addWidget(flbl("Current Password")); vl.addWidget(old_ctn)
        self._old_err = errlbl(); vl.addWidget(self._old_err)

        vl.addSpacing(4)

        # New password + strength
        new_ctn, self._new = self._pw_row("Enter new password (min 8 chars)")
        self._new.textChanged.connect(self._on_pw_change)
        vl.addWidget(flbl("New Password")); vl.addWidget(new_ctn)
        self._strength_bar = PasswordStrengthBar()
        vl.addWidget(self._strength_bar)

        # Confirm
        conf_ctn, self._conf = self._pw_row("Re-enter new password to confirm")
        self._conf.textChanged.connect(self._check_match)
        vl.addWidget(flbl("Confirm New Password")); vl.addWidget(conf_ctn)
        self._match_lbl = QLabel("")
        self._match_lbl.setStyleSheet(f"font-size:11px;")
        vl.addWidget(self._match_lbl)

        # Policy box
        policy = QLabel(
            "  ❖  8 to 64 characters\n"
            "  ❖  At least 3 of 4: Uppercase · Lowercase · Number · Special (!@#$%^&*)\n"
            "  ❖  Cannot reuse your last 5 passwords\n"
            "  ❖  Cannot contain your name or username"
        )
        policy.setStyleSheet(f"color:{TEXT2};font-size:10px;background:{BG3};"
                             f"border:1px solid {BORDER};border-radius:4px;padding:8px 10px;")
        vl.addWidget(policy)

        self._err = errlbl(); self._err.setWordWrap(True)
        vl.addWidget(self._err)

        row = QHBoxLayout()
        ok_btn = mkbtn("✓  Change Password"); ok_btn.setMinimumHeight(40)
        ok_btn.clicked.connect(self._submit)
        cancel = mkbtn("Cancel", "btn_s"); cancel.clicked.connect(self.reject)
        row.addWidget(ok_btn); row.addWidget(cancel); row.addStretch()
        vl.addLayout(row)

    def _on_pw_change(self, text):
        self._strength_bar.update_strength(text)
        self._check_match()

    def _check_match(self):
        new_v = self._new.text(); conf_v = self._conf.text()
        if not conf_v:
            self._match_lbl.setText(""); return
        if new_v == conf_v:
            self._match_lbl.setText("  ✓ Passwords match")
            self._match_lbl.setStyleSheet(f"font-size:11px;color:{GREEN};")
        else:
            self._match_lbl.setText("  ✗ Passwords do not match")
            self._match_lbl.setStyleSheet(f"font-size:11px;color:{RED};")

    def _submit(self):
        # Clear previous errors
        self._old_err.setText(""); self._err.setText("")

        old_v = self._old.text()
        new_v = self._new.text()
        conf_v = self._conf.text()

        if not old_v:
            self._old_err.setText("Current password is required."); return
        if not new_v or not conf_v:
            self._err.setText("New password and confirmation are required."); return
        if new_v != conf_v:
            self._err.setText("New passwords do not match."); return

        ok_r, error = change_password(
            self._user["id"], old_v, new_v,
            self._user.get("username", ""),
            self._user.get("first_name", ""),
            self._user.get("last_name", "")
        )
        if ok_r:
            QMessageBox.information(self, "✓ Password Changed",
                "Your password has been changed successfully!")
            self.accept()
        else:
            # Route specific errors to the right field
            if error and ("incorrect" in error.lower() or "current" in error.lower()):
                self._old_err.setText(error)
            else:
                self._err.setText(error)


# ── User Profile Portal ──────────────────────────────────────
class UserProfileWindow(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self, auth_user: dict):
        super().__init__()
        self._auth_user = auth_user
        self._person = get_person_for_user(auth_user)
        self._specific = get_user_specific_data(self._person) if self._person else None
        self._refreshing_security_tab = False

        name = f"{self._person['first_name']} {self._person['last_name']}" if self._person else auth_user["username"]
        self.setWindowTitle(f"IAM — {name}  ·  My Profile")
        self.setMinimumSize(900, 680); self.resize(1000, 740)
        self._build()

    def _build(self):
        root = QWidget(); rl = QHBoxLayout(root); rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(0)

        # Sidebar
        sb = self._make_sidebar()
        rl.addWidget(sb)

        # Content
        self._stack_widget = QWidget()
        self._content_vl = QVBoxLayout(self._stack_widget)
        self._content_vl.setContentsMargins(32, 28, 32, 28); self._content_vl.setSpacing(0)
        rl.addWidget(self._stack_widget, 1)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._tab_profile(), "👤  My Profile")
        self._tabs.addTab(self._tab_security(), "🔑  Security")
        self._tabs.addTab(self._tab_login_history(), "📋  Login History")
        if self._person:
            self._tabs.addTab(self._tab_identity_history(), "🕐  Identity History")
        # Refresh security tab contents when switched to
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._content_vl.addWidget(self._tabs)

        main = QWidget(); ml = QVBoxLayout(main); ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(0)
        ml.addWidget(root)
        self.setCentralWidget = lambda w: None  # not a MainWindow
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)
        vl.addWidget(root)

    def _make_sidebar(self):
        sb = QWidget(); sb.setObjectName("sidebar")
        sb.setStyleSheet(f"""
            QWidget#sidebar {{
                background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1a1a1a,stop:1 #0f0f0f);
                border-right:2px solid {ORANGE_DIM};
                min-width:220px; max-width:220px;
            }}
        """)
        vl = QVBoxLayout(sb); vl.setContentsMargins(0, 24, 0, 20); vl.setSpacing(0)

        logo = QLabel("🎓  IAM System")
        logo.setStyleSheet(f"font-size:15px;font-weight:700;color:{ORANGE};padding:0 20px;letter-spacing:1px;")
        vl.addWidget(logo)

        uni = QLabel("University of Batna 2")
        uni.setStyleSheet(f"font-size:10px;color:{TEXT2};padding:0 20px 16px 20px;letter-spacing:2px;")
        vl.addWidget(uni)
        vl.addWidget(sep())
        vl.addSpacing(10)

        # User info card
        if self._person:
            name = f"{self._person['first_name']} {self._person['last_name']}"
            uid = self._person["unique_identifier"]
            utype = TYPE_LABELS.get(self._person["type"], self._person["type"])
            status = self._person["status"]
            sc = STATUS_CLR.get(status, TEXT2)
        else:
            name = self._auth_user["username"]
            uid = "ADMIN"
            utype = "Administrator"
            status = "Active"
            sc = GREEN

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color:{TEXT};font-weight:700;font-size:13px;padding:0 16px;")
        name_lbl.setWordWrap(True)
        vl.addWidget(name_lbl)

        id_lbl = QLabel(uid)
        id_lbl.setStyleSheet(f"color:{ORANGE};font-size:12px;font-weight:700;padding:2px 16px;")
        vl.addWidget(id_lbl)

        type_lbl = QLabel(utype)
        type_lbl.setStyleSheet(f"color:{TEXT2};font-size:11px;padding:0 16px;")
        vl.addWidget(type_lbl)

        status_lbl = QLabel(f"● {status}")
        status_lbl.setStyleSheet(f"color:{sc};font-size:11px;font-weight:700;padding:2px 16px 16px 16px;")
        vl.addWidget(status_lbl)

        vl.addWidget(sep())
        vl.addStretch()

        logout = QPushButton("⬅  Sign Out")
        logout.setStyleSheet(f"""
            QPushButton {{
                background:transparent;color:{RED};border:1px solid {RED};
                border-radius:3px;padding:9px 16px;margin:12px 16px;
                font-size:12px;font-weight:700;
            }}
            QPushButton:hover {{ background:{RED};color:{BG}; }}
        """)
        logout.setCursor(Qt.CursorShape.PointingHandCursor)
        logout.clicked.connect(self.logout_requested.emit)
        vl.addWidget(logout)

        ver = QLabel("v2.0  ·  IAM Project")
        ver.setStyleSheet(f"color:#404040;font-size:10px;padding:4px 0;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(ver)

        return sb

    def _kv(self, k, v, color=None):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 3, 0, 3)
        kl = QLabel(k + ":"); kl.setStyleSheet(f"color:{TEXT2};min-width:180px;font-size:12px;")
        vc = color or TEXT
        vl = QLabel(str(v or "—")); vl.setStyleSheet(f"color:{vc};font-size:12px;font-weight:600;")
        vl.setWordWrap(True)
        h.addWidget(kl); h.addWidget(vl); h.addStretch(); return w

    def _tab_profile(self):
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setStyleSheet("background:transparent;border:none;")
        inner = QWidget(); vl = QVBoxLayout(inner); vl.setSpacing(16); vl.setContentsMargins(12, 12, 12, 12)

        if not self._person:
            vl.addWidget(QLabel("No personal record linked to this account.", styleSheet=f"color:{TEXT2};"))
            sa.setWidget(inner); return sa

        p = self._person

        # Common Info card
        card = QWidget(); card.setObjectName("card")
        card.setStyleSheet(f"QWidget#card{{background:{BG2};border:1px solid {BORDER};border-top:2px solid {ORANGE_DIM};border-radius:4px;padding:16px;}}")
        cv = QVBoxLayout(card); cv.setSpacing(2)
        cv.addWidget(QLabel("Personal Information", styleSheet=f"color:{ORANGE};font-size:13px;font-weight:700;padding-bottom:8px;"))
        for k, v in [
            ("Full Name", f"{p['first_name']} {p['last_name']}"),
            ("University ID", p["unique_identifier"]),
            ("Category", TYPE_LABELS.get(p["type"], p["type"])),
            ("Sub-category", p["sub_category"]),
            ("Status", p["status"]),
            ("Date of Birth", p["date_of_birth"]),
            ("Place of Birth", p["place_of_birth"]),
            ("Nationality", p["nationality"]),
            ("Gender", "Male" if p["gender"] == "M" else "Female"),
            ("Email", p["email"]),
            ("Phone", p["phone"]),
            ("Registered", p["created_at"][:10]),
        ]:
            color = STATUS_CLR.get(v, None) if k == "Status" else None
            cv.addWidget(self._kv(k, v, color))
        vl.addWidget(card)

        # Specific data card
        if self._specific:
            scard = QWidget(); scard.setObjectName("scard")
            scard.setStyleSheet(f"QWidget#scard{{background:{BG2};border:1px solid {BORDER};border-top:2px solid {GREEN};border-radius:4px;padding:16px;}}")
            sv = QVBoxLayout(scard); sv.setSpacing(2)

            t = p["type"]
            if t == "STU":
                sv.addWidget(QLabel("Academic Information", styleSheet=f"color:{GREEN};font-size:13px;font-weight:700;padding-bottom:8px;"))
                s = self._specific
                for k, v in [
                    ("Faculty", s.get("faculty")),
                    ("Department", s.get("department")),
                    ("Major", s.get("major")),
                    ("Entry Year", s.get("entry_year")),
                    ("Group", s.get("group_name")),
                    ("High School Type", s.get("high_school_type")),
                    ("HS Honors", s.get("high_school_honors")),
                    ("Academic Status", s.get("academic_status")),
                    ("Scholarship", s.get("scholarship")),
                ]:
                    sv.addWidget(self._kv(k, v))
            elif t == "FAC":
                sv.addWidget(QLabel("Faculty Information", styleSheet=f"color:{GREEN};font-size:13px;font-weight:700;padding-bottom:8px;"))
                f = self._specific
                for k, v in [
                    ("Rank", f.get("rank")),
                    ("Employment Category", f.get("employment_category")),
                    ("Primary Department", f.get("primary_department")),
                    ("Research Areas", f.get("research_areas")),
                    ("HDR", "Yes" if f.get("hdr") else "No"),
                    ("Contract Type", f.get("contract_type")),
                    ("Contract Start", f.get("contract_start")),
                    ("Contract End", f.get("contract_end") or "Open-ended"),
                    ("Teaching Hrs/week", f.get("teaching_hours")),
                    ("Office", f"Bldg:{f.get('office_building','—')} Floor:{f.get('office_floor','—')} Room:{f.get('office_room','—')}"),
                ]:
                    sv.addWidget(self._kv(k, v))
            elif t == "STF":
                sv.addWidget(QLabel("Staff Information", styleSheet=f"color:{GREEN};font-size:13px;font-weight:700;padding-bottom:8px;"))
                s = self._specific
                for k, v in [
                    ("Department", s.get("department")),
                    ("Job Title", s.get("job_title")),
                    ("Grade", s.get("grade")),
                    ("Entry Date", s.get("entry_date")),
                ]:
                    sv.addWidget(self._kv(k, v))

            vl.addWidget(scard)

        vl.addStretch()
        sa.setWidget(inner); return sa

    def _tab_security(self):
        from auth import get_auth_connection, totp_is_enabled, totp_begin_enroll, totp_verify_and_enable
        from auth import secq_is_configured, secq_set, SECURITY_QUESTION_POOL, generate_backup_codes
        _LNAMES  = {1:"L1 — Basic",2:"L2 — Standard",3:"L3 — High",4:"L4 — Critical"}
        _LDESC   = {1:"Password only",2:"Password + SMS OTP",
                    3:"Password + SMS OTP + TOTP",4:"Password + SMS OTP + TOTP + Security Q"}
        _LCOLORS = {1:"#3498db",2:"#f1c40f",3:"#e67e22",4:"#e74c3c"}

        # ── always read fresh level from DB ──────────────────
        try:
            conn2 = get_auth_connection()
            row2  = conn2.execute("SELECT auth_level FROM auth_user WHERE id=?",
                                  (self._auth_user["id"],)).fetchone()
            conn2.close()
            cur_lvl = int(row2["auth_level"]) if row2 and row2["auth_level"] else 1
        except Exception:
            cur_lvl = 1

        lvl_name  = _LNAMES[cur_lvl]
        lvl_desc  = _LDESC[cur_lvl]
        lvl_color = _LCOLORS[cur_lvl]

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        inner = QWidget()
        inner.setStyleSheet(f"background:{BG};")
        vl = QVBoxLayout(inner); vl.setContentsMargins(20,20,20,20); vl.setSpacing(14)

        def CARD(bc):
            return (f"background:{BG2};border:1px solid {bc};"
                    f"border-top:3px solid {bc};border-radius:6px;")

        # ── Auth Level Card ───────────────────────────────────
        acard = QWidget()
        acard.setStyleSheet(CARD(lvl_color))
        av = QVBoxLayout(acard); av.setContentsMargins(16,14,16,14); av.setSpacing(6)

        h_row = QHBoxLayout(); h_row.setSpacing(10)
        ico = QLabel("🔒"); ico.setStyleSheet(f"font-size:20px;background:transparent;border:none;")
        ttl = QLabel("Authentication Level")
        ttl.setStyleSheet(f"color:{lvl_color};font-size:14px;font-weight:700;background:transparent;border:none;")
        h_row.addWidget(ico); h_row.addWidget(ttl); h_row.addStretch()
        av.addLayout(h_row)

        badge = QLabel(f"  {lvl_name}  ")
        badge.setStyleSheet(f"color:{BG};background:{lvl_color};font-size:13px;font-weight:700;"
                            f"border-radius:4px;padding:4px 14px;border:none;max-width:200px;")
        badge.setFixedHeight(30)
        av.addWidget(badge)

        methods_lbl = QLabel(f"Methods:  {lvl_desc}")
        methods_lbl.setStyleSheet(f"color:{TEXT2};font-size:11px;background:transparent;border:none;")
        av.addWidget(methods_lbl)

        note = QLabel("Your security level is managed by the administrator.")
        note.setStyleSheet(f"color:#555;font-size:10px;background:transparent;border:none;")
        av.addWidget(note)
        vl.addWidget(acard)

        # ── Account Info Card ─────────────────────────────────
        ucard = QWidget()
        ucard.setStyleSheet(CARD(ORANGE))
        uv = QVBoxLayout(ucard); uv.setContentsMargins(16,14,16,14); uv.setSpacing(2)

        uv.addWidget(QLabel("Account Information",
            styleSheet=f"color:{ORANGE};font-size:13px;font-weight:700;"
                       f"background:transparent;border:none;padding-bottom:6px;"))

        for label, value, color in [
            ("Username",        self._auth_user["username"],           ORANGE),
            ("Role",            self._auth_user["role"].capitalize(),   TEXT),
            ("Account Created", self._auth_user["created_at"][:10],    TEXT),
            ("Last Updated",    self._auth_user["updated_at"][:10],    TEXT),
        ]:
            rw = QWidget(); rw.setStyleSheet("background:transparent;border:none;")
            rh = QHBoxLayout(rw); rh.setContentsMargins(0,4,0,4); rh.setSpacing(8)
            k_lbl = QLabel(f"{label}:")
            k_lbl.setFixedWidth(150)
            k_lbl.setStyleSheet(f"color:{TEXT2};font-size:12px;background:transparent;border:none;")
            v_lbl = QLabel(str(value or "—"))
            v_lbl.setStyleSheet(f"color:{color};font-size:12px;font-weight:700;"
                                f"background:transparent;border:none;")
            rh.addWidget(k_lbl); rh.addWidget(v_lbl); rh.addStretch()
            uv.addWidget(rw)
        vl.addWidget(ucard)

        # ── Change Password Card ──────────────────────────────
        pwcard = QWidget()
        pwcard.setStyleSheet(CARD(GREEN))
        pv = QVBoxLayout(pwcard); pv.setContentsMargins(16,14,16,14); pv.setSpacing(8)

        pv.addWidget(QLabel("🔑  Change Password",
            styleSheet=f"color:{GREEN};font-size:13px;font-weight:700;"
                       f"background:transparent;border:none;"))

        policy_card = QWidget()
        policy_card.setStyleSheet(f"background:{BG3};border:1px solid {BORDER};"
                                  f"border-radius:4px;")
        pcv = QVBoxLayout(policy_card); pcv.setContentsMargins(10,8,10,8); pcv.setSpacing(3)
        for rule in [
            "❖  8 to 64 characters",
            "❖  At least 3 of 4: Uppercase · Lowercase · Number · Special (!@#$%^&*)",
            "❖  Cannot reuse your last 5 passwords",
            "❖  Cannot contain your name or username",
        ]:
            rl = QLabel(rule)
            rl.setStyleSheet(f"color:{TEXT2};font-size:10px;background:transparent;border:none;")
            pcv.addWidget(rl)
        pv.addWidget(policy_card)

        pw_btn = mkbtn("  🔑  Change My Password  ")
        pw_btn.setMinimumHeight(40)
        pw_btn.clicked.connect(self._open_change_pw)
        pv.addWidget(pw_btn)
        vl.addWidget(pwcard)

        # ── MFA Setup Card ────────────────────────────────────
        mcard = QWidget()
        mcard.setStyleSheet(CARD(PURPLE))
        mv = QVBoxLayout(mcard); mv.setContentsMargins(16,14,16,14); mv.setSpacing(10)
        mv.addWidget(QLabel("🛡️  MFA Setup",
            styleSheet=f"color:{PURPLE};font-size:13px;font-weight:700;background:transparent;border:none;"))

        # TOTP status + setup
        totp_status = QLabel("")
        totp_status.setStyleSheet(f"color:{TEXT2};font-size:11px;")
        mv.addWidget(totp_status)
        qr_lbl = QLabel(""); qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); qr_lbl.hide()
        mv.addWidget(qr_lbl)
        totp_code = QLineEdit(); totp_code.setPlaceholderText("Enter 6-digit TOTP code"); totp_code.setMaxLength(6)
        totp_code.setMinimumHeight(38); totp_code.hide()
        mv.addWidget(totp_code)
        totp_err = QLabel(""); totp_err.setStyleSheet(f"color:{RED};font-size:11px;"); totp_err.setWordWrap(True)
        mv.addWidget(totp_err)

        def refresh_totp_ui():
            enabled = totp_is_enabled(self._auth_user["id"])
            if enabled:
                totp_status.setText("TOTP: ✓ Enabled (Authenticator app configured).")
                qr_lbl.hide(); totp_code.hide()
            else:
                totp_status.setText("TOTP: Not enabled yet. Click “Setup TOTP” to enroll.")

        def setup_totp():
            totp_err.setText("")
            ok_, info = totp_begin_enroll(self._auth_user["id"])
            if not ok_:
                totp_err.setText("Failed to start TOTP enrollment.")
                return
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(info["otpauth_uri"])
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            qimg = QImage.fromData(buf.getvalue(), "PNG")
            qr_lbl.setPixmap(QPixmap.fromImage(qimg).scaledToWidth(260, Qt.TransformationMode.FastTransformation))
            qr_lbl.show()
            totp_code.show()
            totp_status.setText("Scan QR with Authenticator, then enter the 6-digit code to confirm.")

        def confirm_totp():
            totp_err.setText("")
            ok_, res = totp_verify_and_enable(self._auth_user["id"], totp_code.text().strip())
            if not ok_:
                totp_err.setText(res or "Invalid code.")
                return
            bcodes = (res or {}).get("backup_codes") if isinstance(res, dict) else None
            if bcodes:
                QMessageBox.information(self, "Backup codes", "Save these 10 backup codes (shown once):\n\n" + "\n".join(bcodes))
            refresh_totp_ui()

        totp_btn_row = QHBoxLayout()
        setup_btn = mkbtn("Setup TOTP", "btn_s"); setup_btn.clicked.connect(setup_totp)
        conf_btn = mkbtn("Confirm TOTP", "btn_g"); conf_btn.clicked.connect(confirm_totp)
        totp_btn_row.addWidget(setup_btn); totp_btn_row.addWidget(conf_btn); totp_btn_row.addStretch()
        mv.addLayout(totp_btn_row)

        # Security questions (L4)
        secq_status = QLabel("")
        secq_status.setStyleSheet(f"color:{TEXT2};font-size:11px;")
        mv.addWidget(sepeq := QLabel(""));  # spacer
        mv.addWidget(secq_status)
        q1 = QComboBox(); q1.addItems(SECURITY_QUESTION_POOL)
        q2 = QComboBox(); q2.addItems(SECURITY_QUESTION_POOL)
        a1 = QLineEdit(); a1.setPlaceholderText("Answer 1")
        a2 = QLineEdit(); a2.setPlaceholderText("Answer 2")
        for wdg in (q1, q2, a1, a2):
            wdg.setMinimumHeight(36)
        secq_err = QLabel(""); secq_err.setStyleSheet(f"color:{RED};font-size:11px;"); secq_err.setWordWrap(True)
        mv.addWidget(fw("Question 1", q1))
        mv.addWidget(fw("Answer 1", a1))
        mv.addWidget(fw("Question 2", q2))
        mv.addWidget(fw("Answer 2", a2))
        mv.addWidget(secq_err)
        save_sq = mkbtn("Save security questions", "btn_s")
        def save_questions():
            secq_err.setText("")
            ok_, err_ = secq_set(self._auth_user["id"], q1.currentText(), a1.text(), q2.currentText(), a2.text())
            if ok_:
                QMessageBox.information(self, "Saved", "Security questions saved.")
                refresh_secq_ui()
            else:
                secq_err.setText(err_ or "Failed.")
        save_sq.clicked.connect(save_questions)
        mv.addWidget(save_sq)

        def refresh_secq_ui():
            configured = secq_is_configured(self._auth_user["id"])
            secq_status.setText("Security questions: ✓ Configured" if configured else "Security questions: Not configured (required for L4).")

        refresh_totp_ui()
        refresh_secq_ui()
        vl.addWidget(mcard)

        vl.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _on_tab_changed(self, idx):
        if idx == 1:
            self._refresh_security_tab()

    def _refresh_security_tab(self):
        """Replace the Security tab widget with a freshly built one (live level)."""
        if self._refreshing_security_tab:
            return
        self._refreshing_security_tab = True
        try:
            self._tabs.blockSignals(True)
            new_w = self._tab_security()
            self._tabs.removeTab(1)
            self._tabs.insertTab(1, new_w, "🔑  Security")
            self._tabs.setCurrentIndex(1)
        finally:
            self._tabs.blockSignals(False)
            # Allow the event loop to settle before enabling refresh again
            QTimer.singleShot(0, lambda: setattr(self, "_refreshing_security_tab", False))

    def _open_change_pw(self):
        # Enrich auth_user with first/last name from person record for policy check
        user_data = dict(self._auth_user)
        if self._person:
            user_data["first_name"] = self._person.get("first_name", "")
            user_data["last_name"]  = self._person.get("last_name", "")
        dlg = ChangePasswordDialog(user_data, self)
        dlg.exec()

    def _tab_login_history(self):
        w = QWidget(); vl = QVBoxLayout(w); vl.setContentsMargins(12, 12, 12, 12); vl.setSpacing(10)

        hdr = QLabel("📋  Login History  (last 20 sessions)")
        hdr.setStyleSheet(f"color:{ORANGE};font-size:13px;font-weight:700;")
        vl.addWidget(hdr)

        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["Date & Time", "Status", "IP Address", "Failure Reason", "Session ID"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)

        logs = get_login_history(self._auth_user["id"])
        tbl.setRowCount(len(logs))
        for r, log in enumerate(logs):
            success = log["success"]
            vals = [
                log["logged_at"],
                "✓ Success" if success else "✗ Failed",
                log["ip_address"] or "—",
                log["failure_reason"] or "—",
                (log["session_id"] or "—")[:16] + ("..." if log.get("session_id") else ""),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 1:
                    item.setForeground(QColor(GREEN if success else RED))
                tbl.setItem(r, c, item)

        if not logs:
            vl.addWidget(QLabel("No login records found.", styleSheet=f"color:{TEXT2};"))

        vl.addWidget(tbl)
        return w

    def _tab_identity_history(self):
        """Shows the audit trail of changes made to the user's identity record."""
        from db import get_connection as _gc
        w = QWidget(); vl = QVBoxLayout(w); vl.setContentsMargins(12, 12, 12, 12); vl.setSpacing(10)

        hdr = QLabel("🕐  Identity Change History")
        hdr.setStyleSheet(f"color:{ORANGE};font-size:13px;font-weight:700;")
        vl.addWidget(hdr)

        sub = QLabel("All modifications made to your identity record by administrators.")
        sub.setStyleSheet(f"color:{TEXT2};font-size:11px;")
        vl.addWidget(sub)

        if not self._person:
            vl.addWidget(QLabel("No identity record linked to this account.", styleSheet=f"color:{TEXT2};"))
            return w

        conn = _gc()
        rows = conn.execute(
            "SELECT * FROM history WHERE person_id=? ORDER BY changed_at DESC",
            (self._person["id"],)
        ).fetchall()
        conn.close()

        if not rows:
            vl.addWidget(QLabel("No changes recorded yet.", styleSheet=f"color:{TEXT2};"))
            return w

        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["Date & Time", "Action", "Field", "Old Value", "New Value"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setRowCount(len(rows))

        for r, row in enumerate(rows):
            vals = [
                row["changed_at"],
                row["action"],
                row["field_name"] or "—",
                row["old_value"] or "—",
                row["new_value"] or (row["note"] or "—"),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if c == 1:
                    action = row["action"]
                    color = GREEN if "CREATE" in action else (RED if "ARCHIVED" in action else ORANGE)
                    item.setForeground(QColor(color))
                tbl.setItem(r, c, item)

        vl.addWidget(tbl)
        return w


# ── Auth Management Tab (for admin) ─────────────────────────
MAX_FAILED_IMPORT = 5

# Security level colour palette
LEVEL_COLORS = {1: "#3498db", 2: "#f1c40f", 3: "#e67e22", 4: "#e74c3c"}
LEVEL_NAMES  = {
    1: "L1 — Basic",
    2: "L2 — Standard",
    3: "L3 — High",
    4: "L4 — Critical",
}
LEVEL_DESC = {
    1: "Password only",
    2: "Password + SMS OTP",
    3: "Password + SMS OTP + TOTP",
    4: "Password + SMS OTP + TOTP + Security Q",
}


def _ask_new_password(parent):
    dlg = QDialog(parent); dlg.setWindowTitle("Set New Password"); dlg.setMinimumWidth(380)
    vl = QVBoxLayout(dlg); vl.setContentsMargins(20, 20, 20, 20); vl.setSpacing(10)
    vl.addWidget(QLabel("New password for user:", styleSheet=f"color:{TEXT2};"))
    pw = QLineEdit(); pw.setEchoMode(QLineEdit.EchoMode.Password); pw.setPlaceholderText("Enter new password")
    strength = PasswordStrengthBar()
    pw.textChanged.connect(strength.update_strength)
    vl.addWidget(pw); vl.addWidget(strength)
    row = QHBoxLayout()
    ok = mkbtn("Set Password"); ok.clicked.connect(dlg.accept)
    cancel = mkbtn("Cancel", "btn_s"); cancel.clicked.connect(dlg.reject)
    row.addWidget(ok); row.addWidget(cancel)
    vl.addLayout(row)
    result = dlg.exec()
    return pw.text(), result == QDialog.DialogCode.Accepted


# ... [Keep imports and login classes untouched]

class SecurityLevelDialog(QDialog):
    """Admin controls to change a user's authentication security level."""

    def __init__(self, auth_user, person_info, parent=None):
        super().__init__(parent)
        self._user = auth_user
        self._person = person_info
        self._level_btns = {}  
        self.setWindowTitle("Security Level Control"); self.setMinimumWidth(520)
        self._build()

    def _build(self):
        from auth import set_auth_level
        vl = QVBoxLayout(self); vl.setContentsMargins(28, 28, 28, 28); vl.setSpacing(16)

        title = QLabel("🔐  Security Level Control")
        title.setStyleSheet(f"font-size:16px;font-weight:700;color:{ORANGE};")
        vl.addWidget(title)
        vl.addWidget(sep())

        utype = "—"; user_type_code = None; sub_cat = ""
        if self._person:
            user_type_code = self._person.get("type")
            sub_cat = self._person.get("sub_category", "")
            utype = TYPE_LABELS.get(user_type_code, user_type_code)
        name = (f"{self._person['first_name']} {self._person['last_name']}" if self._person else self._user["username"])
        uid  = self._person["unique_identifier"] if self._person else "ADMIN"

        info_card = QWidget()
        info_card.setStyleSheet(f"background:{BG3};border:1px solid {BORDER};border-radius:4px;padding:10px;")
        ic = QGridLayout(info_card); ic.setSpacing(6)
        for col, (lbl, val) in enumerate([("User", name), ("ID", uid), ("Type", utype)]):
            ic.addWidget(QLabel(lbl+":", styleSheet=f"color:{TEXT2};font-size:11px;"), 0, col*2)
            ic.addWidget(QLabel(val, styleSheet=f"color:{ORANGE};font-weight:700;font-size:12px;"), 0, col*2+1)
        vl.addWidget(info_card)

        cur_lvl = int(self._user.get("auth_level") or 1)
        cur_color = LEVEL_COLORS.get(cur_lvl, BLUE)
        cur_lbl = QLabel(f"Current Level:  {LEVEL_NAMES[cur_lvl]}  —  {LEVEL_DESC[cur_lvl]}")
        cur_lbl.setStyleSheet(f"color:{cur_color};font-weight:700;font-size:13px;background:{BG2};border:1px solid {cur_color};border-radius:4px;padding:8px 12px;")
        vl.addWidget(cur_lbl)

        spec_lbl = QLabel(
            "Per project spec — default & upgrade rules:\n"
            "  Students:  L1 default · can upgrade to L2  (International: L2 mandatory)\n"
            "  Faculty:   L2 default · can upgrade to L3  (Dept heads: L3 mandatory)\n"
            "  Staff:     L2 default · can upgrade to L3  (HR/Payroll: L3 mandatory)\n"
            "  IT Admins: L4 always  · no upgrade/downgrade\n"
            "  Contractors: L1 default · can upgrade to L2"
        )
        spec_lbl.setStyleSheet(f"color:{TEXT2};font-size:10px;background:{BG3};border-radius:3px;padding:8px 10px;")
        vl.addWidget(spec_lbl)

        # ── Apply Enforced Level Logic Based on Spec ──
        min_lvl = 1
        max_lvl = 4

        if user_type_code == "STU":
            max_lvl = 2
            if "International" in sub_cat:
                min_lvl = 2
        elif user_type_code == "FAC":
            min_lvl = 2
            max_lvl = 3
        elif user_type_code == "STF":
            min_lvl = 2
            max_lvl = 3
        elif user_type_code == "EXT":
            max_lvl = 2
        elif not self._person:
            min_lvl = 4 # Admin restrictions
            max_lvl = 4

        vl.addWidget(QLabel("Select New Level:", styleSheet=f"color:{TEXT};font-weight:700;"))
        levels_w = QWidget(); levels_l = QVBoxLayout(levels_w); levels_l.setSpacing(8)

        for lvl in [1, 2, 3, 4]:
            color = LEVEL_COLORS[lvl]
            btn = QPushButton(f"  {LEVEL_NAMES[lvl]}")
            btn.setCheckable(True)
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Disable unallowed levels
            if lvl < min_lvl or lvl > max_lvl:
                btn.setEnabled(False)
                btn.setStyleSheet(f"QPushButton{{background:{BG2};color:#555;border:2px solid #444;border-radius:4px;font-size:13px;font-weight:700;text-align:left;padding-left:12px;}}")
            else:
                btn.setStyleSheet(
                    f"QPushButton{{background:{BG2};color:{color};border:2px solid {color};border-radius:4px;font-size:13px;font-weight:700;text-align:left;padding-left:12px;}}"
                    f"QPushButton:checked{{background:{color};color:{BG};border:2px solid {color};}}"
                    f"QPushButton:hover{{background:rgba(255,255,255,0.06);}}"
                )
            row_w = QWidget(); row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0); row_l.setSpacing(10)
            desc_lbl = QLabel(LEVEL_DESC[lvl])
            desc_lbl.setStyleSheet(f"color:{TEXT2};font-size:11px;")
            row_l.addWidget(btn, 2); row_l.addWidget(desc_lbl, 3)
            levels_l.addWidget(row_w)
            self._level_btns[lvl] = btn

        self._level_btns[cur_lvl].setChecked(True)

        def make_toggle(selected_lvl):
            def on_toggle(checked):
                if checked:
                    for ll, bb in self._level_btns.items():
                        if ll != selected_lvl and bb.isChecked():
                            bb.blockSignals(True)
                            bb.setChecked(False)
                            bb.blockSignals(False)
                else:
                    # Don't allow unchecking without selecting another — re-check self
                    pass
            return on_toggle

        for lvl, btn in self._level_btns.items():
            btn.toggled.connect(make_toggle(lvl))

        vl.addWidget(levels_w)
        self._err = errlbl(); vl.addWidget(self._err)

        row = QHBoxLayout()
        apply_btn = mkbtn("✓  Apply Level Change")
        apply_btn.setMinimumHeight(40)
        cancel_btn = mkbtn("Cancel", "btn_s")

        def apply():
            chosen = next((l for l, b in self._level_btns.items() if b.isEnabled() and b.isChecked()), None)
            if chosen is None:
                self._err.setText("Please select a level.")
                return
            if chosen == cur_lvl:
                self._err.setText("That is already the current level.")
                return
            ok_, err_ = set_auth_level(self._user["id"], chosen)
            if ok_:
                QMessageBox.information(
                    self, "Applied",
                    f"Security level set to {LEVEL_NAMES[chosen]} for {name}."
                )
                self.accept()
            else:
                self._err.setText(err_ or "Failed.")

        apply_btn.clicked.connect(apply)
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(apply_btn); row.addWidget(cancel_btn); row.addStretch()
        vl.addLayout(row)

# ... [Keep AuthManagementPage and bottom logic untouched]

class AuthManagementPage(QWidget):
    """Embedded into the main admin app as an extra nav item."""

    def __init__(self, mw):
        super().__init__(); self.mw = mw
        vl = QVBoxLayout(self); vl.setContentsMargins(32, 28, 32, 28); vl.setSpacing(16)
        vl.addWidget(QLabel("Auth Management", objectName="h1"))
        vl.addWidget(QLabel("Manage security levels, unlock accounts, reset passwords, and view logs", objectName="sub"))

        self._tabs = QTabWidget()
        self._tabs.addTab(self._tab_users(), "👥  Users & Security")
        self._tabs.addTab(self._tab_audit(), "📋  Audit Log")
        self._tabs.addTab(self._tab_admin_history(), "🔐  Admin Login History")
        vl.addWidget(self._tabs)

    # ── Tab 1: Users & Security ──────────────────────────────
    def _tab_users(self):
        from auth import get_all_auth_users, unlock_account, reset_password_admin
        from db import get_connection

        w = QWidget(); vl = QVBoxLayout(w); vl.setContentsMargins(12, 12, 12, 12); vl.setSpacing(10)

        # Toolbar — only Refresh (no Create Account)
        btn_row = QHBoxLayout()
        refresh_btn = mkbtn("⟳  Refresh", "btn_s"); refresh_btn.setFixedWidth(120)
        btn_row.addWidget(refresh_btn); btn_row.addStretch()

        # Level legend
        for lvl in [1, 2, 3, 4]:
            dot = QLabel(f"● {LEVEL_NAMES[lvl]}")
            dot.setStyleSheet(f"color:{LEVEL_COLORS[lvl]};font-size:11px;font-weight:700;margin-left:12px;")
            btn_row.addWidget(dot)
        vl.addLayout(btn_row)

        tbl = QTableWidget(0, 7)
        tbl.setHorizontalHeaderLabels([
            "Username", "Linked Person", "Type",
            "Security Level", "Failed Attempts", "Status", "Actions"
        ])
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        tbl.setColumnWidth(6, 230)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False); tbl.setAlternatingRowColors(True)
        tbl.setRowHeight(0, 42)

        def load():
            users = get_all_auth_users()
            conn = get_connection()
            tbl.setRowCount(len(users))
            for r, u in enumerate(users):
                tbl.setRowHeight(r, 42)
                person_info = None
                person_name = "—"; user_type = "—"
                if u["person_id"]:
                    p = conn.execute(
                        "SELECT first_name, last_name, unique_identifier, type FROM person WHERE id=?",
                        (u["person_id"],)).fetchone()
                    if p:
                        person_name = f"{p['first_name']} {p['last_name']} [{p['unique_identifier']}]"
                        user_type = TYPE_LABELS.get(p["type"], p["type"])
                        person_info = dict(p)

                lvl = u.get("auth_level", 1)
                lvl_color = LEVEL_COLORS.get(lvl, BLUE)
                lvl_text  = LEVEL_NAMES.get(lvl, "L1")

                is_locked = False
                if u["locked_until"]:
                    try:
                        if datetime.now() < datetime.strptime(u["locked_until"], "%Y-%m-%d %H:%M:%S"):
                            is_locked = True
                    except Exception: pass

                account_status = "🔒 Locked" if is_locked else ("⚠ Change PW" if u["must_change_pw"] else "✓ Active")
                status_color   = RED if is_locked else (ORANGE if u["must_change_pw"] else GREEN)

                cells = [
                    (u["username"],    ORANGE if u["role"] == "admin" else TEXT),
                    (person_name,      TEXT),
                    (user_type,        TEXT2),
                    (lvl_text,         lvl_color),
                    (str(u["failed_attempts"]), RED if u["failed_attempts"] >= 3 else TEXT),
                    (account_status,   status_color),
                    ("",               TEXT),
                ]
                for c, (val, col) in enumerate(cells):
                    item = QTableWidgetItem(val)
                    item.setForeground(QColor(col))
                    item.setData(Qt.ItemDataRole.UserRole, u)
                    tbl.setItem(r, c, item)

                # Action cell — three buttons
                act_w = QWidget(); act_l = QHBoxLayout(act_w)
                act_l.setContentsMargins(4, 3, 4, 3); act_l.setSpacing(5)

                # 🔐 Security Level button
                sec_btn = QPushButton("🔐 Level")
                sec_btn.setStyleSheet(
                    f"background:transparent;color:{LEVEL_COLORS.get(lvl,BLUE)};"
                    f"border:1px solid {LEVEL_COLORS.get(lvl,BLUE)};border-radius:3px;"
                    f"padding:3px 7px;font-size:11px;font-weight:700;")
                sec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                u_snap = dict(u); p_snap = person_info
                def open_level(_, us=u_snap, pi=p_snap):
                    dlg = SecurityLevelDialog(us, pi, w)
                    if dlg.exec(): load()
                sec_btn.clicked.connect(open_level)
                act_l.addWidget(sec_btn)

                # 🔓 Unlock button (only if locked)
                if is_locked or u["failed_attempts"] >= MAX_FAILED_IMPORT:
                    ul_btn = QPushButton("🔓 Unlock")
                    ul_btn.setStyleSheet(
                        f"background:transparent;color:{GREEN};border:1px solid {GREEN};"
                        f"border-radius:3px;padding:3px 7px;font-size:11px;")
                    ul_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    uid_v = u["id"]
                    ul_btn.clicked.connect(lambda _, uid=uid_v: (unlock_account(uid), load()))
                    act_l.addWidget(ul_btn)

                # 🔑 Reset PW button
                rp_btn = QPushButton("🔑 Reset PW")
                rp_btn.setStyleSheet(
                    f"background:transparent;color:{BLUE};border:1px solid {BLUE};"
                    f"border-radius:3px;padding:3px 7px;font-size:11px;")
                rp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                u_r = dict(u)
                def do_reset(_, u=u_r):
                    pw, ok_ = _ask_new_password(w)
                    if ok_ and pw:
                        ok2, err2 = reset_password_admin(u["id"], pw)
                        if ok2: QMessageBox.information(w, "Done", "Password reset. User must change on next login."); load()
                        else:   QMessageBox.warning(w, "Error", err2 or "Failed.")
                rp_btn.clicked.connect(do_reset)
                act_l.addWidget(rp_btn)
                act_l.addStretch()
                tbl.setCellWidget(r, 6, act_w)
            conn.close()

        refresh_btn.clicked.connect(load)
        vl.addWidget(tbl)
        load()
        return w

    # ── Tab 2: Audit Log ─────────────────────────────────────
    def _tab_audit(self):
        from auth import get_audit_log
        w = QWidget(); vl = QVBoxLayout(w); vl.setContentsMargins(12, 12, 12, 12); vl.setSpacing(10)

        top = QHBoxLayout()
        hdr_lbl = QLabel("Full authentication audit log — all users, all events")
        hdr_lbl.setStyleSheet(f"color:{TEXT2};font-size:11px;")
        refresh_btn = mkbtn("⟳  Refresh", "btn_s"); refresh_btn.setFixedWidth(120)
        top.addWidget(hdr_lbl); top.addStretch(); top.addWidget(refresh_btn)
        vl.addLayout(top)

        tbl = QTableWidget(0, 6)
        tbl.setHorizontalHeaderLabels(["Timestamp", "Username", "Status", "IP Address", "Failure Reason", "Session"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False); tbl.setAlternatingRowColors(True)

        def load():
            logs = get_audit_log(200)
            tbl.setRowCount(len(logs))
            for r, log in enumerate(logs):
                success = log["success"]
                vals = [
                    log["logged_at"], log["username"],
                    "✓ Success" if success else "✗ Failed",
                    log["ip_address"] or "—",
                    log["failure_reason"] or "—",
                    (log["session_id"] or "—")[:16],
                ]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    if c == 2: item.setForeground(QColor(GREEN if success else RED))
                    tbl.setItem(r, c, item)

        refresh_btn.clicked.connect(load)
        vl.addWidget(tbl)
        load()
        return w

    # ── Tab 3: Admin Login History ───────────────────────────
    def _tab_admin_history(self):
        from auth import get_auth_connection
        w = QWidget(); vl = QVBoxLayout(w); vl.setContentsMargins(12, 12, 12, 12); vl.setSpacing(10)

        top = QHBoxLayout()
        hdr_lbl = QLabel("Login history for the admin account only")
        hdr_lbl.setStyleSheet(f"color:{TEXT2};font-size:11px;")
        refresh_btn = mkbtn("⟳  Refresh", "btn_s"); refresh_btn.setFixedWidth(120)
        top.addWidget(hdr_lbl); top.addStretch(); top.addWidget(refresh_btn)
        vl.addLayout(top)

        # Stats row
        stats_row = QHBoxLayout(); stats_row.setSpacing(12)
        self._stat_total = self._stat_card("Total Logins", "0", ORANGE)
        self._stat_ok    = self._stat_card("Successful",   "0", GREEN)
        self._stat_fail  = self._stat_card("Failed",       "0", RED)
        self._stat_lock  = self._stat_card("Lockouts",     "0", PURPLE)
        for card in [self._stat_total, self._stat_ok, self._stat_fail, self._stat_lock]:
            stats_row.addWidget(card)
        vl.addLayout(stats_row)

        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["Date & Time", "Status", "IP Address", "Failure Reason", "Session ID"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False); tbl.setAlternatingRowColors(True)

        def load():
            conn = get_auth_connection()
            admin = conn.execute("SELECT id FROM auth_user WHERE username='admin'").fetchone()
            if not admin: conn.close(); return
            logs = conn.execute(
                "SELECT * FROM login_log WHERE auth_user_id=? ORDER BY logged_at DESC LIMIT 100",
                (admin["id"],)
            ).fetchall()
            conn.close()

            total = len(logs)
            ok_c  = sum(1 for l in logs if l["success"])
            fail_c= total - ok_c
            lock_c= sum(1 for l in logs if l["failure_reason"] and "locked" in (l["failure_reason"] or "").lower())

            self._stat_total.findChild(QLabel, "val").setText(str(total))
            self._stat_ok.findChild(QLabel,    "val").setText(str(ok_c))
            self._stat_fail.findChild(QLabel,  "val").setText(str(fail_c))
            self._stat_lock.findChild(QLabel,  "val").setText(str(lock_c))

            tbl.setRowCount(len(logs))
            for r, log in enumerate(logs):
                success = log["success"]
                vals = [
                    log["logged_at"],
                    "✓ Success" if success else "✗ Failed",
                    log["ip_address"] or "—",
                    log["failure_reason"] or "—",
                    (log["session_id"] or "—")[:20],
                ]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    if c == 1: item.setForeground(QColor(GREEN if success else RED))
                    tbl.setItem(r, c, item)

        refresh_btn.clicked.connect(load)
        vl.addWidget(tbl)
        load()  # Load data immediately on tab creation
        return w

    def _stat_card(self, title: str, value: str, color: str):
        card = QWidget()
        card.setStyleSheet(f"background:{BG2};border:1px solid {BORDER};"
                           f"border-top:2px solid {color};border-radius:4px;padding:10px;")
        cv = QVBoxLayout(card); cv.setSpacing(2); cv.setContentsMargins(12, 10, 12, 10)
        val_lbl = QLabel(value)
        val_lbl.setObjectName("val")
        val_lbl.setStyleSheet(f"font-size:26px;font-weight:700;color:{color};")
        tit_lbl = QLabel(title)
        tit_lbl.setStyleSheet(f"font-size:11px;color:{TEXT2};")
        cv.addWidget(val_lbl); cv.addWidget(tit_lbl)
        return card