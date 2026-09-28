"""EP06 v4 지도·그래픽 씬을 코드로 그린다 — 실제 국경(Natural Earth) + 정사도법(지구본) 카메라 + cv2 안티앨리어싱.

사용:  python scripts/ep06_maps.py [--only n01,n04] [--still]   (--still: 대표 프레임 png 만)
입력: episodes/coldwar/script.json 의 map 씬, audio/<id>.wav 길이(클립 길이를 세그먼트 길이에 정확히 맞춘다 → 속도 보정 없음)
출력: clip/<id>.mp4 (1080x1920, 30fps), img/<id>.png (대표 프레임)
안전 구역(1080x1920): 상단 카드 285~570, 자막 1132~1380 → 지도 초점은 y≈850, 숫자·범례는 1420~1800.
"""
import argparse
import json
import math
import random
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
from matplotlib.path import Path as MPath
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "episodes" / "coldwar"
GEO = ROOT / "assets" / "geo"
FONT = str(ROOT / "assets" / "fonts" / "Montserrat-Bold.ttf")
W, H, FPS = 1080, 1920, 30
SCENE_PAD, XFADE = 0.18, 0.3
CY = 860  # 지도 초점 y

SPACE = np.array((5, 7, 11), np.float32)
OCEAN = np.array((11, 20, 31), np.float32)
LAND = (40, 48, 58)
BORDER = (78, 92, 106)
GRAT = (20, 33, 47)
BLUE = (52, 128, 222)
RED = (206, 44, 44)
WHITE = (242, 242, 242)
MUTED = (160, 170, 182)
HOT = (255, 170, 80)
GREEN = (90, 230, 150)

NATO = "USA CAN GBR FRA DEU ITA ESP PRT NLD BEL LUX DNK NOR ISL GRC TUR POL CZE HUN SVK SVN EST LVA LTU ROU BGR HRV ALB MNE MKD FIN SWE".split()
USSR = "RUS UKR BLR MDA EST LVA LTU GEO ARM AZE KAZ UZB TKM KGZ TJK".split()


# ---------------- 데이터 ----------------
def _rings(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [np.array(p[0], np.float64) for p in polys]


@lru_cache(None)
def countries():
    d = json.loads((GEO / "ne_50m_admin_0_countries.geojson").read_text(encoding="utf-8"))
    out = {}
    for f in d["features"]:
        a3 = f["properties"]["ADM0_A3"]
        out.setdefault(a3, []).extend(_rings(f["geometry"]))
    return out


@lru_cache(None)
def land10():
    d = json.loads((GEO / "ne_10m_land.geojson").read_text(encoding="utf-8"))
    rings = []
    for f in d["features"]:
        rings += _rings(f["geometry"])
    return rings


@lru_cache(None)
def places():
    d = json.loads((GEO / "ne_10m_populated_places_simple.geojson").read_text(encoding="utf-8"))
    return [f["properties"] for f in d["features"]]


def top_cities(codes, n):
    ps = [p for p in places() if p.get("adm0_a3") in codes]
    ps.sort(key=lambda p: -(p.get("pop_max") or 0))
    seen, out = set(), []
    for p in ps:
        if p["name"] in seen:
            continue
        seen.add(p["name"])
        out.append((p["longitude"], p["latitude"], p["name"]))
        if len(out) == n:
            break
    return out


def capitals():
    return {p["adm0_a3"]: (p["longitude"], p["latitude"], p["name"]) for p in places() if p.get("featurecla") == "Admin-0 capital"}


def sample_in(codes, n, box, weight=None, seed=1):
    """국가들 안(box=(lon0,lon1,lat0,lat1))에서 무작위 점 n 개."""
    rng = random.Random(seed)
    paths = [MPath(r) for c in codes for r in countries().get(c, []) if len(r) > 3]
    pts = []
    while len(pts) < n:
        lon, lat = rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3])
        if weight and rng.random() > weight(lon, lat):
            continue
        if any(p.contains_point((lon, lat)) for p in paths):
            pts.append((lon, lat))
    return pts


# ---------------- 카메라(정사도법) ----------------
class Cam:
    def __init__(self, lon0, lat0, R, cx=W / 2, cy=CY):
        self.lon0, self.lat0, self.R, self.cx, self.cy = lon0, lat0, R, cx, cy
        self.l0, self.p0 = math.radians(lon0), math.radians(lat0)

    def xyz(self, lon, lat):
        lam = np.radians(np.asarray(lon, np.float64)) - self.l0
        phi = np.radians(np.asarray(lat, np.float64))
        x = np.cos(phi) * np.sin(lam)
        y = math.cos(self.p0) * np.sin(phi) - math.sin(self.p0) * np.cos(phi) * np.cos(lam)
        z = math.sin(self.p0) * np.sin(phi) + math.cos(self.p0) * np.cos(phi) * np.cos(lam)
        return x, y, z

    def proj(self, lon, lat, alt=0.0, clamp=True):
        x, y, z = self.xyz(lon, lat)
        k = self.R * (1 + np.asarray(alt))
        if clamp:  # 뒷면 점은 테두리(림)로 붙인다
            r = np.hypot(x, y) + 1e-12
            hid = z < 0
            x = np.where(hid, x / r, x)
            y = np.where(hid, y / r, y)
        return np.stack([self.cx + k * x, self.cy - k * y], -1), z

    def pt(self, lon, lat, alt=0.0):
        p, z = self.proj([lon], [lat], alt)
        return float(p[0, 0]), float(p[0, 1])

    def px_per_km(self):
        return self.R / 6371.0


def lerp(a, b, u):
    return a + (b - a) * u


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def cam_lerp(a, b, u):
    u = ease(u)
    # 줌은 로그 보간(일정한 체감 속도)
    R = math.exp(lerp(math.log(a.R), math.log(b.R), u))
    return Cam(lerp(a.lon0, b.lon0, u), lerp(a.lat0, b.lat0, u), R, lerp(a.cx, b.cx, u), lerp(a.cy, b.cy, u))


# ---------------- 그리기 ----------------
SH = 3  # cv2 서브픽셀 시프트
SC = 1 << SH


def _ipts(p):
    return np.round(p * SC).astype(np.int32)


def poly_visible(cam, ring):
    p, z = cam.proj(ring[:, 0], ring[:, 1])
    if (z < 0).all():
        return None
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    if x1 < -50 or y1 < -50 or x0 > W + 50 or y0 > H + 50:
        return None
    return p


def base_map(cam, fills=None, land_rings=None, grat=True, borders=True):
    """바다/지구본 + 육지 + 국가 채색 + 국경 + 경위선. fills: {ADM0_A3: (rgb, alpha)}"""
    img = np.empty((H, W, 3), np.float32)
    img[:] = SPACE
    # 지구본 원(림) — 화면보다 크면 전체가 바다
    disk = np.zeros((H, W), np.uint8)
    cv2.circle(disk, (int(cam.cx * SC), int(cam.cy * SC)), int(cam.R * SC), 255, -1, cv2.LINE_AA, SH)
    grad = np.linspace(1.08, 0.8, H, dtype=np.float32)[:, None, None]
    ocean = OCEAN[None, None, :] * grad
    a = (disk.astype(np.float32) / 255)[..., None]
    img = img * (1 - a) + ocean * a
    # 대기 글로우
    if cam.R < 3000:
        glow = np.zeros((H, W), np.float32)
        cv2.circle(glow, (int(cam.cx), int(cam.cy)), int(cam.R), 1.0, 6, cv2.LINE_AA)
        glow = cv2.GaussianBlur(glow, (0, 0), 14)
        img += glow[..., None] * np.array((40, 80, 140), np.float32) * 1.6
    out = np.clip(img, 0, 255).astype(np.uint8)
    if grat:
        for lon in range(-180, 180, 10):
            lat = np.linspace(-80, 80, 161)
            p, z = cam.proj(np.full_like(lat, lon), lat, clamp=False)
            _polyline_vis(out, p, z, GRAT, 1)
        for lat in range(-80, 90, 10):
            lon = np.linspace(-180, 180, 361)
            p, z = cam.proj(lon, np.full_like(lon, lat), clamp=False)
            _polyline_vis(out, p, z, GRAT, 1)
    polys = []
    rings = land_rings if land_rings is not None else [r for rs in countries().values() for r in rs]
    for r in rings:
        p = poly_visible(cam, r)
        if p is not None:
            polys.append(_ipts(p))
    cv2.fillPoly(out, polys, LAND, cv2.LINE_AA, SH)
    if fills:
        for code, (col, alpha) in fills.items():
            layer = out.copy()
            ps = [_ipts(p) for r in countries().get(code, []) if (p := poly_visible(cam, r)) is not None]
            if ps:
                cv2.fillPoly(layer, ps, col, cv2.LINE_AA, SH)
                out = cv2.addWeighted(layer, alpha, out, 1 - alpha, 0)
    if borders:
        ps = []
        for rs in countries().values():
            for r in rs:
                p = poly_visible(cam, r)
                if p is not None:
                    ps.append(_ipts(p))
        cv2.polylines(out, ps, True, BORDER, 1, cv2.LINE_AA, SH)
    return out


