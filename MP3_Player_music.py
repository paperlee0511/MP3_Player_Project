import sys
import os
import vlc  # 동영상 / 음악 재생 라이브러리(VLC Player 엔진 사용)
from PyQt5.QtCore import QTimer # UI업데이트용 타이머(일정주기마다 동작)
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *       # 아이콘 이미지 등 UI 관련 기능
from PyQt5 import uic
from mutagen.mp3 import MP3     # mp3 파일 정보 읽기(재생시간 , 태그 등)
from mutagen.id3 import ID3     # mp3 파일의 앨범 커버 등 ID3 태그 추출
from PIL import Image           # 이미지 처리 (앨범 커버)
from PIL.ImageQt import ImageQt # PIL 이미지를 파이큐티용 이미지로 변환
from io import BytesIO          # 바이트 데이터 -> 파일처럼 다루기(앨범 커버용)

# mp3 플레이어 클래스
class MP3Player:
    def __init__(self, main_window):
        self.main_window = main_window
        self.is_loading = False

        # VLC 미디어 플레이어 초기화
        self.vlc_instance = vlc.Instance()
        self.media_player = self.vlc_instance.media_player_new()

        # 플레이리스트 관련 변수
        self.playlist = []          # 곡(파일) 목록 저장 {'path', 'name]
        self.current_index = 0      # 현재 재생 중인 곡의 인덱스
        self.is_shuffle = False     # 셔플(랜덤재생) 상태
        self.is_repeat = False      # 반복 재생 상태

        # 슬라이더 제어용 변수
        self.slider_being_moved = False # 사용자가 막대를 움직이고 있는지 표시

        # UI 업데이트용 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)  # 0.5초마다 update_ui 함수 호출
        self.timer.start(500)

        self.setup_connections()    # 버튼, 슬라이더 등 이벤트와 함수 연결
        self.setup_initial_ui()     # UI초기화

# 각종 버튼, 슬라이더 등과 함수 연결
    def setup_connections(self):
        """MP3 플레이어 관련 연결"""
        self.main_window.btn_play.clicked.connect(self.toggle_play_pause)   # 재생 / 일시정지 버튼
        self.main_window.btn_next.clicked.connect(self.next_song)           # 다음곡
        self.main_window.btn_previous.clicked.connect(self.previous_song)   # 이전 곡
        self.main_window.btn_shuffle.clicked.connect(self.toggle_shuffle)   # 셔플 버튼
        self.main_window.btn_repeat.clicked.connect(self.toggle_repeat)     # 반복 버튼

        self.main_window.btn_add.clicked.connect(self.add_songs)            # 곡 추가 버튼
        self.main_window.btn_remove.clicked.connect(self.remove_song)       # 곡 삭제 버튼

        self.main_window.sld_bar.sliderPressed.connect(self.slider_pressed)     # 슬라이더 누를 때
        self.main_window.sld_bar.sliderReleased.connect(self.slider_released)   # 슬라이더 놓을 때
        self.main_window.sld_bar.sliderMoved.connect(self.set_position)         # 슬라이더 움직일 때

        self.main_window.listWidget.itemDoubleClicked.connect(self.play_selected_song)  # 곡 목록에서 더블 클릭 시 재생

