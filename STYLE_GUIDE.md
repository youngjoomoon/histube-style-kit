# histube 스타일 가이드 (2026-09 최신, EP06 냉전 v4 기준)

영어 세계사 세로 영상 채널의 제작 규칙이다. 어떤 툴(Flova 등)로 만들든 이 문서의 규칙과 값을 지키면 같은 느낌이 나온다.
완성 예시는 `examples/ep06_coldwar/`에 있다(영상, 씬별 대본, 실제 프롬프트).

---

## 0. 채널 정체성

- **컨셉:** "교과서에서 다루지 않는 재밌는 세계사". 영어 나레이션이고, 대상은 전 세계 일반 시청자다.
- **본질은 지식 전달이다.** 긴장감만 주는 영상이 아니다. 누가 누구와 대립했는지, 지도 위 위치·배치, 나라별 수치 같은 **구체 정보를 많이** 보여준다.
- **지금 스타일:** 실사풍 시네마틱 컷 + 코드로 그린 정확한 지도·그래픽 + 빨간 정보 태그 + 차분한 다큐 나레이션.

## 1. 포맷

| 항목 | 값 |
|---|---|
| 화면 | 세로 9:16, 1080×1920, 30fps |
| 길이 | 3~4.5분. 쇼츠 3분 제한은 필수가 아니다. 정보가 충분한 쪽을 택한다 |
| 씬 | 한 씬 = 한 화면 = 나레이션 1~2문장, **18단어 이하**(8초 클립에 맞추기 위해) |
| 한 편 | 30~45씬 |

## 2. 대본 규칙

### 구조
- **훅:** 궁금증을 주는 질문이나 모순 → 곧바로 반전·답. 예: "What would a nuclear war between America and Russia actually look like?"
  - 인트로, 채널 소개, 구독 요청(CTA)은 넣지 않는다. 첫 단어부터 본론이다.
- **흥미로운 부분을 앞으로 뺀다.** EP06에서는 "시뮬레이션 먼저 → 실제로 일어날 뻔했다"로 순서를 뒤집었다.
- **사례가 여러 개면** 가장 최근·가장 센 사례 하나를 자세히 다룬다. 나머지는 끝에서 빠르게 요약한다.
- **엔딩:** 오프닝과 수미상관으로 닫는다. 마지막 문장이 훅의 핵심 명사를 다시 받는다.

### 문장
- 짧은 평서문, 문장 하나에 아이디어 하나. 차분하고 확신 있는 다큐 톤.
- **숫자·날짜·지명·고유명사를 약 20단어마다 하나씩** 넣는다.
  - 모든 수치는 확인 가능한 실제 값이어야 한다. 확신이 없으면 "about", "more than"처럼 근사로 쓰고, 가짜 정밀도는 쓰지 않는다.
- **대립 구도를 명시한다.** "a Soviet submarine", "American warning computers", "Russia's radar"처럼 어느 나라의 무엇인지를 항상 붙인다.
- **맥락 없는 문장은 금지한다.** 시청자가 이 시점에 모르는 전제를 쓰지 않는다. 예를 들어 앞 설명 없이 "one person said no"를 쓰면 안 된다.

### 씬 사이 연결 문장 (필수)
씬 경계마다 앞 씬을 받는 짧은 연결어를 넣는다.
- 질문 → 본론: "Before we find that country, meet…"
- 단계 진행: "Then… / With Europe in ruins… / Now multiply it…"
- 파트 전환: "That is not only a simulation. It nearly began for real."
- 답 공개: "The country is Singapore."

초안을 쓴 뒤 **씬 n → n+1 전환만 따로 한 번 훑어서**, 앞 씬 없이도 주어·지시어가 이해되는지 확인한다.

### 나레이션(TTS)용 주의
- 연도 바로 뒤에 시각을 붙이지 않는다. "June 1980, three a.m."은 "nineteen eighty-three a.m."으로 읽힌다 → "Three a.m., June 1980."
- 헷갈리는 동음어를 피한다. "Five pass"는 "Five past"로 들린다 → "Five minutes gone".
- 짧은 문장을 나열하면 TTS가 느려진다. 전체 속도는 편집에서 1.10배로 맞춘다.