def _polyline_vis(img, p, z, col, th):
    seg = []
    for i in range(len(p)):
        if z[i] > 0 and -200 < p[i, 0] < W + 200 and -200 < p[i, 1] < H + 200:
            seg.append(p[i])
        elif seg:
            if len(seg) > 1:
                cv2.polylines(img, [_ipts(np.array(seg))], False, col, th, cv2.LINE_AA, SH)
            seg = []
    if len(seg) > 1:
        cv2.polylines(img, [_ipts(np.array(seg))], False, col, th, cv2.LINE_AA, SH)


def outline(img, cam, codes, col, th=2):
    ps = [_ipts(p) for c in codes for r in countries().get(c, []) if (p := poly_visible(cam, r)) is not None]
    cv2.polylines(img, ps, True, col, th, cv2.LINE_AA, SH)


def fill_codes(img, cam, codes, col, alpha):
    layer = img.copy()
    ps = [_ipts(p) for c in codes for r in countries().get(c, []) if (p := poly_visible(cam, r)) is not None]
    if ps:
        cv2.fillPoly(layer, ps, col, cv2.LINE_AA, SH)
    return cv2.addWeighted(layer, alpha, img, 1 - alpha, 0)


def add_glow(img, pts, col, radius, strength=1.0, core=None):
    """pts [(x,y,intensity)] 에 가산 글로우. radius: 흐림 시그마(px)."""
    if not pts:
        return img
    g = np.zeros((H, W), np.float32)
    for x, y, k in pts:
        if -100 < x < W + 100 and -100 < y < H + 100:
            cv2.circle(g, (int(x), int(y)), max(2, int(radius * 0.6)), float(k), -1, cv2.LINE_AA)
    g = cv2.GaussianBlur(g, (0, 0), radius)
    f = img.astype(np.float32) + g[..., None] * np.array(col, np.float32) * strength
    if core:
        for x, y, k in pts:
            if k > 0.05:
                cv2.circle(f, (int(x), int(y)), core, tuple(float(c) * min(k, 1) + 255 * (1 - min(k, 1)) * 0 for c in (255, 245, 230)), -1, cv2.LINE_AA)
    return np.clip(f, 0, 255).astype(np.uint8)


def ring(img, x, y, r, col, th=2, alpha=1.0):
    if alpha <= 0.01 or r < 1:
        return img
    layer = img.copy()
    cv2.circle(layer, (int(x * SC), int(y * SC)), int(r * SC), col, th, cv2.LINE_AA, SH)
    return cv2.addWeighted(layer, alpha, img, 1 - alpha, 0)


def disc(img, x, y, r, col, alpha=1.0):
    if alpha <= 0.01 or r < 0.5:
        return img
    layer = img.copy()
    cv2.circle(layer, (int(x * SC), int(y * SC)), int(r * SC), col, -1, cv2.LINE_AA, SH)
    return cv2.addWeighted(layer, alpha, img, 1 - alpha, 0)


def gc_path(a, b, n=90):
    """대권 경로 (lon,lat) 배열."""
    def v(lon, lat):
        lo, la = math.radians(lon), math.radians(lat)
        return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])
    p, q = v(*a), v(*b)
    om = math.acos(min(1, max(-1, float(p @ q))))
    t = np.linspace(0, 1, n)
    if om < 1e-6:
        pts = np.outer(np.ones(n), p)
    else:
        pts = (np.sin((1 - t) * om)[:, None] * p + np.sin(t * om)[:, None] * q) / math.sin(om)
    lon = np.degrees(np.arctan2(pts[:, 1], pts[:, 0]))
    lat = np.degrees(np.arcsin(np.clip(pts[:, 2], -1, 1)))
    return lon, lat, om * 6371


def arc(img, cam, a, b, u, col, peak=0.08, th=3, head=True, alpha=0.9, glow=None):
    """a→b 탄도 호. u: 0~1 진행. glow: 헤드 글로우 목록에 추가할 list."""
    if u <= 0:
        return img
    lon, lat, km = gc_path(a, b)
    t = np.linspace(0, 1, len(lon))
    alt = peak * min(1.0, km / 6000) * np.sin(np.pi * t)
    p, z = cam.proj(lon, lat, alt)
    k = max(2, int(len(p) * min(u, 1)))
    layer = img.copy()
    cv2.polylines(layer, [_ipts(p[:k])], False, col, th, cv2.LINE_AA, SH)
    img = cv2.addWeighted(layer, alpha, img, 1 - alpha, 0)
    if head and u < 1 and glow is not None:
        glow.append((p[k - 1, 0], p[k - 1, 1], 1.0))
    return img


def dashed(img, p0, p1, col, th=2, dash=14, gap=10, alpha=1.0, upto=1.0):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0) * upto
    if L < 1:
        return img
    ux, uy = (x1 - x0) / (L / upto), (y1 - y0) / (L / upto)
    layer = img.copy()
    s = 0.0
    while s < L:
        e = min(s + dash, L)
        cv2.line(layer, (int((x0 + ux * s) * SC), int((y0 + uy * s) * SC)), (int((x0 + ux * e) * SC), int((y0 + uy * e) * SC)), col, th, cv2.LINE_AA, SH)
        s = e + gap
    return cv2.addWeighted(layer, alpha, img, 1 - alpha, 0)


