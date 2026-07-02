import os, random, re, json
from collections import Counter, defaultdict
import mido

midi_dir = r'C:\Users\samue\Documents\Claude Vault\Claude Vault\Projetos\Downcharter\midis\Venue learn songs\midi_files'

random.seed(42)
songs = sorted(os.listdir(midi_dir))
selected = random.sample(songs, 20)

print("=" * 70)
print("CAMERA CUT TRANSITION ANALYSIS")
print(f"Analyzing {len(selected)} random songs from {len(songs)} total")
print("=" * 70)

all_coop_events = []
all_directed_events = []
coop_event_counts = Counter()
directed_event_counts = Counter()
song_event_counts = Counter()
coop_transitions_total = Counter()
directed_transitions_total = Counter()
coop_cluster_by_song = {}
directed_cluster_by_song = {}
section_coop = defaultdict(Counter)
failed = []

for song_dir in selected:
    path = os.path.join(midi_dir, song_dir)
    mid_files = [f for f in os.listdir(path) if f.endswith('.mid') or f.endswith('.midi')]
    if not mid_files:
        failed.append(song_dir)
        continue
    
    mid_path = os.path.join(path, mid_files[0])
    
    try:
        mid = mido.MidiFile(mid_path)
    except Exception as e:
        print(f"  ERROR loading {song_dir}: {e}")
        failed.append(song_dir)
        continue
    
    coop_events = []
    directed_events = []
    
    for track in mid.tracks:
        if track.name.upper() == 'VENUE':
            abs_tick = 0
            for msg in track:
                abs_tick += msg.time
                if msg.type == 'text' or msg.type == 'marker':
                    text = msg.text.strip()
                    
                    m_coop = re.match(r'\[(coop_[^\]]+)\]', text)
                    if m_coop:
                        coop_events.append((abs_tick, m_coop.group(1)))
                        all_coop_events.append((song_dir, abs_tick, m_coop.group(1)))
                        coop_event_counts[m_coop.group(1)] += 1
                    
                    m_dir = re.match(r'\[(directed_[^\]]+)\]', text)
                    if m_dir:
                        directed_events.append((abs_tick, m_dir.group(1)))
                        all_directed_events.append((song_dir, abs_tick, m_dir.group(1)))
                        directed_event_counts[m_dir.group(1)] += 1
    
    coop_events.sort(key=lambda x: x[0])
    directed_events.sort(key=lambda x: x[0])
    
    coop_cluster_by_song[song_dir] = [e[1] for e in coop_events]
    directed_cluster_by_song[song_dir] = [e[1] for e in directed_events]
    
    song_event_counts[song_dir] = len(coop_events) + len(directed_events)
    
    for i in range(len(coop_events) - 1):
        from_shot = coop_events[i][1]
        to_shot = coop_events[i+1][1]
        coop_transitions_total[(from_shot, to_shot)] += 1
    
    for i in range(len(directed_events) - 1):
        from_shot = directed_events[i][1]
        to_shot = directed_events[i+1][1]
        directed_transitions_total[(from_shot, to_shot)] += 1
    
    print(f"  {song_dir}: {len(coop_events)} coop + {len(directed_events)} directed = {len(coop_events)+len(directed_events)} total")

if failed:
    print(f"\nFailed to read: {failed}")

total_coop = len(all_coop_events)
total_directed = len(all_directed_events)
total_events = total_coop + total_directed

print(f"\n{'='*70}")
print(f"OVERALL STATS")
print(f"{'='*70}")
print(f"Total coop events:     {total_coop}")
print(f"Total directed events: {total_directed}")
print(f"Total events:          {total_events}")
print(f"Coop:Directed ratio:   {total_coop}:{total_directed} = {total_coop/total_directed:.2f}:1")
print(f"Avg events per song:   {total_events/20:.1f}")

print(f"\n{'='*70}")
print(f"TOP 20 COOP SHOT TYPES (by frequency)")
print(f"{'='*70}")
for i, (shot, count) in enumerate(coop_event_counts.most_common(20), 1):
    print(f"  {i:2d}. {shot:35s}  {count:4d} ({100*count/total_coop:.1f}%)")

print(f"\n{'='*70}")
print(f"TOP 20 DIRECTED SHOT TYPES (by frequency)")
print(f"{'='*70}")
for i, (shot, count) in enumerate(directed_event_counts.most_common(20), 1):
    print(f"  {i:2d}. {shot:35s}  {count:4d} ({100*count/total_directed:.1f}%)")

