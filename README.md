# histube style kit

영어 세계사 세로 영상(9:16) 채널의 **최신 제작 스타일** 공유 패키지다. 기준은 EP06 냉전 편 v4(2026-09-27)이다.
Flova 같은 영상 툴에서 그대로 따라 만들 수 있게 규칙, 프롬프트 틀, 디자인 값, 에셋, 완성 예시를 모았다.

## 먼저 볼 것
1. **`examples/ep06_coldwar/final_540p.mp4`**: 완성본(4분 27초). 이 느낌이 목표다.
2. **`STYLE_GUIDE.md`**: 대본 규칙, 화면 톤, 프롬프트 틀(복사용), 레이아웃, 지도, 그래픽·사운드 값, 제작 순서, 체크리스트.
3. **`examples/ep06_coldwar/SCENES.md`**: 41씬 전체의 시각, 화면 종류, 나레이션, 카드. AI 실사 컷의 실제 스틸·모션 프롬프트도 들어 있다.

## 폴더

| 경로 | 내용 |
|---|---|
| `STYLE_GUIDE.md` | 스타일의 모든 규칙과 값 |
| `prompts/scene_flow_system.md` | 씬 대본을 만드는 시스템 프롬프트(현재 사용본). 주제와 팩트를 user 메시지로 넣으면 씬별 JSON이 나온다 |
| `prompts/metadata_title_thumbnail.md` | 제목·설명·태그·썸네일 문구 프롬프트 |
| `prompts/legacy/` | 초기(클레이 모형·드론샷 시절) 프롬프트. **참고용, 지금 스타일 아님** |
| `assets/fonts/` | Montserrat Bold + OFL 라이선스 |
| `assets/sfx/` | 폭발·충격파·여진·미사일 효과음(직접 합성, 자유 사용) |
| `assets/tag_samples/` | 키워드 카드·자막·빨간 태그 디자인 샘플 PNG |
| `examples/ep06_coldwar/` | 완성 영상, 프레임 모음(`frames.jpg`), 씬표(`SCENES.md`), AI 컷 원본 JSON, 효과음 큐 |
| `tools/` | (선택) 파이썬 도구. 아래 참고 |

## tools/ (선택: 파이썬을 쓸 수 있으면)
Flova 같은 툴로는 만들기 어려운 부분을 코드로 만든 원본이다. 원래 프로젝트 폴더 구조(`episodes/<ep>/clip`, `assets/`)를 가정하고 있어서, 그대로는 안 돌고 경로를 맞춰야 한다.
- `ep06_maps.py`: 실제 국경(Natural Earth GeoJSON) 지도 애니메이션. 지구본 카메라, 탄도 호, 카운터. 필요: `numpy opencv-python pillow matplotlib`, ffmpeg. 데이터는 https://github.com/nvkelso/natural-earth-vector 의 `geojson/` 폴더.
- `fx_overlay.py`: 영상 위에 빨간 태그·원·치수선·화살표를 프레임 단위로 그린다(`FX` dict에 씬별 좌표).
- `clip_fx.py`: 섬광·흔들림 효과.
- `sfx_synth.py`: 효과음 합성(numpy).

## 들어 있지 않은 것
- API 키, 클라우드 설정, 비용 기록: 각자 계정을 쓴다.
- 원본 고화질 영상과 중간 산출물(용량이 큼).
- 레퍼런스로 분석한 다른 채널의 원본 영상.
