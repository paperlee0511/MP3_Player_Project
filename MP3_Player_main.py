import sys
import os
from PyQt5.QtGui import QIcon

from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic

from MP3_Player_music import MP3Player
from MP3_Player_video import YouTubeVideoPlayer

# YouTube 웹엔진 크래시 방지 옵션
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QTWEBENGINE_PROFILE_PATH"] = os.path.join(os.getcwd(), "qtwebengine_profile")

# QApplication 생성 전에 설정 (필수)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("./MP3_and_VIDEO_5.ui", self)

        self.setWindowTitle("jonghui MP3 & Video Player")
        self.setWindowIcon(QIcon('./images/mp3_icon.png'))

        # MP3, Video 클래스에 현재 메인윈도우(self) 전달
        self.mp3_player = MP3Player(self)
        self.video_player = YouTubeVideoPlayer(self)

        self.btn_video.clicked.connect(self.show_video_page)
        self.btn_back.clicked.connect(self.show_mp3_page)

        self.stackedWidget.setCurrentIndex(0)

    def show_video_page(self):
        self.stackedWidget.setCurrentIndex(1)

    def show_mp3_page(self):
        self.stackedWidget.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec_())