# ---------------- 글자 ----------------
@lru_cache(512)
def text_patch(text, size, color=WHITE, stroke=0, stroke_col=(0, 0, 0), box=None, pad=(18, 10)):
    f = ImageFont.truetype(FONT, size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    w, h = r - l, b - t
    px, py = pad if box else (stroke + 2, stroke + 2)
    im = Image.new("RGBA", (w + 2 * px, h + 2 * py), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if box:
        d.rectangle([0, 0, im.width - 1, im.height - 1], fill=box + (255,))
    d.text((px - l, py - t), text, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=stroke_col + (255,))
    return np.array(im)


def blit(img, patch, x, y, anchor="mm", alpha=1.0):
    if alpha <= 0.01:
        return img
    h, w = patch.shape[:2]
    ox = {"l": 0, "m": w // 2, "r": w}[anchor[0]]
    oy = {"t": 0, "m": h // 2, "b": h}[anchor[1]]
    x0, y0 = int(x) - ox, int(y) - oy
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return img
    sub = patch[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = sub[..., 3:4] / 255 * alpha
    reg = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = (reg * (1 - a) + sub[..., :3] * a).astype(np.uint8)
    return img


def label(img, text, x, y, size=34, color=WHITE, alpha=1.0, anchor="mm"):
    return blit(img, text_patch(text, size, color, 3, (0, 0, 0)), x, y, anchor, alpha)


def tag(img, text, x, y, sub=None, alpha=1.0, anchor="mm", size=40, col=RED):
    """채널 공통 빨간 태그 (fx_overlay 와 같은 룩)."""
    p = text_patch(text, size, WHITE, 0, (0, 0, 0), col, (20, 12))
    img = blit(img, p, x, y, anchor, alpha)
    if sub:
        h = p.shape[0]
        dy = {"t": h, "m": h // 2, "b": 0}[anchor[1]]
        sp = text_patch(sub, int(size * 0.62), WHITE, 0, (0, 0, 0), (18, 18, 22), (16, 8))
        img = blit(img, sp, x if anchor[0] == "m" else x, y + dy + 4, anchor[0] + "t", alpha)
    return img


def fade(t, t0, d=0.35):
    return ease((t - t0) / d) if t >= t0 else 0.0


def big_number(img, value, x, y, size=120, color=WHITE, alpha=1.0):
    return blit(img, text_patch(value, size, color, 5, (0, 0, 0)), x, y, "mm", alpha)


def fmt_int(v):
    return f"{int(round(v)):,}"


def clock_txt(sec):
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


# ---------------- 고정 좌표 ----------------
KALININGRAD = (20.5, 54.7)
MOSCOW = (37.62, 55.75)
ANDOYA = (16.02, 69.29)
OLENEGORSK = (33.91, 68.15)
SVALBARD = (15.6, 78.2)
SPLASH = (14.0, 76.0)       # "스피츠베르겐 인근" — 정확한 지점 미상, 넓은 원으로 표시
BARENTS_SUB = (27.0, 72.8)
NYC = (-73.98, 40.75)
US_ICBM = [(-111.2, 47.5), (-101.3, 48.4), (-104.8, 41.1)]            # Malmstrom, Minot, F.E. Warren
US_SSBN = [(-35.0, 57.0), (-25.0, 63.0), (-160.0, 45.0), (-150.0, 52.0)]  # 북대서양·북태평양 초계 해역(개략)
RU_FIELDS = [(35.8, 54.0), (45.6, 51.7), (59.8, 51.0), (89.8, 55.3), (59.5, 50.8), (40.5, 56.9), (47.9, 56.6),
             (83.0, 55.3), (104.3, 52.3), (83.7, 53.3), (33.7, 57.9), (60.3, 58.2), (33.3, 69.25), (158.4, 52.9)]
US_TARGETS = US_ICBM + [(-81.5, 30.8), (-122.7, 47.7), (-93.5, 38.7), (-93.7, 32.5), (-104.5, 38.8), (-97.0, 38.0)]
RADARS = [(33.91, 68.15, "OLENEGORSK"), (57.3, 65.2, "PECHORA"), (37.8, 56.2, "MOSCOW")]


def polar(R=560, lon0=-100.0, lat0=80.0, cy=CY - 40):
    return Cam(lon0, lat0, R, cy=cy)


EUROPE = Cam(22.0, 53.0, 1900)
NORTH = Cam(24.0, 71.0, 3600)


# ---------------- 씬 ----------------
class Ctx:
    """씬 공통: 오디오 기준 단어 시각 w("단어") → 클립 시각."""
    def __init__(self, sc, audio_dur, offset):
        self.sc, self.A, self.off = sc, audio_dur, offset
        self.text = sc["narration_text"]

    def w(self, needle, frac=0.0):
        i = self.text.find(needle)
        i = 0 if i < 0 else i
        return self.off + 0.05 + (i + frac * len(needle)) / len(self.text) * (self.A - 0.15)


def s_polar_intro(t, c, cache):
    cam = cam_lerp(polar(500, -112, 72), polar(600, -98, 80), t / c.L)
    img = base_map(cam, {"USA": (BLUE, 0.55), "RUS": (RED, 0.6)})
    a = fade(t, 0.6)
    img = label(img, "USA", *cam.pt(-100, 47), 44, WHITE, a)
    img = label(img, "RUSSIA", *cam.pt(95, 62), 44, WHITE, a)
    p = cam.pt(-100, 70)
    img = dashed(img, cam.pt(-100, 40), cam.pt(80, 58), MUTED, 2, alpha=0.6 * fade(t, 1.4, 1.0), upto=fade(t, 1.4, 1.6))
    tp = c.w("Princeton")
    img = tag(img, "PRINCETON SGS · \"PLAN A\"", W / 2, 1560, "simulation built from real war plans", fade(t, tp))
    return img


def s_europe_advance(t, c, cache):
    if "base" not in cache:
        img = base_map(EUROPE, {**{k: (BLUE, 0.42) for k in NATO}, "RUS": (RED, 0.55), "BLR": (RED, 0.45)})
        cache["base"] = img
    img = cache["base"].copy()
    a = fade(t, 0.3)
    img = label(img, "NATO", *EUROPE.pt(10, 50.5), 46, WHITE, a)
    img = label(img, "RUSSIA", *EUROPE.pt(38, 56.5), 46, WHITE, a)
    img = label(img, "BELARUS", *EUROPE.pt(28, 53.4), 26, MUTED, a)
    img = label(img, "KALININGRAD", *EUROPE.pt(20.8, 55.35), 24, MUTED, a)
    u = ease((t - c.w("advancing")) / 1.6)
    for lat in (57.5, 53.2, 49.5):
        x0, y0 = EUROPE.pt(15.5 if lat < 56 else 21.0, lat)
        x1, y1 = EUROPE.pt((21.0 if lat < 56 else 25.5) + 3.2 * u, lat)
        if u > 0:
            cv2.arrowedLine(img, (int(x0 * SC), int(y0 * SC)), (int(x1 * SC), int(y1 * SC)), BLUE, 10, cv2.LINE_AA, SH, 0.28)
    img = tag(img, "CONVENTIONAL WAR", W / 2, 1560, "no nuclear weapons used yet", fade(t, 0.8))
    return img


def s_kaliningrad_shot(t, c, cache):
    Z = Cam(20.0, 55.0, 5200)
    cam = cam_lerp(EUROPE, Z, t / 1.8)
    img = base_map(cam, {**{k: (BLUE, 0.42) for k in NATO}, "RUS": (RED, 0.55), "BLR": (RED, 0.45)}, grat=False)
    img = label(img, "KALININGRAD", *cam.pt(21.3, 54.6), 30, WHITE, fade(t, 1.2))
    img = label(img, "POLAND", *cam.pt(18.5, 53.4), 26, MUTED, fade(t, 1.2))
    img = label(img, "LITHUANIA", *cam.pt(23.9, 55.35), 26, MUTED, fade(t, 1.2))
    glow = []
    t1 = c.w("warning shot") - 0.6
    tgt = (18.6, 56.0)
    img = arc(img, cam, KALININGRAD, tgt, (t - t1) / 0.7, RED, 0.02, 4, glow=glow)
    if t > t1 + 0.7:
        x, y = cam.pt(*tgt)
        k = max(0, 1 - (t - t1 - 0.7) / 2.2)
        glow.append((x, y, 2.5 * k))
        img = ring(img, x, y, 20 + 160 * ease((t - t1 - 0.7) / 1.4), HOT, 3, 1 - ease((t - t1 - 0.7) / 1.4))
        img = tag(img, "RUSSIA: WARNING SHOT", x, y - 110, alpha=fade(t, t1 + 0.8))
    t2 = c.w("NATO answers") - 0.2
    src = (14.4, 53.0)
    base = (20.9, 54.95)
    img = arc(img, cam, src, base, (t - t2) / 0.8, BLUE, 0.02, 4, glow=glow)
    if t > t2 + 0.8:
        x, y = cam.pt(*base)
        k = max(0, 1 - (t - t2 - 0.8) / 2.2)
        glow.append((x, y, 2.5 * k))
        img = ring(img, x, y, 20 + 150 * ease((t - t2 - 0.8) / 1.4), HOT, 3, 1 - ease((t - t2 - 0.8) / 1.4))
        img = tag(img, "NATO: ONE STRIKE", x, y + 120, alpha=fade(t, t2 + 0.9))
    img = add_glow(img, glow, HOT, 18, 1.4)
    return img


def _dots(cache):
    if "red" not in cache:
        cache["red"] = sample_in(NATO, 300, (4, 29, 44, 59), lambda lo, la: 0.15 + 0.85 * min(1, (lo - 4) / 20), 3)
        cache["blue"] = sample_in(["RUS", "BLR"], 180, (23, 46, 49, 60), lambda lo, la: 1.0 - 0.8 * min(1, (lo - 23) / 23), 4)
        rng = random.Random(9)
        cache["rt"] = sorted(rng.random() for _ in range(300))
        cache["bt"] = sorted(rng.random() for _ in range(180))
    return cache


def s_tactical_dots(t, c, cache):
    if "base" not in cache:
        cache["base"] = base_map(EUROPE, {**{k: (BLUE, 0.42) for k in NATO}, "RUS": (RED, 0.55), "BLR": (RED, 0.45)})
    _dots(cache)
    img = cache["base"].copy()
    tr, tb = c.w("three hundred"), c.w("one hundred eighty") - 0.3
    glow_r, glow_b, nr, nb = [], [], 0, 0
    for (lon, lat), q in zip(cache["red"], cache["rt"]):
        ts = tr + q * 2.4
        if t >= ts:
            nr += 1
            x, y = EUROPE.pt(lon, lat)
            k = max(0.35, 1.6 * math.exp(-(t - ts) * 2.5))
            glow_r.append((x, y, k))
    for (lon, lat), q in zip(cache["blue"], cache["bt"]):
        ts = tb + q * 2.0
        if t >= ts:
            nb += 1
            x, y = EUROPE.pt(lon, lat)
            glow_b.append((x, y, max(0.35, 1.6 * math.exp(-(t - ts) * 2.5))))
    img = add_glow(img, glow_r, (255, 120, 60), 6, 1.2)
    img = add_glow(img, glow_b, (255, 200, 120), 6, 1.2)
    for x, y, k in glow_r + glow_b:
        cv2.circle(img, (int(x * SC), int(y * SC)), 3 * SC, (255, 235, 210), -1, cv2.LINE_AA, SH)
    img = big_number(img, str(nr), 330, 1540, 130, RED, fade(t, tr))
    img = label(img, "RUSSIAN WARHEADS", 330, 1640, 30, WHITE, fade(t, tr))
    img = big_number(img, str(nb), 760, 1540, 130, BLUE, fade(t, tb))
    img = label(img, "NATO WARHEADS", 760, 1640, 30, WHITE, fade(t, tb))
    return img


def s_europe_casualties(t, c, cache):
    if "base" not in cache:
        cache["base"] = base_map(EUROPE, {**{k: (BLUE, 0.42) for k in NATO}, "RUS": (RED, 0.55), "BLR": (RED, 0.45)})
    _dots(cache)
    img = cache["base"].copy()
    u = ease(t / (c.L * 0.8))
    pts = [(*EUROPE.pt(lo, la), 0.5 + 0.6 * u) for lo, la in cache["red"] + cache["blue"]]
    img = add_glow(img, pts, (255, 90, 40), 10 + 26 * u, 0.9)
    v = 2_600_000 * ease((t - 0.3) / (c.w("million") - 0.3 + 0.2))
    img = big_number(img, fmt_int(v), W / 2, 1520, 120, WHITE, fade(t, 0.2))
    img = label(img, "DEAD OR WOUNDED", W / 2, 1620, 34, MUTED, fade(t, 0.2))
    img = tag(img, "+3 HOURS", W / 2, 1730, alpha=fade(t, 0.4))
    return img


def _polar_base(cache, R=580, lon0=-100):
    if "base" not in cache:
        cam = polar(R, lon0, 78)
        cache["cam"] = cam
        cache["base"] = base_map(cam, {"USA": (BLUE, 0.5), "RUS": (RED, 0.55)})
    return cache["cam"], cache["base"].copy()


def _blue_routes():
    rng = random.Random(5)
    routes = []
    for i in range(60):
        src = US_ICBM[i % 3] if i % 2 == 0 else US_SSBN[i % 4]
        dst = RU_FIELDS[rng.randrange(len(RU_FIELDS))]
        routes.append((src, (dst[0] + rng.uniform(-1.5, 1.5), dst[1] + rng.uniform(-1, 1)), rng.random()))
    return routes


def _red_routes():
    rng = random.Random(6)
    return [(RU_FIELDS[i % 12], (lambda d: (d[0] + rng.uniform(-1.5, 1.5), d[1] + rng.uniform(-1, 1)))(US_TARGETS[rng.randrange(len(US_TARGETS))]), rng.random())
            for i in range(60)]


def s_polar_blue_arcs(t, c, cache):
    cam, img = _polar_base(cache)
    t0 = c.w("launches") - 0.3
    glow = []
    n = 0
    for src, dst, q in _blue_routes():
        u = (t - t0 - q * 2.5) / 4.0
        if u > 0:
            n += 1
        img = arc(img, cam, src, dst, u * 0.55, BLUE, 0.1, 2, glow=glow, alpha=0.8)
    img = add_glow(img, glow, (140, 190, 255), 5, 1.4)
    img = label(img, "USA", *cam.pt(-100, 47), 40, WHITE)
    img = label(img, "RUSSIA", *cam.pt(95, 62), 40, WHITE)
    img = big_number(img, fmt_int(600 * min(1, n / 60)), W / 2, 1540, 130, BLUE, fade(t, t0))
    img = label(img, "US WARHEADS → RUSSIAN MISSILE SITES", W / 2, 1640, 30, WHITE, fade(t, t0))
    img = tag(img, "SILOS + SUBMARINES", W / 2, 1735, alpha=fade(t, c.w("silos")))
    return img


def s_polar_red_arcs(t, c, cache):
    cam, img = _polar_base(cache)
    glow = []
    for src, dst, q in _blue_routes():
        img = arc(img, cam, src, dst, 0.55 + 0.3 * (t / c.L) - q * 0.1, BLUE, 0.1, 2, glow=glow, alpha=0.7)
    t0 = c.w("fires back") - 0.2
    for src, dst, q in _red_routes():
        img = arc(img, cam, src, dst, (t - t0 - q * 1.6) / 4.5 * 0.7, RED, 0.1, 2, glow=glow, alpha=0.85)
    img = add_glow(img, glow, (255, 200, 150), 5, 1.4)
    img = label(img, "USA", *cam.pt(-100, 47), 40, WHITE)
    img = label(img, "RUSSIA", *cam.pt(95, 62), 40, WHITE)
    img = label(img, "ARCTIC", *cam.pt(0, 88), 26, MUTED, fade(t, c.w("Arctic")))
    tc = c.w("thirty minutes") - 0.6
    sec = 30 * 60 * ease((t - tc) / 1.4) if t > tc else 0
    img = big_number(img, clock_txt(sec), W / 2, 1540, 140, WHITE, fade(t, tc - 0.3))
    img = label(img, "FLIGHT TIME ACROSS THE POLE", W / 2, 1645, 30, MUTED, fade(t, tc - 0.3))
    img = tag(img, "LAUNCH ON WARNING", W / 2, 1735, alpha=fade(t, c.w("fires back")))
    return img


def s_polar_bursts(t, c, cache):
    cam, img = _polar_base(cache)
    rng = random.Random(8)
    glow = []
    tgts = RU_FIELDS + US_TARGETS
    for i, (lo, la) in enumerate(tgts):
        ts = 0.2 + (i / len(tgts)) * 2.2 + rng.random() * 0.3
        if t > ts:
            x, y = cam.pt(lo, la)
            glow.append((x, y, 0.5 + 1.8 * math.exp(-(t - ts) * 2)))
            img = ring(img, x, y, 6 + 40 * ease((t - ts) / 1.2), HOT, 2, 1 - ease((t - ts) / 1.2))
    img = add_glow(img, glow, (255, 120, 50), 9, 1.2)
    img = label(img, "USA", *cam.pt(-100, 47), 40, WHITE)
    img = label(img, "RUSSIA", *cam.pt(95, 62), 40, WHITE)
    v = 3_400_000 * ease((t - 0.2) / max(1.0, c.w("million") - 0.2))
    img = big_number(img, "+" + fmt_int(v), W / 2, 1520, 120, WHITE, fade(t, 0.1))
    img = label(img, "MORE CASUALTIES", W / 2, 1620, 34, MUTED, fade(t, 0.1))
    img = tag(img, "+45 MINUTES", W / 2, 1730, alpha=fade(t, 0.3))
    return img


def s_zoom_city(t, c, cache):
    cam0 = polar(580, -100, 78)
    cam1 = Cam(NYC[0], NYC[1], 70000)
    tz = c.w("To see") - 0.2
    u = (t - tz) / 2.2
    cam = cam_lerp(cam0, cam1, u) if u > 0 else cam0
    img = base_map(cam, {"USA": (BLUE, 0.5 * (1 - ease(u))), "RUS": (RED, 0.55)}, land_rings=land10() if cam.R > 20000 else None,
                   grat=cam.R < 8000, borders=cam.R < 20000)
    cities = top_cities(["USA"], 30) + top_cities(["RUS"], 30)
    glow = []
    for i, (lo, la, _) in enumerate(cities):
        ts = 0.3 + i * 0.03
        if t > ts:
            x, y = cam.pt(lo, la)
            glow.append((x, y, 0.8 * (1 - ease(u))))
    img = add_glow(img, glow, (255, 170, 90), 5, 1.3)
    if u > 0.3:
        x, y = cam.pt(*NYC)
        a = fade(u, 0.3, 0.4)
        r = lerp(200, 90, ease(u))
        img = ring(img, x, y, r, RED, 3, a)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cv2.line(img, (int((x + dx * r * 0.6) * SC), int((y + dy * r * 0.6) * SC)), (int((x + dx * r * 1.4) * SC), int((y + dy * r * 1.4) * SC)), RED, 3, cv2.LINE_AA, SH)
        img = tag(img, "ONE WARHEAD", x, 1540, "one city", a)
    else:
        img = tag(img, "NEXT TARGETS: CITIES", W / 2, 1560, alpha=fade(t, 0.3))
    return img


def s_nyc_rings(t, c, cache):
    cam = Cam(NYC[0], NYC[1], 6371 * 1080 / 42)  # 화면 너비 ≈ 42 km
    if "base" not in cache:
        cache["base"] = base_map(cam, None, land_rings=land10(), grat=False, borders=False)
    img = cache["base"].copy()
    x, y = cam.pt(*NYC)
    k = cam.px_per_km()
    rings = [(0.75, "1.5 KM FIREBALL", (255, 235, 180), 0.0), (5.4, "5 KM · BUILDINGS COLLAPSE", (255, 140, 40), 0.0),
             (9.0, "9 KM · 3RD-DEGREE BURNS", (230, 70, 40), c.w("Nine") - 0.1), (15.0, "15 KM · WINDOWS SHATTER", (200, 170, 170), c.w("fifteen") - 0.1)]
    for rkm, txt, col, t0 in reversed(rings):
        a = fade(t, t0, 0.5)
        img = disc(img, x, y, rkm * k * ease((t - t0) / 0.6 + 0.001), col, 0.16 * a)
        img = ring(img, x, y, rkm * k * ease((t - t0) / 0.6 + 0.001), col, 3, a)
    ly = 1440
    for rkm, txt, col, t0 in rings:
        a = fade(t, t0, 0.5)
        cv2.circle(img, (70, ly), 13, col, -1, cv2.LINE_AA)
        img = label(img, txt, 100, ly, 32, WHITE, a, "lm")
        ly += 62
    img = label(img, "MANHATTAN", x + 10, y - 30, 24, MUTED, 1.0)
    img = label(img, "NEW YORK · FOR SCALE", 60, 620, 28, MUTED, 1.0, "lm")
    img = label(img, "NUKEMAP · W88 455 KT AIRBURST", W / 2, 1860, 22, MUTED)
    return img


def _city_sets():
    nato = top_cities(NATO, 30)
    rus = top_cities(["RUS"], 30)
    return nato, rus


def s_cities_30(t, c, cache):
    cam, img = _polar_base(cache, 600, -40)
    nato, rus = _city_sets()
    t0 = c.w("Each side")
    glow = []
    for i, (lo, la, nm) in enumerate(nato):
        ts = t0 + i * 0.07
        if t > ts:
            x, y = cam.pt(lo, la)
            glow.append((x, y, 0.6 + 1.4 * math.exp(-(t - ts) * 3)))
    for i, (lo, la, nm) in enumerate(rus):
        ts = t0 + 0.2 + i * 0.07
        if t > ts:
            x, y = cam.pt(lo, la)
            glow.append((x, y, 0.6 + 1.4 * math.exp(-(t - ts) * 3)))
    img = add_glow(img, glow, (255, 200, 120), 5, 1.4)
    for lo, la, nm in [x for x in nato + rus if x[2] in ("New York", "London", "Paris", "Moscow", "Chicago", "Istanbul")]:
        img = label(img, nm.upper(), *(np.array(cam.pt(lo, la)) + (0, -26)), 22, WHITE, fade(t, t0 + 1.5))
    img = big_number(img, "30 + 30", W / 2, 1530, 120, WHITE, fade(t, t0))
    img = label(img, "LARGEST CITIES · NATO + RUSSIA", W / 2, 1630, 30, MUTED, fade(t, t0))
    img = tag(img, "5–10 WARHEADS EACH", W / 2, 1730, alpha=fade(t, c.w("five to ten")))
    return img


def s_cities_burn(t, c, cache):
    cam, img = _polar_base(cache, 600, -40)
    nato, rus = _city_sets()
    u = ease(t / (c.L * 0.7))
    pts = [(*cam.pt(lo, la), 0.9 + 0.8 * u) for lo, la, _ in nato + rus]
    img = add_glow(img, pts, (255, 90, 30), 6 + 14 * u, 1.2)
    v = 85_300_000 * ease((t - 0.2) / max(1.0, c.w("million") - 0.2))
    img = big_number(img, fmt_int(v), W / 2, 1520, 116, WHITE, fade(t, 0.1))
    img = label(img, "CASUALTIES", W / 2, 1620, 34, MUTED, fade(t, 0.1))
    img = tag(img, "+45 MINUTES", W / 2, 1730, alpha=fade(t, 0.3))
    return img


def s_totals(t, c, cache):
    if "base" not in cache:
        cam = polar(600, -40, 78)
        b = base_map(cam, {"USA": (BLUE, 0.5), "RUS": (RED, 0.55)})
        cache["base"] = (b.astype(np.float32) * 0.35).astype(np.uint8)
    img = cache["base"].copy()
    x0, x1, y0, bh = 110, 970, 700, 110
    segs = [(2.6, "EUROPE", (255, 170, 80)), (3.4, "MISSILE SITES", (255, 110, 60)), (85.3, "CITIES", RED)]
    total = 91.3
    u = ease((t - 0.2) / 1.6)
    cx = x0
    for v, nm, col in segs:
        w = (x1 - x0) * v / total * u
        if w > 1:
            cv2.rectangle(img, (int(cx), y0), (int(cx + w), y0 + bh), col, -1, cv2.LINE_AA)
            cv2.rectangle(img, (int(cx + w) - 2, y0), (int(cx + w), y0 + bh), (5, 7, 11), -1)
        cx += w
    a = fade(t, 1.0)
    img = label(img, "2.6M EUROPE", x0, y0 - 40, 26, WHITE, a, "lm")
    img = label(img, "3.4M MISSILE SITES", x0 + 250, y0 - 40, 26, WHITE, a, "lm")
    img = label(img, "85.3M CITIES", x1, y0 + bh + 40, 26, WHITE, a, "rm")
    img = big_number(img, "91.5 MILLION", W / 2, 1000, 96, WHITE, fade(t, 1.2))
    img = label(img, "CASUALTIES IN UNDER 5 HOURS", W / 2, 1080, 30, MUTED, fade(t, 1.2))
    td = c.w("thirty-four")
    img = big_number(img, "34.1M", 300, 1520, 110, RED, fade(t, td))
    img = label(img, "DEAD", 300, 1615, 34, WHITE, fade(t, td))
    ti = c.w("fifty-seven")
    img = big_number(img, "57.4M", 780, 1520, 110, HOT, fade(t, ti))
    img = label(img, "INJURED", 780, 1615, 34, WHITE, fade(t, ti))
    img = tag(img, "FALLOUT NOT INCLUDED", W / 2, 1735, alpha=fade(t, c.w("fallout")))
    img = label(img, "PRINCETON SGS · PLAN A", W / 2, 1860, 22, MUTED)
    return img


def s_zoom_north(t, c, cache):
    cam = cam_lerp(polar(580, -40, 78), Cam(28, 66, 2200), (t - 0.8) / 3.0)
    img = base_map(cam, {"RUS": (RED, 0.55), "NOR": (BLUE, 0.55)})
    a = fade(t, 3.0)
    img = label(img, "NORWAY", *cam.pt(12, 64.5), 32, WHITE, a)
    img = label(img, "RUSSIA", *cam.pt(42, 64), 40, WHITE, a)
    img = big_number(img, "1995", W / 2, 1540, 150, WHITE, fade(t, c.w("1995") - 0.1))
    return img


def s_ussr_to_russia(t, c, cache):
    cam = Cam(62, 58, 1250, cy=CY + 20)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"NOR": (BLUE, 0.55)})
    img = cache["base"].copy()
    tg = c.w("gone")
    others = [k for k in USSR if k != "RUS"]
    img = fill_codes(img, cam, ["RUS"], RED, 0.6)
    img = fill_codes(img, cam, others, RED, 0.6 * (1 - fade(t, tg, 0.8)))
    img = label(img, "USSR", *cam.pt(70, 58), 60, WHITE, 1 - fade(t, tg, 0.5))
    img = label(img, "RUSSIA", *cam.pt(80, 62), 52, WHITE, fade(t, tg + 0.5))
    img = label(img, "15 COUNTRIES · 1991", *cam.pt(66, 45), 26, MUTED, fade(t, tg + 0.5))
    img = label(img, "NORWAY · NATO", *cam.pt(8, 61.5), 24, WHITE, 1.0, "lm")
    tm = c.w("thousands")
    glow = []
    for i, (lo, la) in enumerate(RU_FIELDS):
        if t > tm + i * 0.08:
            glow.append((*cam.pt(lo, la), 0.8 + 0.5 * math.sin(6 * (t - tm))))
    img = add_glow(img, glow, (255, 150, 90), 6, 1.4)
    img = tag(img, "MISSILES STILL ON ALERT", W / 2, 1560, alpha=fade(t, tm))
    return img


def s_barents_trident(t, c, cache):
    cam = Cam(33, 64, 3000, cy=CY)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"RUS": (RED, 0.5), "NOR": (BLUE, 0.5), "FIN": (BLUE, 0.3), "SWE": (BLUE, 0.3)})
    img = cache["base"].copy()
    img = label(img, "BARENTS SEA", *cam.pt(45, 71.5), 26, MUTED)
    img = label(img, "NORWAY", *cam.pt(14, 66), 26, WHITE)
    x, y = cam.pt(*MOSCOW)
    cv2.circle(img, (int(x), int(y)), 9, WHITE, -1, cv2.LINE_AA)
    img = label(img, "MOSCOW", x + 16, y, 30, WHITE, 1, "lm")
    sx, sy = cam.pt(*BARENTS_SUB)
    a = fade(t, c.w("submarine") - 0.3)
    cv2.ellipse(img, (int(sx), int(sy)), (22, 8), 0, 0, 360, BLUE, -1, cv2.LINE_AA)
    img = label(img, "US SUBMARINE", sx, sy - 34, 24, WHITE, a)
    tt = c.w("Trident")
    glow = []
    img = arc(img, cam, BARENTS_SUB, MOSCOW, (t - tt) / 1.6, BLUE, 0.05, 4, glow=glow)
    img = add_glow(img, glow, (140, 190, 255), 6, 1.5)
    _, _, km = gc_path(BARENTS_SUB, MOSCOW)
    img = label(img, f"≈{int(round(km, -2)):,} KM", *cam.pt(34, 64.5), 26, WHITE, fade(t, tt + 0.8))
    tm = c.w("ten minutes") - 0.3
    img = big_number(img, "~10 MIN", W / 2, 1540, 130, WHITE, fade(t, tm))
    img = label(img, "TRIDENT FLIGHT TIME TO MOSCOW", W / 2, 1640, 30, MUTED, fade(t, tm))
    return img


def s_hemp_burst(t, c, cache):
    cam = Cam(48, 62, 1900, cy=CY)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"RUS": (RED, 0.5), "NOR": (BLUE, 0.5)})
    img = cache["base"].copy()
    tb = c.w("bursting")
    bx, by = cam.pt(45, 64)
    u = ease((t - tb) / 1.8)
    if t > tb:
        img = disc(img, bx, by, 520 * u, (255, 245, 220), 0.12 * (1 - 0.5 * u))
        img = ring(img, bx, by, 520 * u, (255, 245, 220), 3, 1 - 0.4 * u)
        img = add_glow(img, [(bx, by, 2.0 * math.exp(-(t - tb)))], (255, 255, 230), 22, 1.2)
        img = tag(img, "HIGH-ALTITUDE BURST", W / 2, 1450, "the feared first move", fade(t, tb + 0.2))
    tr = c.w("radars")
    for lo, la, nm in RADARS:
        x, y = cam.pt(lo, la)
        blind = t > tr + 0.2
        col = MUTED if blind else GREEN
        cv2.ellipse(img, (int(x), int(y)), (18, 18), 0, 200, 340, col, 4, cv2.LINE_AA)
        cv2.circle(img, (int(x), int(y)), 5, col, -1, cv2.LINE_AA)
        img = label(img, nm, x, y + 34, 22, WHITE, fade(t, 0.3))
        if blind:
            a = fade(t, tr + 0.2)
            for s in (-1, 1):
                cv2.line(img, (int(x - 14), int(y - 14 * s)), (int(x + 14), int(y + 14 * s)), RED, 4, cv2.LINE_AA)
    img = tag(img, "RADARS BLINDED", W / 2, 1620, "before the main attack", fade(t, tr + 0.3))
    return img


