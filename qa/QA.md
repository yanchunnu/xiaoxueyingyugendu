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

주제 페이지는 오른쪽 단어 칸, 왼쪽 본문, 문장 아래 한글, 한 페이지에 들어가도록 글자 크기를 키운다. QR 100개는 `https://yanchunnu.github.io/xiaoxueyingyugendu/player.html?t=NNN` 으로 디코드된다. 플레이어에서 English / 中文 을 고르면 된다. PDF는 영어 그대로다.

## 중국어

민아는 米娜, 여동생은 妹妹다. 단어 1000개, 문장 1101개, 제목 100개를 같은 순서의 간체 중국어와 성조 병음으로 넣었다. 한글은 바꾸지 않았다. 음성은 `zh-CN-XiaoxiaoNeural`, 속도 `-20%`, 모노 24 kHz, 48 kbps다. 조각은 `audio/zh/clips/NNN/w01.mp3`, `s01.mp3`, `full.mp3` 2201개다. 주제별 긴 중국어 MP3는 만들지 않았다.

faster-whisper `small`, `language=zh`로 본문 100개와 단어 조각을 받아 적었다. 짧은 단어는 환각이 많다. 본문에서 문자가 빠지거나 다른 말로 들리면 그 문장 조각을 다시 받아 적어 확인했다. 他/她/它, 的/地/得, 铅笔/签笔, 坐/做, 玩/丸, 雪橇/雪敲처럼 소리가 같은 것은 고치지 않았다. 游泳, 首尔을 단어만 읽으면 받아 적기가 흔들리지만, 문장 안에서는 맞게 들린다. 28번과 89번 본문 전체를 한 번에 받아 적으면 앞이나 끝이 빠지기도 한다. 문장 조각과 다시 받아 적은 전체는 대본과 맞다.

## 고친 중국어

| 주제 | 원래 | 들린 소리 | 고친 말 |
| --- | --- | --- | --- |
| 1, 3, 20 | 단어 年级 | 年纪 | 几年级. 문장의 六年级, 四年级는 그대로다. |
| 23 | 下午街道很热闹。 | 接到 | 下午马路上很热闹。 |
| 24 | 长椅 | 단어는 乘以, 문장은 墙椅·床椅 | 板凳 |
| 34 | 铃, 车铃 | 零, 灵 | 铃声. “它有铃声。” “铃声会响。” |
| 40 | 有趣的书让人不想合上。 | 不想和尚 | 有趣的书让人不想放下。 |
| 44 | 涂色 | 图色 | 上色 |
| 44 | 纸可以变成任何东西，所以我享受画画。 | 只可以…想说话话 | 空白的地方能变成任何东西，所以我喜欢画图。 |
| 46 | 水很凉快。 | 谁很凉快 | 池水很凉快。 |
| 46 | 然后浮着休息。 | 扶着 | 然后浮在水上休息。 |
| 48 | 给我力气。 | 给我立起 | 给我力量。 |
| 77 | 문장의 五一 | 武衣, 我一日 | 句子는 劳动节. 단어 五一만 읽으면 五一으로 들린다. |
| 79 | 日营 | 日盈 | 日间营 |
| 79 | 早上我享受一本书。 | 想收 | 早上我开心地读一本书。 |

고친 조각은 다시 받아 적었다. 几年级, 板凳, 铃声, 放下, 上色, 空白的地方…画图, 池水, 力量, 劳动节 문장, 日间营, 开心地读一本书 로 들린다.