print(f"\n{'='*70}")
print(f"TOP 30 COOP to COOP TRANSITIONS")
print(f"{'='*70}")
total_coop_trans = sum(coop_transitions_total.values())
print(f"Total coop transitions: {total_coop_trans}")
print(f"{'From':40s} {'To':40s} {'Count':6s} {'Pct':6s}")
print('-' * 92)
for i, ((from_shot, to_shot), count) in enumerate(coop_transitions_total.most_common(30), 1):
    pct = 100 * count / total_coop_trans
    print(f"  {i:2d}. {from_shot:35s} -> {to_shot:35s}  {count:4d}  {pct:5.1f}%")

print(f"\n{'='*70}")
print(f"TOP 20 DIRECTED to DIRECTED TRANSITIONS")
print(f"{'='*70}")
total_dir_trans = sum(directed_transitions_total.values())
print(f"Total directed transitions: {total_dir_trans}")
print(f"{'From':40s} {'To':40s} {'Count':6s} {'Pct':6s}")
print('-' * 92)
for i, ((from_shot, to_shot), count) in enumerate(directed_transitions_total.most_common(20), 1):
    pct = 100 * count / total_dir_trans
    print(f"  {i:2d}. {from_shot:35s} -> {to_shot:35s}  {count:4d}  {pct:5.1f}%")

def categorize_coop(shot):
    closeup_keywords = ['closeup', 'close']
    wide_keywords = ['far', 'behind', 'all_']
    for kw in closeup_keywords:
        if kw in shot:
            return 'closeup'
    for kw in wide_keywords:
        if kw in shot:
            return 'wide'
    return 'medium'

print(f"\n{'='*70}")
print("CLUSTERING ANALYSIS - Framing Categories")
print(f"{'='*70}")

same_frame = 0
diff_frame = 0
frame_transitions = Counter()
for (from_shot, to_shot), count in coop_transitions_total.items():
    cat_from = categorize_coop(from_shot)
    cat_to = categorize_coop(to_shot)
    frame_transitions[(cat_from, cat_to)] += count
    if cat_from == cat_to:
        same_frame += count
    else:
        diff_frame += count

print(f"  Same-category transitions: {same_frame}/{total_coop_trans} ({100*same_frame/total_coop_trans:.1f}%)")
print(f"  Cross-category transitions: {diff_frame}/{total_coop_trans} ({100*diff_frame/total_coop_trans:.1f}%)")
print(f"\n  Framing transition matrix:")
print(f"  {'From -> To':20s} {'Count':6s} {'Pct':6s}")
print("  " + '-' * 32)
for (cat_from, cat_to), count in frame_transitions.most_common():
    pct = 100 * count / total_coop_trans
    print(f"  {cat_from:8s} -> {cat_to:8s}  {count:4d}  {pct:5.1f}%")

print(f"\n{'='*70}")
print("SELF-TRANSITION ANALYSIS")
print(f"{'='*70}")
self_trans_count = 0
self_trans_by_shot = Counter()
non_self_by_shot = Counter()
for (from_shot, to_shot), count in coop_transitions_total.items():
    if from_shot == to_shot:
        self_trans_count += count
        self_trans_by_shot[from_shot] += count
    else:
        non_self_by_shot[from_shot] += count

print(f"  Self-transitions (same shot repeated): {self_trans_count}/{total_coop_trans} ({100*self_trans_count/total_coop_trans:.1f}%)")
print(f"\n  Self-transition rate by shot type:")
print(f"  {'Shot':35s} {'Self':6s} {'Total':6s} {'Rate':6s}")
print("  " + '-' * 53)
for shot in sorted(set(list(self_trans_by_shot.keys()) + list(non_self_by_shot.keys()))):
    s = self_trans_by_shot.get(shot, 0)
    t = s + non_self_by_shot.get(shot, 0)
    if t > 0:
        print(f"  {shot:35s} {s:4d}  {t:4d}  {100*s/t:5.1f}%")

print(f"\n{'='*70}")
print("SECTION ANALYSIS")
print(f"{'='*70}")

for song_dir in selected:
    path = os.path.join(midi_dir, song_dir)
    mid_files = [f for f in os.listdir(path) if f.endswith('.mid') or f.endswith('.midi')]
    if not mid_files:
        continue
    mid_path = os.path.join(path, mid_files[0])
    try:
        mid = mido.MidiFile(mid_path)
    except:
        continue
    for track in mid.tracks:
        if track.name.upper() == 'VENUE':
            abs_tick = 0
            current_section = 'unknown'
            for msg in track:
                abs_tick += msg.time
                if msg.type == 'text' or msg.type == 'marker':
                    text = msg.text.strip()
                    m_sec = re.match(r'\[(\w+)\]', text)
                    if m_sec:
                        sec_name = m_sec.group(1).lower()
                        known_sections = {'verse', 'chorus', 'bridge', 'intro', 'outro',
                                          'solo', 'prechorus', 'postchorus', 'breakdown',
                                          'interlude', 'hook', 'riff', 'head', 'middle8',
                                          'instrumental', 'refrain', 'build', 'transition',
                                          'coda', 'ending'}
                        if sec_name in known_sections:
                            current_section = sec_name
                    m_coop = re.match(r'\[(coop_[^\]]+)\]', text)
                    if m_coop:
                        section_coop[current_section][m_coop.group(1)] += 1