def s_aurora_plan(t, c, cache):
    cam = Cam(17, 73, 3300, cy=CY + 40)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"NOR": (BLUE, 0.5), "RUS": (RED, 0.45)})
    img = cache["base"].copy()
    # 오로라 띠 (스발바르 상공)
    g = np.zeros((H, W), np.float32)
    for k in range(3):
        lon = np.linspace(-5, 40, 80)
        lat = 75.5 + 1.2 * k + 0.8 * np.sin(lon / 6 + t * 1.2 + k)
        p, _ = cam.proj(lon, lat)
        cv2.polylines(g, [_ipts(p)], False, 1.0 - 0.25 * k, 10, cv2.LINE_AA, SH)
    g = cv2.GaussianBlur(g, (0, 0), 16) * fade(t, 0.3, 1.0)
    img = np.clip(img.astype(np.float32) + g[..., None] * np.array((60, 255, 150), np.float32) * 0.9, 0, 255).astype(np.uint8)
    img = label(img, "SVALBARD", *cam.pt(18, 78.8), 30, WHITE)
    x, y = cam.pt(*ANDOYA)
    cv2.circle(img, (int(x), int(y)), 10, WHITE, -1, cv2.LINE_AA)
    img = tag(img, "ANDØYA ROCKET RANGE", x, y + 70, "Norway", fade(t, 0.8))
    img = label(img, "NORTHERN LIGHTS", *cam.pt(20, 74.3), 26, GREEN, fade(t, c.w("northern")))
    img = tag(img, "NORWAY + USA · SCIENCE ROCKET", W / 2, 1600, alpha=fade(t, c.w("scientists")))
    return img


