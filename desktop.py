import sys
import os
import time
import requests

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BG_IMAGE = os.path.join(BASE_DIR, "assets", "background.jpg")
APP_ICON = os.path.join(BASE_DIR, "assets", "app_icon.ico")

API_UPLOAD_URL = "http://127.0.0.1:8000/upload/"
# =========================================


# ================= CHART CANVAS =================
class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None, width=6, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)


# ================= MAIN APP =================
class DesktopApp(QWidget):
    def __init__(self):
        super().__init__()

        # ---------- WINDOW ----------
        self.setWindowTitle("ChemScope – Chemical Equipment Visualizer")
        self.setWindowIcon(QIcon(APP_ICON))
        self.showMaximized()

        # ---------- BACKGROUND ----------
        self.bg_pixmap = QPixmap(BG_IMAGE)

        # ---------- STYLE ----------
        self.setStyleSheet("""
            QWidget { font-family: Segoe UI; background: transparent; }
            QPushButton {
                background: rgba(37,99,235,0.95);
                color: white;
                padding: 16px 32px;
                border-radius: 16px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover { background: rgba(29,78,216,0.95); }
            QLabel#title { font-size: 30px; font-weight: bold; color: white; }
            QLabel.card {
                color: white;
                padding: 24px;
                border-radius: 20px;
                font-size: 18px;
                font-weight: 600;
            }
            QLabel#status { color: white; font-size: 15px; }
        """)

        self.last_report_url = None
        self.build_ui()

    # ---------- BACKGROUND ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.bg_pixmap.isNull():
            painter.drawPixmap(
                self.rect(),
                self.bg_pixmap.scaled(
                    self.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
            )

    # ---------- UI ----------
    def build_ui(self):
        self.main = QVBoxLayout()
        self.main.setContentsMargins(50, 50, 50, 50)
        self.main.setSpacing(28)
        self.setLayout(self.main)

        title = QLabel("🧪 ChemScope – Chemical Equipment Visualizer")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        self.main.addWidget(title)

        btns = QHBoxLayout()
        btns.setAlignment(Qt.AlignCenter)
        btns.setSpacing(40)

        self.upload_btn = QPushButton("📂 Upload CSV")
        self.upload_btn.clicked.connect(self.upload_csv)

        self.download_btn = QPushButton("⬇ Download PDF")
        self.download_btn.clicked.connect(self.download_pdf)

        btns.addWidget(self.upload_btn)
        btns.addWidget(self.download_btn)
        self.main.addLayout(btns)

        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignCenter)
        self.main.addWidget(self.status)

        summary = QHBoxLayout()
        summary.setSpacing(24)

        self.total = self.card("Total Rows\n—", "rgba(37,99,235,0.85)")
        self.pressure = self.card("Avg Pressure\n—", "rgba(34,197,94,0.85)")
        self.temp = self.card("Avg Temperature\n—", "rgba(249,115,22,0.85)")

        summary.addWidget(self.total)
        summary.addWidget(self.pressure)
        summary.addWidget(self.temp)
        self.main.addLayout(summary)

        charts = QHBoxLayout()
        charts.setSpacing(30)

        self.pie = ChartCanvas(self)
        self.bar = ChartCanvas(self)

        charts.addWidget(self.pie)
        charts.addWidget(self.bar)
        self.main.addLayout(charts)

    # ---------- CARD ----------
    def card(self, text, color):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setMinimumHeight(140)
        lbl.setProperty("class", "card")
        lbl.setStyleSheet(f"background:{color};")
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return lbl

    # ---------- UPLOAD ----------
    def upload_csv(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if not file:
            return

        try:
            self.status.setText("Uploading & analyzing...")
            with open(file, "rb") as f:
                r = requests.post(API_UPLOAD_URL, files={"file": f}, timeout=30)

            if r.status_code != 200:
                QMessageBox.critical(self, "Error", r.text)
                return

            resp = r.json()
            data = resp.get("data", {})
            self.last_report_url = resp.get("report")

            # ---- SUMMARY (MATCH BACKEND) ----
            self.total.setText(f"Total Rows\n{data.get('total_rows', '-')}")
            self.pressure.setText(f"Avg Pressure\n{data.get('average_pressure', '-')}")
            self.temp.setText(f"Avg Temperature\n{data.get('average_temperature', '-')}")

            # ---- PIE CHART ----
            self.pie.axes.clear()
            dist = data.get("type_distribution", {})
            if dist:
                self.pie.axes.pie(
                    dist.values(),
                    labels=dist.keys(),
                    autopct="%1.1f%%",
                    startangle=140
                )
                self.pie.axes.set_title("Equipment Type Distribution")
            self.pie.draw()

            # ---- BAR CHART ----
            self.bar.axes.clear()
            self.bar.axes.bar(
                ["Pressure", "Temperature"],
                [
                    data.get("average_pressure", 0),
                    data.get("average_temperature", 0),
                ],
                color=["#2563eb", "#dc2626"]
            )
            self.bar.axes.set_title("System Averages")
            self.bar.draw()

            self.status.setText("Upload successful ✔")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status.setText("Error")

    # ---------- PDF ----------
    def download_pdf(self):
        if not self.last_report_url:
            QMessageBox.information(self, "Info", "No PDF available yet")
            return
        try:
            r = requests.get(self.last_report_url, timeout=20)
            r.raise_for_status()
            path = os.path.join(
                os.path.expanduser("~"),
                "Downloads",
                f"chemical_report_{int(time.time())}.pdf"
            )
            with open(path, "wb") as f:
                f.write(r.content)
            os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# ---------- RUN ----------
def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(APP_ICON))
    win = DesktopApp()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
