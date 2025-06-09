import os
import requests                     # 웹 요청(유튜브 페이지에서 가져올 때)
from urllib.parse import quote      # url에 한글/특수문자 포함시 인코딩
import json                         # 유튜브에서 받은 데이터
import re                           # 정규 표현식
from PyQt5.QtCore import QThread, pyqtSignal, QUrl  # 스레드, 시그널, url 관리
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from bs4 import BeautifulSoup                       # HTML 파싱
from audio import YouTubeAudioExtractor             # 음원 추출 기능
from PyQt5.QtCore import QSize
from PyQt5.QtCore import Qt



# 유튜브 검색을 위한 별도 스레드 클래스
class YoutubeSearchThread(QThread):
    """YouTube 검색 스레드"""
    search_finished = pyqtSignal(list)      # 검색 결과가 준비되면 이벤트 발생

    def __init__(self, query):
        super().__init__()
        self.query = query  # 검색할 문자열

    def run(self):
        try:
            # 더 안정적인 헤더 설정
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            # 검색어를 url에 넣을 수 있게 인코딩 # 검색 쿼리 인코딩
            query_encoded = quote(self.query)
            url = f"https://www.youtube.com/results?search_query={query_encoded}"

            # 세션 사용으로 쿠키 관리
            session = requests.Session()
            session.headers.update(headers)

            # 타임아웃 설정
            response = session.get(url, timeout=10) # 10초 제한
            response.raise_for_status()

            # 응답 텍스트에서 JavaScript 데이터 추출
            results = self.extract_video_data(response.text)

            self.search_finished.emit(results)

        except requests.exceptions.RequestException as e:
            print(f"[네트워크 오류]: {e}")
            self.search_finished.emit([])
        except Exception as e:
            print(f"[검색 오류]: {e}")
            self.search_finished.emit([])

    def extract_video_data(self, html_content):
        """HTML에서 비디오 데이터 추출"""
        results = []

        try:
            # 유튜브 결과페이지에서 'var ytInitialData = ... 부분 추출
            # 방법 1: JavaScript 데이터에서 추출
            pattern = r'var ytInitialData = ({.*?});'
            match = re.search(pattern, html_content)

            if match:
                try:
                    data = json.loads(match.group(1))   # json 파싱
                    # ytInitialData에서 비디오 정보 추출
                    contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents',
                                                                                                      {}).get(
                        'sectionListRenderer', {}).get('contents', [])

                    for section in contents:
                        if 'itemSectionRenderer' in section:
                            items = section['itemSectionRenderer'].get('contents', [])
                            for item in items:
                                if 'videoRenderer' in item:
                                    video = item['videoRenderer']
                                    video_id = video.get('videoId', '')
                                    title = video.get('title', {}).get('runs', [{}])[0].get('text', 'Unknown Title')

                                    if video_id and title:
                                        results.append({
                                            'title': title,
                                            'url': f'https://www.youtube.com/watch?v={video_id}',
                                            'video_id': video_id
                                        })

                                        if len(results) >= 20:
                                            break
                            if len(results) >= 20:
                                break
                        if len(results) >= 20:
                            break

                except json.JSONDecodeError:
                    print("JSON 파싱 실패, 대안 방법 사용")
                    results = self.fallback_extraction(html_content)
            else:
                # 대안 방법
                results = self.fallback_extraction(html_content)

        except Exception as e:
            print(f"데이터 추출 오류: {e}")
            results = self.fallback_extraction(html_content)

        return results

    def fallback_extraction(self, html_content):
        """대안 추출 방법"""
        results = []

        try:
            # BeautifulSoup을 사용한 기본 추출
            soup = BeautifulSoup(html_content, 'html.parser')

            # 비디오 링크 패턴 찾기
            video_links = soup.find_all('a', href=re.compile(r'/watch\?v='))

            seen_urls = set()
            for link in video_links:
                href = link.get('href')
                if href and href not in seen_urls:
                    # 제목 추출 시도
                    title = link.get('title') or link.get_text(strip=True)

                    if title and len(title) > 5:  # 너무 짧은 제목 제외
                        full_url = f"https://www.youtube.com{href}"
                        results.append({
                            'title': title[:100],  # 제목 길이 제한
                            'url': full_url,
                            'video_id': href.split('v=')[1].split('&')[0] if 'v=' in href else ''
                        })
                        seen_urls.add(href)

                        if len(results) >= 5:
                            break

        except Exception as e:
            print(f"대안 추출 오류: {e}")

        return results

