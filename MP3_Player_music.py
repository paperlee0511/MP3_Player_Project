import sys
import os
import vlc
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from PIL import Image
from PIL.ImageQt import ImageQt
from io import BytesIO


class MP3Player:
    def __init__(self, main_window):
        self.main_window = main_window
        self.is_loading = False

        # VLC 미디어 플레이어 초기화
        self.vlc_instance = vlc.Instance()
        self.media_player = self.vlc_instance.media_player_new()

        # 플레이리스트 관련 변수
        self.playlist = []
        self.current_index = 0
        self.is_shuffle = False
        self.is_repeat = False

        # 슬라이더 제어용 변수
        self.slider_being_moved = False

        # UI 업데이트용 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(500)

        self.setup_connections()
        self.setup_initial_ui()

    def setup_connections(self):
        """MP3 플레이어 관련 연결"""
        self.main_window.btn_play.clicked.connect(self.toggle_play_pause)
        self.main_window.btn_next.clicked.connect(self.next_song)
        self.main_window.btn_previous.clicked.connect(self.previous_song)
        self.main_window.btn_shuffle.clicked.connect(self.toggle_shuffle)
        self.main_window.btn_repeat.clicked.connect(self.toggle_repeat)

        self.main_window.btn_add.clicked.connect(self.add_songs)
        self.main_window.btn_remove.clicked.connect(self.remove_song)

        self.main_window.sld_bar.sliderPressed.connect(self.slider_pressed)
        self.main_window.sld_bar.sliderReleased.connect(self.slider_released)
        self.main_window.sld_bar.sliderMoved.connect(self.set_position)

        self.main_window.listWidget.itemDoubleClicked.connect(self.play_selected_song)

    def setup_initial_ui(self):
        """초기 UI 설정"""
        self.main_window.lbl_song_name.setText("재생할 곡을 선택하세요")
        self.main_window.current_time.setText("00:00")
        self.main_window.total_time.setText("00:00")
        self.main_window.sld_bar.setValue(0)

        # 초기 아이콘 설정
        self.main_window.btn_play.setIcon(QIcon("images/play_icon.png"))
        self.update_shuffle_icon()
        self.update_repeat_icon()

    def add_songs(self):
        """곡 추가"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.main_window,
            "MP3 파일 선택",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac)"
        )

        for file_path in file_paths:
            if file_path:
                file_name = os.path.basename(file_path)
                self.playlist.append({'path': file_path, 'name': file_name})
                self.main_window.listWidget.addItem(file_name)

        if len(self.playlist) == len(file_paths) and self.playlist:
            self.load_current_song()

    def remove_song(self):
        """곡 제거"""
        current_row = self.main_window.listWidget.currentRow()
        if current_row >= 0:
            self.main_window.listWidget.takeItem(current_row)
            self.playlist.pop(current_row)

            if current_row == self.current_index:
                self.media_player.stop()
                self.main_window.lbl_song_name.setText("재생할 곡을 선택하세요")

            if self.current_index >= len(self.playlist):
                self.current_index = 0

    def play_selected_song(self, item):
        """선택된 곡 재생"""
        self.current_index = self.main_window.listWidget.row(item)
        self.load_current_song()
        self.media_player.play()
        self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))

    def load_current_song(self):
        """현재 곡 로드"""
        if self.is_loading:
            return
        self.is_loading = True

        try:
            self.timer.stop()
            self.media_player.stop()
            QApplication.processEvents()

            if self.playlist and 0 <= self.current_index < len(self.playlist):
                current_song = self.playlist[self.current_index]
                media = self.vlc_instance.media_new(current_song['path'])
                self.media_player.set_media(media)
                self.main_window.lbl_song_name.setText(current_song['name'])
                self.main_window.listWidget.setCurrentRow(self.current_index)

                self.show_album_cover(current_song['path'])
        except Exception as e:
            print(f"곡 로딩 중 오류: {e}")
        finally:
            self.timer.start(500)
            self.is_loading = False

    def toggle_play_pause(self):
        """재생/일시정지 토글"""
        state = self.media_player.get_state()
        if state == vlc.State.Playing:
            self.media_player.pause()
            self.main_window.btn_play.setIcon(QIcon("images/play_icon.png"))
        else:
            if not self.playlist:
                self.add_songs()
                return

            if state == vlc.State.Paused:
                self.media_player.play()
            else:
                self.load_current_song()
                self.media_player.play()

            self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))

    def next_song(self):
        """다음 곡"""
        if not self.playlist:
            return

        if self.is_shuffle:
            import random
            self.current_index = random.randint(0, len(self.playlist) - 1)
        else:
            self.current_index = (self.current_index + 1) % len(self.playlist)

        self.load_current_song()
        self.media_player.play()
        self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))

    def previous_song(self):
        """이전 곡"""
        if not self.playlist:
            return

        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.load_current_song()
        self.media_player.play()
        self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))

    def toggle_shuffle(self):
        """랜덤 재생 토글"""
        self.is_shuffle = not self.is_shuffle
        self.update_shuffle_icon()

    def toggle_repeat(self):
        """반복 재생 토글"""
        self.is_repeat = not self.is_repeat
        self.update_repeat_icon()

    def update_shuffle_icon(self):
        """셔플 아이콘 업데이트"""
        if self.is_shuffle:
            icon_path = "images/shuffle_on_icon.png"
        else:
            icon_path = "images/shuffle_icon.png"
        self.main_window.btn_shuffle.setIcon(QIcon(icon_path))

    def update_repeat_icon(self):
        """반복 아이콘 업데이트"""
        if self.is_repeat:
            icon_path = "images/repeat_on_icon.png"
        else:
            icon_path = "images/repeat_icon.png"
        self.main_window.btn_repeat.setIcon(QIcon(icon_path))

    def slider_pressed(self):
        """슬라이더 누름"""
        self.slider_being_moved = True

    def slider_released(self):
        """슬라이더 놓음"""
        self.slider_being_moved = False
        self.set_position(self.main_window.sld_bar.value())

    def set_position(self, value):
        """재생 위치 설정"""
        self.media_player.set_time(value)

    def update_ui(self):
        """UI 업데이트"""
        try:
            state = self.media_player.get_state()

            if state == vlc.State.Playing and not self.slider_being_moved:
                current_time = self.media_player.get_time()
                duration = self.media_player.get_length()

                if duration > 0:
                    self.main_window.sld_bar.setMaximum(duration)
                    self.main_window.sld_bar.setValue(current_time)
                    self.main_window.current_time.setText(self.format_time(current_time))
                    self.main_window.total_time.setText(self.format_time(duration))

            if state == vlc.State.Ended:
                if self.is_repeat:
                    self.load_current_song()
                    self.media_player.play()
                    self.main_window.btn_play.setIcon(QIcon("images/pause_icon.png"))
                else:
                    self.next_song()

        except Exception as e:
            print(f"[UI 업데이트 오류]: {e}")

    def format_time(self, ms):
        """시간 포맷팅"""
        if ms < 0:
            ms = 0
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def show_album_cover(self, filepath):
        """앨범 커버 표시"""
        try:
            audio = MP3(filepath, ID3=ID3)
            tags = audio.tags.getall("APIC")
            if tags:
                image_data = tags[0].data
                image = Image.open(BytesIO(image_data))

                if image.format not in ['JPEG', 'PNG', 'BMP', 'GIF']:
                    raise ValueError("지원되지 않는 이미지 포맷")

                max_size = (200, 200)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

                qt_image = QPixmap.fromImage(ImageQt(image))

                if qt_image.isNull():
                    raise ValueError("QPixmap 변환 실패")

                self.main_window.lbl_image.setPixmap(qt_image)
            else:
                self.main_window.lbl_image.setPixmap(QPixmap("images/mp3_icon.png"))
        except Exception as e:
            print(f"[앨범 커버 로드 실패]: {e}")
            self.main_window.lbl_image.setPixmap(QPixmap("images/mp3_icon.png"))

    def get_current_song_name(self):
        """현재 재생 중인 곡 이름 반환"""
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]['name']
        return None