def s_notify_30(t, c, cache):
    cam = Cam(22, 52, 1500, cy=CY)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"NOR": (BLUE, 0.55), "RUS": (RED, 0.45)})
    img = cache["base"].copy()
    caps = capitals()
    oslo = caps.get("NOR", (10.75, 59.91, "Oslo"))
    picks = "SWE FIN DNK ISL GBR IRL FRA DEU NLD BEL LUX CHE AUT ITA ESP PRT POL CZE SVK HUN ROU BGR GRC TUR UKR BLR EST LVA LTU USA".split()
    dests = [caps[k] for k in picks if k in caps][:29]
    ox, oy = cam.pt(oslo[0], oslo[1])
    t0 = c.w("notifies")
    n = 0
    for i, (lo, la, nm) in enumerate(dests):
        u = ease((t - t0 - i * 0.06) / 0.6)
        if u <= 0:
            continue
        if lo < -30:  # 워싱턴: 화면 밖 → 왼쪽 가장자리로
            x, y = 20, oy + 40
        else:
            x, y = cam.pt(lo, la)
        img = dashed(img, (ox, oy), (x, y), (120, 180, 255), 2, 10, 8, 0.8, u)
        if u >= 1:
            n += 1
            cv2.circle(img, (int(x), int(y)), 5, (120, 180, 255), -1, cv2.LINE_AA)
    mx, my = cam.pt(*MOSCOW)
    tm = c.w("Russia included")
    u = ease((t - tm) / 0.8)
    if u > 0:
        n_m = 1
        img = dashed(img, (ox, oy), (mx, my), (120, 180, 255), 3, 10, 8, 1.0, u)
        cv2.circle(img, (int(mx), int(my)), 7, WHITE, -1, cv2.LINE_AA)
        img = label(img, "MOSCOW", mx + 14, my, 28, WHITE, 1, "lm")
    else:
        n_m = 0
    tb = c.w("never")
    if t > tb:
        a = fade(t, tb)
        cx, cy = mx - 50, my - 18
        for s in (-1, 1):
            cv2.line(img, (int(cx - 22), int(cy - 22 * s)), (int(cx + 22), int(cy + 22 * s)), RED, 7, cv2.LINE_AA)
        img = tag(img, "NEVER REACHED THE MILITARY", W / 2, 1560, "Russian General Staff not told", a)
    img = blit(img, text_patch("OSLO", 26, WHITE, 3), ox, oy - 28, "mm")
    img = big_number(img, str(n + n_m), 150, 1760, 90, WHITE, fade(t, t0))
    img = label(img, "COUNTRIES NOTIFIED", 230, 1760, 28, MUTED, fade(t, t0), "lm")
    img = label(img, "21 DEC 1994", W - 60, 640, 28, MUTED, fade(t, 0.2), "rm")
    return img


