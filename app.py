# ============================================================
# app.py  —  University Identity Management System
# PyQt6 Desktop Application  |  University of Batna 2
# Run:  python3 app.py
# Requires: pip install PyQt6
# ============================================================

import sys, re, uuid
from datetime import date, datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QScrollArea, QFrame, QGroupBox,
    QAbstractItemView, QTabWidget,
)
from PyQt6.QtCore  import Qt, QDate
from PyQt6.QtGui   import QColor

from db    import get_connection, init_db
from auth import (
    ensure_person_auth_user, hash_password, lock_until_iso,
    log_auth_event, validate_password_policy, verify_password,
)
from utils import (
    CATEGORIES, TYPE_LABELS, MIN_AGE, SUBCAT_PREFIX,
    HIGH_SCHOOL_TYPES, HONORS_LIST, ACADEMIC_STATUSES,
    FACULTY_CATALOG, FACULTIES, DEPARTMENTS, GROUPS,
    FACULTY_RANKS, EMPLOYMENT_CATS, CONTRACT_TYPES, STAFF_GRADES,
    STATUS_TRANSITIONS, STATUS_DESCRIPTIONS,
    calc_age, generate_id, log_history, letters_only,
)

BG="#0f0f0f"; BG2="#1a1a1a"; BG3="#252525"; BORDER="#3a3a3a"
TEXT="#f5f5f5"; TEXT2="#a0a0a0"; ORANGE="#ff8c42"; ORANGE_DIM="#d96d2e"
GREEN="#66bb6a"; RED="#e74c3c"; PURPLE="#9b59b6"

STATUS_CLR = {"Pending": ORANGE, "Active": GREEN, "Suspended": RED, "Inactive": TEXT2, "Archived": "#505050"}
CAT_CLR    = {"STU": ORANGE, "FAC": GREEN, "STF": ORANGE, "EXT": PURPLE}

QSS=f"""
* {{ font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; color: {TEXT}; }}
QMainWindow, QWidget {{ background: {BG}; }}
QDialog {{ background: {BG2}; }}
QScrollArea {{ border: none; background: transparent; }}

#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1a1a1a, stop:1 #0f0f0f);
    border-right: 2px solid {ORANGE_DIM};
    min-width: 230px; max-width: 230px;
}}
#logo {{
    font-size: 16px; font-weight: 700; color: {ORANGE};
    padding: 0 20px; letter-spacing: 1px;
}}
#uni  {{ font-size: 11px; color: {TEXT2}; padding: 0 20px 16px 20px; letter-spacing: 2px; text-transform: uppercase; }}
#nav  {{
    background: transparent; color: {TEXT2}; border: none;
    border-left: 3px solid transparent;
    border-radius: 0px; padding: 12px 20px;
    text-align: left; font-size: 13px; margin: 1px 0px;
}}
#nav:hover  {{ background: rgba(255,140,66,0.08); color: {ORANGE}; border-left: 3px solid {ORANGE_DIM}; }}
#nav_on {{
    background: rgba(255,140,66,0.12); color: {ORANGE};
    border: none; border-left: 3px solid {ORANGE};
    border-radius: 0px; padding: 12px 20px;
    text-align: left; font-size: 13px; font-weight: 700; margin: 1px 0px;
}}
#ver {{ color: #404040; font-size: 11px; padding: 12px 0; letter-spacing: 1px; }}

#card {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-top: 2px solid {ORANGE_DIM};
    border-radius: 4px; padding: 20px;
}}
#card_blue  {{
    background: {BG2};
    border: 1px solid {ORANGE_DIM};
    border-top: 2px solid {ORANGE};
    border-radius: 4px; padding: 20px;
}}
#card_green {{
    background: {BG2};
    border: 1px solid #558b4a;
    border-top: 2px solid {GREEN};
    border-radius: 4px; padding: 20px;
}}

QLineEdit, QComboBox, QDateEdit {{
    background: {BG3};
    border: 1px solid {BORDER};
    border-bottom: 2px solid {BORDER};
    border-radius: 3px;
    padding: 7px 10px; color: {TEXT}; min-height: 22px;
    font-family: 'Consolas', monospace;
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border-bottom: 2px solid {ORANGE};
    background: #2a2520;
}}
QLineEdit[err="1"] {{ border-bottom: 2px solid {RED}; background: #2a1515; }}
QComboBox::drop-down {{ border: none; padding-right: 8px; }}
QComboBox QAbstractItemView {{
    background: {BG3}; border: 1px solid {BORDER};
    color: {TEXT}; selection-background-color: {ORANGE_DIM};
    outline: none;
}}

#h1   {{ font-size: 22px; font-weight: 700; color: {TEXT}; letter-spacing: 1px; }}
#sub  {{ color: {TEXT2}; font-size: 12px; letter-spacing: 1px; }}
#flbl {{ color: {ORANGE}; font-size: 11px; font-weight: 700; margin-bottom: 2px; letter-spacing: 1px; text-transform: uppercase; }}
#err  {{ color: {RED}; font-size: 11px; }}

#btn_p {{
    background: transparent; color: {ORANGE};
    border: 1px solid {ORANGE}; border-radius: 3px;
    padding: 9px 22px; font-weight: 700; min-width: 110px;
    letter-spacing: 1px;
}}
#btn_p:hover   {{ background: {ORANGE}; color: {BG}; }}
#btn_p:disabled {{ border-color: {BORDER}; color: {TEXT2}; }}
#btn_s {{
    background: transparent; color: {TEXT2};
    border: 1px solid {BORDER}; border-radius: 3px;
    padding: 9px 22px; min-width: 90px;
}}
#btn_s:hover {{ border-color: {TEXT2}; color: {TEXT}; }}
#btn_g {{
    background: transparent; color: {GREEN};
    border: 1px solid {GREEN}; border-radius: 3px;
    padding: 9px 22px; font-weight: 700;
}}
#btn_g:hover {{ background: {GREEN}; color: {BG}; }}

QTableWidget {{
    background: {BG2}; border: 1px solid {BORDER};
    border-radius: 4px; gridline-color: {BORDER};
    color: {TEXT}; alternate-background-color: {BG3};
}}
QTableWidget::item         {{ padding: 9px 12px; border-bottom: 1px solid {BORDER}; }}
QTableWidget::item:selected {{ background: rgba(255,140,66,0.15); color: {ORANGE}; }}
QHeaderView::section {{
    background: {BG}; color: {ORANGE}; font-size: 11px; font-weight: 700;
    padding: 10px 12px; border: none; border-bottom: 2px solid {ORANGE_DIM};
    letter-spacing: 2px; text-transform: uppercase;
}}

QTabWidget::pane  {{ border: 1px solid {BORDER}; border-radius: 4px; background: {BG2}; top: -1px; }}
QTabBar::tab      {{
    background: transparent; color: {TEXT2};
    padding: 9px 22px; border-bottom: 2px solid transparent;
    margin-right: 4px; border-radius: 0;
}}
QTabBar::tab:selected {{ color: {ORANGE}; border-bottom: 2px solid {ORANGE}; background: transparent; }}
QTabBar::tab:hover    {{ color: {TEXT}; background: rgba(0,201,177,0.06); }}

QGroupBox {{
    border: 1px solid {BORDER}; border-radius: 4px;
    margin-top: 10px; padding-top: 6px;
    color: {ORANGE}; font-size: 11px; font-weight: 700; letter-spacing: 1px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}

#sep {{ background: {BORDER}; max-height: 1px; margin: 6px 0; }}

QScrollBar:vertical   {{ background: {BG}; width: 5px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {ORANGE_DIM}; border-radius: 3px; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QMessageBox {{ background: {BG2}; }}
QMessageBox QPushButton {{
    background: transparent; color: {ORANGE};
    border: 1px solid {ORANGE}; border-radius: 3px;
    padding: 7px 18px; min-width: 70px;
}}
QMessageBox QPushButton:hover {{ background: {ORANGE}; color: {BG}; }}
"""

def sep():
    f=QFrame(); f.setObjectName("sep"); f.setFrameShape(QFrame.Shape.HLine); return f
def flbl(t):
    l=QLabel(t); l.setObjectName("flbl"); return l
def errlbl():
    l=QLabel(""); l.setObjectName("err"); return l
def fw(label,widget,err=None):
    w=QWidget(); v=QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(2)
    v.addWidget(flbl(label)); v.addWidget(widget)
    if err: v.addWidget(err)
    return w
def mkbtn(text,obj="btn_p"):
    b=QPushButton(text); b.setObjectName(obj); b.setCursor(Qt.CursorShape.PointingHandCursor); return b
def sh(txt,color=None):
    c=color or ORANGE; l=QLabel(txt); l.setStyleSheet(f"font-size:14px;font-weight:700;color:{c};padding:6px 0 2px 0;"); return l


