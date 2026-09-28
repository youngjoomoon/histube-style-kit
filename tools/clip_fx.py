"""클립 후처리 연출: 핵섬광(화면 백색) + 감쇠하는 카메라 흔들림. Veo 비용 0.

  python scripts/clip_fx.py coldwar s023 --flash 0 --shake 0:3:14
  python scripts/clip_fx.py coldwar s024 --shake 0.3:6:18 --draft

--flash T[:HOLD[:FADE]]  T초에 화면이 하얗게 → HOLD 초 유지 → FADE 초에 걸쳐 원래 밝기로 (기본 0.12, 0.9)
--shake T0:T1:PX          T0~T1 초 동안 최대 PX 픽셀 흔들림, 지수 감쇠
원본은 clip[/_draft]/_raw/<sid>.mp4 에 한 번만 보관하고, 항상 그 원본에서 다시 만든다(이중 적용 방지).
"""
import argparse, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("ep"); ap.add_argument("sid")
ap.add_argument("--flash"); ap.add_argument("--shake"); ap.add_argument("--draft", action="store_true")
a = ap.parse_args()

d = ROOT / "episodes" / a.ep / "clip" / ("_draft" if a.draft else "")
clip, raw = d / f"{a.sid}.mp4", d / "_raw" / f"{a.sid}.mp4"
if not raw.exists():
    raw.parent.mkdir(exist_ok=True); shutil.copy2(clip, raw)

W, H = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(raw)],
                      capture_output=True, text=True, check=True).stdout.strip().split(",")
vf = []
if a.shake:
    t0, t1, px = map(float, a.shake.split(":"))
    k = 3.0 / (t1 - t0)  # t1 에서 약 5% 로 감쇠
    amp = f"{px}*between(t,{t0},{t1})*exp(-{k}*(t-{t0}))"
    z = 1 + 2.2 * px / 720
    vf += [f"scale=iw*{z:.4f}:ih*{z:.4f}",
           f"crop=iw/{z:.4f}:ih/{z:.4f}:'(iw-ow)/2+{amp}*sin(t*53)':'(ih-oh)/2+{amp}*sin(t*41+1.3)'"]
if a.flash:
    p = [float(x) for x in a.flash.split(":")] + [0.12, 0.9][len(a.flash.split(":")) - 1:]
    t, hold, fade = p[0], p[1], p[2]
    b = f"if(lt(t,{t}),0,if(lt(t,{t + hold}),1,max(0,1-(t-{t + hold})/{fade})))"
    vf += [f"eq=brightness='0.9*{b}':contrast='1-0.6*{b}':eval=frame"]
if not vf:
    sys.exit("--flash 또는 --shake 필요")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-vf", ",".join(vf) + f",scale={W}:{H},setsar=1",
                "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-an", str(clip)], check=True)
print(f"{a.sid}: {', '.join(x for x in ('flash' if a.flash else '', 'shake' if a.shake else '') if x)} -> {clip}")