def _rocket_track(n=60):
    """안도야 → 북쪽(스발바르 방향) 개략 궤적. 정확한 비행경로는 공개 자료로 확인 불가 → 개략."""
    lat = np.linspace(ANDOYA[1], SPLASH[1], n)
    lon = np.linspace(ANDOYA[0], SPLASH[0], n) + 1.2 * np.sin(np.linspace(0, np.pi, n))
    return lon, lat


def _radar_fan(img, cam, t, strength=1.0):
    ox, oy = cam.pt(*OLENEGORSK)
    rng_px = 1300 * cam.px_per_km()
    g = np.zeros((H, W), np.float32)
    cv2.ellipse(g, (int(ox), int(oy)), (int(rng_px), int(rng_px)), 0, 190, 330, 0.35, -1, cv2.LINE_AA)
    sweep = 190 + (t * 40) % 140
    cv2.ellipse(g, (int(ox), int(oy)), (int(rng_px), int(rng_px)), 0, sweep - 6, sweep, 1.0, -1, cv2.LINE_AA)
    g = cv2.GaussianBlur(g, (0, 0), 3) * strength
    img = np.clip(img.astype(np.float32) + g[..., None] * np.array((30, 160, 90), np.float32) * 0.7, 0, 255).astype(np.uint8)
    cv2.circle(img, (int(ox), int(oy)), 9, GREEN, -1, cv2.LINE_AA)
    return img, (ox, oy)