### 팩트체크
- 각 씬의 확인 가능한 주장(숫자, 날짜, 이름, 인과관계)을 뽑아서 출처로 확인한다. 통과한 뒤에 유료 생성 단계로 넘어간다.
- 출처를 확인하지 못한 서술은 화면에 "feared scenario", "illustration"처럼 표시하거나 뺀다.

## 3. 화면 톤 — AI 실사 컷

### 룩
- **Cinematic photoreal 3D render.** 실제 장소 안에 카메라가 있고, 장소가 화면 밖으로 계속 이어지는 느낌.
- 부드러운 자연광, 실사 재질(땅, 돌, 나무, 금속, 천).
- 에피소드마다 **팔레트 한 줄을 정해서 모든 컷에 붙인다.** 예(EP06): cold blue-green CRT and radar glow, dark rooms, hard red warning lights, brushed steel and bakelite; outdoors grey winter light.
- **첫 컷(기준 프레임)은 글 프롬프트만으로 만든다.** 이후 컷은 기준 프레임을 "화풍 참조"로 첨부한다. 구도는 복사하지 않는다.

### 인물 규칙
- 시대 고증에 맞는 실사 인물을 **소수**만 쓴다(0~5명, 최대 10명). 인원수는 "exactly three…"처럼 정확히 적는다.
- **온전한 전신을 멀리** 둔다. 손·다리만 잡는 부분 구도는 금지다(잘린 다리, 거인 손이 나온다).
- **실존 인물은 뒷모습·실루엣·먼 거리로만** 보여준다. 얼굴은 닮게 그리지 않고, **이름은 빨간 태그로** 붙인다(6장).
  - "face not visible"이라고 쓰면 얼굴을 검게 지운다. 대신 카메라를 등 뒤에 두거나 손·팔만 나오는 크롭으로 설계한다.
- 피, 상처, 시신, 손상된 맨살은 영상 AI 안전 필터에 걸린다. 자세, 추위, 진흙, 물, 연기로 표현한다.
- 파괴 장면(폭발 등)에는 사람을 넣지 않는다. 건물, 차량, 하늘, 지형만 쓴다.

### 컷 종류 (`style`)
- `landscape`(기본, 인물 허용)
- `no_people`
- `top_down`: 수직 부감, 하늘 없음
- `map`: 입체 지형 모형. 정확한 지도는 5장처럼 코드로 그린다
- `studio`: 밝은 바닥 위 미니어처, 비교 도해용

### 스틸(첫 프레임) 프롬프트 틀 — 복사해서 쓰기
```
{무엇이 보이는지: 장소·구조물·땅·날씨·빛·인물 정확한 수와 위치. 스케일은 대문자로 못 박기 — 예: "the trench is DEEPER than the man is tall"}
Setting: {era}, {region}. Colour palette: {palette}. Avoid: {negative}.
Cinematic photoreal 3D render, the camera placed inside a continuous real place that extends beyond every edge of the frame, a natural sky filling the top of the frame, photoreal materials with real-looking ground, vegetation, stone, timber, metal and cloth, soft natural daylight, every person {people_style}, realistic, with natural human proportions and natural posture, weathered and period-accurate, faces ordinary and never looking at the camera, vertical 9:16 composition filled top to bottom, no text, no letters, no numbers, no labels, no logos.
One single continuous picture: no panels, no split screen, no translucent bars, no letterbox, no graphics, no arrows, no captions. No modern buildings, no modern vehicles, nothing from another era.
```
- 2번째 컷부터는 맨 앞에 다음 문장을 붙인다: `The attached image is an earlier frame of this same film. Use it ONLY for rendering style, materials, colour grade and the look of the people, structures and terrain. Do NOT reuse its camera angle or composition: build the new view described below.`
- 같은 카메라로 전후를 비교하는 컷(예: 폭발 전 → 후): `Edit the attached image. Keep exactly the same camera position, framing, horizon and the same main subject in the same place, and change the scene to this: …`
- 한 컷에 장소를 두 개 쓰면 화면이 상하로 쪼개진다. **장소는 하나만** 쓴다.
- 잠수함·벙커 같은 실내는 "sealed hull, NO windows/portholes/skylights"를 명시한다. 안 쓰면 창문과 하늘이 생긴다.