class ChangePasswordDialog(QDialog):
    def __init__(self, username, full_name="", birthdate="", parent=None):
        super().__init__(parent)
        self.username = username
        self.full_name = full_name
        self.birthdate = birthdate
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("<b>First login detected — change your password.</b>"))
        self.current = QLineEdit(); self.current.setEchoMode(QLineEdit.EchoMode.Password)
        self.new = QLineEdit(); self.new.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.err = QLabel(""); self.err.setObjectName("err")
        v.addWidget(fw("Current Password", self.current))
        v.addWidget(fw("New Password", self.new))
        v.addWidget(fw("Confirm Password", self.confirm))
        v.addWidget(self.err)
        row = QHBoxLayout()
        ok = mkbtn("Update Password")
        cancel = mkbtn("Cancel", "btn_s")
        ok.clicked.connect(self._apply)
        cancel.clicked.connect(self.reject)
        row.addWidget(ok); row.addWidget(cancel); row.addStretch()
        v.addLayout(row)

    def _apply(self):
        conn = get_connection()
        rec = conn.execute("SELECT * FROM auth_user WHERE username=?", (self.username,)).fetchone()
        if not rec or not verify_password(self.current.text(), rec["password_hash"]):
            self.err.setText("Current password is incorrect."); conn.close(); return
        new_pw = self.new.text()
        if new_pw != self.confirm.text():
            self.err.setText("Password confirmation does not match."); conn.close(); return
        ok, msg = validate_password_policy(new_pw, self.username, self.full_name, self.birthdate)
        if not ok:
            self.err.setText(msg); conn.close(); return
        conn.execute(
            "UPDATE auth_user SET password_hash=?, first_login=0, password_changed_at=datetime('now') WHERE username=?",
            (hash_password(new_pw), self.username),
        )
        conn.commit(); conn.close()
        self.accept()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = None
        self.setWindowTitle("University Authentication")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        title = QLabel("Authentication System"); title.setObjectName("h1")
        v.addWidget(title)
        v.addWidget(QLabel("Use admin/admin for full management access.", objectName="sub"))
        self.username = QLineEdit(); self.username.setPlaceholderText("Username")
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password); self.password.setPlaceholderText("Password")
        self.err = QLabel(""); self.err.setObjectName("err")
        v.addWidget(fw("Username / Identity ID", self.username))
        v.addWidget(fw("Password", self.password))
        v.addWidget(self.err)
        btn = mkbtn("Login")
        btn.clicked.connect(self._login)
        v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _login(self):
        user = self.username.text().strip()
        pw = self.password.text()
        if not user or not pw:
            self.err.setText("Username and password are required."); return
        conn = get_connection()
        rec = conn.execute("SELECT * FROM auth_user WHERE username=?", (user,)).fetchone()
        if not rec:
            log_auth_event(conn, user, 0, "unknown-user")
            conn.commit(); conn.close()
            self.err.setText("Invalid credentials."); return
        if rec["locked_until"] and datetime.utcnow() < datetime.strptime(rec["locked_until"], "%Y-%m-%d %H:%M:%S"):
            self.err.setText("Account locked for 30 minutes after too many failed attempts."); conn.close(); return
        if not verify_password(pw, rec["password_hash"]):
            attempts = rec["failed_attempts"] + 1
            locked = lock_until_iso() if attempts >= 5 else None
            conn.execute("UPDATE auth_user SET failed_attempts=?, locked_until=? WHERE id=?", (attempts, locked, rec["id"]))
            log_auth_event(conn, user, 0, "invalid-password")
            conn.commit(); conn.close()
            self.err.setText("Invalid credentials."); return
        conn.execute("UPDATE auth_user SET failed_attempts=0, locked_until=NULL WHERE id=?", (rec["id"],))
        sid = str(uuid.uuid4())
        log_auth_event(conn, user, 1, "", 0, sid)
        person = conn.execute("SELECT * FROM person WHERE id=?", (rec["person_id"],)).fetchone() if rec["person_id"] else None
        conn.commit(); conn.close()
        self.session = {"username": user, "role": rec["role"], "first_login": rec["first_login"], "person": person}
        self.accept()


class StudentPortalWindow(QMainWindow):
    def __init__(self, session):
        super().__init__()
        self.session = session
        p = session["person"]
        self.setWindowTitle(f"Student Portal — {session['username']}")
        self.setMinimumSize(980, 660)
        root = QWidget(); self.setCentralWidget(root)
        v = QVBoxLayout(root); v.setContentsMargins(26, 24, 26, 24)
        h1 = QLabel("User Security Dashboard"); h1.setObjectName("h1"); v.addWidget(h1)
        v.addWidget(QLabel(f"Logged in as: {session['username']} (L1 Basic)", objectName="sub"))
        card = QWidget(); card.setObjectName("card"); g = QGridLayout(card); g.setSpacing(10)
        info = [
            ("Identity ID", p["unique_identifier"]), ("Full Name", f"{p['first_name']} {p['last_name']}"),
            ("Category", TYPE_LABELS.get(p["type"], p["type"])), ("Sub-category", p["sub_category"]),
            ("Status", p["status"]), ("Email", p["email"]), ("Phone", p["phone"]),
            ("DOB", p["date_of_birth"]),
        ]
        for i, (k, val) in enumerate(info):
            g.addWidget(QLabel(f"{k}:", styleSheet=f"color:{TEXT2};font-weight:700;"), i, 0)
            g.addWidget(QLabel(str(val)), i, 1)
        v.addWidget(card)
        hist = QTableWidget(0, 3)
        hist.setHorizontalHeaderLabels(["Time (UTC)", "Success", "Reason"])
        hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        conn = get_connection()
        rows = conn.execute("SELECT event_time,success,failure_reason FROM auth_event WHERE username=? ORDER BY id DESC LIMIT 20", (session["username"],)).fetchall()
        conn.close()
        hist.setRowCount(len(rows))
        for r, row in enumerate(rows):
            hist.setItem(r, 0, QTableWidgetItem(row["event_time"]))
            hist.setItem(r, 1, QTableWidgetItem("Yes" if row["success"] else "No"))
            hist.setItem(r, 2, QTableWidgetItem(row["failure_reason"] or "—"))
        v.addWidget(QLabel("Recent Login History", styleSheet=f"font-weight:700;color:{ORANGE};"))
        v.addWidget(hist)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IAM — University of Batna 2")
        self.setMinimumSize(1260,780); self.resize(1400,860)
        root=QWidget(); self.setCentralWidget(root)
        hl=QHBoxLayout(root); hl.setContentsMargins(0,0,0,0); hl.setSpacing(0)
        self._sb=self._make_sb(); hl.addWidget(self._sb)
        self.stack=QStackedWidget(); hl.addWidget(self.stack)
        self.p_dash=DashboardPage(self); self.p_create=CreatePage(self)
        self.p_search=SearchPage(self); self.p_update=UpdatePage(self)
        self.p_status=StatusPage(self); self.p_promote=PromotePage(self)
        for p in (self.p_dash,self.p_create,self.p_search,self.p_update,self.p_status,self.p_promote):
            self.stack.addWidget(p)
        self._btns=[]; self.goto(0)

    def _make_sb(self):
        sb=QWidget(); sb.setObjectName("sidebar")
        vl=QVBoxLayout(sb); vl.setContentsMargins(0,24,0,20); vl.setSpacing(0)
        logo=QLabel("🎓  IAM System"); logo.setObjectName("logo"); logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        uni=QLabel("University of Batna 2"); uni.setObjectName("uni"); uni.setAlignment(Qt.AlignmentFlag.AlignLeft)
        vl.addWidget(logo); vl.addWidget(uni); vl.addWidget(sep()); vl.addSpacing(6)
        items=[("🏠  Dashboard",0),("➕  Create Identity",1),("🔍  Search",2),
               ("✏️   Update",3),("🔄  Change Status",4),("🎓  Promote Student → FAC",5)]
        self._btns=[]
        for lbl,idx in items:
            b=QPushButton(lbl); b.setObjectName("nav")
            b.clicked.connect(lambda _,i=idx: self.goto(i))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            vl.addWidget(b); self._btns.append(b)
        vl.addStretch()
        ver=QLabel("v2.0  •  IAM Project"); ver.setObjectName("ver"); ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(ver); return sb

    def goto(self,idx):
        self.stack.setCurrentIndex(idx)
        for i,b in enumerate(self._btns):
            b.setObjectName("nav_on" if i==idx else "nav"); b.style().unpolish(b); b.style().polish(b)
        if idx==0: self.p_dash.refresh()
        if idx==2: self.p_search.refresh()
        if idx==3: self.p_update.reset()
        if idx==4: self.p_status.reset()
        if idx==5: self.p_promote.reset()

    def refresh_all(self): self.p_dash.refresh()


class DashboardPage(QWidget):
    def __init__(self,mw):
        super().__init__(); self.mw=mw
        vl=QVBoxLayout(self); vl.setContentsMargins(32,28,32,28); vl.setSpacing(18)
        h1=QLabel("Dashboard"); h1.setObjectName("h1"); vl.addWidget(h1)
        vl.addWidget(QLabel("Overview of all registered identities",objectName="sub"))
        self._cr=QHBoxLayout(); self._cr.setSpacing(14); vl.addLayout(self._cr)
        vl.addWidget(QLabel("Recently Registered",styleSheet=f"font-size:14px;font-weight:700;color:{TEXT};padding-top:6px;"))
        self._tbl=self._mt(["ID","Full Name","Category","Sub-category","Status","Created"])
        self._tbl.setMaximumHeight(280); vl.addWidget(self._tbl); vl.addStretch(); self.refresh()

    def _mt(self,h):
        t=QTableWidget(0,len(h)); t.setHorizontalHeaderLabels(h)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False); t.setAlternatingRowColors(True); return t

    def refresh(self):
        conn=get_connection(); total=conn.execute("SELECT COUNT(*) FROM person").fetchone()[0]
        while self._cr.count():
            it=self._cr.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self._card("Total",total,TEXT,"All identities")
        for code,lbl in TYPE_LABELS.items():
            cnt=conn.execute("SELECT COUNT(*) FROM person WHERE type=?",(code,)).fetchone()[0]
            self._card(lbl,cnt,CAT_CLR.get(code,TEXT),code)
        arch=conn.execute("SELECT COUNT(*) FROM person WHERE status='Archived'").fetchone()[0]
        self._card("Archived",arch,STATUS_CLR["Archived"],"Archived")
        rows=conn.execute("SELECT unique_identifier,first_name,last_name,type,sub_category,status,created_at FROM person ORDER BY created_at DESC LIMIT 12").fetchall()
        conn.close()
        self._tbl.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=[row["unique_identifier"],f"{row['first_name']} {row['last_name']}",
                  TYPE_LABELS.get(row["type"],row["type"]),row["sub_category"],row["status"],row["created_at"][:10]]
            for c,v in enumerate(vals):
                item=QTableWidgetItem(v); item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
                if c==4: item.setForeground(QColor(STATUS_CLR.get(v,TEXT)))
                self._tbl.setItem(r,c,item)

    def _card(self,title,value,color,subtitle=""):
        card=QWidget(); card.setObjectName("card"); vl=QVBoxLayout(card); vl.setSpacing(3)
        num=QLabel(str(value)); num.setStyleSheet(f"font-size:30px;font-weight:700;color:{color};")
        t=QLabel(title); t.setStyleSheet(f"font-size:13px;font-weight:600;color:{TEXT};")
        s=QLabel(subtitle); s.setStyleSheet(f"font-size:11px;color:{TEXT2};")
        vl.addWidget(num); vl.addWidget(t); vl.addWidget(s); self._cr.addWidget(card)


