import os
import sys
import yt_dlp
from pydub import AudioSegment
import re


class YouTubeAudioExtractor:
    def __init__(self, output_dir="downloads"):
        """
        YouTube 음원 추출기 초기화

        Args:
            output_dir (str): 다운로드 파일이 저장될 디렉토리
        """
        self.output_dir = output_dir
        self.create_output_dir()

    def create_output_dir(self):
        """출력 디렉토리가 없으면 생성"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"디렉토리 생성: {self.output_dir}")

    def sanitize_filename(self, filename):
        """파일명에서 특수문자 제거"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.replace(' ', '_')
        return filename[:100]  # 파일명 길이 제한

    def extract_audio(self, url, output_format='mp3', quality='320'):
        """
        YouTube URL에서 음원 추출

        Args:
            url (str): YouTube URL
            output_format (str): 출력 포맷 (mp3, wav, m4a 등)
            quality (str): 음질 (128, 192, 320 kbps)

        Returns:
            str: 생성된 파일 경로 또는 None (실패시)
        """
        try:
            # yt-dlp 옵션 설정
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': quality,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': output_format,
                    'preferredquality': quality,
                }],
                'postprocessor_args': [
                    '-ar', '44100',  # 샘플링 레이트
                ],
                'prefer_ffmpeg': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 비디오 정보 가져오기
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)

                print(f"제목: {title}")
                print(f"길이: {duration // 60}분 {duration % 60}초")
                print("다운로드 시작...")

                # 실제 다운로드 및 변환
                ydl.download([url])

                # 생성된 파일 경로 찾기
                safe_title = self.sanitize_filename(title)
                output_file = os.path.join(self.output_dir, f"{safe_title}.{output_format}")

                # 실제로 생성된 파일 찾기 (제목이 변경될 수 있음)
                for file in os.listdir(self.output_dir):
                    if file.endswith(f'.{output_format}') and title.split()[0] in file:
                        actual_file = os.path.join(self.output_dir, file)
                        print(f"다운로드 완료: {actual_file}")
                        return actual_file

                return output_file

        except Exception as e:
            print(f"오류 발생: {str(e)}")
            return None

    def extract_multiple_audio(self, urls, output_format='mp3', quality='320'):
        """
        여러 YouTube URL에서 음원 추출

        Args:
            urls (list): YouTube URL 리스트
            output_format (str): 출력 포맷
            quality (str): 음질

        Returns:
            list: 성공적으로 다운로드된 파일 경로 리스트
        """
        successful_downloads = []

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 처리 중...")
            result = self.extract_audio(url, output_format, quality)
            if result:
                successful_downloads.append(result)
            print("-" * 50)

        return successful_downloads

    def convert_audio_format(self, input_file, output_format='mp3'):
        """
        오디오 파일 포맷 변환

        Args:
            input_file (str): 입력 파일 경로
            output_format (str): 출력 포맷

        Returns:
            str: 변환된 파일 경로
        """
        try:
            audio = AudioSegment.from_file(input_file)
            output_file = input_file.rsplit('.', 1)[0] + f'.{output_format}'
            audio.export(output_file, format=output_format)
            print(f"포맷 변환 완료: {output_file}")
            return output_file
        except Exception as e:
            print(f"포맷 변환 오류: {str(e)}")
            return None


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("        YouTube 음원 추출기")
    print("=" * 60)

    # 추출기 인스턴스 생성
    extractor = YouTubeAudioExtractor()

    while True:
        print("\n선택하세요:")
        print("1. 단일 URL 음원 추출")
        print("2. 여러 URL 음원 추출")
        print("3. 종료")

        choice = input("\n선택 (1-3): ").strip()

        if choice == '1':
            url = input("YouTube URL을 입력하세요: ").strip()
            if url:
                format_choice = input("출력 포맷 (mp3/wav/m4a, 기본값: mp3): ").strip() or 'mp3'
                quality = input("음질 (128/192/320, 기본값: 320): ").strip() or '320'

                result = extractor.extract_audio(url, format_choice, quality)
                if result:
                    print(f"\n✅ 성공적으로 다운로드됨: {result}")
                else:
                    print("\n❌ 다운로드 실패")

        elif choice == '2':
            print("YouTube URL들을 입력하세요 (빈 줄 입력시 종료):")
            urls = []
            while True:
                url = input("URL: ").strip()
                if not url:
                    break
                urls.append(url)

            if urls:
                format_choice = input("출력 포맷 (mp3/wav/m4a, 기본값: mp3): ").strip() or 'mp3'
                quality = input("음질 (128/192/320, 기본값: 320): ").strip() or '320'

                results = extractor.extract_multiple_audio(urls, format_choice, quality)
                print(f"\n✅ {len(results)}/{len(urls)}개 파일 다운로드 완료")

        elif choice == '3':
            print("프로그램을 종료합니다.")
            break

        else:
            print("잘못된 선택입니다.")


if __name__ == "__main__":
    # 필요한 라이브러리 설치 확인
    try:
        import yt_dlp
        from pydub import AudioSegment
    except ImportError as e:
        print("필요한 라이브러리가 설치되지 않았습니다.")
        print("다음 명령어로 설치하세요:")
        print("pip install yt-dlp pydub")
        print("\n추가로 FFmpeg가 필요합니다:")
        print("Windows: https://ffmpeg.org/download.html")
        print("Mac: brew install ffmpeg")
        print("Linux: sudo apt install ffmpeg")
        sys.exit(1)

    main()