### 8초 영상(모션) 프롬프트 틀 — 복사해서 쓰기
```
A 8-second shot. It is on screen for about {N} seconds, so the key action happens within the first {N} seconds and the rest settles.
SHOT: {렌즈·시점 한 문장}
BEAT 1: {이미 움직이고 있는 것으로 시작}
BEAT 2: {핵심 동작}
BEAT 3: {정지로 가라앉음}
EYE ORDER: {시선이 가는 순서}
CAMERA: camera not moving.   (또는 one single very slow continuous push in, nothing else. / one single slow tilt up, nothing else — no pan, the camera never tracks sideways.)
HOLD: exactly {n} people from first frame to last, each one the same person in the same clothes; bodies move with real weight and natural human timing, no sliding, no floating, no sped-up or looping motion; hands have normal fingers; tools and weapons stay in their owners' hands and never multiply, bend or pass through bodies; everyone stays where they are unless a beat says otherwise, nobody walks toward the camera; keep {유지할 것} exactly as in the first frame; nothing dissolves, melts, fades, warps or disappears; the light stays unchanged; the scene keeps extending past every edge of the frame, no floating block, no studio backdrop.
END FRAME: {마지막 프레임 한 문장}
NEVER: nothing enters the frame from outside; no extra people appear and nobody vanishes; no giant hands, no giant objects, no new objects, no modern clothing or equipment, no text and no graphics ever appear; any torch or flame stays a small steady point of light and never grows, spreads or becomes a fire, no smoke; the only moving things are the ones named in the beats. This is one single continuous shot from first frame to last: no cuts, no scene change, no jump to a different place or a different angle.
```
(인물이 없는 컷은 HOLD 첫 부분을 `no person ever appears;`로 바꾼다.)

### 영상 AI에서 겪은 실패와 대처
- **카메라:** 고정, 아주 느린 푸시인, 느린 틸트업만 쓴다. 풀백·횡이동·오빗은 스틸에 없는 영역을 지어내서 장소가 통째로 바뀐다.
- **금지 동작:** 카메라 쪽으로 걸어오는 사람, 프레임에 새로 들어오는 사람, 손도구를 카메라 가까이서 휘두르는 동작. 제3의 인물이 끼어든다.
- **이동 동작:** "앞으로 나가 확인하고 돌아온다" 같은 이동은 발을 고정하고 고개만 돌리게 바꾼다.
- **그래픽:** 영상 AI에 그리게 하면 0.5초 만에 지우거나 뭉갠다. **깨끗한 컷을 먼저 뽑고 그래픽은 편집에서 얹는다.**
- **시간 순서:** 팔레트에 "then blinding white, then fire"처럼 순서를 쓰면 기준 스틸부터 폭발로 그린다. 팔레트는 중립으로 두고, 변화는 각 컷 설명에 쓴다.
- **폭발 규모:** 폭발 규모감은 **원경**(20km 밖 언덕에서 도시를 화면 하단 1/3의 얇은 띠로)으로 잡는다. 근접 부감은 미니어처처럼 보인다.
- **시험 생성:** 싼 초안 모델로 먼저 전체를 뽑아 보고, 통과한 컷만 고화질로 만든다.

## 4. 편집 레이아웃 — 화면 안전 구역 (1080×1920 기준)

| 구역 | y 범위 | 용도 |
|---|---|---|
| 상단 키워드 카드 | 285 ~ 570 | 카드만. 중요한 피사체·태그 금지 |
| 초점 구역 | 580 ~ 1120 | 주 피사체, 지도 중심(y≈860) |
| 자막 | 1132 ~ 1380 | 자막만 |
| 하단 정보 | 1420 ~ 1850 | 큰 숫자, 범례, 보조 태그 |

