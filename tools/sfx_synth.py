"""효과음 합성(외부 음원 없이 numpy). assets/sfx/*.wav 48k stereo.

  python scripts/sfx_synth.py            # 전부 다시 만든다
"""
import pathlib, wave
import numpy as np

SR = 48000
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "sfx"
rng = np.random.default_rng(7)


def lp(x, fc):  # 빠른 버전: FFT 브릭월 + 부드러운 롤오프
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x))


def hp(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (f / fc) ** 4 / (1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x))


def env(n, attack, decay_tau, t0=0.0):
    t = np.arange(n) / SR - t0
    e = np.where(t < 0, 0, np.minimum(1, t / max(attack, 1e-4)) * np.exp(-np.maximum(t - attack, 0) / decay_tau))
    return e


def stereo(l, r=None, width=0.0):
    r = l if r is None else r
    return np.stack([l * (1 - width / 2) + r * width / 2, r * (1 - width / 2) + l * width / 2], 1)


def save(name, x, peak=0.89):
    x = x / (np.abs(x).max() + 1e-9) * peak
    fade = int(0.05 * SR); x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    print(name, f"{len(x) / SR:.1f}s")


def noise(sec):
    return rng.standard_normal(int(sec * SR))


def brown(sec):
    b = np.cumsum(noise(sec)); b -= lp(b, 8); return b / np.abs(b).max()


def detonation(sec=9.0):
    """섬광 순간: 날카로운 크랙 + 서브 쿵 + 길게 굴러가는 저음 럼블."""
    n = int(sec * SR); t = np.arange(n) / SR
    crack = hp(noise(sec), 1800) * env(n, 0.002, 0.09) * 0.9
    sweep = np.sin(2 * np.pi * np.cumsum(28 + 70 * np.exp(-t / 0.35)) / SR) * env(n, 0.01, 1.4) * 1.4
    rumbleL, rumbleR = lp(brown(sec), 140), lp(brown(sec), 140)
    rum_env = env(n, 0.25, 3.2) * (1 + 0.35 * np.sin(2 * np.pi * 1.7 * t) * np.exp(-t / 2))
    crackle = hp(noise(sec), 900) * (rng.random(n) < 0.004) * 6 * env(n, 0.3, 1.8, 0.2)
    L = crack + sweep + rumbleL * rum_env * 1.6 + lp(crackle, 5000) * 0.4
    R = crack + sweep + rumbleR * rum_env * 1.6 + lp(np.roll(crackle, 700), 5000) * 0.4
    return stereo(L, R, 0.3)


def blast_wave(sec=7.0, arrive=2.2):
    """충격파가 다가와 덮친다: 부풀어 오르는 굉음 + 도착 순간 쾅 + 파편 쉭쉭."""
    n = int(sec * SR); t = np.arange(n) / SR
    swell = np.clip(t / arrive, 0, 1) ** 3
    after = np.exp(-np.maximum(t - arrive, 0) / 2.4)
    roar = (lp(noise(sec), 700) * 0.8 + lp(brown(sec), 200) * 1.2) * swell * after
    hit = lp(noise(sec), 300) * env(n, 0.005, 0.6, arrive) * 2.0 + np.sin(2 * np.pi * 38 * t) * env(n, 0.005, 0.9, arrive) * 1.2
    debris = hp(noise(sec), 2500) * env(n, 0.1, 1.6, arrive) * 0.5
    L, R = roar + hit + debris, lp(noise(sec), 700) * 0.8 * swell * after + lp(brown(sec), 200) * 1.2 * swell * after + hit + np.roll(debris, 900)
    return stereo(L, R, 0.2)


def rumble_tail(sec=9.0):
    """폐허 위 저음 여운(재·불)."""
    n = int(sec * SR); t = np.arange(n) / SR
    body = lp(brown(sec), 90) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t))
    fire = lp(hp(noise(sec), 400), 2500) * (rng.random(n) < 0.02) * 3
    e = np.minimum(1, t / 1.0) * np.minimum(1, (sec - t) / 2.0)
    return stereo(body * e * 1.3 + lp(fire, 3000) * e * 0.25, None, 0)


def whoosh(sec=2.5):
    """떨어지는 탄두: 위에서 내리꽂는 휘익(고음→저음)."""
    n = int(sec * SR); t = np.arange(n) / SR
    y = lp(noise(sec), 2500) * 0.6 + hp(lp(noise(sec), 5000), 600) * 0.3
    e = np.minimum(1, t / (sec * 0.8)) ** 2 * np.minimum(1, (sec - t) / 0.08)
    return stereo(y * e, None, 0)


if __name__ == "__main__":
    save("nuke_detonation", detonation())
    save("nuke_blast_wave", blast_wave())
    save("nuke_rumble_tail", rumble_tail(), peak=0.6)
    save("warhead_whoosh", whoosh(), peak=0.5)
