"""클립 위에 편집 그래픽을 코드로 그린다 — 빨간 계측선·원+라벨선·구분선·태그·쌍안경 마스크.

Veo 에게 그래픽을 그리게 하면 0.5초 만에 지우거나 뭉갠다. 그래서 깨끗한 클립을 먼저 뽑고 여기서 얹는다.
사용:  python scripts/fx_overlay.py episodes/ww1_trench_v2 [--only s003,s016]
  원본은 clip/_clean/sNNN.mp4 에 보관하고 clip/sNNN.mp4 를 그래픽 입힌 본으로 바꾼다. 클립을 다시 뽑으면 자동으로 새 원본을 잡는다.
좌표는 클립 픽셀(720x1280) 기준. (a, b) 튜플은 클립 시작→끝으로 선형 보간(푸시인 추적용). t 는 등장 시각(초).
"""
import argparse
import hashlib
import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = str(ROOT / "assets" / "fonts" / "Montserrat-Bold.ttf")
RED, WHITE, SS = (198, 40, 40), (255, 255, 255), 2  # SS = 슈퍼샘플 배율

FX = {
    "colosseum": {
        # s003: 모래층 = 뚜껑. 단면의 모래 띠(y≈635~690)·목재 데크(690~725) 위치. 좌표는 720x1280 클립 기준(스틸 1536x2752 의 0.46875 배)
        "s003": [{"type": "tag", "at": (560, 600), "text": "SAND", "sub": "arena = sand", "pointer": "down", "t": 1.6, "until": 4.2},
                 {"type": "tag", "at": (450, 780), "text": "A LID", "sub": "timber deck under the sand", "pointer": "up", "t": 4.6}],
        # s004: 나무 뚜껑의 장축 83 m(세로, 타원 y 250~1035) · 단축 48 m(가로, x 95~625)
        "s004": [{"type": "measure", "p0": (668, 250), "p1": (668, 1035), "ext0": 360, "ext1": 360, "t": 0.8, "label": "83 M", "label_at": (600, 560)},
                 {"type": "measure", "p0": (95, 1110), "p1": (625, 1110), "ext0": 642, "ext1": 642, "t": 2.6, "label": "48 M", "label_at": (360, 1175)}],
        # s016: 단면 안 기계 부품 라벨 — 바닥의 뚜껑(467,687) · 샤프트에 올라간 케이지(253,800) · 캡스턴(473,953)
        "s016": [{"type": "tag", "at": (467, 630), "text": "TRAPDOOR", "pointer": "down", "t": 0.5},
                 {"type": "tag", "at": (250, 742), "text": "LIFT SHAFT", "sub": "cage on ropes", "pointer": "down", "t": 1.6},
                 {"type": "tag", "at": (520, 1030), "text": "CAPSTAN", "sub": "8 men each", "pointer": "up", "t": 2.8}],
    },
    "coldwar": {
        # 사용자 요청: 실제 인물 이름 매핑(빨간 태그). 실존 인물 초상 회피 → 뒷모습 컷 위에 NAME · role · date. 좌표는 스틸(1536x2752→0.46875) 기준 초안; Fast 후 프레임 보고 조정.
        # v3 대립 구도: 누가 누구와 — 국가·진영 태그 (2026-09-26 사용자 요청 "어떤 나라와 어떤 나라가 대립관계였는지 충분히")
        "s002b": [{"type": "tag", "at": (230, 520), "text": "USA + NATO", "sub": "US-led bloc · 1949", "t": 1.6},
                  {"type": "tag", "at": (500, 640), "text": "USSR + WARSAW PACT", "sub": "Soviet-led bloc · 1955", "t": 3.4}],
        "s004b": [{"type": "circle", "c": (385, 495), "r": 50, "t": 1.4, "label": "SOVIET MISSILES", "sub": "Cuba · 1962", "label_at": (560, 415)},
                  {"type": "tag", "at": (360, 1000), "text": "US NAVY BLOCKADE", "sub": "Florida is 145 km away", "pointer": "up", "t": 3.6}],
        "s005": [{"type": "tag", "at": (360, 440), "text": "USSR · SUBMARINE B-59", "sub": "nuclear torpedo aboard", "t": 0.6}],
        "s006": [{"type": "tag", "at": (360, 440), "text": "US NAVY", "sub": "destroyers above, dropping charges", "pointer": "up", "t": 0.6}],
        "s010": [{"type": "tag", "at": (360, 640), "text": "USA · NORAD", "sub": "early-warning computers · Colorado", "t": 0.6}],
        "s013": [{"type": "tag", "at": (360, 560), "text": "USSR · SERPUKHOV-15", "sub": "early-warning bunker near Moscow", "t": 0.8}],
        "s017": [{"type": "tag", "at": (200, 560), "text": "NORWAY · NATO", "sub": "Andøya · science rocket", "t": 2.2}],
        "s027": [{"type": "tag", "at": (150, 420), "text": "USA", "pointer": "down", "t": 1.0}, {"type": "tag", "at": (600, 460), "text": "RUSSIA", "pointer": "down", "t": 1.6}],
        "s004": [{"type": "tag", "at": (360, 1000), "text": "30 MIN", "sub": "ICBM · Russia → USA", "t": 0.6, "until": 3.2},
                 {"type": "tag", "at": (360, 1000), "text": "< 10 MIN", "sub": "for the president to decide", "t": 3.4}],
        "s007": [{"type": "circle", "c": (490, 640), "r": 60, "t": 1.0, "label": "KEY 3", "sub": "untouched", "label_at": (500, 420)}],
        "s008": [{"type": "tag", "at": (360, 440), "text": "VASILY ARKHIPOV", "sub": "chief of staff, B-59 · 27 Oct 1962", "pointer": "down", "t": 0.6}],
        "s009": [{"type": "tag", "at": (360, 440), "text": "ZBIGNIEW BRZEZINSKI", "sub": "US National Security Adviser · 3 June 1980", "t": 0.8}],
        "s011": [{"type": "tag", "at": (360, 440), "text": "ONE MINUTE", "sub": "before the call to President Carter", "t": 1.2}],
        "s012": [{"type": "reframe", "zoom": 1.5, "focus": (360, 880)}, {"type": "tag", "at": (360, 470), "text": "46 ¢ CHIP", "sub": "one faulty part", "pointer": "down", "t": 1.2}],
        "s015": [{"type": "tag", "at": (360, 440), "text": "STANISLAV PETROV", "sub": "Lt Col, Serpukhov-15 · 26 Sept 1983", "pointer": "down", "t": 0.6}],
        "s018": [{"type": "tag", "at": (360, 440), "text": "BORIS YELTSIN", "sub": "Cheget nuclear briefcase · 25 Jan 1995", "t": 0.8}],
        "s019": [{"type": "tag", "at": (540, 440), "text": "8 OF 10 MIN", "sub": "spent tracking", "pointer": "down", "t": 0.8}],
        "s020": [{"type": "tag", "at": (360, 1000), "text": "USA · B-52", "sub": "Goldsboro, North Carolina · Jan 1961", "t": 0.5},
                 {"type": "circle", "c": (330, 570), "r": 70, "t": 2.0, "label": "ONE SWITCH", "sub": "3 of 4 safeties failed · 3.8 Mt", "label_at": (330, 420)}],
        # ── v4 (2026-09-27): 재사용 컷 n-id. 옛 sNNN 태그를 옮기고 문맥에 맞게 수정 ──
        "n11": [{"type": "circle", "c": ((360, 600), (355, 480)), "r": (130, 150), "t": 0.6, "label": "1.5 KM", "sub": "fireball · 1 second", "label_at": (360, 1000)}],
        "n12": [{"type": "tag", "at": (360, 1000), "text": "5 KM", "sub": "5 psi · buildings collapse", "t": 0.3}],
        "n14": [{"type": "tag", "at": (360, 1000), "text": "1,000,000+ DEAD", "sub": "in 24 h · one warhead · NUKEMAP", "t": 1.0}],
        "n18": [{"type": "tag", "at": (360, 1000), "text": "150 Tg SOOT", "sub": "full US–Russia exchange · climate models", "t": 1.0}],
        "n19": [{"type": "tag", "at": (360, 1000), "text": "−7 °C", "sub": "global average · for years", "t": 1.0}],
        "n20": [{"type": "tag", "at": (360, 1000), "text": "5 BILLION", "sub": "starve within two years · Xia 2022", "t": 1.2}],
        "n21": [{"type": "tag", "at": (360, 440), "text": "GEN. JOHN HYTEN", "sub": "US Strategic Command · 2016–18", "t": 0.8},
                {"type": "tag", "at": (360, 1000), "text": "\"IT ENDS THE SAME WAY EVERY TIME\"", "sub": "on the Global Thunder war game", "t": 3.2}],
        "n28": [{"type": "tag", "at": (200, 560), "text": "NORWAY · NATO", "sub": "Andøya · Black Brant XII", "t": 2.2}],
        "n31": [{"type": "tag", "at": (360, 440), "text": "BORIS YELTSIN", "sub": "Cheget nuclear briefcase · 25 Jan 1995", "t": 0.8},
                {"type": "tag", "at": (360, 1000), "text": "3 BRIEFCASES", "sub": "Yeltsin · Grachev · Kolesnikov", "t": 3.4}],
        "n35": [{"type": "tag", "at": (360, 440), "text": "YELTSIN · 26 JAN 1995", "sub": "\"I used my little black case\"", "t": 0.8}],
        "n37": [{"type": "tag", "at": (360, 1000), "text": "USA · B-52", "sub": "Goldsboro, North Carolina · Jan 1961", "t": 0.5},
                {"type": "circle", "c": (330, 570), "r": 70, "t": 2.6, "label": "ONE SWITCH", "sub": "3 of 4 safeties failed · 3.8 Mt", "label_at": (330, 420)}],
        "n38": [{"type": "tag", "at": (360, 440), "text": "VASILY ARKHIPOV", "sub": "USSR · submarine B-59 · 27 Oct 1962", "pointer": "down", "t": 0.6}],
        "n39": [{"type": "reframe", "zoom": 1.5, "focus": (360, 880)}, {"type": "tag", "at": (360, 470), "text": "46 ¢ CHIP", "sub": "USA · NORAD · 3 June 1980", "pointer": "down", "t": 1.0}],
        "n40": [{"type": "tag", "at": (360, 440), "text": "STANISLAV PETROV", "sub": "USSR · Serpukhov-15 · 26 Sept 1983", "pointer": "down", "t": 0.6}],
        # 시뮬: 도시 위 동심원은 s024 프레임을 본 뒤 measure/circle 로 (반경 픽셀은 Fast 프레임에서 잡는다)
        "s023": [{"type": "circle", "c": ((360, 600), (355, 480)), "r": (130, 150), "t": 0.6, "label": "1.5 KM", "sub": "fireball · 1 second", "label_at": (360, 1000)}],
        "s024": [{"type": "tag", "at": (360, 1000), "text": "5 KM", "sub": "5 psi · buildings collapse", "t": 0.3}],
        "s026": [{"type": "tag", "at": (360, 1000), "text": "1,000,000+ DEAD", "sub": "in 24 h · one warhead · NUKEMAP", "t": 1.0}],
        "s028": [{"type": "tag", "at": (360, 1000), "text": "150 Tg SOOT", "sub": "into the stratosphere", "t": 1.0}],
        "s029": [{"type": "tag", "at": (360, 1000), "text": "−7 °C", "sub": "global average · for years", "t": 1.0}],
        "s030": [{"type": "tag", "at": (360, 1000), "text": "5 BILLION", "sub": "starve within two years", "t": 1.2}],
        "s031": [{"type": "tag", "at": (360, 1000), "text": "ARKHIPOV · PETROV · A 46¢ CHIP", "sub": "what stood between us and that", "t": 0.8}],
    },
    "torture": {
        # 사용자 요청(2026-09-24): "빨간 레이블로 어느 쪽을 자극해서 고통을 주는지" — 통증 부위 원/태그 + 힘 화살표.
        # 좌표는 스틸(1536x2752 → 0.46875) 기준 초안. Fast 클립이 나오면 첫/끝 프레임 눈금으로 재확인할 것.
        # 주리: 장대 끝 힘 → 무릎이 받침점 → 정강이뼈가 옆으로 휨
        "s005": [{"type": "arrow", "p0": (215, 290), "p1": (95, 290), "t": 0.8}, {"type": "arrow", "p0": (505, 290), "p1": (625, 290), "t": 0.8},
                 {"type": "circle", "c": (360, 848), "r": 46, "t": 2.8, "label": "FULCRUM", "sub": "the bound knees take the force", "label_at": (360, 620)}],
        "s006": [{"type": "circle", "c": ((280, 690), (272, 700)), "r": (60, 66), "t": 2.0, "label": "TIBIA", "sub": "bent sideways → stress crack", "label_at": (200, 420)},
                 {"type": "tag", "at": (500, 900), "text": "CALF MUSCLE", "sub": "crushed between bone and pole", "pointer": "up", "t": 2.6}],
        # 스트라파도: 어깨 관절이 뒤로 꺾인 채 전체 체중
        "s008": [{"type": "circle", "c": (361, 500), "r": 60, "t": 1.2, "label": "SHOULDER SOCKET", "sub": "rotated backward · dislocates", "label_at": (361, 300)},
                 {"type": "arrow", "p0": (500, 700), "p1": (500, 900), "t": 2.8}, {"type": "tag", "at": (500, 960), "text": "FULL BODY WEIGHT", "pointer": "up", "t": 2.8}],
        "s009": [{"type": "circle", "c": (300, 470), "r": 48, "t": 2.4, "label": "SHOULDER SOCKET", "sub": "humerus head pulled up and back", "label_at": (250, 300)},
                 {"type": "tag", "at": (330, 560), "text": "BRACHIAL PLEXUS", "sub": "arm nerves stretched · paralysis", "pointer": "up", "t": 3.2}],
        # 랙: 래칫 한 칸 = 장력 증가, 관절 하나씩
        "s012": [{"type": "tag", "at": (180, 330), "text": "+1 CLICK = +TENSION", "pointer": "down", "t": 2.0}],
        "s013": [{"type": "circle", "c": ((542, 497), (560, 500)), "r": 48, "t": 2.0, "label": "SHOULDER", "label_at": (542, 330)},
                 {"type": "circle", "c": ((387, 632), (392, 640)), "r": 48, "t": 2.8, "label": "HIP", "label_at": (200, 560)},
                 {"type": "circle", "c": ((277, 774), (270, 790)), "r": 48, "t": 3.6, "label": "KNEE", "sub": "ligaments stretch · joints pull apart", "label_at": (520, 760)}],
        # 폐지 연표: 촛불 위 연도 라벨(꺼지는 순서와 맞춤)
        "s017": [{"type": "tag", "at": (197, 540), "text": "PRUSSIA", "sub": "1740", "pointer": "down", "t": 0.8},
                 {"type": "tag", "at": (306, 470), "text": "AUSTRIA", "sub": "1776", "pointer": "down", "t": 2.8},
                 {"type": "tag", "at": (416, 540), "text": "FRANCE", "sub": "1788", "pointer": "down", "t": 4.8},
                 {"type": "tag", "at": (526, 470), "text": "KOREA", "sub": "1894", "pointer": "down", "t": 6.8}],
        # 태형: 규격 · 보호 부위 · 팁 속도 · 접촉선
        "s021": [{"type": "tag", "at": (360, 1000), "text": "SOAKED OVERNIGHT", "sub": "supple · bends without splitting", "t": 0.8}],
        "s022": [{"type": "circle", "c": (477, 510), "r": 60, "t": 3.6, "label": "KIDNEYS · SPINE", "sub": "padded · protected", "label_at": (250, 380)},
                 {"type": "tag", "at": (194, 800), "text": "WRIST CUFFS", "pointer": "up", "t": 1.6, "until": 3.4},
                 {"type": "tag", "at": (535, 1030), "text": "ANKLE CUFFS", "pointer": "up", "t": 1.6, "until": 3.4}],
        "s025": [{"type": "tag", "at": (360, 1000), "text": "SLOW MOTION", "sub": "the tip whips forward", "t": 0.3, "until": 2.2},
                 {"type": "tag", "at": (360, 1000), "text": "TIP = FASTEST POINT", "sub": "the bend travels down the cane", "t": 2.4}],
        "s026": [{"type": "circle", "c": ((300, 470), (330, 470)), "r": 90, "t": 1.6, "label": "CONTACT LINE", "sub": "shockwave through skin + fat", "label_at": (250, 880)}],
        "s027": [{"type": "circle", "c": ((535, 486), (522, 546)), "r": (40, 50), "t": 1.8, "label": "1 CM STRIP", "sub": "skin + fat · the skin splits → scars", "label_at": (250, 330)},
                 {"type": "tag", "at": (505, 640), "text": "PELVIS", "sub": "hip bone", "pointer": "up", "t": 2.6, "until": 3.5},
                 {"type": "tag", "at": (548, 680), "text": "GLUTEUS", "sub": "muscle · undisturbed", "pointer": "up", "t": 3.6, "until": 4.5},
                 {"type": "tag", "at": (540, 840), "text": "SCIATIC NERVE", "pointer": "down", "t": 4.6}],
    },
    "ww1_trench_v2": {
        "s003": [{"type": "measure", "p0": (585, 300), "p1": (585, 1032), "ext0": 468, "ext1": 452, "t": 0.9, "label": "7 FT", "label_at": (648, 666)}],
        # 워크스루: 카메라가 전진하므로 추적 대신 화면 가장자리의 고정 태그(until 로 퇴장)
        "s006b": [{"type": "tag", "at": (500, 1030), "text": "DUCKBOARDS", "pointer": "down", "t": 1.0, "until": 3.3},
                  {"type": "tag", "at": (500, 480), "text": "REVETMENT", "sub": "timber + wire netting", "t": 3.7}],
        "s006c": [{"type": "tag", "at": (360, 430), "text": "TRAVERSE", "sub": "a corner every few yards", "t": 0.4, "until": 2.5},
                  {"type": "tag", "at": (360, 150), "text": "DUGOUT", "pointer": "down", "t": 3.6}],
        "s008": [{"type": "binoculars", "c1": (232, 640), "c2": (488, 640), "r": 252, "zoom": 1.3, "focus": (430, 640)}],
        "s010": [{"type": "tag", "at": (360, 96), "text": "GERMAN LINE", "pointer": "down", "t": 0.4},
                 {"type": "tag", "at": (360, 1132), "text": "BRITISH LINE", "pointer": "up", "t": 0.7},
                 {"type": "hdash", "y": 640, "t": 1.0, "label": "NO MAN'S LAND"}],
        # 솜 첫날: 사상자 57,470 중 전사 19,240 (영국 공식 집계)
        "s012": [{"type": "tag", "at": (360, 1092), "text": "19,240 KILLED", "sub": "1 July 1916 · first day of the Somme", "t": 1.2}],
        # 발이 자막 자리와 겹쳐서 1.3배 재구도로 발을 위로 올린 뒤 원을 친다 (좌표는 재구도 후 기준)
        "s015b": [{"type": "reframe", "zoom": 1.3, "focus": (380, 800)},
                  {"type": "circle", "c": ((386, 744), (412, 750)), "r": 128, "t": 1.0, "label": "BLOOD FLOW CUT OFF", "sub": "cold + wet · the tissue dies", "label_at": (440, 392)}],
        "s020": [{"type": "tag", "at": (360, 1150), "text": "STAY IN · DISEASE", "pointer": "up", "t": 0.4},
                 {"type": "arrow", "p0": (360, 850), "p1": (360, 640), "block": True, "t": 2.9},
                 {"type": "tag", "at": (360, 560), "text": "GO OVER · MACHINE GUNS", "t": 3.5}],
        "s021": [{"type": "arc", "p0": (110, 640), "c": (360, 150), "p1": (615, 640), "t": 2.0}],
        "s016": [{"type": "circle", "c": ((365, 812), (360, 700)), "r": 98, "t": 0.5, "label": "WEIL'S DISEASE", "sub": "Leptospira bacteria · rat urine", "label_at": (470, 520)}],
        "s017": [{"type": "circle", "c": ((355, 640), (385, 620)), "r": (82, 112), "t": 0.6, "label": "BODY LICE", "sub": "Bartonella quintana bacteria", "label_at": (470, 398)}],
    }
}


