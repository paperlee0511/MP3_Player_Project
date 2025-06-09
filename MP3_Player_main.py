import sys
import os
from PyQt5.QtGui import QIcon   # 창 아이콘 표시 PyQt5 모듈

from PyQt5.QtWebEngineWidgets import QWebEngineView # 웹페이지 띄우는 위젯(유튜브 영상 표시용)
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic

from MP3_Player_music import MP3Player  # music 부분 클래스 가져옴
from MP3_Player_video import YouTubeVideoPlayer # video 부분 클래스 가져옴

# YouTube 웹엔진 크래시 방지 옵션
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QTWEBENGINE_PROFILE_PATH"] = os.path.join(os.getcwd(), "qtwebengine_profile")

# QApplication 생성 전에 OpenGL 공유 옵션을 설정해줌 (동영상, 웹엔진 사용시 충돌방지)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

# 메인 윈도우 클래스 정의
class MainApp(QMainWindow): # QMainWindow를 상속해서 내 프로그램 창 만듬
    def __init__(self):
        super().__init__()
        uic.loadUi("./MP3_and_VIDEO_5.ui", self)

        self.setWindowTitle("jonghui MP3 & Video Player")   # 창 상단에 표시될 이름
        self.setWindowIcon(QIcon('./images/mp3_icon.png'))  # 창 아이콘 설정

        # MP3 플레이어와 비디오 플레이어 객체 생성, 메인윈도우(self) 넘겨줌
        self.mp3_player = MP3Player(self)
        self.video_player = YouTubeVideoPlayer(self)

        self.btn_video.clicked.connect(self.show_video_page)    # 비디오로 전환하는 버튼 클릭시 show_video_page 함수 연결
        self.btn_back.clicked.connect(self.show_mp3_page)       # 뒤로가기 버튼 클릭 시 show_mp3_page 함수 연결

        self.stackedWidget.setCurrentIndex(0)   # 프로그램이 시작 할 때 음악페이지로 설정(index = 0)

    # 비디오 페이지로 전환하는 함수
    def show_video_page(self):
        self.stackedWidget.setCurrentIndex(1)
    # mp3 페이지로 전환하는 함수
    def show_mp3_page(self):
        self.stackedWidget.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec_())

# 요약
# 프로그램 실행과 화면 전환을 담당
# ui파일을 읽어, mp3플레이어와 비디오 플레이어가 둘 다 동작하는 큰틀의 창을 만듬
# 버튼 클릭스 음악 , 비디오 화면전환
# 실제 음악/ 비디오 재생기능은 각각 따로 구현되어 있음