스틸을 만들 때 "upper third kept visually calm for a title card, lower-middle band uncluttered for subtitles"를 의식한다. 피사체가 자막 자리에 걸리면 편집에서 1.3~1.5배 확대해 위로 올린다.

## 5. 지도·데이터 그래픽 (코드로 그린다, AI 생성 금지)

AI가 그린 지도는 국경이 틀린다. **실제 국경 데이터(Natural Earth)로 그린다.** 스크립트는 `tools/ep06_maps.py`이고, 예시 25컷이 영상 안에 있다.

| 요소 | 값 |
|---|---|
| 우주/배경 | #05070B |
| 바다 | #0B141F, 위→아래 약간 어두워짐. 지구본 테두리에 옅은 푸른 대기 글로우 |
| 육지 | #28303A, 국경선 #4E5C6A 1px |
| 경위선 | #14212F, 10° 간격 |
| 서방·NATO·미국 | 파랑 #3480DE, 투명도 40~55% |
| 러시아·소련 | 빨강 #CE2C2C, 투명도 50~60% |
| 폭발·타격 | 주황 글로우 #FFAA50 + 퍼지는 링 |
| 레이더·오로라 | 초록 #5AE696 |
| 투영 | 정사도법(지구본). 미국·러시아는 북극 위에서 내려다보는 구도, 지역은 확대 |
| 움직임 | 로그 줌 카메라 이동, 탄도 호(대권 경로 + 고도), 점이 순서대로 켜짐, 숫자 카운터가 올라감 |
| 글자 | 지명은 흰색 Montserrat + 검정 외곽선. 핵심 수치는 하단 정보 구역에 110~150pt 큰 숫자 + 설명 한 줄 |
| 출처 표기 | 맨 아래 22pt 회색(예: `PRINCETON SGS · PLAN A`, `NUKEMAP · W88 455 KT AIRBURST`) |

- **자주 쓰는 그래픽:** 진영 지도, 공격 점 분포, 미사일 궤적, 피해 반경 동심원(실제 도시 위, "FOR SCALE" 표시), 30개국 통보선, 레이더 부채꼴, 카운트다운 링, 막대그래프, 사건 핀 지도.
- 위치를 정확히 모르면(예: 낙하 지점) 점 대신 **넓은 원 + "near …"**로 표시한다.

## 6. 그래픽 디자인 값 (샘플: `assets/tag_samples/`)

- **폰트:** Montserrat Bold 하나만 쓴다(`assets/fonts`, OFL 무료 라이선스).
- **채널 레드:** `#C62828`(RGB 198, 40, 40). 흰색은 `#FFFFFF`.

| 요소 | 스펙 |
|---|---|
| **키워드 카드** (상단) | 씬마다 1개. 대문자 1~3단어 또는 숫자("8 OF 10 MINUTES", "455 KT"). 104pt 흰 글씨 + 빨간 박스, 화면 상단 중앙(MarginV 290). 등장 시 0.16초 동안 82%→100% 팝 + 0.1초 페이드, 씬 끝까지 유지. 두 줄은 " / "로 구분 |
| **자막** (하단) | 86pt 흰 글씨, 검정 외곽선 7px + 그림자 2, 하단 중앙(MarginV 560). 2~4단어(16자 이하)씩 끊는다. 한 단어만 남으면 앞 묶음과 합쳐 반으로 나눈다. 문장 단위로 실제 음성 구간에 맞춘다 |
| **빨간 태그** | 빨간 박스 + 흰 대문자(클립 1080 기준 약 51pt, 여백 18). 아래에 흰 보조줄(약 40pt, 검정 외곽선). 0.55초 페이드인 |
| 인물 태그 | `NAME` + `나라 · 역할 · 날짜` (예: VASILY ARKHIPOV / USSR · submarine B-59 · 27 Oct 1962) |
| 수치 태그 | `5 KM` + `5 psi · buildings collapse` |
| **원 강조** | 빨간 원(두께 5 + 옅은 글로우 11)이 시계방향으로 그려짐 → 지시선 → 태그 |
| **치수선** | 빨간 선 + 끝 눈금 + 보조선, 가운데 태그(예: "7 FT") |
| **화살표·호** | 두께 7 빨간 선 + 삼각 머리, 그려지며 등장 |

