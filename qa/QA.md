# QA 기록 (긴 문장 형식)

점검: 2026-11-22. 문장은 주제마다 10–12개의 완전한 문장이다. 민아는 여자아이, 열세 살, 6학년이고 여동생은 열한 살, 4학년이다. 1번 JSON은 제공된 `about_me_long` 원고와 같다.

영어 문장과 한글 뜻을 대조했다. 단어 8–10개가 본문에 있는지는 원고를 저장할 때 검사한다. 음원 100개는 faster-whisper `base.en`으로 받아 적어 대본과 비교했다. 짧은 단어만 이상하면 그 조각만 다시 받아 적었다.

## 고친 문장

| 주제 | 원래 | 들린 소리 | 고친 문장 |
| --- | --- | --- | --- |
| 16 | Tom is my best friend, and I trust him. | Thomas my best friend… | My best friend is Tom, and I trust him. / 나의 가장 친한 친구는 톰이고, 나는 톰을 믿어요. |
| 16 | I am happy when Tom is with me. | when Thomas with me | I am happy when I am with Tom. / 나는 톰과 함께 있을 때 행복해요. |
| 24 | 단어 near, The park is near my home…, because it is near. | 단어만 읽으면 mirror | 단어를 nearby로 바꿈. The park is nearby, and I go there often. / We like this park because it is nearby. / 오빠 문장은 along the path. |

고친 문장은 따로 읽어 확인했다. “My best friend is Tom…”, “I am happy when I am with Tom.”, “nearby”, “The park is nearby…” 로 들린다.

## 고치지 않은 것

- Seoul은 /soʊl/이라 긴 파일에서 soul로 적힌다. 발음은 맞다.
- sea는 see, 글자 C와 같은 소리다.
- schoolbag은 school bag으로 나뉜다.
- May Day는 Mayday로 붙는다. 소리는 같다.
- fourth, sixth, eleven, thirteen은 4th, 6th, 11, 13으로 적힌다. 서수와 숫자의 소리다.
- 24번 긴 파일을 VAD로 자르면 앞부분이 빠지지만, VAD 없이 다시 들으면 문장이 다 있다.
- cute를 단어만 읽으면 Hute로 적히지만, 문장 “she is cute”는 cute로 들린다.
- weekend 문장만 읽으면 “on the weekend”가 맞다. 긴 파일의 Celt는 한 번의 오기다.

## 페이지

주제 페이지는 오른쪽 단어 칸, 왼쪽 본문, 문장 아래 한글, 한 페이지에 들어가도록 글자 크기를 키운다. QR 100개는 `https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t=NNN` 으로 디코드된다. 저장소가 비공개이고 Pages가 꺼져 있으면 휴대폰에서 열리지 않는다.
