"""Per-instrument balance of coop_* framings: after enlarging the framing pools and
adding anti-recency, do the per-instrument quotas (drums/vocal/bass/guitar/keys)
still match the 20 official venues? Compares official corpus vs our generated output."""
import os, glob, collections, statistics, re
import mido

MIDI_DIR = "midis/Venue learn songs/midi_files"
INSTR = {"d": "drums", "v": "vocal", "b": "bass", "g": "guitar", "k": "keys"}


def classify(coop):
    """Return set of focused instruments for a coop_* framing (group framings -> set())."""
    n = coop.replace("coop_", "")
    if n.startswith(("all", "front")):
        return set()
    # leading instrument letters before first '_': e.g. 'dv_near', 'd_closeup_hand'
    head = n.split("_", 1)[0]
    return {INSTR[c] for c in head if c in INSTR}


def shares_from_events(coops):
    cnt = collections.Counter()
    for c in coops:
        for inst in classify(c):
            cnt[inst] += 1
    tot = sum(cnt.values()) or 1
    return {k: 100 * cnt.get(k, 0) / tot for k in INSTR.values()}


def official():
    agg = collections.Counter()
    for d in sorted(glob.glob(os.path.join(MIDI_DIR, "*"))):
        mids = glob.glob(os.path.join(d, "*.mid"))
        if not mids:
            continue
        ven = next((t for t in mido.MidiFile(mids[0]).tracks
                    if (t.name or "").upper() == "VENUE"), None)
        if not ven:
            continue
        for msg in ven:
            if msg.type == "text":
                t = msg.text.strip("[]")
                if t.startswith("coop_"):
                    for inst in classify(t):
                        agg[inst] += 1
    return agg


def main():
    agg = official()
    tot = sum(agg.values()) or 1
    print("OFFICIAL per-instrument coop framing share (single-focus framings):")
    for k in INSTR.values():
        print(f"  {k:7s} {agg.get(k,0):5d}  {100*agg.get(k,0)/tot:5.1f}%")


if __name__ == "__main__":
    main()