class CreatePage(QWidget):
    def __init__(self,mw):
        super().__init__(); self.mw=mw
        self._cat=None; self._sub=None; self._fields={}; self._errs={}
        outer=QVBoxLayout(self); outer.setContentsMargins(32,28,32,28); outer.setSpacing(0)
        h1=QLabel("Create New Identity"); h1.setObjectName("h1"); outer.addWidget(h1)
        outer.addWidget(QLabel("Register a new person in the system",objectName="sub")); outer.addSpacing(12)
        self._sa=QScrollArea(); self._sa.setWidgetResizable(True)
        self._sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(self._sa)
        self._con=QWidget(); self._vl=QVBoxLayout(self._con)
        self._vl.setSpacing(16); self._vl.setContentsMargins(0,4,16,8)
        self._sa.setWidget(self._con); self._step0()

    def _clr(self):
        while self._vl.count():
            it=self._vl.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self._fields={}; self._errs={}

    def _step0(self):
        self._clr()
        card=QWidget(); card.setObjectName("card"); cv=QVBoxLayout(card); cv.setSpacing(14)
        cv.addWidget(QLabel("Step 1 — Choose Category and Sub-category",styleSheet=f"font-weight:700;font-size:14px;color:{ORANGE};"))
        row=QHBoxLayout(); row.setSpacing(16)
        g1=QGroupBox("Category"); gl1=QVBoxLayout(g1)
        self._cc=QComboBox()
        for k,v in CATEGORIES.items(): self._cc.addItem(v["label"],k)
        self._cc.currentIndexChanged.connect(self._sync_sub); gl1.addWidget(self._cc); row.addWidget(g1)
        g2=QGroupBox("Sub-category"); gl2=QVBoxLayout(g2)
        self._sc=QComboBox(); gl2.addWidget(self._sc); row.addWidget(g2)
        cv.addLayout(row)
        btn=mkbtn("Continue  →"); btn.clicked.connect(self._step0_next)
        cv.addWidget(btn,alignment=Qt.AlignmentFlag.AlignLeft)
        self._vl.addWidget(card); self._vl.addStretch(); self._sync_sub(0)

    def _sync_sub(self,_):
        code=self._cc.currentData(); self._sc.clear()
        if code:
            for s in CATEGORIES[code]["subcategories"]: self._sc.addItem(s)

    def _step0_next(self):
        self._cat=self._cc.currentData(); self._sub=self._sc.currentText()
        if self._cat and self._sub: self._build_form()

    def _build_form(self):
        self._clr()
        back=mkbtn("← Back","btn_s"); back.clicked.connect(self._step0)
        crumb=QLabel(f"  {CATEGORIES[self._cat]['label']}  ›  {self._sub}")
        crumb.setStyleSheet(f"color:{ORANGE};font-size:12px;")
        top=QHBoxLayout(); top.addWidget(back); top.addWidget(crumb); top.addStretch()
        tw=QWidget(); tw.setLayout(top); self._vl.addWidget(tw)
        # common
        self._vl.addWidget(sh("Common Information"))
        cc=QWidget(); cc.setObjectName("card"); cg=QGridLayout(cc); cg.setSpacing(10)
        self._tf(cg,0,0,"First Name *","first_name"); self._tf(cg,0,1,"Last Name *","last_name")
        self._tf(cg,1,0,"Place of Birth *","place_of_birth"); self._tf(cg,1,1,"Nationality *","nationality")
        self._tf(cg,2,0,"Email *","email"); self._tf(cg,2,1,"Phone * (digits only)","phone")
        dob=QDateEdit(); dob.setCalendarPopup(True); dob.setDisplayFormat("yyyy-MM-dd")
        dob.setDate(QDate(2000,1,1)); dob.setMaximumDate(QDate.currentDate())
        self._fields["dob"]=dob; e=errlbl(); self._errs["dob"]=e
        cg.addWidget(fw("Date of Birth *",dob,e),3,0)
        gen=QComboBox(); gen.addItems(["Male","Female"]); self._fields["gender"]=gen
        cg.addWidget(fw("Gender *",gen),3,1); self._vl.addWidget(cc)
        # type-specific
        if   self._cat=="STU": self._form_stu()
        elif self._cat=="FAC": self._form_fac()
        elif self._cat=="STF": self._form_stf()
        # submit
        row=QHBoxLayout()
        ok=mkbtn("✓  Create Identity"); ok.setMinimumHeight(42); ok.clicked.connect(self._submit)
        rst=mkbtn("Reset","btn_s"); rst.clicked.connect(self._step0)
        row.addWidget(ok); row.addWidget(rst); row.addStretch()
        rw=QWidget(); rw.setLayout(row); self._vl.addWidget(rw); self._vl.addStretch()

    def _form_stu(self):
        self._vl.addWidget(sh("Academic Information"))
        card=QWidget(); card.setObjectName("card"); g=QGridLayout(card); g.setSpacing(10)
        hst=QComboBox(); hst.addItems(HIGH_SCHOOL_TYPES); self._fields["hs_type"]=hst
        g.addWidget(fw("High School Type *",hst),0,0)
        hsh=QComboBox(); hsh.addItems(HONORS_LIST); self._fields["hs_honors"]=hsh
        g.addWidget(fw("High School Honors *",hsh),0,1)
        self._tf(g,1,0,"High School Year * (YYYY)","hs_year")
        self._tf(g,1,1,"Entry Year * (YYYY)","entry_year")
        fac=QComboBox(); fac.addItems(FACULTIES); self._fields["fac"]=fac
        g.addWidget(fw("Faculty *",fac),2,0)
        dept=QComboBox(); self._fields["dept"]=dept; g.addWidget(fw("Department *",dept),2,1)
        maj=QComboBox(); self._fields["major"]=maj; g.addWidget(fw("Major *",maj),3,0)
        fac.currentTextChanged.connect(lambda f: self._sync_dept(f,dept,maj))
        dept.currentTextChanged.connect(lambda d: self._sync_maj(fac.currentText(),d,maj))
        self._sync_dept(fac.currentText(),dept,maj)
        if self._sub in ("Undergraduate","Continuing Education"):
            grp=QComboBox(); grp.addItems(GROUPS); self._fields["group"]=grp
            g.addWidget(fw("Group *",grp),3,1)
        sch=QComboBox(); sch.addItems(["No","Yes"]); self._fields["scholarship"]=sch
        g.addWidget(fw("Scholarship *",sch),4,0); self._vl.addWidget(card)

    def _form_fac(self):
        self._vl.addWidget(sh("Professional Information"))
        card=QWidget(); card.setObjectName("card"); g=QGridLayout(card); g.setSpacing(10)
        rm={"Tenured":["Professor","Associate Professor","Assistant Professor"],
            "Adjunct / Part-time":["Assistant Professor","Lecturer","Teaching Assistant"],
            "Visiting Researcher":FACULTY_RANKS}
        rank=QComboBox(); rank.addItems(rm.get(self._sub,FACULTY_RANKS)); self._fields["rank"]=rank
        g.addWidget(fw("Rank *",rank),0,0)
        emp=QComboBox(); emp.addItems(EMPLOYMENT_CATS); self._fields["emp_cat"]=emp
        g.addWidget(fw("Employment Category *",emp),0,1)
        appt=QDateEdit(); appt.setCalendarPopup(True); appt.setDisplayFormat("yyyy-MM-dd")
        appt.setDate(QDate.currentDate()); self._fields["appt_start"]=appt
        g.addWidget(fw("Appointment Start *",appt),1,0)
        dpt=QComboBox(); dpt.addItems(DEPARTMENTS); self._fields["primary_dept"]=dpt
        g.addWidget(fw("Primary Department *",dpt),1,1)
        self._tf(g,2,0,"Secondary Departments (optional)","secondary")
        self._tf(g,2,1,"PhD Institution (optional)","phd_inst")
        self._tf(g,3,0,"Research Areas (optional)","research")
        self._tf(g,3,1,"Office Building (optional)","bldg")
        self._tf(g,4,0,"Office Floor (optional)","floor")
        self._tf(g,4,1,"Office Room (optional)","room")
        hdr=QComboBox(); hdr.addItems(["No","Yes"]); self._fields["hdr"]=hdr
        g.addWidget(fw("HDR *",hdr),5,0); self._vl.addWidget(card)
        self._vl.addWidget(sh("Contract"))
        c2=QWidget(); c2.setObjectName("card"); g2=QGridLayout(c2); g2.setSpacing(10)
        ct=QComboBox(); ct.addItems(CONTRACT_TYPES); self._fields["contract_type"]=ct
        g2.addWidget(fw("Contract Type *",ct),0,0)
        cs=QDateEdit(); cs.setCalendarPopup(True); cs.setDisplayFormat("yyyy-MM-dd")
        cs.setDate(QDate.currentDate()); self._fields["contract_start"]=cs
        g2.addWidget(fw("Contract Start *",cs),0,1)
        ce=QDateEdit(); ce.setCalendarPopup(True); ce.setDisplayFormat("yyyy-MM-dd")
        ce.setDate(QDate(2099,12,31)); self._fields["contract_end"]=ce
        g2.addWidget(fw("Contract End (optional)",ce),1,0)
        self._tf(g2,1,1,"Teaching Hours / week *","teaching_h"); self._vl.addWidget(c2)

    def _form_stf(self):
        self._vl.addWidget(sh("Staff Information"))
        card=QWidget(); card.setObjectName("card"); g=QGridLayout(card); g.setSpacing(10)
        dept=QComboBox(); dept.addItems(DEPARTMENTS); self._fields["dept"]=dept
        g.addWidget(fw("Department *",dept),0,0)
        self._tf(g,0,1,"Job Title *","job_title")
        grade=QComboBox(); grade.addItems(STAFF_GRADES); self._fields["grade"]=grade
        g.addWidget(fw("Grade *",grade),1,0)
        ed=QDateEdit(); ed.setCalendarPopup(True); ed.setDisplayFormat("yyyy-MM-dd")
        ed.setDate(QDate.currentDate()); self._fields["entry_date"]=ed
        g.addWidget(fw("Date of Entry *",ed),1,1); self._vl.addWidget(card)

    def _sync_dept(self,f,dc,mc):
        dc.clear()
        if f in FACULTY_CATALOG: dc.addItems(list(FACULTY_CATALOG[f].keys()))
        self._sync_maj(f,dc.currentText(),mc)
    def _sync_maj(self,f,d,mc):
        mc.clear()
        if f in FACULTY_CATALOG and d in FACULTY_CATALOG[f]: mc.addItems(FACULTY_CATALOG[f][d])

    def _tf(self,g,r,c,label,key):
        le=QLineEdit(); le.setPlaceholderText(label.replace(" *","").replace(" (optional)",""))
        self._fields[key]=le; e=errlbl(); self._errs[key]=e; g.addWidget(fw(label,le,e),r,c)

    def _get(self,k,default=""):
        w=self._fields.get(k)
        if w is None: return default
        if isinstance(w,QLineEdit): return w.text().strip()
        if isinstance(w,QComboBox): return w.currentText()
        if isinstance(w,QDateEdit): return w.date().toString("yyyy-MM-dd")
        return default

    def _serr(self,k,m):
        if k in self._errs: self._errs[k].setText(m)
        if k in self._fields:
            w=self._fields[k]
            if isinstance(w,QLineEdit):
                w.setProperty("err","1" if m else "0"); w.style().unpolish(w); w.style().polish(w)
    def _cerrs(self):
        for k in self._errs: self._serr(k,"")

    def _submit(self):
        self._cerrs(); errors={}
        fn=self._get("first_name"); ln=self._get("last_name")
        if len(fn)<2: errors["first_name"]="Minimum 2 characters."
        elif letters_only(fn): errors["first_name"]=letters_only(fn)
        if len(ln)<2: errors["last_name"]="Minimum 2 characters."
        elif letters_only(ln): errors["last_name"]=letters_only(ln)
        for k in ("place_of_birth","nationality"):
            v=self._get(k)
            if not v: errors[k]="Required."
            elif letters_only(v): errors[k]=letters_only(v)
        dob=self._get("dob"); age=calc_age(dob)
        ma=MIN_AGE.get(self._cat,16)
        if age<ma: errors["dob"]=f"Minimum age for {CATEGORIES[self._cat]['label']} is {ma}."
        email=self._get("email")
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$",email): errors["email"]="Invalid email."
        else:
            conn=get_connection()
            if conn.execute("SELECT id FROM person WHERE email=?",(email,)).fetchone(): errors["email"]="Email in use."
            conn.close()
        phone=self._get("phone")
        if not re.match(r"^\d{9,15}$",phone): errors["phone"]="Digits only, 9-15 chars."
        else:
            conn=get_connection()
            if conn.execute("SELECT id FROM person WHERE phone=?",(phone,)).fetchone(): errors["phone"]="Phone in use."
            conn.close()
        conn=get_connection()
        if not errors.get("first_name") and not errors.get("last_name") and not errors.get("dob"):
            if conn.execute("SELECT id FROM person WHERE first_name=? AND last_name=? AND date_of_birth=?",(fn,ln,dob)).fetchone():
                errors["first_name"]="Duplicate: same name + DOB exists."
        conn.close()
        if self._cat=="STU":
            hy=self._get("hs_year"); ey=self._get("entry_year"); by=int(dob.split("-")[0])
            if not hy.isdigit() or int(hy)<by+17: errors["hs_year"]=f"Must be >= {by+17}."
            if not ey.isdigit() or (hy.isdigit() and int(ey)<int(hy)): errors["entry_year"]="Must be >= HS year."
        if self._cat=="FAC":
            try: float(self._get("teaching_h"))
            except: errors["teaching_h"]="Must be a number."
        if self._cat=="STF" and len(self._get("job_title"))<2: errors["job_title"]="Required."
        for k,m in errors.items(): self._serr(k,m)
        if errors: return
        conn=get_connection()
        try: new_id,prefix=generate_id(conn,self._sub)
        except ValueError as e: QMessageBox.critical(self,"ID Limit",str(e)); conn.close(); return
        gen="M" if self._get("gender")=="Male" else "F"
        conn.execute("INSERT INTO person (unique_identifier,type,sub_category,id_prefix,status,first_name,last_name,date_of_birth,place_of_birth,nationality,gender,email,phone) VALUES (?,?,?,?,'Pending',?,?,?,?,?,?,?,?)",
            (new_id,self._cat,self._sub,prefix,fn,ln,dob,self._get("place_of_birth"),self._get("nationality"),gen,email,phone))
        pid=conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        log_history(conn,pid,"CREATE",note=f"{CATEGORIES[self._cat]['label']} — {self._sub}")
        if self._cat=="STU":
            grp=self._get("group") if "group" in self._fields else None
            conn.execute("INSERT INTO student (person_id,high_school_type,high_school_year,high_school_honors,major,entry_year,academic_status,faculty,department,group_name,scholarship) VALUES (?,?,?,?,?,?,'Active',?,?,?,?)",
                (pid,self._get("hs_type"),int(self._get("hs_year")),self._get("hs_honors"),self._get("major"),int(self._get("entry_year")),self._get("fac"),self._get("dept"),grp,"yes" if self._get("scholarship")=="Yes" else "no"))
        elif self._cat=="FAC":
            conn.execute("INSERT INTO faculty (person_id,rank,employment_category,appointment_start,primary_department,secondary_departments,office_building,office_floor,office_room,phd_institution,research_areas,hdr,contract_type,contract_start,contract_end,teaching_hours) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pid,self._get("rank"),self._get("emp_cat"),self._get("appt_start"),self._get("primary_dept"),self._get("secondary") or None,self._get("bldg") or None,self._get("floor") or None,self._get("room") or None,self._get("phd_inst") or None,self._get("research") or None,1 if self._get("hdr")=="Yes" else 0,self._get("contract_type"),self._get("contract_start"),self._get("contract_end") or None,float(self._get("teaching_h"))))
        elif self._cat=="STF":
            conn.execute("INSERT INTO staff (person_id,department,job_title,grade,entry_date) VALUES (?,?,?,?,?)",
                (pid,self._get("dept"),self._get("job_title"),self._get("grade"),self._get("entry_date")))
        ensure_person_auth_user(conn, pid, new_id, dob)
        conn.commit(); conn.close()
        d=QDialog(self); d.setWindowTitle("Identity Created"); d.setMinimumWidth(340)
        dv=QVBoxLayout(d); dv.setContentsMargins(28,28,28,28); dv.setSpacing(10)
        dv.addWidget(QLabel("✓",styleSheet=f"font-size:44px;color:{GREEN};",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(QLabel("<b>Identity Created Successfully</b>",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(QLabel(f"Name: <b>{fn} {ln}</b>",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(QLabel(f"<span style='font-size:16px;font-weight:700;color:{ORANGE};'>{new_id}</span>",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(QLabel(f"Login username: <b>{new_id}</b>",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(QLabel(f"Temporary password: <b>{dob.replace('-','')}</b>",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(QLabel(f"Status: <b style='color:{ORANGE};'>Pending</b>",alignment=Qt.AlignmentFlag.AlignCenter))
        ok=mkbtn("OK"); ok.clicked.connect(d.accept); dv.addWidget(ok,alignment=Qt.AlignmentFlag.AlignCenter)
        d.exec(); self.mw.refresh_all(); self._step0()


class SearchPage(QWidget):
    def __init__(self,mw):
        super().__init__(); self.mw=mw
        vl=QVBoxLayout(self); vl.setContentsMargins(32,28,32,28); vl.setSpacing(14)
        vl.addWidget(QLabel("Search Identities",objectName="h1"))
        bar=QHBoxLayout(); bar.setSpacing(10)
        self.q=QLineEdit(); self.q.setPlaceholderText("Search name, ID, email, phone…")
        self.q.textChanged.connect(self._load); bar.addWidget(self.q,3)
        self.fc=QComboBox(); self.fc.addItem("All Categories","")
        for k,v in CATEGORIES.items(): self.fc.addItem(v["label"],k)
        self.fc.currentIndexChanged.connect(self._load); bar.addWidget(self.fc)
        self.fs=QComboBox(); self.fs.addItems(["All Statuses","Pending","Active","Suspended","Inactive","Archived"])
        self.fs.currentIndexChanged.connect(self._load); bar.addWidget(self.fs)
        vl.addLayout(bar)
        self.tbl=QTableWidget(0,7); self.tbl.setHorizontalHeaderLabels(["ID","Full Name","Category","Sub-category","Status","Email","Phone"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setAlternatingRowColors(True)
        self.tbl.itemDoubleClicked.connect(self._detail); vl.addWidget(self.tbl)
        self.cnt=QLabel(""); self.cnt.setStyleSheet(f"color:{TEXT2};font-size:12px;"); vl.addWidget(self.cnt); self._load()

    def refresh(self): self._load()

    def _load(self):
        q=self.q.text().strip(); cat=self.fc.currentData(); sta=self.fs.currentText()
        sql="SELECT * FROM person WHERE 1=1"; p=[]
        
        # Support searching by full name (e.g., "bob nad" or "nad bob")
        if q:
            words = q.split()
            if len(words) >= 2:
                # Multiple words - search for name combinations in any order
                word1, word2 = words[0], words[1]
                sql+=" AND (unique_identifier LIKE ? OR email LIKE ? OR phone LIKE ? OR ((first_name LIKE ? AND last_name LIKE ?) OR (first_name LIKE ? AND last_name LIKE ?)) OR first_name LIKE ? OR last_name LIKE ?)"
                p+=[f"%{q}%", f"%{q}%", f"%{q}%", f"%{word1}%", f"%{word2}%", f"%{word2}%", f"%{word1}%", f"%{q}%", f"%{q}%"]
            else:
                # Single word search
                sql+=" AND (first_name LIKE ? OR last_name LIKE ? OR unique_identifier LIKE ? OR email LIKE ? OR phone LIKE ?)"
                p+=[f"%{q}%"]*5
        
        if cat: sql+=" AND type=?"; p.append(cat)
        if sta!="All Statuses": sql+=" AND status=?"; p.append(sta)
        sql+=" ORDER BY created_at DESC"
        conn=get_connection(); rows=conn.execute(sql,p).fetchall(); conn.close()
        self.tbl.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=[row["unique_identifier"],f"{row['first_name']} {row['last_name']}",
                  TYPE_LABELS.get(row["type"],row["type"]),row["sub_category"],row["status"],row["email"],row["phone"]]
            for c,v in enumerate(vals):
                item=QTableWidgetItem(v); item.setData(Qt.ItemDataRole.UserRole,dict(row))
                if c==4: item.setForeground(QColor(STATUS_CLR.get(v,TEXT)))
                self.tbl.setItem(r,c,item)
        self.cnt.setText(f"{len(rows)} record(s) found")

    def _detail(self,item):
        data=item.data(Qt.ItemDataRole.UserRole)
        if data: PersonDetailDlg(data,self).exec(); self._load()


class PersonDetailDlg(QDialog):
    def __init__(self,person,parent=None):
        super().__init__(parent); self.p=person
        self.setWindowTitle(f"Identity — {person['unique_identifier']}"); self.setMinimumSize(720,560)
        vl=QVBoxLayout(self); vl.setContentsMargins(24,24,24,24); vl.setSpacing(14)
        hl=QHBoxLayout()
        il=QLabel(person["unique_identifier"]); il.setStyleSheet(f"font-size:18px;font-weight:700;color:{ORANGE};")
        nl=QLabel(f"  {person['first_name']} {person['last_name']}"); nl.setStyleSheet(f"font-size:15px;")
        sl=QLabel(f"  {person['status']}"); sl.setStyleSheet(f"color:{STATUS_CLR.get(person['status'],TEXT)};font-weight:700;")
        hl.addWidget(il); hl.addWidget(nl); hl.addWidget(sl); hl.addStretch(); vl.addLayout(hl); vl.addWidget(sep())
        tabs=QTabWidget()
        tabs.addTab(self._tab_common(),"Common"); tabs.addTab(self._tab_specific(),"Specific"); tabs.addTab(self._tab_history(),"History")
        vl.addWidget(tabs)
        close=mkbtn("Close","btn_s"); close.clicked.connect(self.accept); vl.addWidget(close,alignment=Qt.AlignmentFlag.AlignRight)

    def _kv(self,k,v):
        w=QWidget(); h=QHBoxLayout(w); h.setContentsMargins(0,2,0,2)
        kl=QLabel(k+":"); kl.setStyleSheet(f"color:{TEXT2};min-width:200px;")
        vl=QLabel(str(v or "—")); vl.setWordWrap(True)
        h.addWidget(kl); h.addWidget(vl); h.addStretch(); return w

    def _tab_common(self):
        sa=QScrollArea(); sa.setWidgetResizable(True)
        inner=QWidget(); vl=QVBoxLayout(inner); vl.setSpacing(2); vl.setContentsMargins(12,12,12,12)
        p=self.p
        for k,v in [("Full Name",f"{p['first_name']} {p['last_name']}"),("Unique ID",p["unique_identifier"]),
                    ("Category",TYPE_LABELS.get(p["type"],p["type"])),("Sub-category",p["sub_category"]),
                    ("Status",p["status"]),("Date of Birth",p["date_of_birth"]),("Place of Birth",p["place_of_birth"]),
                    ("Nationality",p["nationality"]),("Gender","Male" if p["gender"]=="M" else "Female"),
                    ("Email",p["email"]),("Phone",p["phone"]),
                    ("Previous Identity ID",p.get("previous_identity_id") or "—"),
                    ("Created",p["created_at"]),("Updated",p["updated_at"])]:
            vl.addWidget(self._kv(k,v))
        vl.addStretch(); sa.setWidget(inner); return sa

    def _tab_specific(self):
        sa=QScrollArea(); sa.setWidgetResizable(True)
        inner=QWidget(); vl=QVBoxLayout(inner); vl.setSpacing(2); vl.setContentsMargins(12,12,12,12)
        conn=get_connection(); t=self.p["type"]; pairs=[]
        if t=="STU":
            s=conn.execute("SELECT * FROM student WHERE person_id=?",(self.p["id"],)).fetchone()
            if s: pairs=[("HS Type",s["high_school_type"]),("HS Year",s["high_school_year"]),("HS Honors",s["high_school_honors"]),("Faculty",s["faculty"]),("Department",s["department"]),("Major",s["major"]),("Entry Year",s["entry_year"]),("Group",s["group_name"]),("Scholarship",s["scholarship"]),("Academic Status",s["academic_status"])]
        elif t=="FAC":
            f=conn.execute("SELECT * FROM faculty WHERE person_id=?",(self.p["id"],)).fetchone()
            if f: pairs=[("Rank",f["rank"]),("Employment Cat.",f["employment_category"]),("Appt. Start",f["appointment_start"]),("Primary Dept.",f["primary_department"]),("Secondary Depts.",f["secondary_departments"]),("Office",f"Bldg:{f['office_building']} Floor:{f['office_floor']} Room:{f['office_room']}"),("PhD Institution",f["phd_institution"]),("Research Areas",f["research_areas"]),("HDR","Yes" if f["hdr"] else "No"),("Contract Type",f["contract_type"]),("Contract Start",f["contract_start"]),("Contract End",f["contract_end"] or "Open-ended"),("Teaching Hrs/wk",f["teaching_hours"])]
        elif t=="STF":
            s=conn.execute("SELECT * FROM staff WHERE person_id=?",(self.p["id"],)).fetchone()
            if s: pairs=[("Department",s["department"]),("Job Title",s["job_title"]),("Grade",s["grade"]),("Entry Date",s["entry_date"])]
        conn.close()
        for k,v in pairs: vl.addWidget(self._kv(k,v))
        if not pairs: vl.addWidget(QLabel("No specific data.",styleSheet=f"color:{TEXT2};"))
        vl.addStretch(); sa.setWidget(inner); return sa

    def _tab_history(self):
        sa=QScrollArea(); sa.setWidgetResizable(True)
        inner=QWidget(); vl=QVBoxLayout(inner); vl.setSpacing(8); vl.setContentsMargins(12,12,12,12)
        conn=get_connection()
        rows=conn.execute("SELECT * FROM history WHERE person_id=? ORDER BY changed_at DESC",(self.p["id"],)).fetchall()
        conn.close()
        if not rows: vl.addWidget(QLabel("No history.",styleSheet=f"color:{TEXT2};"))
        for r in rows:
            card=QWidget(); card.setObjectName("card"); cv=QVBoxLayout(card); cv.setSpacing(2)
            cv.addWidget(QLabel(f"<b>{r['action']}</b>  <span style='color:{TEXT2};font-size:11px;'>{r['changed_at']}</span>"))
            if r["field_name"]: cv.addWidget(QLabel(f"  {r['field_name']}: {r['old_value'] or '—'} → {r['new_value'] or '—'}",styleSheet=f"color:{TEXT2};font-size:12px;"))
            if r["note"]: cv.addWidget(QLabel(f"  Note: {r['note']}",styleSheet=f"color:{TEXT2};font-size:11px;"))
            vl.addWidget(card)
        vl.addStretch(); sa.setWidget(inner); return sa


class UpdatePage(QWidget):
    def __init__(self,mw):
        super().__init__(); self.mw=mw; self._person=None
        vl=QVBoxLayout(self); vl.setContentsMargins(32,28,32,28); vl.setSpacing(14)
        vl.addWidget(QLabel("Update Identity",objectName="h1"))
        vl.addWidget(QLabel("Search for a person then edit their information",objectName="sub"))
        self.q=QLineEdit(); self.q.setPlaceholderText("Search name or ID…"); self.q.textChanged.connect(self._search); vl.addWidget(self.q)
        self.rtbl=QTableWidget(0,5); self.rtbl.setHorizontalHeaderLabels(["ID","Full Name","Type","Sub-category","Status"])
        self.rtbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rtbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rtbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rtbl.verticalHeader().setVisible(False); self.rtbl.setMaximumHeight(200)
        self.rtbl.itemSelectionChanged.connect(self._on_sel); vl.addWidget(self.rtbl)
        self._ep=QWidget(); self._ep.hide()
        ev=QVBoxLayout(self._ep); ev.setSpacing(14); ev.setContentsMargins(0,0,0,0)
        self._etitle=QLabel(""); self._etitle.setStyleSheet(f"font-size:14px;font-weight:700;color:{TEXT};")
        ev.addWidget(self._etitle)
        self._tabs=QTabWidget(); ev.addWidget(self._tabs)
        sr=QHBoxLayout()
        sv=mkbtn("💾  Save Changes"); sv.clicked.connect(self._save)
        cx=mkbtn("Cancel","btn_s"); cx.clicked.connect(self.reset)
        sr.addWidget(sv); sr.addWidget(cx); sr.addStretch()
        sw=QWidget(); sw.setLayout(sr); ev.addWidget(sw)
        sa=QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(self._ep); vl.addWidget(sa)
        self._ef={}; self._ee={}

    def reset(self):
        self.q.clear(); self.rtbl.setRowCount(0); self._ep.hide(); self._person=None

    def _search(self):
        q=self.q.text().strip()
        if not q: self.rtbl.setRowCount(0); self._ep.hide(); return
        conn=get_connection()
        
        # Support searching by full name (e.g., "bob nad" or "nad bob")
        words = q.split()
        if len(words) >= 2:
            # Multiple words - search for name combinations in any order
            word1, word2 = words[0], words[1]
            rows=conn.execute("""SELECT * FROM person WHERE 
                unique_identifier LIKE ? OR 
                ((first_name LIKE ? AND last_name LIKE ?) OR (first_name LIKE ? AND last_name LIKE ?)) OR 
                first_name LIKE ? OR last_name LIKE ?
                ORDER BY last_name""",(f"%{q}%", f"%{word1}%", f"%{word2}%", f"%{word2}%", f"%{word1}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows=conn.execute("SELECT * FROM person WHERE first_name LIKE ? OR last_name LIKE ? OR unique_identifier LIKE ? ORDER BY last_name",(f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        
        conn.close(); self.rtbl.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,v in enumerate([row["unique_identifier"],f"{row['first_name']} {row['last_name']}",TYPE_LABELS.get(row["type"],row["type"]),row["sub_category"],row["status"]]):
                item=QTableWidgetItem(v); item.setData(Qt.ItemDataRole.UserRole,dict(row))
                if c==4: item.setForeground(QColor(STATUS_CLR.get(v,TEXT)))
                self.rtbl.setItem(r,c,item)

    def _on_sel(self):
        sel=self.rtbl.selectedItems()
        if not sel: return
        p=self.rtbl.item(self.rtbl.currentRow(),0).data(Qt.ItemDataRole.UserRole)
        if p: self._load_edit(p)

    def _mef(self,lbl,key,val,validator=None):
        le=QLineEdit(str(val or "")); le.setPlaceholderText(lbl)
        self._ef[key]=("text",le,validator); e=errlbl(); self._ee[key]=e; return fw(lbl,le,e)
    def _mec(self,lbl,key,opts,curr):
        cb=QComboBox(); cb.addItems(opts)
        if curr in opts: cb.setCurrentText(curr)
        self._ef[key]=("combo",cb,None); return fw(lbl,cb)
    def _med(self,lbl,key,val):
        de=QDateEdit(); de.setCalendarPopup(True); de.setDisplayFormat("yyyy-MM-dd")
        try: de.setDate(QDate.fromString(str(val),"yyyy-MM-dd"))
        except: de.setDate(QDate.currentDate())
        self._ef[key]=("date",de,None); return fw(lbl,de)

    def _load_edit(self,person):
        self._person=person; self._ef={}; self._ee={}
        self._etitle.setText(f"Editing: {person['first_name']} {person['last_name']}  [{person['unique_identifier']}]")
        while self._tabs.count(): self._tabs.removeTab(0)
        self._tabs.addTab(self._tab_common(person),"Common Info")
        t=person["type"]
        if t=="STU": self._tabs.addTab(self._tab_stu(person),"Academic")
        elif t=="FAC": self._tabs.addTab(self._tab_fac(person),"Faculty")
        elif t=="STF": self._tabs.addTab(self._tab_stf(person),"Staff")
        self._ep.show()

    def _tab_common(self,p):
        w=QWidget(); g=QGridLayout(w); g.setSpacing(10); g.setContentsMargins(12,12,12,12)
        g.addWidget(self._mef("First Name *","first_name",p["first_name"],lambda v:"Min 2 chars." if len(v)<2 else letters_only(v)),0,0)
        g.addWidget(self._mef("Last Name *","last_name",p["last_name"],lambda v:"Min 2 chars." if len(v)<2 else letters_only(v)),0,1)
        g.addWidget(self._mef("Place of Birth","place_of_birth",p["place_of_birth"],letters_only),1,0)
        g.addWidget(self._mef("Nationality","nationality",p["nationality"],letters_only),1,1)
        g.addWidget(self._mef("Phone","phone",p["phone"],lambda v:"Digits 9-15." if not re.match(r"^\d{9,15}$",v) else None),2,0)
        return w

    def _tab_stu(self,p):
        conn=get_connection(); s=conn.execute("SELECT * FROM student WHERE person_id=?",(p["id"],)).fetchone(); conn.close()
        if not s: return QLabel("No student data.")
        w=QWidget(); g=QGridLayout(w); g.setSpacing(10); g.setContentsMargins(12,12,12,12)
        g.addWidget(self._mec("HS Honors","hs_honors",HONORS_LIST,s["high_school_honors"]),0,0)
        g.addWidget(self._mec("Faculty","fac",FACULTIES,s["faculty"]),0,1)
        g.addWidget(self._mec("Department","dept_stu",DEPARTMENTS,s["department"]),1,0)
        g.addWidget(self._mec("Group","group",GROUPS,s["group_name"] or GROUPS[0]),1,1)
        g.addWidget(self._mec("Scholarship","scholarship",["yes","no"],s["scholarship"]),2,0)
        return w

    def _tab_fac(self,p):
        conn=get_connection(); f=conn.execute("SELECT * FROM faculty WHERE person_id=?",(p["id"],)).fetchone(); conn.close()
        if not f: return QLabel("No faculty data.")
        w=QWidget(); g=QGridLayout(w); g.setSpacing(10); g.setContentsMargins(12,12,12,12)
        g.addWidget(self._mec("Rank","rank",FACULTY_RANKS,f["rank"]),0,0)
        g.addWidget(self._mec("Employment Cat.","emp_cat",EMPLOYMENT_CATS,f["employment_category"]),0,1)
        g.addWidget(self._mec("Primary Dept.","primary_dept",DEPARTMENTS,f["primary_department"]),1,0)
        g.addWidget(self._mef("Secondary Depts.","secondary",f["secondary_departments"]),1,1)
        g.addWidget(self._mef("Research Areas","research",f["research_areas"]),2,0)
        g.addWidget(self._mef("Teaching Hours","teaching_h",f["teaching_hours"],lambda v:"Must be number." if not v.replace(".","",1).isdigit() else None),2,1)
        g.addWidget(self._mec("Contract Type","contract_type",CONTRACT_TYPES,f["contract_type"]),3,0)
        g.addWidget(self._med("Contract End","contract_end",f["contract_end"]),3,1)
        return w

    def _tab_stf(self,p):
        conn=get_connection(); s=conn.execute("SELECT * FROM staff WHERE person_id=?",(p["id"],)).fetchone(); conn.close()
        if not s: return QLabel("No staff data.")
        w=QWidget(); g=QGridLayout(w); g.setSpacing(10); g.setContentsMargins(12,12,12,12)
        g.addWidget(self._mec("Department","dept_stf",DEPARTMENTS,s["department"]),0,0)
        g.addWidget(self._mef("Job Title","job_title",s["job_title"]),0,1)
        g.addWidget(self._mec("Grade","grade",STAFF_GRADES,s["grade"]),1,0)
        return w

    def _save(self):
        if not self._person: return
        conn=get_connection(); pid=self._person["id"]; errors={}
        for key,(_,widget,validator) in self._ef.items():
            if _ =="text" and validator:
                v=widget.text().strip(); err=validator(v)
                if err: errors[key]=err
        for k,m in errors.items():
            if k in self._ee: self._ee[k].setText(m)
        if errors: conn.close(); return
        for k in self._ee: self._ee[k].setText("")
        fmap={"first_name":("person","first_name"),"last_name":("person","last_name"),
              "place_of_birth":("person","place_of_birth"),"nationality":("person","nationality"),"phone":("person","phone"),
              "hs_honors":("student","high_school_honors"),
              "fac":("student","faculty"),"dept_stu":("student","department"),"group":("student","group_name"),"scholarship":("student","scholarship"),
              "rank":("faculty","rank"),"emp_cat":("faculty","employment_category"),"primary_dept":("faculty","primary_department"),
              "secondary":("faculty","secondary_departments"),"research":("faculty","research_areas"),
              "teaching_h":("faculty","teaching_hours"),"contract_type":("faculty","contract_type"),"contract_end":("faculty","contract_end"),
              "dept_stf":("staff","department"),"job_title":("staff","job_title"),"grade":("staff","grade")}
        for key,(kind,widget,_) in self._ef.items():
            if kind=="text": val=widget.text().strip()
            elif kind=="combo": val=widget.currentText()
            elif kind=="date": val=widget.date().toString("yyyy-MM-dd")
            else: continue
            if key not in fmap: continue
            tbl,col=fmap[key]
            if tbl=="person":
                old=self._person.get(col)
                conn.execute(f"UPDATE person SET {col}=? WHERE id=?",(val,pid))
            else:
                row=conn.execute(f"SELECT * FROM {tbl} WHERE person_id=?",(pid,)).fetchone()
                if not row: continue
                old=dict(row).get(col)
                conn.execute(f"UPDATE {tbl} SET {col}=? WHERE person_id=?",(val,pid))
            log_history(conn,pid,"UPDATE",field=col,old_val=old,new_val=val)
        conn.execute("UPDATE person SET updated_at=datetime('now') WHERE id=?",(pid,))
        conn.commit(); conn.close()
        QMessageBox.information(self,"Saved","Changes saved successfully.")
        self.mw.refresh_all(); self.reset()


class StatusPage(QWidget):
    def __init__(self,mw):
        super().__init__(); self.mw=mw; self._person=None
        vl=QVBoxLayout(self); vl.setContentsMargins(32,28,32,28); vl.setSpacing(14)
        vl.addWidget(QLabel("Change Status",objectName="h1"))
        vl.addWidget(QLabel("Search for a person and apply a status transition",objectName="sub"))
        self.q=QLineEdit(); self.q.setPlaceholderText("Search name or ID…"); self.q.textChanged.connect(self._search); vl.addWidget(self.q)
        self.tbl=QTableWidget(0,5); self.tbl.setHorizontalHeaderLabels(["ID","Full Name","Type","Sub-category","Status"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setMaximumHeight(200)
        self.tbl.itemSelectionChanged.connect(self._on_sel); vl.addWidget(self.tbl)
        self._panel=QWidget(); self._panel.setObjectName("card"); self._panel.hide()
        pv=QVBoxLayout(self._panel); pv.setSpacing(12)
        self._pn=QLabel(""); self._pn.setStyleSheet(f"font-size:14px;font-weight:700;")
        self._pc=QLabel(""); self._pc.setStyleSheet(f"color:{TEXT2};")
        pv.addWidget(self._pn); pv.addWidget(self._pc)
        tr=QHBoxLayout(); tr.addWidget(QLabel("New Status:",styleSheet=f"color:{TEXT2};min-width:90px;font-weight:600;"))
        self._ns=QComboBox(); self._ns.setMinimumWidth(260); tr.addWidget(self._ns); tr.addStretch(); pv.addLayout(tr)
        self._note=QLineEdit(); self._note.setPlaceholderText("Reason / Note (optional)"); pv.addWidget(self._note)
        br=QHBoxLayout()
        ap=mkbtn("Apply Status Change"); ap.clicked.connect(self._apply)
        cx=mkbtn("Cancel","btn_s"); cx.clicked.connect(self.reset)
        br.addWidget(ap); br.addWidget(cx); br.addStretch()
        bw=QWidget(); bw.setLayout(br); pv.addWidget(bw)
        vl.addWidget(self._panel); vl.addStretch()

    def reset(self): self.q.clear(); self.tbl.setRowCount(0); self._panel.hide(); self._person=None

    def _search(self):
        q=self.q.text().strip()
        if not q: self.tbl.setRowCount(0); self._panel.hide(); return
        conn=get_connection()
        
        # Support searching by full name (e.g., "bob nad" or "nad bob")
        words = q.split()
        if len(words) >= 2:
            # Multiple words - search for name combinations in any order
            word1, word2 = words[0], words[1]
            rows=conn.execute("""SELECT * FROM person WHERE 
                unique_identifier LIKE ? OR 
                ((first_name LIKE ? AND last_name LIKE ?) OR (first_name LIKE ? AND last_name LIKE ?)) OR 
                first_name LIKE ? OR last_name LIKE ?
                ORDER BY last_name""",(f"%{q}%", f"%{word1}%", f"%{word2}%", f"%{word2}%", f"%{word1}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows=conn.execute("SELECT * FROM person WHERE first_name LIKE ? OR last_name LIKE ? OR unique_identifier LIKE ? ORDER BY last_name",(f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        
        conn.close(); self.tbl.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,v in enumerate([row["unique_identifier"],f"{row['first_name']} {row['last_name']}",TYPE_LABELS.get(row["type"],row["type"]),row["sub_category"],row["status"]]):
                item=QTableWidgetItem(v); item.setData(Qt.ItemDataRole.UserRole,dict(row))
                if c==4: item.setForeground(QColor(STATUS_CLR.get(v,TEXT)))
                self.tbl.setItem(r,c,item)

    def _on_sel(self):
        sel=self.tbl.selectedItems()
        if not sel: return
        p=self.tbl.item(self.tbl.currentRow(),0).data(Qt.ItemDataRole.UserRole)
        if not p: return
        self._person=p; curr=p["status"]; allowed=STATUS_TRANSITIONS.get(curr,[])
        self._pn.setText(f"{p['first_name']} {p['last_name']}  [{p['unique_identifier']}]")
        self._pc.setText(f"Current: {curr}  —  {STATUS_DESCRIPTIONS.get(curr,'')}")
        self._ns.clear()
        if not allowed: self._ns.addItem("No transitions available"); self._ns.setEnabled(False)
        else:
            self._ns.setEnabled(True)
            for s in allowed: self._ns.addItem(f"{s}  —  {STATUS_DESCRIPTIONS.get(s,'')}",s)
        self._panel.show()

    def _apply(self):
        if not self._person: return
        new_s=self._ns.currentData()
        if not new_s: return
        curr=self._person["status"]
        if curr=="Inactive" and new_s=="Archived":
            try:
                upd=datetime.strptime(self._person["updated_at"][:19],"%Y-%m-%d %H:%M:%S")
                yrs=(datetime.now()-upd).days/365.25
                if yrs<5: QMessageBox.warning(self,"Cannot Archive",f"Must be Inactive >= 5 years.\nElapsed: {yrs:.2f} years."); return
            except: pass
        note=self._note.text().strip() or None
        conn=get_connection()
        conn.execute("UPDATE person SET status=?,updated_at=datetime('now') WHERE id=?",(new_s,self._person["id"]))
        log_history(conn,self._person["id"],"STATUS_CHANGE",field="status",old_val=curr,new_val=new_s,note=note)
        conn.commit(); conn.close()
        QMessageBox.information(self,"Updated",f"Status: {curr} → {new_s}\n{self._person['first_name']} {self._person['last_name']}")
        self.mw.refresh_all(); self.reset()


class PromotePage(QWidget):
    def __init__(self,mw):
        super().__init__(); self.mw=mw; self._student=None
        self._ff={}; self._fe={}
        vl=QVBoxLayout(self); vl.setContentsMargins(32,28,32,28); vl.setSpacing(14)
        vl.addWidget(QLabel("Promote Student → Faculty",objectName="h1"))
        vl.addWidget(QLabel("The student identity is archived. A new Faculty identity is created with the same personal data.",objectName="sub"))
        self._step_lbl=QLabel("Step 1 — Find the student"); self._step_lbl.setStyleSheet(f"color:{ORANGE};font-size:13px;font-weight:700;padding:4px 0;")
        vl.addWidget(self._step_lbl); vl.addWidget(sep())
        # search
        self._sp=QWidget(); sv=QVBoxLayout(self._sp); sv.setContentsMargins(0,0,0,0); sv.setSpacing(10)
        self.q=QLineEdit(); self.q.setPlaceholderText("Search student by name or ID…"); self.q.textChanged.connect(self._search); sv.addWidget(self.q)
        self.tbl=QTableWidget(0,5); self.tbl.setHorizontalHeaderLabels(["ID","Full Name","Sub-category","Status","DOB"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False); self.tbl.setMaximumHeight(190)
        self.tbl.itemSelectionChanged.connect(self._on_sel)
        sv.addWidget(self.tbl); vl.addWidget(self._sp)
        # student summary card
        self._sc=QWidget(); self._sc.setObjectName("card_blue"); self._sc.hide()
        sk=QVBoxLayout(self._sc); sk.setSpacing(6)
        self._sn=QLabel(""); self._sn.setStyleSheet(f"font-size:14px;font-weight:700;color:{ORANGE};")
        self._sd=QLabel(""); self._sd.setStyleSheet(f"color:{TEXT2};font-size:12px;")
        sk.addWidget(self._sn); sk.addWidget(self._sd); vl.addWidget(self._sc)
        # faculty form (scrollable)
        self._fp=QWidget(); self._fp.hide()
        fv=QVBoxLayout(self._fp); fv.setContentsMargins(0,0,0,0); fv.setSpacing(14)
        fv.addWidget(QLabel("Step 2 — Enter new Faculty information",styleSheet=f"color:{GREEN};font-weight:700;font-size:13px;"))
        fsa=QScrollArea(); fsa.setWidgetResizable(True)
        fsa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        fi=QWidget(); self._fvl=QVBoxLayout(fi); self._fvl.setSpacing(14); self._fvl.setContentsMargins(0,4,12,4)
        fsa.setWidget(fi); fv.addWidget(fsa)
        br=QHBoxLayout()
        pb=mkbtn("🎓  Confirm Promotion","btn_g"); pb.setMinimumHeight(42); pb.clicked.connect(self._do_promote)
        cx=mkbtn("Cancel","btn_s"); cx.clicked.connect(self.reset)
        br.addWidget(pb); br.addWidget(cx); br.addStretch()
        bw=QWidget(); bw.setLayout(br); fv.addWidget(bw)
        vl.addWidget(self._fp); vl.addStretch()

    def reset(self):
        self.q.clear(); self.tbl.setRowCount(0); self._sc.hide(); self._fp.hide()
        self._student=None; self._ff={}; self._fe={}
        self._step_lbl.setText("Step 1 — Find the student")

    def _search(self):
        q=self.q.text().strip()
        if not q: self.tbl.setRowCount(0); self._sc.hide(); self._fp.hide(); return
        conn=get_connection()
        
        # Support searching by full name (e.g., "bob nad" or "nad bob")
        words = q.split()
        if len(words) >= 2:
            # Multiple words - search for name combinations in any order
            word1, word2 = words[0], words[1]
            rows=conn.execute("""SELECT * FROM person WHERE type='STU' AND status NOT IN ('Archived') AND (
                unique_identifier LIKE ? OR 
                ((first_name LIKE ? AND last_name LIKE ?) OR (first_name LIKE ? AND last_name LIKE ?)) OR 
                first_name LIKE ? OR last_name LIKE ?)
                ORDER BY last_name""",(f"%{q}%", f"%{word1}%", f"%{word2}%", f"%{word2}%", f"%{word1}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows=conn.execute("SELECT * FROM person WHERE type='STU' AND status NOT IN ('Archived') AND (first_name LIKE ? OR last_name LIKE ? OR unique_identifier LIKE ?) ORDER BY last_name",(f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        
        conn.close(); self.tbl.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,v in enumerate([row["unique_identifier"],f"{row['first_name']} {row['last_name']}",row["sub_category"],row["status"],row["date_of_birth"]]):
                item=QTableWidgetItem(v); item.setData(Qt.ItemDataRole.UserRole,dict(row))
                if c==3: item.setForeground(QColor(STATUS_CLR.get(v,TEXT)))
                self.tbl.setItem(r,c,item)

    def _on_sel(self):
        sel=self.tbl.selectedItems()
        if not sel: return
        p=self.tbl.item(self.tbl.currentRow(),0).data(Qt.ItemDataRole.UserRole)
        if not p: return
        self._student=p
        self._sn.setText(f"{p['first_name']} {p['last_name']}  ·  {p['unique_identifier']}")
        self._sd.setText(f"Sub-category: {p['sub_category']}  |  Status: {p['status']}  |  DOB: {p['date_of_birth']}")
        self._sc.show(); self._build_ff(); self._fp.show()
        self._step_lbl.setText("Step 1 ✓  Student selected   /   Step 2 — Fill Faculty details below")

    def _build_ff(self):
        while self._fvl.count():
            it=self._fvl.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self._ff={}; self._fe={}

        # card 1: role
        c1=QWidget(); c1.setObjectName("card"); g1=QGridLayout(c1); g1.setSpacing(10)
        sc_cb=QComboBox(); sc_cb.addItems(CATEGORIES["FAC"]["subcategories"]); self._ff["sub_cat"]=sc_cb
        g1.addWidget(fw("Faculty Sub-category *",sc_cb),0,0)
        rm={"Tenured":["Professor","Associate Professor","Assistant Professor"],
            "Adjunct / Part-time":["Assistant Professor","Lecturer","Teaching Assistant"],
            "Visiting Researcher":FACULTY_RANKS}
        rank_cb=QComboBox(); rank_cb.addItems(rm.get(sc_cb.currentText(),FACULTY_RANKS)); self._ff["rank"]=rank_cb
        g1.addWidget(fw("Rank *",rank_cb),0,1)
        sc_cb.currentTextChanged.connect(lambda t:(rank_cb.clear(),rank_cb.addItems(rm.get(t,FACULTY_RANKS))))
        emp=QComboBox(); emp.addItems(EMPLOYMENT_CATS); self._ff["emp_cat"]=emp
        g1.addWidget(fw("Employment Category *",emp),1,0)
        appt=QDateEdit(); appt.setCalendarPopup(True); appt.setDisplayFormat("yyyy-MM-dd")
        appt.setDate(QDate.currentDate()); self._ff["appt_start"]=appt
        g1.addWidget(fw("Appointment Start *",appt),1,1)
        dpt=QComboBox(); dpt.addItems(DEPARTMENTS); self._ff["primary_dept"]=dpt
        g1.addWidget(fw("Primary Department *",dpt),2,0)
        sec=QLineEdit(); sec.setPlaceholderText("optional"); self._ff["secondary"]=sec
        g1.addWidget(fw("Secondary Departments",sec),2,1)
        self._fvl.addWidget(sh("Professional Details")); self._fvl.addWidget(c1)

        # card 2: office + research
        c2=QWidget(); c2.setObjectName("card"); g2=QGridLayout(c2); g2.setSpacing(10)
        for i,(lbl,key) in enumerate([("Office Building","bldg"),("Office Floor","floor"),("Office Room","room"),("PhD Institution","phd_inst"),("Research Areas","research")]):
            le=QLineEdit(); le.setPlaceholderText("optional"); self._ff[key]=le; g2.addWidget(fw(lbl,le),i//2,i%2)
        hdr=QComboBox(); hdr.addItems(["No","Yes"]); self._ff["hdr"]=hdr; g2.addWidget(fw("HDR *",hdr),3,0)
        self._fvl.addWidget(sh("Office & Research")); self._fvl.addWidget(c2)

        # card 3: contract
        c3=QWidget(); c3.setObjectName("card"); g3=QGridLayout(c3); g3.setSpacing(10)
        ct=QComboBox(); ct.addItems(CONTRACT_TYPES); self._ff["contract_type"]=ct; g3.addWidget(fw("Contract Type *",ct),0,0)
        cs=QDateEdit(); cs.setCalendarPopup(True); cs.setDisplayFormat("yyyy-MM-dd")
        cs.setDate(QDate.currentDate()); self._ff["contract_start"]=cs; g3.addWidget(fw("Contract Start *",cs),0,1)
        ce=QDateEdit(); ce.setCalendarPopup(True); ce.setDisplayFormat("yyyy-MM-dd")
        ce.setDate(QDate(2099,12,31)); self._ff["contract_end"]=ce; g3.addWidget(fw("Contract End (optional)",ce),1,0)
        th=QLineEdit(); th.setPlaceholderText("e.g. 12.0"); self._ff["teaching_h"]=th
        e=errlbl(); self._fe["teaching_h"]=e; g3.addWidget(fw("Teaching Hours / week *",th,e),1,1)
        self._fvl.addWidget(sh("Contract")); self._fvl.addWidget(c3); self._fvl.addStretch()

    def _gf(self,k):
        w=self._ff.get(k)
        if isinstance(w,QLineEdit): return w.text().strip()
        if isinstance(w,QComboBox): return w.currentText()
        if isinstance(w,QDateEdit): return w.date().toString("yyyy-MM-dd")
        return ""

    def _do_promote(self):
        if not self._student: return
        for k in self._fe: self._fe[k].setText("")
        try: float(self._gf("teaching_h"))
        except:
            if "teaching_h" in self._fe: self._fe["teaching_h"].setText("Must be a number."); return

        stu=self._student; sub_cat=self._gf("sub_cat")
        reply=QMessageBox.question(self,"Confirm Promotion",
            f"Promote {stu['first_name']} {stu['last_name']} ({stu['unique_identifier']}) to Faculty?\n\n"
            f"• Current student identity → Archived\n"
            f"• New {sub_cat} identity will be created\n"
            f"• All personal data preserved and linked",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if reply!=QMessageBox.StandardButton.Yes: return

        conn=get_connection()
        try:
            # Archive old student AND free up email/phone so new FAC record can reuse them
            archived_email = f"__archived_{stu['id']}_{stu['email']}"
            archived_phone = f"__archived_{stu['id']}_{stu['phone']}"
            conn.execute(
                "UPDATE person SET status='Archived', email=?, phone=?, updated_at=datetime('now') WHERE id=?",
                (archived_email, archived_phone, stu["id"])
            )
            log_history(conn,stu["id"],"PROMOTION_ARCHIVED",field="status",old_val=stu["status"],new_val="Archived",note=f"Archived — promoted to Faculty ({sub_cat})")
            new_id,prefix=generate_id(conn,sub_cat)
            # New FAC record gets the real email and phone
            conn.execute("INSERT INTO person (unique_identifier,type,sub_category,id_prefix,status,first_name,last_name,date_of_birth,place_of_birth,nationality,gender,email,phone,previous_identity_id) VALUES (?,'FAC',?,?,'Pending',?,?,?,?,?,?,?,?,?)",
                (new_id,sub_cat,prefix,stu["first_name"],stu["last_name"],stu["date_of_birth"],stu["place_of_birth"],stu["nationality"],stu["gender"],stu["email"],stu["phone"],stu["id"]))
            new_pid=conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO faculty (person_id,rank,employment_category,appointment_start,primary_department,secondary_departments,office_building,office_floor,office_room,phd_institution,research_areas,hdr,contract_type,contract_start,contract_end,teaching_hours) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (new_pid,self._gf("rank"),self._gf("emp_cat"),self._gf("appt_start"),self._gf("primary_dept"),self._gf("secondary") or None,self._gf("bldg") or None,self._gf("floor") or None,self._gf("room") or None,self._gf("phd_inst") or None,self._gf("research") or None,1 if self._gf("hdr")=="Yes" else 0,self._gf("contract_type"),self._gf("contract_start"),self._gf("contract_end") or None,float(self._gf("teaching_h"))))
            ensure_person_auth_user(conn, new_pid, new_id, stu["date_of_birth"])
            log_history(conn,new_pid,"PROMOTED_FROM_STUDENT",note=f"Promoted from student ID: {stu['unique_identifier']}")
            conn.commit()
        except Exception as e:
            conn.rollback(); conn.close()
            QMessageBox.critical(self,"Error",f"Promotion failed:\n{e}"); return
        conn.close()

        d=QDialog(self); d.setWindowTitle("Promotion Complete"); d.setMinimumWidth(400)
        dv=QVBoxLayout(d); dv.setContentsMargins(28,28,28,28); dv.setSpacing(10)
        dv.addWidget(QLabel("🎓",styleSheet="font-size:48px;",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(QLabel("<b>Promotion Completed Successfully</b>",alignment=Qt.AlignmentFlag.AlignCenter))
        dv.addWidget(sep())
        for lbl,val,col in [("Person",f"{stu['first_name']} {stu['last_name']}",TEXT),("Old Student ID",stu["unique_identifier"],STATUS_CLR["Archived"]),("Old Status","Archived",STATUS_CLR["Archived"]),("New Faculty ID",new_id,ORANGE),("New Status","Pending",ORANGE),("Sub-category",sub_cat,GREEN)]:
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,2,0,2)
            rl.addWidget(QLabel(lbl+":",styleSheet=f"color:{TEXT2};min-width:140px;"))
            rl.addWidget(QLabel(val,styleSheet=f"color:{col};font-weight:700;")); rl.addStretch()
            dv.addWidget(rw)
        ok=mkbtn("OK"); ok.clicked.connect(d.accept); dv.addWidget(ok,alignment=Qt.AlignmentFlag.AlignCenter)
        d.exec(); self.mw.refresh_all(); self.reset()


if __name__=="__main__":
    init_db()
    app=QApplication(sys.argv); app.setStyleSheet(QSS)
    app.setApplicationName("IAM — Batna 2")
    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted or not login.session:
        sys.exit(0)
    session = login.session
    if session["first_login"]:
        person = session.get("person")
        full_name = f"{person['first_name']} {person['last_name']}" if person else ""
        birthdate = person["date_of_birth"] if person else ""
        cp = ChangePasswordDialog(session["username"], full_name, birthdate)
        if cp.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
    if session["role"] == "admin":
        w = MainWindow()
    else:
        w = StudentPortalWindow(session)
    w.show()
    sys.exit(app.exec())
