#!/usr/bin/env python3
"""Петли мотора для спайка звука S-07 (docs/SPIKES.md): 4 цилиндра, синтез без сэмплов.
Только спайк (scenes/dev/ — в релиз не идёт). Настоящий мотор — этап 1.5.

Запуск из корня проекта: python3 scenes/dev/spikes/audio/src/gen_engine_loops.py
Нужны numpy и ffmpeg с libvorbis. Результат: scenes/dev/spikes/audio/engine_r070.ogg, _r100, _r180
(r = обороты относительно базы 3000 об/мин: 0,7 · 1,0 · 1,8 — края и середина ползунка спайка).

Бесшовность: сигнал строится по кругу длиной LOOP_S. Число вспышек в петле целое и кратно числу
цилиндров, импульсы ставятся в частотной области (дробное время без «ступенек»), шум фильтруется
круговой свёрткой через FFT. Поэтому последний отсчёт петли непрерывно переходит в первый.
Повторный запуск даёт те же файлы (seed фиксирован, ffmpeg с -fflags +bitexact)."""
import os
import subprocess
import sys
import wave

import numpy as np

SR = 22050                 # Гц; мотор почти весь ниже 5 кГц, ×1,8 по тону — всё ещё ниже Найквиста
LOOP_S = 2.0               # длина петли; короче — слышна повторяемость «рисунка» вспышек
BASE_RPM = 3000.0
CYL = 4
CYL_GAIN = (1.0, 0.88, 0.96, 0.82)   # разброс цилиндров → субгармоники, «бурчание»; ровнее — «пылесос»
JITTER = 0.012             # дрожание момента вспышки, доля периода
AMP_JITTER = 0.06          # разброс силы вспышки
# резонансы выхлопа и кузова: (частота Гц, добротность, усиление). От оборотов не зависят — в этом
# и разница с подъёмом тона одной петли, где резонансы «уезжают» вверх вместе с тоном.
RESONANCES = ((160.0, 1.6, 1.0), (480.0, 2.5, 0.55), (1250.0, 3.5, 0.22), (2600.0, 4.0, 0.08))
PULSE_HZ = 1800.0          # ширина вспышки (гауссов спад спектра)
NOISE_DB = -20.0           # шум сгорания относительно тона
TARGET_RMS_DB = -16.0
RATIOS = (0.7, 1.0, 1.8)
QUALITY = 3                # libvorbis -q:a; 3 ≈ 80 кбит/с, петля 2 с ≈ 20 КБ


def resonance(f: np.ndarray) -> np.ndarray:
    h = np.zeros_like(f, dtype=complex)
    fs = np.maximum(f, 1e-3)
    for fc, q, g in RESONANCES:
        h += g / (1 + 1j * q * (fs / fc - fc / fs))
    hp = (fs / 35.0) ** 2 / (1 + (fs / 35.0) ** 2)          # срез ниже 35 Гц: телефонный динамик всё равно не играет
    return h * hp


def engine_loop(ratio: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * LOOP_S)
    f_fire = BASE_RPM * ratio / 60.0 * CYL / 2.0
    n_fire = int(round(f_fire * LOOP_S))
    assert n_fire % CYL == 0 and abs(n_fire - f_fire * LOOP_S) < 1e-6, "петля должна вмещать целое число циклов"
    period = n / n_fire
    t = (np.arange(n_fire) + rng.uniform(-JITTER, JITTER, n_fire)) * period
    amp = np.array([CYL_GAIN[i % CYL] for i in range(n_fire)]) * (1 + rng.uniform(-AMP_JITTER, AMP_JITTER, n_fire))
    k = np.arange(n // 2 + 1)
    f = k * SR / n
    spec = np.zeros(k.size, dtype=complex)
    for ti, ai in zip(t, amp):
        spec += ai * np.exp(-2j * np.pi * k * ti / n)
    spec *= np.exp(-(f / PULSE_HZ) ** 2) * resonance(f)
    spec[0] = 0
    tone = np.fft.irfft(spec, n)
    # шум сгорания: белый шум × огибающая вспышек (по кругу), полоса 700–4000 Гц
    idx = np.arange(n)
    env = np.zeros(n)
    for ti, ai in zip(t, amp):
        d = (idx - ti) % n
        env += ai * np.exp(-d / (0.003 * SR))
    noise = rng.standard_normal(n) * env
    nspec = np.fft.rfft(noise)
    band = (f / 700.0) ** 2 / (1 + (f / 700.0) ** 2) / (1 + (f / 4000.0) ** 4)
    noise = np.fft.irfft(nspec * band, n)
    noise *= np.sqrt(np.mean(tone ** 2) / max(np.mean(noise ** 2), 1e-12)) * 10 ** (NOISE_DB / 20)
    x = tone + noise
    x *= 10 ** (TARGET_RMS_DB / 20) / np.sqrt(np.mean(x ** 2))
    x = np.tanh(1.4 * x) / 1.4                                 # мягкое ограничение пиков
    x *= 10 ** (TARGET_RMS_DB / 20) / np.sqrt(np.mean(x ** 2))
    peak = np.max(np.abs(x))
    if peak > 0.95:
        x *= 0.95 / peak
    return x


def write_ogg(x: np.ndarray, path: str) -> None:
    tmp = path + ".tmp.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:a", "libvorbis", "-q:a", str(QUALITY),
                    "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", path], check=True)
    os.remove(tmp)


def main() -> None:
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    for i, r in enumerate(RATIOS):
        x = engine_loop(r, seed=100 + i)
        path = os.path.normpath(os.path.join(out_dir, f"engine_r{int(round(r * 100)):03d}.ogg"))
        write_ogg(x, path)
        f_fire = BASE_RPM * r / 60.0 * CYL / 2.0
        print(f"{os.path.relpath(path)}: {BASE_RPM * r:.0f} об/мин, вспышки {f_fire:.0f} Гц, "
              f"{os.path.getsize(path) // 1024} КБ, пик {np.max(np.abs(x)):.2f}")


if __name__ == "__main__":
    sys.exit(main())
