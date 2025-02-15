import os

# 기본 파일 저장 디렉토리 (환경 변수나 기본값 설정)
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

def get_file_path(filename: str) -> str:
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    return os.path.join(DOWNLOAD_DIR, filename)