- 그래픽은 **AI 영상 위에 편집으로 얹는다.** 영상 AI 프롬프트에는 항상 "no text, no graphics"를 넣는다.

## 7. 사운드

| 요소 | 값 |
|---|---|
| 나레이터 | 깊고 차분한 권위 있는 남성 다큐 톤(Gemini TTS의 **Charon** 목소리). 지시문: `Read aloud as a deep, calm, authoritative documentary narrator, at a brisk steady pace:` |
| 속도 | 생성본 앞뒤 무음을 잘라낸 뒤 **1.10배속** |
| 배경음 | 저음 드론: 55Hz + 82.4Hz + 110.6Hz 사인파 + 갈색 노이즈(260Hz 로우패스), 느린 트레몰로(0.12Hz) + 긴 에코. 나레이션 볼륨에 맞춰 자동으로 줄어들게(덕킹). 처음 1초 페이드인, 끝 1.6초 페이드아웃 |
| 효과음 | `assets/sfx/`: detonation(폭발), blast_wave(충격파), rumble_tail(여진), whoosh(미사일). 타격 순간에 −8~0dB로. 큐 예시는 `examples/ep06_coldwar/sfx.json` |
| 음량 | 최종 −14 LUFS, 트루피크 −1.2dB |

## 8. 편집 리듬

- 씬과 씬 사이 숨 0.18초, 전환은 0.3초 디졸브.
- 씬 최소 1.5초, 한 컷 5초 이내가 이상적. 마지막 씬 뒤 여운 1.2초.
- 영상 클립은 8초로 뽑아 앞부분만 쓴다(빨리감기 없음). 핵심 동작이 앞 N초 안에 끝나게 프롬프트를 쓴다.
- 폭발 순간은 편집에서 흰 섬광(0.18초 유지 → 1.1초 페이드)과 화면 흔들림을 더하고, 효과음을 맞춘다.

## 9. 제작 순서

1. **주제·각도:** 흥미 포인트를 앞으로 뺀 구성으로 잡는다.
2. **자료 조사:** 수치마다 출처를 적은 팩트 시트(예: `FACTS` 문서)를 만든다.
3. **씬 대본:** `prompts/scene_flow_system.md`를 시스템 프롬프트로 쓴다. 씬마다 나레이션, 카드, 주장 목록, 스틸, 모션.
4. **연결 문장 점검 + 팩트체크:** 통과해야 다음으로 간다.
5. **정보 씬 배치:** 지도·그래프로 갈 씬을 먼저 정하고, 코드로 그린다.
6. **AI 실사 컷:** 기준 프레임 → 나머지 스틸 → 싼 초안 영상 → 검수 → 고화질.
7. **그래픽 얹기:** 빨간 태그, 원, 치수선, 섬광, 흔들림.
8. **나레이션:** 1.10배속.
9. **합성:** 카드, 자막, 배경음, 효과음, −14 LUFS.
10. **검증:** 최종 영상의 오디오를 다시 받아써서 대본·자막과 단어가 일치하는지 확인한다. 화면(자막)과 소리(나레이션)는 따로 만들어지므로 둘 다 확인해야 한다.

## 10. 출고 전 체크리스트
- [ ] 첫 문장이 질문·모순이고, 바로 답·반전이 나온다
- [ ] 모든 대립 문장에 나라가 명시돼 있다
- [ ] 약 20단어마다 숫자·날짜·고유명사가 있다
- [ ] 씬 전환마다 연결어가 있고, 맥락 없는 지시어가 없다
- [ ] 지도는 실제 국경 데이터로 그렸고, 출처 표기가 있다
- [ ] 실존 인물은 얼굴 없이, 이름은 빨간 태그로
- [ ] 카드는 상단 구역에, 자막은 자막 구역에만 있고 서로 겹치지 않는다
- [ ] 최종 오디오 받아쓰기가 대본과 일치한다
- [ ] 구독 요청(CTA)·인트로가 없다