# 유튜브 검색, 재생, 음원추출 모두 담당하는 클랙스
class YouTubeVideoPlayer:
    """YouTube 비디오 플레이어 클래스"""

    def __init__(self, main_window):
        self.main_window = main_window  # 메인 윈도우 객체 받아옴
        self.search_results = []        # 검색결과(딕셔너리 리스트)
        self.search_thread = None       # 검색용 백그라운드 스레드

        self.setup_video_page()         # 비디오 페이지 ui 초기화
        self.setup_connections()        # 각종 이벤트 연결

    # 버튼, 입력창 등과 함수 연결
    def setup_connections(self):
        """비디오 페이지 관련 연결"""
        self.main_window.btn_result.clicked.connect(self.search_youtube)       # 검색 버튼 클릭
        self.main_window.btn_downloa0d.clicked.connect(self.download_audio)     # 다운로드 버튼 클릭

        # 검색 결과 테이블 더블클릭 시 비디오 재생
        self.main_window.result_view.itemDoubleClicked.connect(self.play_selected_video)

        # 엔터키로 검색 가능하도록
        self.main_window.lied_youtube.returnPressed.connect(self.search_youtube)

    # 비디오 관련 ui 초기화
    def setup_video_page(self):
        self.main_window.result_view.clear()        # 결과 목록 비움
        self.main_window.result_view.setSpacing(5)  # 아이템 간격
        self.main_window.lied_youtube.clear()       # 검색어 입력창 비움
        self.main_window.lied_youtube.setPlaceholderText("검색어를 입력하세요...")
        self.main_window.lied_youtube_url.clear()   # url 입력창 비움
        self.main_window.lied_youtube_url.setPlaceholderText("YouTube URL을 입력하세요...")

    # 검색 버튼/엔터 입력시 유튜브에서 검색
    def search_youtube(self):
        """YouTube 검색 실행"""
        query = self.main_window.lied_youtube.text().strip()    # 입력된 검색어 가져옴
        if not query:
            QMessageBox.warning(self.main_window, "경고", "검색어를 입력해주세요.")
            return

        if self.search_thread and self.search_thread.isRunning():
            return  # 이미 검색 중이면 무시

        # 검색 중 표시 UI로 표시
        self.main_window.btn_result.setText("검색 중...")
        self.main_window.btn_result.setEnabled(False)
        self.main_window.result_view.clear()

        # 검색 스레드 시작
        self.search_thread = YoutubeSearchThread(query)
        self.search_thread.search_finished.connect(self.display_search_results)
        self.search_thread.start()

    # 검색결과 리스트에 표시
    def display_search_results(self, results):
        self.search_results = results
        self.main_window.result_view.clear()  # 기존 결과 삭제

        for i, result in enumerate(results):
            # 리스트 아이템 생성(썸네일 + 제목 표시)
            item = QListWidgetItem()
            item.setSizeHint(QSize(390, 70))  # 한 행 높이, 너비 조정 (필요시 변경)
            self.main_window.result_view.addItem(item)

            # 썸네일 생성(미리보기 이미지) 표시
            video_id = result.get("video_id", "")
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/default.jpg"
            thumb_label = QLabel()
            try:
                resp = requests.get(thumbnail_url, timeout=3)
                if resp.ok:
                    img = QImage()
                    img.loadFromData(resp.content)
                    pixmap = QPixmap.fromImage(img)
                    pixmap = pixmap.scaled(90, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    thumb_label.setPixmap(pixmap)
                else:
                    thumb_label.setText("X")
            except Exception as e:
                print("썸네일 에러:", e)
                thumb_label.setText("X")
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setFixedSize(90, 60)

            # 제목 라벨 생성
            title_label = QLabel(result["title"])
            title_label.setToolTip(result["title"])     # 마우스 올리면 전체 제목 보여줌
            title_label.setWordWrap(True)               # 줄바꿈 허용
            # title_label.setMinimumWidth(260)
            # title_label.setMaximumWidth(360)
            font = title_label.font()
            font.setPointSize(11)
            title_label.setFont(font)

            # 수평 레이아웃으로 썸네일 + 제목 배치 # 썸네일 + 제목을 가로로 배치
            widget = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(5, 2, 5, 2)
            layout.setSpacing(12)
            layout.addWidget(thumb_label)
            layout.addWidget(title_label)
            widget.setLayout(layout)

            self.main_window.result_view.setItemWidget(item, widget)

        # 검색 버튼 다시 활성화
        self.main_window.btn_result.setText("검색")
        self.main_window.btn_result.setEnabled(True)

        if not results:
            QMessageBox.information(self.main_window, "정보", "검색 결과가 없습니다.\n네트워크 연결을 확인하거나 다른 검색어를 시도해보세요.")
        else:
            print(f"검색 완료: {len(results)}개 결과")

    # 검색결과 더블 클릭시 비디오 재생
    def play_selected_video(self, item):
        row = self.main_window.result_view.row(item)
        if 0 <= row < len(self.search_results):
            video_url = self.search_results[row]["url"]
            video_title = self.search_results[row]["title"]

            self.main_window.lied_youtube_url.setText(video_url)    # url 입력창에 링크 표시
            self.load_video(video_url)                              # 유튜브 재생
            print(f"재생 중: {video_title}")

    # 비디오를 웹뷰에 로드(재생)
    def load_video(self, url):
        """비디오를 웹뷰에 로드"""
        try:
            # YouTube URL을 embed 형식으로 변환
            video_id = ""
            if "youtube.com/watch?v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            elif "youtube.com/embed/" in url:
                video_id = url.split("embed/")[1].split("?")[0]

            if video_id:
                # 자동재생 및 관련 비디오 표시 옵션 추가
                embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1"
                self.main_window.view_video.load(QUrl(embed_url))
                print(f"비디오 로드: {embed_url}")
            else:
                # 일반 URL 그대로 사용
                self.main_window.view_video.load(QUrl(url))

        except Exception as e:
            print(f"비디오 로드 오류: {e}")
            QMessageBox.warning(self.main_window, "오류", f"비디오를 로드할 수 없습니다: {str(e)}")

    def download_audio(self):
        """오디오 다운로드"""
        url = self.main_window.lied_youtube_url.text().strip()
        if not url:
            QMessageBox.warning(self.main_window, "경고", "다운로드할 URL을 입력해주세요.")
            return

        # audio.py의 추출기 인스턴스 생성
        extractor = YouTubeAudioExtractor()

        # 다운로드 안내 메시지
        reply = QMessageBox.question(
            self.main_window,
            "음원 다운로드",
            f"다음 URL의 음원을 다운로드하시겠습니까?\n\n{url}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 실제 다운로드 수행
            self.main_window.setEnabled(False)
            try:
                # progress dialog 등 UI block 방지 추가 가능
                file_path = extractor.extract_audio(url)
                if file_path and os.path.exists(file_path):
                    QMessageBox.information(self.main_window, "성공", f"다운로드 완료: {file_path}")
                else:
                    QMessageBox.warning(self.main_window, "실패", "다운로드에 실패했습니다.")
            except Exception as e:
                QMessageBox.critical(self.main_window, "오류", f"다운로드 중 오류 발생: {str(e)}")
            finally:
                self.main_window.setEnabled(True)

    def set_search_query(self, query):
        """검색어 설정 (외부에서 호출 가능)"""
        self.main_window.lied_youtube.setText(query)

