# 초등 영어 듣고 따라 읽기

초등학교 3–4학년을 위한 영어 듣기·따라 말하기 책입니다. 주제 100개. 각 주제는 단어 8–10개와 짧은 문장 6–9개로 되어 있고, 문장은 따라 말하기 좋은 조각으로 나뉩니다.

말하는 사람은 민아(Mina)입니다. 열 살, 4학년, 서울에 사는 여자아이로 맞춰 두었습니다. 가족·친구·학교 이야기는 서로 어긋나지 않게 썼습니다. 63번(선생님)과 64번(의사)은 서로 다른 꿈의 예시입니다. 50번 제목은 목록에 있는 영국식 철자 **My Favourite Colour** 이고, 본문과 단어는 미국식 음성(Jenny)에 맞춰 **favorite / color** 로 적었습니다. 소리는 같습니다.

## 폴더

| 경로 | 내용 |
| --- | --- |
| `content/` | 주제 JSON 100개와 `manifest.json`. 1번은 원본 `about_me.json` 그대로입니다. |
| `audio/` | `001_about_me.mp3` 형식의 음원. 모노 24 kHz, 48 kbps. |
| `qr/` | 각 주제 MP3 주소가 들어 있는 QR 이미지. |
| `pdf/listen_and_repeat.pdf` | 표지, 차례, 주제 100쪽이 모인 책. |
| `pdf/topics/` | 주제별 PDF 한 장. |
| `scripts/` | JSON 내보내기, 음원, PDF·QR을 다시 만드는 스크립트. |
| `fonts/` | PDF 영어 글꼴 (SIL OFL). 한글은 빌드할 때 Noto Sans KR을 받아 부분집합으로 넣습니다. |
| `index.html` | 주제 목록과 오디오 플레이어. 같은 폴더의 `audio/`를 재생합니다. |

## 음원 구성

각 MP3는 같은 순서입니다.

1. 제목
2. “Words. Listen and repeat.”
3. 단어를 한 번씩 읽고, 약 2초 쉬고, 단어마다 세 번
4. “Now, let's read. Listen and repeat.”
5. 문장 조각을 한 번 읽고, 그 길이의 약 1.5배(최소 2.5초) 쉽니다
6. 본문을 쉬지 않고 한 번 더 읽습니다
7. “Great job!”

음성은 Microsoft Edge TTS `en-US-JennyNeural`, 속도 `-20%` 입니다. 제목에 괄호가 있으면 읽어 주는 문장은 괄호 없이 말합니다. 예: 화면의 `Self-Introduction (1)` 은 소리로 `Self-Introduction, Part One` 입니다. 본문에 적힌 영어와 들리는 영어는 같습니다.

## QR 코드

각 주제 페이지 오른쪽 위의 QR은 이 주소를 가리킵니다.

`https://raw.githubusercontent.com/yanchunnu/xiaoxueyingyugendu/main/audio/NNN_slug.mp3`

휴대폰 브라우저가 MP3를 바로 재생하는 주소입니다. **이 저장소는 비공개입니다.** 로그인하지 않은 사람, 그리고 저장소 권한이 없는 휴대폰에서는 이 주소가 열리지 않습니다. 학급에서 QR을 쓰려면 저장소를 공개로 바꾼 뒤 `main`에 음원이 있어야 합니다. 공개로 바꾸면 지금 QR을 다시 만들 필요는 없습니다.

`index.html`의 재생기는 QR과 달리 상대 경로 `audio/...mp3` 를 씁니다. 이 폴더를 통째로 열거나, 공개 GitHub Pages로 이 저장소를 올리면 페이지 안에서 들을 수 있습니다. 비공개 저장소의 Pages도 외부 휴대폰에는 막혀 있습니다.

## 다시 만들기

필요 프로그램: Python 3, `ffmpeg`, `zbarimg`. 파이썬 패키지는 `requirements.txt` 입니다.

```bash
pip install -r requirements.txt
python3 scripts/export_content.py   # content JSON (1번 파일은 덮어쓰지 않음)
python3 scripts/build_audio.py      # audio/NNN_slug.mp3
python3 scripts/build_book.py       # QR, 합본 PDF, 주제 PDF, index.html
```

음원만 일부만 다시 만들려면 `python3 scripts/build_audio.py --only 12,50` 입니다. 글을 고친 뒤에는 `export_content.py`를 먼저 실행하세요. 주제 글의 원본은 `scripts/data/` 에 있습니다.

`build_book.py`는 한글 글꼴이 없으면 Noto Sans KR 가변 폰트를 받아 `build/fonts/`에 두고, 책에 쓰인 글자만 남겨 PDF에 넣습니다. `fonts/NotoSansKR-var.ttf`가 있으면 그 파일을 씁니다.

발음 점검은 `python3 scripts/qa_audio.py` 입니다. faster-whisper로 음원 100개를 받아 적어 대본과 비교하고 `qa/audio_report.json`에 남깁니다. QR은 `build_book.py`가 만들 때마다 zbar로 주소가 맞는지 확인합니다.