def s_radar_detect(t, c, cache):
    cam = Cam(25, 70.5, 5200, cy=CY + 60)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"NOR": (BLUE, 0.5), "RUS": (RED, 0.45), "FIN": (BLUE, 0.25), "SWE": (BLUE, 0.25)}, grat=True)
    img = cache["base"].copy()
    img, (ox, oy) = _radar_fan(img, cam, t, fade(t, c.w("Olenegorsk") - 0.3))
    img = label(img, "OLENEGORSK RADAR", ox, oy + 36, 26, WHITE, fade(t, c.w("Olenegorsk") - 0.3))
    ax, ay = cam.pt(*ANDOYA)
    cv2.circle(img, (int(ax), int(ay)), 8, WHITE, -1, cv2.LINE_AA)
    img = label(img, "ANDØYA", ax, ay + 32, 26, WHITE)
    img = dashed(img, (ax, ay), (ox, oy), WHITE, 2, alpha=0.8, upto=ease(t / 1.2))
    img = label(img, "≈700 KM", (ax + ox) / 2, (ay + oy) / 2 - 26, 28, WHITE, fade(t, 1.0))
    lon, lat = _rocket_track()
    k = max(2, int(len(lon) * 0.25 * ease(t / c.L)))
    p, _ = cam.proj(lon[:k], lat[:k])
    cv2.polylines(img, [_ipts(p)], False, (255, 230, 150), 3, cv2.LINE_AA, SH)
    img = add_glow(img, [(p[-1, 0], p[-1, 1], 1.2)], (255, 220, 150), 8, 1.4)
    img = tag(img, "CLIMBING FAST", p[-1, 0] + 140, p[-1, 1] - 60, alpha=fade(t, c.w("climbing")))
    return img


def s_radar_scope(t, c, cache):
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = (6, 12, 10)
    cx, cy, R = W // 2, 880, 420
    for r in (R, R * 0.75, R * 0.5, R * 0.25):
        cv2.circle(img, (cx, cy), int(r), (24, 80, 50), 2, cv2.LINE_AA)
    cv2.line(img, (cx - R, cy), (cx + R, cy), (24, 80, 50), 1, cv2.LINE_AA)
    cv2.line(img, (cx, cy - R), (cx, cy + R), (24, 80, 50), 1, cv2.LINE_AA)
    g = np.zeros((H, W), np.float32)
    ang = (t * 150) % 360
    cv2.ellipse(g, (cx, cy), (R, R), 0, ang - 30, ang, 0.5, -1, cv2.LINE_AA)
    g = cv2.GaussianBlur(g, (0, 0), 6)
    # 블립: 좌하단에서 우상단으로 상승, 단 분리
    u = ease(t / (c.L * 0.9))
    path = [(cx - 260 + 420 * s, cy + 250 - 470 * s * (1.2 - 0.4 * s)) for s in np.linspace(0, u, 30)]
    for i, (x, y) in enumerate(path):
        cv2.circle(g, (int(x), int(y)), 4, 0.3 + 0.7 * i / len(path), -1, cv2.LINE_AA)
    ts = c.w("falling stages")
    if t > ts:
        for j in range(1, 4):
            s = max(0.0, (t - ts - j * 0.35) * 0.6)
            if s > 0:
                x, y = path[-1]
                cv2.circle(g, (int(x - 40 * j * s), int(y + 60 * j * s * s + 20 * j * s)), 5, 1.0, -1, cv2.LINE_AA)
    hx, hy = path[-1]
    cv2.circle(g, (int(hx), int(hy)), 7, 1.0, -1, cv2.LINE_AA)
    g = cv2.GaussianBlur(g, (0, 0), 1.5) + cv2.GaussianBlur(g, (0, 0), 8) * 0.8
    img = np.clip(img.astype(np.float32) + g[..., None] * np.array((60, 255, 140), np.float32), 0, 255).astype(np.uint8)
    rows = [("SPEED", c.w("speed")), ("ARC", c.w("arc")), ("STAGES", c.w("falling stages"))]
    y = 1450
    for nm, t0 in rows:
        a = fade(t, t0)
        img = label(img, nm, 330, y, 40, WHITE, a, "lm")
        img = label(img, "MATCH", 750, y, 40, RED, a, "rm")
        y += 70
    img = tag(img, "LOOKS LIKE: TRIDENT", W / 2, 1720, "US submarine-launched missile", fade(t, c.w("looks like")))
    img = label(img, "OLENEGORSK · RADAR TRACK (ILLUSTRATION)", W / 2, 1860, 22, MUTED)
    return img


def s_countdown(t, c, cache):
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = (8, 6, 8)
    cx, cy, R = W // 2, 880, 330
    marks = [(0, 0)] + [(c.w(w_), m) for w_, m in (("Five", 5), ("Six", 6), ("Seven", 7), ("Eight", 8))]
    passed = 0
    for t0, m in marks:
        if t >= t0 - 0.05:
            passed = m
    for i in range(10):
        a0 = -90 + i * 36 + 2
        col = RED if i < passed else (50, 40, 44)
        cv2.ellipse(img, (cx, cy), (R, R), 0, a0, a0 + 32, col, 34, cv2.LINE_AA)
    img = big_number(img, clock_txt((10 - passed) * 60), cx, cy - 20, 170, WHITE)
    img = label(img, "LEFT TO DECIDE", cx, cy + 100, 34, MUTED)
    img = label(img, f"{passed} MIN PASSED" if passed else "10 MIN TO MOSCOW", cx, 1560, 46, RED if passed else WHITE, fade(t, 0.2))
    return img


