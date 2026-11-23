# 초등 영어 듣고 따라 읽기

초등학교 3–4학년 수준의 영어 듣기·따라 말하기 책입니다. 주제는 100개입니다. 각 주제는 단어 8–10개와 문장 10–12개로 되어 있습니다. 문장은 짧지만 완전한 문장이고, `and`나 `because`를 쓸 수 있습니다.

말하는 사람은 민아입니다. 민아는 여자아이이고 열세 살, 6학년입니다. 여동생은 열한 살, 4학년입니다. 민아를 가리킬 때는 she/her를 씁니다. 1번 「About Me」는 제공된 긴 원고 그대로입니다.

## 폴더

| 경로 | 내용 |
| --- | --- |
| `content/` | 주제 JSON 100개와 `manifest.json` |
| `audio/` | `001_about_me.mp3` 형식의 영어 음원. 모노 24 kHz, 48 kbps |
| `audio/zh/clips/` | 중국어 단어·문장·본문 조각. `zh-CN-XiaoxiaoNeural`, `-20%` |
| `qr/` | 각 주제 MP3 주소가 들어 있는 QR 이미지 |
| `pdf/listen_and_repeat.pdf` | 영어판 책. 표지, 차례, 주제 100쪽 |
| `pdf/topics/` | 영어판 주제별 PDF 한 장 |
| `pdf/zh/listen_and_repeat_zh.pdf` | 중국어판 책. 표지, 차례, 주제 100쪽 |
| `pdf/zh/topics/` | 중국어판 주제별 PDF. 파일 이름은 `NNN_slug_zh.pdf` |
| `scripts/` | JSON, 음원, PDF를 다시 만드는 스크립트 |
| `fonts/` | PDF 영어 글꼴 (SIL OFL). 한글은 Noto Sans KR입니다 |
| `index.html` | 주제 목록과 오디오 플레이어 |

페이지 왼쪽은 본문입니다. 영어 문장 바로 아래에 한글이 있습니다. 단어는 오른쪽 칸에 위에서 아래로 있고, 영어 다음에 뜻이 있습니다. 글자 크기는 한 페이지에 들어가도록 자동으로 맞춥니다.

## 음원

1. 제목
2. “Words. Listen and repeat.”
3. 단어를 읽고 약 2초 쉰 뒤, 단어마다 세 번
4. “Now, let's read. Listen and repeat.”
5. 문장을 한 문장씩 읽고, 그 길이의 약 1.3배(최소 3초) 쉽니다
6. 본문을 쉬지 않고 한 번 더 읽습니다
7. “Great job!”

음성은 Edge TTS `en-US-JennyNeural`, 속도 `-20%` 입니다. 제목에 괄호가 있으면 소리에서는 괄호를 빼서 읽습니다. 예: `Self-Introduction (1)` 은 “Self-Introduction, Part One” 입니다. 본문에 적힌 영어와 들리는 영어는 같습니다.

## 따라 읽기 플레이어

`player.html?t=001` 처럼 주제 번호를 엽니다. 휴대폰에서도 버튼이 크게 보입니다.

- 단어 따라읽기 횟수 (기본 3, 0이면 건너뜀)
- 본문 문장별 따라읽기 횟수 (기본 1)
- 본문 전체 듣기 횟수 (기본 1)
- 한국어 뜻 보기/숨기기

단어는 조각 길이에 0.6초를 더하고, 전체 쉼은 최소 1.2초입니다. 문장과 본문 전체는 조각 길이에 1.5초를 더합니다. 횟수는 0부터 5까지이고, 설정은 브라우저에 기억됩니다. 영어 조각은 `audio/clips/NNN/w01.mp3`, `s01.mp3`, `full.mp3` 입니다. 전체 음원 `audio/NNN_slug.mp3` 도 그대로 있습니다.

플레이어 위쪽에서 English / 中文 을 고릅니다. 선택은 `localStorage` 에 남고, 주소의 `lang=zh` 또는 `lang=en` 이 그 선택을 덮어씁니다. 기본은 영어입니다. 중국어일 때는 한자 위에 성조가 있는 병음이 나오고, 병음은 숨길 수 있습니다. 한글 뜻은 어느 언어에서나 같은 버튼으로 숨깁니다. 중국어 조각은 `audio/zh/clips/NNN/` 입니다. 민아는 米娜, 여동생은 妹妹 입니다.

중국어 PDF는 `pdf/zh/listen_and_repeat_zh.pdf` 입니다. 왼쪽은 병음, 중국어 문장, 한글 뜻이고, 오른쪽 칸은 중국어 단어, 병음, 한글 뜻입니다. 그 QR은 `player.html?t=NNN&lang=zh` 로 갑니다. 영어 PDF의 QR은 예전처럼 플레이어로 가며, 플레이어에서 중국어를 고를 수 있습니다.

## QR 코드

QR은 웹 플레이어로 갑니다.

`https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t=001`

휴대폰에서 들으려면 저장소가 공개이고 GitHub Pages가 `main` 의 `/ (root)` 여야 합니다. 예: `https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t=001&lang=zh`

## 다시 만들기

Python 3, `ffmpeg`, `zbarimg`이 필요합니다. 패키지는 `requirements.txt` 입니다.

```bash
pip install -r requirements.txt
python3 scripts/export_content.py
python3 scripts/build_audio.py
python3 scripts/build_book.py
python3 scripts/build_zh_book.py
```

음원 일부만 다시 만들려면 `python3 scripts/build_audio.py --only 14,81` 입니다. 글을 고친 뒤에는 `export_content.py`를 먼저 실행하세요. 1번 JSON은 덮어쓰지 않습니다. 주제 원고는 `scripts/data/` 에 있습니다.

한글 글꼴이 없으면 `build_book.py`가 Noto Sans KR 가변 폰트를 받아 `build/fonts/`에 두고, 책에 쓰인 글자만 PDF에 넣습니다.

발음 점검은 `python3 scripts/qa_audio.py` 입니다. faster-whisper로 음원 100개를 받아 적어 대본과 비교합니다.
