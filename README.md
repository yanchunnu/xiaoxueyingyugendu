# 초등 영어 듣고 따라 읽기

초등학교 3–4학년 수준의 영어 듣기·따라 말하기 책입니다. 주제는 100개입니다. 각 주제는 단어 8–10개와 문장 10–12개로 되어 있습니다. 문장은 짧지만 완전한 문장이고, `and`나 `because`를 쓸 수 있습니다.

말하는 사람은 민아입니다. 민아는 여자아이이고 열세 살, 6학년입니다. 여동생은 열한 살, 4학년입니다. 민아를 가리킬 때는 she/her를 씁니다. 1번 「About Me」는 제공된 긴 원고 그대로입니다.

## 폴더

| 경로 | 내용 |
| --- | --- |
| `content/` | 주제 JSON 100개와 `manifest.json` |
| `audio/` | `001_about_me.mp3` 형식의 음원. 모노 24 kHz, 48 kbps |
| `qr/` | 각 주제 MP3 주소가 들어 있는 QR 이미지 |
| `pdf/listen_and_repeat.pdf` | 표지, 차례, 주제 100쪽이 모인 책 |
| `pdf/topics/` | 주제별 PDF 한 장 |
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

한 번 재생한 뒤에는 그 소리 길이만큼 더하고 1.5초를 더 쉬었다가 다음을 재생합니다. 설정은 브라우저에 기억됩니다. 조각 음원은 `audio/clips/NNN/w01.mp3`, `s01.mp3`, `full.mp3` 입니다. 전체 음원 `audio/NNN_slug.mp3` 도 그대로 있습니다.

## QR 코드

QR은 웹 플레이어로 갑니다.

`https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t=001`

**저장소를 공개로 바꾸고 GitHub Pages를 켜야 휴대폰에서 열립니다.** Settings → Pages → Branch를 `main`, 폴더는 `/ (root)` 로 저장하세요. 이 저장소는 지금 비공개라서, 공개하고 Pages를 켜기 전에는 QR이 동작하지 않습니다. `main`에 이 파일들이 있어야 합니다.

## 다시 만들기

Python 3, `ffmpeg`, `zbarimg`이 필요합니다. 패키지는 `requirements.txt` 입니다.

```bash
pip install -r requirements.txt
python3 scripts/export_content.py
python3 scripts/build_audio.py
python3 scripts/build_book.py
```

음원 일부만 다시 만들려면 `python3 scripts/build_audio.py --only 14,81` 입니다. 글을 고친 뒤에는 `export_content.py`를 먼저 실행하세요. 1번 JSON은 덮어쓰지 않습니다. 주제 원고는 `scripts/data/` 에 있습니다.

한글 글꼴이 없으면 `build_book.py`가 Noto Sans KR 가변 폰트를 받아 `build/fonts/`에 두고, 책에 쓰인 글자만 PDF에 넣습니다.

발음 점검은 `python3 scripts/qa_audio.py` 입니다. faster-whisper로 음원 100개를 받아 적어 대본과 비교합니다.
