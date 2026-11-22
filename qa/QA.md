# QA 기록

점검 날짜: 2026-11-22. 음성 인식은 faster-whisper `base.en` (CPU, int8, VAD)로 음원 100개를 받아 적어 대본과 비교했다. QR 100개는 `zbarimg`으로 주소를 확인했다. PDF는 텍스트 추출과 페이지 이미지로 한글·강세 표시·QR 자리를 보았다.

## 고친 것

| 주제 | 원래 문장 | 문제 | 고친 문장 |
| --- | --- | --- | --- |
| 14, 21 | Tom is kind. | 통째로 들으면 “Thomas Kind”처럼 붙어 들림 | Tom can be kind. / 톰은 친절할 수 있어요. |
| 81 | I ride a sled. | “I write a slide.”로 들림 | I play on a sled. / 나는 썰매를 타며 놀아요. |

고친 세 음원을 다시 받아 적었고, 14·21은 “Tom can be kind”가 조각 읽기와 통독에 각각 한 번씩 나왔고, 81은 “I play on a sled”로 들렸다.

## 고치지 않은 인식 차이

발음이 맞는데 받아쓰기 철자만 다른 경우다.

- Seoul은 /soʊl/이라 긴 파일에서는 soul로 적힌다. 문장만 따로 읽히면 Seoul로 적힌다.
- sea와 see, 글자 C는 같은 소리다. 페이지 철자는 sea다.
- schoolbag은 school bag으로 나뉜다. 소리 경계가 맞다.
- May Day는 긴 파일에서 Mayday로 붙는다. 문장만 읽히면 May Day다. 소리도 같다.
- “I write in my diary.”는 긴 파일에서 한 번 ride로 적혔다. 그 문장만 읽히면 write다.
- fair가 한 번 Fairrypt로 깨진 뒤 Fair로 두 번 들렸다. 단어만 읽히면 Fair다.
- “There is a long river.”가 긴 파일에서 한 번 깨졌다. 문장만 읽히면 정확하다.

괄호가 있는 제목은 소리에서 괄호를 빼 읽는다. 예: Self-Introduction (1) → “Self-Introduction, Part One”. 본문 영어와 들리는 영어는 같다. p.m., a.m. 같은 줄임은 쓰지 않았고, 숫자는 단어로 적었다.

## 글 점검

- 단어 8–10개, 문장 6–9개, 단어가 본문에 실제로 나오는지, 강조 단어가 그 문장 안에 있는지는 `scripts/export_content.py`가 저장 전에 검사한다.
- 1번 About Me는 제공된 JSON과 바이트 단위로 같다.
- 한글은 해요체. 가족 구성(민아 10살 4학년, 오빠 12살, 언니 14살, 여동생 6살, 식구 여섯)이 주제 사이에 맞지 않는 곳은 없었다. 63·64는 서로 다른 꿈의 예시다.

## PDF와 QR

- 합본 104쪽(표지, 차례 3쪽, 주제 100쪽). 표지, 차례, 1·42·49·68·84번 페이지를 이미지로 보았고 한글이 깨지지 않았다.
- 핵심 단어는 본문에서 코랄색으로 표시된다.
- QR 100개 모두 `https://raw.githubusercontent.com/yanchunnu/xiaoxueyingyugendu/main/audio/NNN_slug.mp3` 로 디코드된다.
- 저장소가 비공개라서, 권한이 없는 휴대폰에서는 이 주소가 재생되지 않는다.
