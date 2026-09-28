# 03 · Visual Style Bible + Image/Video Prompt Templates

> 레퍼런스 룩: 흰 클레이 모델 도시 + 사실적 물 + 항공/단면 시점 + 빨간 치수선. 텍스트는 이미지에 넣지 않고(생성 모델이 망침) 편집에서 키워드 카드로 얹는다.
> 모든 이미지 프롬프트는 `FRAME + STYLE_PREFIX + scene.visual_prompt + ANCHOR + STYLE_SUFFIX` 순서로 조립한다. (조립 코드: `scripts/build_manual_kit.py`)
> 2026-09-17 s001 테스트 반영: ① 색을 접두어에 고정하면 에피소드 팔레트를 덮어씀(참호가 흰 건물+파란 물로 나옴) → 색은 ANCHOR의 palette가 결정 ② ANCHOR에 camera_style(시퀀스 설명)을 넣으면 2x2 콜라주가 나옴 → 장면 프롬프트에서 제외 ③ 단일 프레임·화면비를 FRAME으로 명시. ⑤ 2026-09-18: 첫 결과물이 '손으로 만든 클레이 매크로(얕은 심도, 인물 클로즈업)'로 나와 레퍼런스와 달랐음 → 접두어를 '드론으로 찍은 매싱 모델·딥포커스·사람은 실루엣 피규어'로 교체, 앵글을 SHOTS 어휘로 고정, 참조 프레임(`reference/sinbi_hangang_short/shots/`) 도입. ⑥ 2026-09-18 2단계 생성으로 전환(3D 인포그래픽 제작 프롬프트 참고): 1차는 **그래픽 없는 장면만**(`visual_prompt`), 빨간 그래픽은 `overlay` 필드로 분리해 2차 이미지 편집 또는 편집툴에서 추가. 한 컷 ≤5초 — 나레이션이 5초를 넘는 장면은 `extra_shots`로 컷을 나눔(대본은 그대로). 접두어에 '3D infographic keyframe · 단일 초점 대상 · 단순한 배경 · 입체감 · 반복 대상 디자인 일관성' 추가. ④ 빨간 주석선은 visual_prompt에 red 선이 명시된 도해 장면에만 넣고, 나머지는 `No overlay graphics, no annotation lines, no viewfinder marks.`로 대체(클로즈업에서 카메라 HUD처럼 보였음).

## FRAME (맨 앞, 화면비별)
```
A single full-frame vertical 9:16 portrait image, one continuous shot, not a collage, no split panels, no grid. Subject centred, upper third kept visually calm for a title card, lower-middle band uncluttered for subtitles. 
A single full-frame horizontal 16:9 image, one continuous shot, not a collage, no split panels, no grid. 
```

## STYLE_PREFIX (FRAME 뒤에 고정)
```
High-quality 3D infographic documentary keyframe, educational engineering-visualisation style, like a physical massing model filmed from a drone: simplified low-detail matte forms, terrain as a sculpted relief model coloured in the palette given below, water rendered realistically with reflections, people only as tiny dark silhouette figurines. One clear focal subject, uncluttered surroundings, strong sense of depth and volume, cinematic dynamic camera angle. Even overcast daylight, soft shadows, wide-angle lens, deep focus with everything sharp, no background blur. Recurring objects keep exactly the same design, colours and materials in every image of the series. 
```

## STYLE_SUFFIX (모든 프롬프트 뒤에 고정)
```
 High detail, sharp focus, no text, no letters, no numbers, no logos, no watermark, no people's faces, no modern objects unless specified.
```

## ANCHOR (에피소드마다 Claude가 script.visual_anchor로 생성 → 문장으로 이어붙임)
```
Setting: {era}, {region}. Colour palette: {palette}. Only if they belong in this shot, recurring elements look like: {recurring_subjects}. Avoid: {negative}.
```
`camera_style`은 대본 작성용 가이드로만 쓰고 장면 프롬프트에는 넣지 않는다.

## SHOTS — 앵글 어휘 (scene.shot, 레퍼런스 프레임에서 추출)
조립 순서(1차): `{FRAME}{STYLE_PREFIX}{SHOTS[shot]} {visual_prompt}. {ANCHOR}{NO_ACCENTS}{STYLE_SUFFIX}` — `hud_card`만 NO_ACCENTS 생략
`visual_prompt`에는 앵글도 그래픽도 쓰지 않고 **무엇이 보이는지**만 쓴다. 빨간 그래픽은 `overlay`에 따로 쓴다.