if section_coop:
    print(f"  Coop shots by section (sections with >= 5 events):")
    print(f"  {'Section':15s} {'Top shots':60s}")
    print("  " + '-' * 75)
    for sec in sorted(section_coop.keys()):
        total_sec = sum(section_coop[sec].values())
        if total_sec >= 5:
            top = section_coop[sec].most_common(5)
            top_str = ', '.join(f'{s}({c})' for s, c in top)
            print(f"  {sec:15s} {top_str}")

print(f"\n{'='*70}")
print("NOTABLE PATTERNS")
print(f"{'='*70}")

print("\n--- Common 3-shot sequences (coop) ---")
triplet_counter = Counter()
for song, events in coop_cluster_by_song.items():
    for i in range(len(events) - 2):
        triplet = (events[i], events[i+1], events[i+2])
        triplet_counter[triplet] += 1

for (a, b, c), count in triplet_counter.most_common(15):
    print(f"  {a:35s} -> {b:35s} -> {c:35s}  ({count}x)")

print(f"\n--- Unique coop shots per song ---")
shot_counts = []
for song, events in coop_cluster_by_song.items():
    n_unique = len(set(events))
    n_total = len(events)
    shot_counts.append(n_unique)
    if n_total > 0:
        print(f"  {song:40s} {n_unique:2d} unique / {n_total:2d} total")

avg_unique = sum(shot_counts) / len(shot_counts) if shot_counts else 0
print(f"\n  Average unique shots per song: {avg_unique:.1f}")

print(f"\n{'='*70}")
print("COOP + DIRECTED CO-OCCURRENCES")
print(f"{'='*70}")
coop_directed_pairs = Counter()

for song_dir in selected:
    path = os.path.join(midi_dir, song_dir)
    mid_files = [f for f in os.listdir(path) if f.endswith('.mid') or f.endswith('.midi')]
    if not mid_files:
        continue
    mid_path = os.path.join(path, mid_files[0])
    try:
        mid = mido.MidiFile(mid_path)
    except:
        continue
    for track in mid.tracks:
        if track.name.upper() == 'VENUE':
            abs_tick = 0
            all_venue = []
            for msg in track:
                abs_tick += msg.time
                if msg.type == 'text' or msg.type == 'marker':
                    text = msg.text.strip()
                    m_coop = re.match(r'\[(coop_[^\]]+)\]', text)
                    m_dir = re.match(r'\[(directed_[^\]]+)\]', text)
                    if m_coop:
                        all_venue.append((abs_tick, m_coop.group(1), 'coop'))
                    elif m_dir:
                        all_venue.append((abs_tick, m_dir.group(1), 'directed'))
            
            # Find simultaneous or near-simultaneous events
            events_sorted = sorted(all_venue, key=lambda x: x[0])
            for i in range(len(events_sorted)):
                for j in range(i+1, min(i+5, len(events_sorted))):
                    if abs(events_sorted[j][0] - events_sorted[i][0]) <= 5:
                        t1, n1, tp1 = events_sorted[i]
                        t2, n2, tp2 = events_sorted[j]
                        if tp1 != tp2:
                            if tp1 == 'coop':
                                coop_directed_pairs[(n1, n2)] += 1
                            else:
                                coop_directed_pairs[(n2, n1)] += 1

print("Top 15 coop+directed co-occurrences (within same tick):")
for (coop, dir_), count in coop_directed_pairs.most_common(15):
    print(f"  {coop:35s} + {dir_:35s}  ({count}x)")

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"  Songs analyzed:   {len(selected) - len(failed)}")
print(f"  Total events:     {total_events}")
print(f"  Coop events:      {total_coop} ({100*total_coop/total_events:.1f}%)")
print(f"  Directed events:  {total_directed} ({100*total_directed/total_events:.1f}%)")
print(f"  Coop:Dir ratio:   {total_coop/total_directed:.2f}:1")
print(f"  Self-transition:  {100*self_trans_count/total_coop_trans:.1f}% of coop transitions")
print(f"  Same-category:    {100*same_frame/total_coop_trans:.1f}% of coop transitions")