def digest(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames", "-of", "csv=p=0", path.name],
                         cwd=path.parent, capture_output=True, encoding="utf-8").stdout.strip().split(",")
    num, den = out[2].split("/")
    return int(out[0]), int(out[1]), float(num) / float(den), int(out[3]) if out[3].isdigit() else 0


def lerp(v, u):
    if isinstance(v, tuple) and isinstance(v[0], tuple):
        return tuple(a + (b - a) * u for a, b in zip(*v))
    if isinstance(v, tuple) and len(v) == 2 and not isinstance(v[0], tuple) and isinstance(v, tuple) and getattr(v, "_kf", False):
        return v[0] + (v[1] - v[0]) * u
    return v


def num(v, u):
    return v[0] + (v[1] - v[0]) * u if isinstance(v, tuple) else v


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def S(p):
    return tuple(int(round(c * SS)) for c in p)


def glow_line(d, pts, w, alpha=255):
    d.line([S(p) for p in pts], fill=RED + (int(alpha * 0.28),), width=w * SS * 3)
    d.line([S(p) for p in pts], fill=RED + (alpha,), width=w * SS)


def label_box(layer, d, center, text, sub, alpha):
    f = ImageFont.truetype(FONT, 34 * SS)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    tw, th = x1 - x0, y1 - y0
    cx, cy = S(center)
    pad = 12 * SS
    box = [cx - tw // 2 - pad, cy - th // 2 - pad, cx + tw // 2 + pad, cy + th // 2 + pad]
    d.rectangle(box, fill=RED + (alpha,))
    d.text((cx - tw // 2 - x0, cy - th // 2 - y0), text, font=f, fill=WHITE + (alpha,))
    if sub:
        fs = ImageFont.truetype(FONT, 27 * SS)
        sx0, sy0, sx1, sy1 = d.textbbox((0, 0), sub, font=fs)
        d.text((cx - (sx1 - sx0) // 2 - sx0, box[3] + 8 * SS), sub, font=fs, fill=WHITE + (alpha,), stroke_width=3 * SS, stroke_fill=(0, 0, 0, alpha))
    return [b / SS for b in box]


def draw(layer, el, t, u):
    d = ImageDraw.Draw(layer)
    a = ease((t - el.get("t", 0)) / 0.55)
    if el.get("until") is not None:
        a *= ease((el["until"] + 0.4 - t) / 0.4)
    if a <= 0:
        return
    al = int(255 * ease((a - 0.7) / 0.3))
    if el["type"] == "measure":
        # 세로 계측(ext = 피사체의 x) 또는 가로 계측(p0·p1 의 y 가 같으면, ext = 피사체의 y)
        p0, p1 = el["p0"], el["p1"]
        horiz = abs(p0[1] - p1[1]) < abs(p0[0] - p1[0])
        tip = (p1[0] + (p0[0] - p1[0]) * a, p1[1] + (p0[1] - p1[1]) * a)
        glow_line(d, [p1, tip], 4)

        def tick(p, alpha):
            glow_line(d, [(p[0], p[1] - 16), (p[0], p[1] + 16)] if horiz else [(p[0] - 16, p[1]), (p[0] + 16, p[1])], 4, alpha)

        def ext(p, e, alpha):
            if horiz:
                gap = 20 if e < p[1] else -20
                d.line([S((p[0], e)), S((p[0], p[1] - gap))], fill=RED + (alpha,), width=2 * SS)
            else:
                gap = 20 if e < p[0] else -20
                d.line([S((e, p[1])), S((p[0] - gap, p[1]))], fill=RED + (alpha,), width=2 * SS)

        tick(p1, 255)
        ext(p1, el["ext1"], 150)
        if a > 0.98:
            tick(p0, al)
            ext(p0, el["ext0"], int(al * 0.6))
        if al:
            label_box(layer, d, el["label_at"], el["label"], el.get("sub"), al)
    elif el["type"] == "circle":
        c, r = lerp(el["c"], u), num(el["r"], u)
        box = [S((c[0] - r, c[1] - r)), S((c[0] + r, c[1] + r))]
        d.arc([box[0][0] - 3 * SS, box[0][1] - 3 * SS, box[1][0] + 3 * SS, box[1][1] + 3 * SS], -90, -90 + 360 * a, fill=RED + (70,), width=11 * SS)
        d.arc([*box[0], *box[1]], -90, -90 + 360 * a, fill=RED + (255,), width=5 * SS)
        if al:
            b = label_box(layer, d, el["label_at"], el["label"], el.get("sub"), al)
            lx, ly = el["label_at"]
            ang = math.atan2(ly - c[1], lx - c[0])
            start = (c[0] + r * math.cos(ang), c[1] + r * math.sin(ang))
            end = (max(b[0], min(b[2], start[0])), b[3] + (34 if el.get("sub") else 0) if ly < c[1] else b[1])
            d.line([S(start), S(end)], fill=RED + (al,), width=3 * SS)
            d.ellipse([S((start[0] - 5, start[1] - 5)), S((start[0] + 5, start[1] + 5))], fill=RED + (al,))
    elif el["type"] in ("arrow", "arc"):
        if el["type"] == "arrow":
            pts = [el["p0"], el["p1"]]
        else:
            (x0, y0), (cx, cy), (x1, y1) = el["p0"], el["c"], el["p1"]
            pts = [((1 - k) ** 2 * x0 + 2 * (1 - k) * k * cx + k * k * x1, (1 - k) ** 2 * y0 + 2 * (1 - k) * k * cy + k * k * y1) for k in [i / 40 for i in range(41)]]
        n = max(2, int(round((len(pts) - 1) * a)) + 1) if len(pts) > 2 else 2
        seg = pts[:n] if len(pts) > 2 else [pts[0], (pts[0][0] + (pts[1][0] - pts[0][0]) * a, pts[0][1] + (pts[1][1] - pts[0][1]) * a)]
        glow_line(d, seg, 7)
        (ax, ay), (bx, by) = seg[-2], seg[-1]
        ang = math.atan2(by - ay, bx - ax)
        head = [(bx + 30 * math.cos(ang), by + 30 * math.sin(ang))] + [(bx + 24 * math.cos(ang + s_), by + 24 * math.sin(ang + s_)) for s_ in (2.5, -2.5)]
        d.polygon([S(q) for q in head], fill=RED + (255,))
        if el.get("block") and a > 0.98:
            glow_line(d, [(bx - 90, by - 44), (bx + 90, by - 44)], 9, al)
    elif el["type"] == "hdash":
        w = layer.size[0] / SS
        x = 0
        while x < w * a:
            d.line([S((x, el["y"])), S((min(x + 22, w * a), el["y"]))], fill=RED + (255,), width=4 * SS)
            x += 36
        if al and el.get("label"):
            label_box(layer, d, (w / 2, el["y"]), el["label"], None, al)
    elif el["type"] == "tag":
        al2 = int(255 * a)
        b = label_box(layer, d, el["at"], el["text"], el.get("sub"), al2)
        cx = el["at"][0]
        if el.get("pointer") == "down":
            d.polygon([S((cx - 14, b[3])), S((cx + 14, b[3])), S((cx, b[3] + 20))], fill=RED + (al2,))
        elif el.get("pointer") == "up":
            d.polygon([S((cx - 14, b[1])), S((cx + 14, b[1])), S((cx, b[1] - 20))], fill=RED + (al2,))


def binocular_mask(size, el):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for c in (el["c1"], el["c2"]):
        d.ellipse([c[0] - el["r"], c[1] - el["r"], c[0] + el["r"], c[1] + el["r"]], fill=255)
    return m.filter(ImageFilter.GaussianBlur(9))


def process(src, dst, els):
    w, h, fps, n = probe(src)
    dec = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src.name, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], cwd=src.parent, stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
                            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", dst.name], cwd=dst.parent, stdin=subprocess.PIPE)
    total = max(n, int(fps * 4))
    bino = next((e for e in els if e["type"] in ("binoculars", "reframe")), None)
    mask = binocular_mask((w, h), bino) if bino and bino["type"] == "binoculars" else None
    black = Image.new("RGB", (w, h), (0, 0, 0))
    i = 0
    while True:
        raw = dec.stdout.read(w * h * 3)
        if len(raw) < w * h * 3:
            break
        t, u = i / fps, min(i / max(total - 1, 1), 1.0)
        frame = Image.frombytes("RGB", (w, h), raw)
        if bino:
            z, (fx, fy) = bino["zoom"], bino["focus"]
            if mask:
                fx, fy = fx + 7 * math.sin(t * 1.3), fy + 5 * math.cos(t * 0.9)  # 손떨림
            cw, ch = w / z, h / z
            x0, y0 = min(max(fx - cw / 2, 0), w - cw), min(max(fy - ch / 2, 0), h - ch)
            frame = frame.resize((w, h), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
            if mask:
                frame = Image.composite(frame, black, mask)
        layer = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        for el in els:
            if el["type"] not in ("binoculars", "reframe"):
                draw(layer, el, t, u)
        frame = Image.alpha_composite(frame.convert("RGBA"), layer.resize((w, h), Image.LANCZOS)).convert("RGB")
        enc.stdin.write(frame.tobytes())
        i += 1
    enc.stdin.close()
    enc.wait()
    dec.wait()
    return i


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    ep = Path(a.episode).resolve()
    spec = FX.get(ep.name) or {}
    only = [x for x in a.only.split(",") if x]
    clean = ep / "clip" / "_clean"
    clean.mkdir(exist_ok=True)
    for sid, els in spec.items():
        if only and sid not in only:
            continue
        clip, keep, mark = ep / "clip" / f"{sid}.mp4", clean / f"{sid}.mp4", clean / f"{sid}.fx"
        # 클립이 마지막 fx 결과와 내용이 같으면 _clean 이 원본이다. 다르면(처음이거나 클립을 다시 뽑았으면) 지금 클립이 새 원본
        if not keep.exists() or not mark.exists() or mark.read_text().strip() != digest(clip):
            shutil.copy2(clip, keep)
        tmp = ep / "clip" / f"{sid}_fx_tmp.mp4"
        n = process(keep, tmp, els)
        tmp.replace(clip)
        mark.write_text(digest(clip))
        print(f"fx {sid}: {n} frames, {', '.join(e['type'] for e in els)}", flush=True)