| shot | 참조 프레임 | 프롬프트 문구 |
|---|---|---|
| `axis_aerial` | `axis_aerial.jpg` | High drone aerial looking straight down the long axis of the subject, symmetrical one-point perspective, the subject running from the bottom centre of the frame to a horizon in the top quarter. |
| `oblique_aerial` | `oblique_aerial.jpg` | Oblique 45-degree aerial view, isometric feel, the landscape filling the whole frame with no sky. |
| `top_down_map` | `top_down_map.jpg` | Straight top-down view of a relief model, like a 3D satellite map, no horizon. |
| `relief_map` | `relief_map.jpg` | Steep oblique aerial over a stylised relief-map model of the region, simplified grey landforms and blue water. |
| `cutaway` | `cutaway.jpg` | Cutaway cross-section: the terrain block is sliced vertically facing the camera like a cake, the ground line runs horizontally across the upper third with open sky above it, and the exposed layered earth strata fill the lower two thirds. |
| `macro` | `macro.jpg` | Low close view of a single object on the model, wide-angle, deep focus, the landscape still readable behind it. |
| `low_inside` | `low_inside.jpg` | Low camera at floor level inside the structure looking along its length, strong one-point perspective, walls rising on both sides. |
| `pictogram` | `pictogram.jpg` | High oblique aerial diagram view, rows of identical tiny dark silhouette figurines arranged in clean lines like an infographic built on the model. |
| `hud_card` | `hud_card.jpg` | Dark navy blueprint-style background with a faint thin grid, a few thin red crosshair lines and corner brackets, a small simplified section drawing of a trench in thin lines near the bottom. |

추가 참조 프레임(`scene.ref`): `outline_aerial.jpg`(영역을 빨간 외곽선으로), `oblique_rings.jpg`(대상 주변 빨간 동심원).

## 빨간 그래픽 어휘 (scene.overlay에 서술 → 2차 편집)
| 용도 | 표현 |
|---|---|
| 치수 | `a red dimension line with end ticks spanning …` (세로/가로/점선) |
| 영역 | `a glowing red outline tracing the boundary of …` |
| 경로 | `a thick glowing red ribbon laid on the terrain from … to …`, `a red location pin` |
| 강조 | `flat red concentric rings glowing on the ground around …` |
| 지시 | `thin red leader lines each ending in a small blank red tag` (글자는 편집에서) |
| 힘·이동 | `a bold red arrow …`, `thin straight red trajectory lines` |

2차 편집 프롬프트 템플릿 (1차 결과 이미지를 첨부):
```
Edit the attached image. Keep the scene, camera, colours and every object exactly as they are, and add only this graphic on top: {overlay}. All red graphics are flat vector overlays in one bright red with a slight glow, in the manner of CAD annotation: thin lines with small arrowheads and end ticks, any tags left blank, no legible characters. No other changes.
```
1차 생성에 항상 붙는 문구:
```
Scene only: no infographic elements of any kind — no arrows, no lines, no labels, no icons, no overlay graphics, no viewfinder marks.
```
hero 장면은 그래픽 추가본을 Veo에 넣으면 선이 카메라와 함께 움직인다(레퍼런스 방식). 선이 일그러지면 클린본으로 영상화하고 그래픽은 편집툴에서 얹는다.

## 참조 이미지 첨부 시 프롬프트 맨 앞에
```
Use the attached image only as a reference for camera angle, framing and rendering style. Do not copy its subject, location, red graphics, text, subtitles or watermark.
```

## 정지화상 프롬프트 템플릿 (Nano Banana / gemini-3.1-flash-image, 16:9, 2K)
```
{FRAME}{STYLE_PREFIX}{SHOTS[shot]} {visual_prompt}. {ANCHOR}{NO_ACCENTS}{STYLE_SUFFIX}
```

## 영상 클립 프롬프트 템플릿 (Veo image-to-video = 첫 프레임 방식 / Omni, 입력 = 해당 장면 정지화상 + 텍스트. 길이는 duration_hint를 4/6/8초로 올림)
```
Animate this image as a single continuous {motion} over {4|6|8} seconds. {scene.visual_prompt} Keep every object, colour and layout exactly as in the input image; only the camera and natural elements (rain, water, mist, smoke) move. No cuts, no zoom bursts, no new objects, no text.
```
`{motion}` 매핑:
| motion_hint | 문구 |
|---|---|
| slow_push_in | slow forward dolly push-in |
| pull_out | slow backward pull-out revealing the surroundings |
| pan_left / pan_right | slow lateral pan to the left / right |
| tilt_up | slow tilt from the water surface up to the skyline |
| orbit | slow 20-degree orbit around the subject |
| static | locked-off camera, only water and light moving |
| dramatic | slow push-in with rising floodwater or surging current |

## 키워드 카드 (편집에서 얹는 텍스트 — 이미지 프롬프트에 넣지 않음)
- 장면당 최대 1개, `scene.on_screen_text` 사용. 1~3단어, 숫자 우선.
- 스타일: 대형 산세리프 볼드, 흰색 또는 채널 레드(#C62828), 얇은 검정 외곽선, 화면 상단 1/3 또는 중앙. 0.3s 팝인, 장면 끝까지 유지.
- 챕터 오프너는 흰 배경 전체 카드에 검정/빨강 대형 활자로 챕터 제목.

## 자막
- 하단 1/3 중앙, 흰 볼드(Montserrat) + 검정 외곽선 3px, 2~5단어 단위, 나레이션 단어 타이밍에 동기화. 쇼츠는 크기 1.6배, 중앙 정렬.

## 네거티브 (항상 포함)
```
text, letters, numbers, captions, logos, watermark, signature, readable signage, real human faces, photorealistic crowds, modern cars or phones in historical scenes, blurry, low detail, cartoon outline, oversaturated
```
