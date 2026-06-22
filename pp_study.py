"""Post-proc (.pp) placement study: what audio context drives each pp FAMILY, and
do pp changes line up with section boundaries vs audio transitions?
Reuses the loaders from venue_audio_study."""
import os, glob, collections, statistics
import numpy as np
import mido
from venue_audio_study import (load_mono, stft_mag, tempo_map, tick_to_ms,
                               pct_of, MIDI_DIR, MOGG_DIR, HOP, WIN)


def pp_family(name):
    n = name.replace(".pp", "")
    if any(k in n for k in ("b+w", "bw", "sepia", "silvertone", "photocopy",
                            "desat", "16mm", "security")):
        return "bw_desat"
    if any(k in n for k in ("trail", "psychedelic", "posterize", "negative",
                            "mirror", "space", "horror", "flicker")):
        return "trippy"
    if any(k in n for k in ("contrast",)):
        return "contrast"
    if any(k in n for k in ("bright", "bloom", "clean")):
        return "bright"
    if any(k in n for k in ("profilm", "video_a")):
        return "filmic_color"
    if "blue" in n:
        return "blue"
    return "other:" + n


def analyze(mid_path, mogg_path):
    mid = mido.MidiFile(mid_path)
    tpb = mid.ticks_per_beat
    tmap = tempo_map(mid)
    venue = next((t for t in mid.tracks if t.name and t.name.upper() == "VENUE"), None)
    sect_ticks = []
    events = []  # (tick, kind, text)
    t = 0
    if venue is None:
        return None, None
    for msg in venue:
        t += msg.time
        if msg.type == "text" and msg.text.strip("[]").endswith(".pp"):
            events.append((t, msg.text.strip("[]")))
    # section boundaries from EVENTS
    ev = next((tr for tr in mid.tracks if tr.name and tr.name.upper() == "EVENTS"), None)
    if ev:
        t = 0
        for msg in ev:
            t += msg.time
            if msg.type == "text" and ("section" in msg.text or "prc_" in msg.text):
                sect_ticks.append(t)
    sect_ticks.sort()

    mono, sr = load_mono(mogg_path)
    mag = stft_mag(mono, sr)
    if mag is None:
        return None, None
    stft_s = HOP / sr
    freqs = np.fft.rfftfreq(WIN, 1.0 / sr)
    rms = np.sqrt((mag ** 2).mean(axis=1) + 1e-9)
    centroid = (mag * freqs).sum(axis=1) / (mag.sum(axis=1) + 1e-9)
    rms_s = np.sort(rms); cen_s = np.sort(centroid)

    rows = []
    near_section = 0
    for tk, txt in events:
        ms = tick_to_ms(tk, tmap, tpb)
        fi = int(round(ms / 1000.0 / stft_s))
        if fi < 0 or fi >= len(rms):
            continue
        fam = pp_family(txt)
        rows.append((fam, pct_of(rms_s, rms[fi]), pct_of(cen_s, centroid[fi])))
        # is this pp change within 1/2 beat of a section boundary?
        if sect_ticks:
            import bisect
            i = bisect.bisect_left(sect_ticks, tk)
            cand = []
            if i < len(sect_ticks): cand.append(abs(sect_ticks[i] - tk))
            if i > 0: cand.append(abs(sect_ticks[i-1] - tk))
            if cand and min(cand) <= tpb // 2:
                near_section += 1
    return rows, (near_section, len(rows))


def main():
    moggs = {os.path.splitext(os.path.basename(p))[0]: p
             for p in glob.glob(os.path.join(MOGG_DIR, "*.mogg"))}
    allrows = []
    tot_near = tot = 0
    for d in sorted(glob.glob(os.path.join(MIDI_DIR, "*"))):
        mids = glob.glob(os.path.join(d, "*.mid"))
        if not mids:
            continue
        name = os.path.splitext(os.path.basename(mids[0]))[0]
        mogg = moggs.get(name)
        if not mogg:
            continue
        try:
            rows, ns = analyze(mids[0], mogg)
        except Exception as e:
            print("ERR", name, e); continue
        if rows:
            allrows.extend(rows)
            tot_near += ns[0]; tot += ns[1]

    print(f"total .pp events: {len(allrows)}")
    print(f"pp changes within 1/2 beat of a section boundary: "
          f"{tot_near}/{tot} = {100*tot_near/max(1,tot):.0f}%\n")
    fam = collections.defaultdict(list)
    for r in allrows:
        fam[r[0]].append(r)
    print(f"{'pp family':16s} {'n':>5s} {'%share':>7s} {'loud_p':>8s} {'bright_p':>9s}")
    for f in sorted(fam, key=lambda k: -len(fam[k])):
        rs = fam[f]
        if len(rs) < 5:
            continue
        lp = statistics.median([r[1] for r in rs])
        bp = statistics.median([r[2] for r in rs])
        print(f"{f:16s} {len(rs):5d} {100*len(rs)/len(allrows):6.0f}% {lp:8.1f} {bp:9.1f}")


if __name__ == "__main__":
    main()
