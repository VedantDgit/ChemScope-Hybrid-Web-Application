import sys
import os
import requests
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt
import webbrowser
import time
import subprocess

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


API_UPLOAD_URL = os.environ.get('API_UPLOAD_URL', 'http://127.0.0.1:8000/upload/')


class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.subplots()
        super().__init__(fig)
        self.setParent(parent)


class DesktopApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Chemical Equipment Visualizer - Desktop')
        self.resize(900, 600)

        main_layout = QVBoxLayout()

        header = QLabel('Desktop Visualizer')
        header.setStyleSheet('font-size:20px; font-weight:600;')
        header.setAlignment(Qt.AlignCenter)

        main_layout.addWidget(header)

        controls = QHBoxLayout()
        self.upload_btn = QPushButton('Choose CSV and Upload')
        self.upload_btn.clicked.connect(self.choose_and_upload)
        controls.addWidget(self.upload_btn)

        self.refresh_btn = QPushButton('Refresh History')
        self.refresh_btn.clicked.connect(self.fetch_history)
        controls.addWidget(self.refresh_btn)

        self.status_label = QLabel('Ready')
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        controls.addWidget(self.status_label)

        main_layout.addLayout(controls)

        # Summary labels
        summary_layout = QHBoxLayout()
        self.total_label = QLabel('Total Rows: -')
        self.pressure_label = QLabel('Avg Pressure: -')
        self.temp_label = QLabel('Avg Temperature: -')

        for lbl in (self.total_label, self.pressure_label, self.temp_label):
            lbl.setStyleSheet('background:#f3f4f6; padding:8px; border-radius:6px;')
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            summary_layout.addWidget(lbl)

        main_layout.addLayout(summary_layout)

        # Charts area
        charts_layout = QHBoxLayout()
        self.pie_canvas = ChartCanvas(self, width=4, height=3)
        self.bar_canvas = ChartCanvas(self, width=4, height=3)
        charts_layout.addWidget(self.pie_canvas)
        charts_layout.addWidget(self.bar_canvas)

        main_layout.addLayout(charts_layout)

        # History list
        self.history_layout = QVBoxLayout()
        hist_card = QWidget()
        hist_card.setLayout(self.history_layout)
        hist_card.setStyleSheet('background:#fff; padding:10px; border-radius:8px;')
        main_layout.addWidget(QLabel('Recent uploads'))
        main_layout.addWidget(hist_card)

        self.setLayout(main_layout)

    def choose_and_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select CSV file', '', 'CSV Files (*.csv)')
        if not file_path:
            return
        try:
            self.status_label.setText('Uploading...')
            with open(file_path, 'rb') as fh:
                r = requests.post(API_UPLOAD_URL, files={'file': fh})
            if r.status_code != 200:
                QMessageBox.critical(self, 'Upload failed', f'Status: {r.status_code}\n{r.text}')
                self.status_label.setText('Upload failed')
                return

            payload = r.json()
            data = payload.get('data', {})
            self._update_summary(data)
            self._update_charts(data)
            self.status_label.setText('Upload complete')
            # refresh history after upload
            self.fetch_history()
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))
            self.status_label.setText('Error')

    def _update_summary(self, data):
        self.total_label.setText(f"Total Rows: {data.get('total_rows', '-')}")
        self.pressure_label.setText(f"Avg Pressure: {data.get('average_pressure', '-')}")
        self.temp_label.setText(f"Avg Temperature: {data.get('average_temperature', '-')}")

    def _update_charts(self, data):
        # Pie chart for type distribution
        type_dist = data.get('type_distribution', {}) or {}
        labels = list(type_dist.keys())
        sizes = list(type_dist.values())

        self.pie_canvas.axes.clear()
        if labels and sizes:
            self.pie_canvas.axes.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
            self.pie_canvas.axes.set_title('Type Distribution')
        else:
            self.pie_canvas.axes.text(0.5, 0.5, 'No type data', ha='center', va='center')
        self.pie_canvas.draw()

        # Bar chart for averages
        self.bar_canvas.axes.clear()
        avgs = [data.get('average_pressure') or 0, data.get('average_temperature') or 0]
        names = ['Pressure', 'Temperature']
        self.bar_canvas.axes.bar(names, avgs, color=['#3b82f6', '#ef4444'])
        self.bar_canvas.axes.set_title('Averages')
        self.bar_canvas.draw()

    def fetch_history(self):
        try:
            r = requests.get(API_UPLOAD_URL.replace('/upload/', '/datasets/'))
            payload = r.json()
            items = payload.get('items') if isinstance(payload, dict) else payload
        except Exception as e:
            QMessageBox.warning(self, 'History error', f'Could not load history: {e}')
            return

        # clear old items
        for i in reversed(range(self.history_layout.count())):
            w = self.history_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        # show items
        for it in items or []:
            row = QHBoxLayout()
            w = QWidget()
            lbl = QLabel(f"{it.get('filename')} — {it.get('uploaded_at')}")
            row.addWidget(lbl)
            btn_open = QPushButton('Open PDF')
            report_url = it.get('report_url')
            btn_open.clicked.connect(lambda _, u=report_url: self.open_pdf(u) if u else QMessageBox.information(self, 'No PDF', 'No report available'))
            row.addWidget(btn_open)
            btn_load = QPushButton('Load')
            btn_load.clicked.connect(lambda _, s=it.get('summary'): (self._update_summary(s), self._update_charts(s)))
            row.addWidget(btn_load)
            w.setLayout(row)
            self.history_layout.addWidget(w)

    def open_pdf(self, url):
        if not url:
            QMessageBox.information(self, 'No PDF', 'No report available')
            return
        try:
            self.status_label.setText('Downloading PDF...')
            r = requests.get(url, stream=True, timeout=20)
            r.raise_for_status()
            downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'chemical_visualizer_reports')
            os.makedirs(downloads_dir, exist_ok=True)
            local_path = os.path.join(downloads_dir, f"report_{int(time.time())}.pdf")
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            self.status_label.setText('Opening PDF...')
            if os.name == 'nt':
                os.startfile(local_path)
            elif sys.platform == 'darwin':
                subprocess.call(['open', local_path])
            else:
                subprocess.call(['xdg-open', local_path])
            self.status_label.setText('Ready')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Could not download/open PDF: {e}')
            self.status_label.setText('Error')


def main():
    app = QApplication(sys.argv)
    win = DesktopApp()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