# UI(라벨, 시간, 아이콘 등) 초기화
    def setup_initial_ui(self):
        """초기 UI 설정"""
        self.main_window.lbl_song_name.setText("재생할 곡을 선택하세요") # 처음, 곡 정보 없음
        self.main_window.current_time.setText("00:00")                  # 현재 시간 초기화
        self.main_window.total_time.setText("00:00")                    # 전체 시간 초기화
        self.main_window.sld_bar.setValue(0)                            # 슬라이더 위치 0

        # 초기 재생 / 일시정지 아이콘 설정
        self.main_window.btn_play.setIcon(QIcon("images/play_icon.png"))
        self.update_shuffle_icon()  # 셔플 아이콘 초기화
        self.update_repeat_icon()   # 반복 아이콘 초기화
        
    # 곡 추가
    def add_songs(self):
        """곡 추가"""
        # 파일 선택창 띄워서 여러개 음악 파일 선택
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.main_window,
            "MP3 파일 선택",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac)"
        )
        # 선택된 파일들을 플레이리스트에 추가 + 목록에 표시
        for file_path in file_paths:
            if file_path:   # 선택한 파일이 있으면
                file_name = os.path.basename(file_path) # 파일명만 추출
                self.playlist.append({'path': file_path, 'name': file_name})    # 플레이 리스트에 추가
                self.main_window.listWidget.addItem(file_name)                  # 목록에 표시
        # 플레이 리스트가 처음 만들어 졌으면 첫 곡을 자동으로 로드
        if len(self.playlist) == len(file_paths) and self.playlist:
            self.load_current_song()

    # 곡 제거
    def remove_song(self):
        """곡 제거"""
        current_row = self.main_window.listWidget.currentRow()  # 현재 선택된 곡 번호
        if current_row >= 0:
            self.main_window.listWidget.takeItem(current_row)   # 목록에서 삭제
            self.playlist.pop(current_row)                      # 플레이리스트에서도 삭제

            if current_row == self.current_index:               # 지금 재생 중인 곡이면
                self.media_player.stop()                        # 재생 중지
                self.main_window.lbl_song_name.setText("재생할 곡을 선택하세요")  # 안내 메시지

            if self.current_index >= len(self.playlist):        # 곡이 줄어서 인덱스가 범위를 벗어나면 0으로
                self.current_index = 0

    # 곡 목록에서 더블클릭시, 해당 곡 재생
    def play_selected_song(self, item):
        """선택된 곡 재생"""
        self.current_index = self.main_window.listWidget.row(item)          # 더블클릭한 곡의 번호
        self.load_current_song()                                            # 해당 곡 로드
        self.media_player.play()                                            # 재생 시작
        self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))   # 일시정지 아이콘으로 변경

    # 현재 곡 로드
    def load_current_song(self):
        """현재 곡 로드"""
        if self.is_loading: # 이미 로딩중이면 무시
            return
        self.is_loading = True

        try:
            self.timer.stop()               # 타이머(자동업데이트) 잠시 멈춤
            self.media_player.stop()        # 재생 중지
            QApplication.processEvents()    # 파이큐티 이벤트 강제로 처리(UI멈춤 방지)

            if self.playlist and 0 <= self.current_index < len(self.playlist):  # 곡이 있으면
                current_song = self.playlist[self.current_index]
                media = self.vlc_instance.media_new(current_song['path'])       # VLC용 미디어 객체 생성
                self.media_player.set_media(media)                              # 미디어 플레이어 설정
                self.main_window.lbl_song_name.setText(current_song['name'])    # 곡 이름 표시
                self.main_window.listWidget.setCurrentRow(self.current_index)   # 목록에서 현재 곡 표시

                self.show_album_cover(current_song['path'])                     # 앨범 커버 표시
        except Exception as e:
            print(f"곡 로딩 중 오류: {e}")
        finally:
            self.timer.start(500)   # 타이머 재시작
            self.is_loading = False

    # 재생 / 일시정지 토글
    def toggle_play_pause(self):
        """재생/일시정지 토글"""
        state = self.media_player.get_state()   # 현재 재생상태 확인
        if state == vlc.State.Playing:
            self.media_player.pause()           # 재생 중이면 일시정지
            self.main_window.btn_play.setIcon(QIcon("images/play_icon.png"))    # 재생 아이콘으로 변경
        else:
            if not self.playlist:           # 플레이리스트가 비었으면 곡 추가 요청
                self.add_songs()
                return

            if state == vlc.State.Paused:   # 일시정지 상태면 다시 재생
                self.media_player.play()
            else:
                self.load_current_song()    # 정지 상태면 곡 로드 후 재생
                self.media_player.play()

            self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))   # 일시정지 아이콘으로 변경

    # 다음 곡 재생
    def next_song(self):
        """다음 곡"""
        if not self.playlist:
            return

        if self.is_shuffle:     # 셔플이면 랜덤 인덱스 선택
            import random
            self.current_index = random.randint(0, len(self.playlist) - 1)
        else:                   # 아니면 순차적으로 재생
            self.current_index = (self.current_index + 1) % len(self.playlist)

        self.load_current_song()
        self.media_player.play()
        self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))

    # 이전 곡 재생
    def previous_song(self):
        """이전 곡"""
        if not self.playlist:
            return

        self.current_index = (self.current_index - 1) % len(self.playlist)  # 인덱스 하나 뒤로 
        self.load_current_song()
        self.media_player.play()
        self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))

    # 셔플 모드 온/오프
    def toggle_shuffle(self):
        """랜덤 재생 토글"""
        self.is_shuffle = not self.is_shuffle
        self.update_shuffle_icon()  # 아이콘 변경

    # 반복 재생 온/오프
    def toggle_repeat(self):
        """반복 재생 토글"""
        self.is_repeat = not self.is_repeat
        self.update_repeat_icon()   # 아이콘 변경

    # 셔플 아이콘 업데이트
    def update_shuffle_icon(self):
        """셔플 아이콘 업데이트"""
        if self.is_shuffle:
            icon_path = "images/shuffle_on_icon.png"
        else:
            icon_path = "images/shuffle_icon.png"
        self.main_window.btn_shuffle.setIcon(QIcon(icon_path))

    # 반복 아이콘 업데이트
    def update_repeat_icon(self):
        """반복 아이콘 업데이트"""
        if self.is_repeat:
            icon_path = "images/repeat_on_icon.png"
        else:
            icon_path = "images/repeat_icon.png"
        self.main_window.btn_repeat.setIcon(QIcon(icon_path))

    # 슬라이더바 누르기 시작
    def slider_pressed(self):
        """슬라이더 누름"""
        self.slider_being_moved = True
    # 슬라이더바 놓기
    def slider_released(self):
        """슬라이더 놓음"""
        self.slider_being_moved = False
        self.set_position(self.main_window.sld_bar.value())
    # 슬라이더바 값에 맞춰 곡 재생 위치 변경
    def set_position(self, value):
        """재생 위치 설정"""
        self.media_player.set_time(value)

    # ui 업데이트(0.5초마다) 시간 설정은 초기에 코드 초반부에 있음
    def update_ui(self):
        """UI 업데이트"""
        try:
            state = self.media_player.get_state()   # 현재 재생 상태

            if state == vlc.State.Playing and not self.slider_being_moved:
                current_time = self.media_player.get_time() # 현재 재생 위치
                duration = self.media_player.get_length()   # 전체 곡 길이

                if duration > 0:
                    self.main_window.sld_bar.setMaximum(duration)       # 슬라이더 최대 값 설정
                    self.main_window.sld_bar.setValue(current_time)     # 슬라이더 현재 값 설정
                    self.main_window.current_time.setText(self.format_time(current_time))   # 현재 시간 표시
                    self.main_window.total_time.setText(self.format_time(duration))         # 전체 시간 표시

            if state == vlc.State.Ended:        # 곡이 끝나면
                if self.is_repeat:              # 반복 모드면 같은 곡 다시
                    self.load_current_song()
                    self.media_player.play()
                    self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))
                else:                           # 아니면 다음 곡 재생
                    self.next_song()

        except Exception as e:
            print(f"[UI 업데이트 오류]: {e}")

    # ms를 mm : ss 형식 문자열로 변환
    def format_time(self, ms):
        """시간 포맷팅"""
        if ms < 0:
            ms = 0
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    # 앨범 커버 이미지 표시
    def show_album_cover(self, filepath):
        """앨범 커버 표시"""
        try:
            audio = MP3(filepath, ID3=ID3)            # mp3 파일에서 태그 일긱
            tags = audio.tags.getall("APIC")                # 앨범 커버 데이터 추출 
            if tags:
                image_data = tags[0].data                   # 커버 이미지
                image = Image.open(BytesIO(image_data))     # 이미지 열기 

                if image.format not in ['JPEG', 'PNG', 'BMP', 'GIF']:   # 지원 포맷 확인
                    raise ValueError("지원되지 않는 이미지 포맷")

                max_size = (200, 200)   # 썸네일 작게
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

                qt_image = QPixmap.fromImage(ImageQt(image))

                if qt_image.isNull():
                    raise ValueError("QPixmap 변환 실패")

                self.main_window.lbl_image.setPixmap(qt_image)
            else:   # 앨범 커버 없으면 기본 아이콘
                self.main_window.lbl_image.setPixmap(QPixmap("images/mp3_icon.png"))
        except Exception as e:
            print(f"[앨범 커버 로드 실패]: {e}")
            self.main_window.lbl_image.setPixmap(QPixmap("images/mp3_icon.png"))

    # 현재 곡 이름 반환
    def get_current_song_name(self):
        """현재 재생 중인 곡 이름 반환"""
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]['name']
        return None

    # 내용 정리
    # 곡 추가, 삭제, 재생, 일시정지, 다음, 이전, 셔플, 반복, 슬라이더, 시간, 커버 이미지 표시 기능 구현