def s_trajectory_away(t, c, cache):
    cam = Cam(22, 72.5, 3600, cy=CY + 40)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"NOR": (BLUE, 0.5), "RUS": (RED, 0.45)})
    img = cache["base"].copy()
    img, (ox, oy) = _radar_fan(img, cam, t, 0.8)
    img = label(img, "OLENEGORSK", ox, oy + 30, 22, WHITE)
    img = label(img, "SVALBARD", *cam.pt(18, 78.8), 26, WHITE)
    ax, ay = cam.pt(*ANDOYA)
    cv2.circle(img, (int(ax), int(ay)), 8, WHITE, -1, cv2.LINE_AA)
    img = label(img, "ANDØYA", ax, ay + 30, 22, WHITE)
    lon, lat = _rocket_track()
    u = 0.25 + 0.6 * ease((t - c.w("bends") + 0.3) / 2.5)
    k = max(2, int(len(lon) * u))
    p, _ = cam.proj(lon[:k], lat[:k])
    cv2.polylines(img, [_ipts(p)], False, (255, 230, 150), 3, cv2.LINE_AA, SH)
    img = add_glow(img, [(p[-1, 0], p[-1, 1], 1.2)], (255, 220, 150), 8, 1.4)
    x, y = cam.pt(*MOSCOW) if False else (ox, oy)
    img = tag(img, "AWAY FROM RUSSIA", W / 2, 1560, "out to sea", fade(t, c.w("away")))
    return img


def s_splashdown(t, c, cache):
    cam = Cam(22, 72.5, 3600, cy=CY + 40)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"NOR": (BLUE, 0.5), "RUS": (RED, 0.45)})
    img = cache["base"].copy()
    img = label(img, "SVALBARD", *cam.pt(18, 78.8), 26, WHITE)
    ax, ay = cam.pt(*ANDOYA)
    cv2.circle(img, (int(ax), int(ay)), 8, WHITE, -1, cv2.LINE_AA)
    lon, lat = _rocket_track()
    u = 0.85 + 0.15 * ease(t / 1.2)
    k = max(2, int(len(lon) * u))
    p, _ = cam.proj(lon[:k], lat[:k])
    cv2.polylines(img, [_ipts(p)], False, (255, 230, 150), 3, cv2.LINE_AA, SH)
    sx, sy = cam.pt(*SPLASH)
    ts = 1.2
    if t > ts:
        for j in range(3):
            r = 20 + 90 * ease(((t - ts) * 0.8 + j * 0.33) % 1.0)
            img = ring(img, sx, sy, r, (150, 210, 255), 2, 1 - ease(((t - ts) * 0.8 + j * 0.33) % 1.0))
        img = tag(img, "SPLASHDOWN", sx + 160, sy - 50, "near Spitsbergen", fade(t, ts))
    img = big_number(img, "T+24 MIN", W / 2, 1450, 100, WHITE, fade(t, 0.3))
    # 고도 인셋: 로켓 최고 1,453 km vs ISS ~400 km
    ta = c.w("fourteen hundred") - 0.4
    a = fade(t, ta)
    if a > 0:
        x0, x1, yb, yt = 170, 910, 1840, 1640
        pan = img.copy(); cv2.rectangle(pan, (120, 1540), (960, 1870), (6, 9, 14), -1); img = cv2.addWeighted(pan, 0.8 * a, img, 1 - 0.8 * a, 0)
        cv2.line(img, (x0, yb), (x1, yb), MUTED, 2, cv2.LINE_AA)
        hmax = 1453
        s = np.linspace(0, 1, 60) * ease((t - ta) / 1.0)
        pts = np.stack([x0 + (x1 - x0) * s, yb - (yb - yt) * np.sin(np.pi * s)], -1)
        cv2.polylines(img, [_ipts(pts)], False, (255, 230, 150), 3, cv2.LINE_AA, SH)
        yi = yb - (yb - yt) * 400 / hmax
        img = dashed(img, (x0, yi), (x1, yi), MUTED, 1, 8, 8, a)
        img = label(img, "ISS ~400 KM", x1, yi - 16, 20, MUTED, a, "rb")
        img = label(img, "1,453 KM UP", (x0 + x1) / 2, yt - 26, 28, WHITE, a)
    return img


def s_close_calls(t, c, cache):
    cam = Cam(-33, 52, 540, cy=CY - 10)
    if "base" not in cache:
        cache["base"] = base_map(cam, {"USA": (BLUE, 0.45), "RUS": (RED, 0.5)})
    img = cache["base"].copy()
    pins = [(-77.99, 35.38, "1961", "GOLDSBORO"), (-73.0, 25.0, "1962", "B-59 NEAR CUBA"), (-104.85, 38.74, "1980", "NORAD"),
            (37.6, 55.1, "1983", "SERPUKHOV-15"), (16.02, 69.29, "1995", "ANDØYA")]
    t4 = c.w("Before it")
    for i, (lo, la, yr, nm) in enumerate(pins):
        t0 = 0.3 if yr == "1995" else t4 + (i * 0.35)
        a = fade(t, t0)
        if a <= 0:
            continue
        x, y = cam.pt(lo, la)
        col = RED if yr == "1995" else HOT
        cv2.circle(img, (int(x), int(y)), 10, col, -1, cv2.LINE_AA)
        img = ring(img, x, y, 18 + 10 * math.sin(4 * t), col, 2, a)
        dy = -48 if i % 2 == 0 else 48
        img = label(img, yr, x, y + dy, 34, WHITE, a)
        img = label(img, nm, x, y + dy + (30 if dy > 0 else -30), 20, MUTED, a)
    return img


SCENES = {k[2:]: v for k, v in globals().items() if k.startswith("s_")}


# ---------------- 렌더 ----------------
def scene_len(ep_scenes, i):
    sc = ep_scenes[i]
    wav = EP / "audio" / f"{sc['id']}.wav"
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)], capture_output=True, text=True)
    A = float(p.stdout.strip())
    dur = A + SCENE_PAD
    L = dur + (XFADE / 2 if i else 0) + (XFADE / 2 if i < len(ep_scenes) - 1 else 0)
    return A, L, (XFADE / 2 if i else 0)


def render(job):
    sid, name, sc, A, L, off, still = job
    fn = SCENES[name]
    c = Ctx(sc, A, off)
    c.L = L
    cache = {}
    n = int(math.ceil(L * FPS)) + 2
    if still:
        img = fn(L * 0.8, c, cache)
        Image.fromarray(img).save(EP / "img" / f"{sid}.png")
        return f"{sid} still"
    out = EP / "clip" / f"{sid}.mp4"
    proc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(out)],
                            stdin=subprocess.PIPE)
    mid = None
    for f in range(n):
        t = f / FPS
        img = fn(t, c, cache)
        if f == int(n * 0.8):
            mid = img
        proc.stdin.write(np.ascontiguousarray(img).tobytes())
    proc.stdin.close()
    proc.wait()
    Image.fromarray(mid).save(EP / "img" / f"{sid}.png")
    return f"{sid} {name} {L:.2f}s ok"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--still", action="store_true")
    ap.add_argument("-j", type=int, default=6)
    a = ap.parse_args()
    scenes = json.loads((EP / "script.json").read_text(encoding="utf-8"))["scenes"]
    only = {x for x in a.only.split(",") if x}
    jobs = []
    for i, sc in enumerate(scenes):
        if not sc.get("map") or (only and sc["id"] not in only):
            continue
        A, L, off = scene_len(scenes, i)
        jobs.append((sc["id"], sc["map"], sc, A, L, off, a.still))
    with Pool(a.j) as p:
        for r in p.imap_unordered(render, jobs):
            print(r, flush=True)


if __name__ == "__main__":
    main()
