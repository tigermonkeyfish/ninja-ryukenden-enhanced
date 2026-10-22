#!/usr/bin/env python3
"""Compare captured cinema sequences; no game or image libraries required."""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def load(directory):
    scenes = defaultdict(list)
    for line in (directory / 'frames.jsonl').read_text().splitlines():
        row = json.loads(line)
        scenes[row['scene']].append(row['png_sha256'])
    return scenes


def transitions(sequence):
    # Static images can be held for different durations. Keep all image changes
    # in order, including animation loops, rather than comparing unordered sets.
    return [value for i, value in enumerate(sequence) if i == 0 or value != sequence[i - 1]]


def compare(reference, candidate):
    a, b = load(reference), load(candidate)
    results = []
    for scene in sorted(a.keys() | b.keys()):
        original, changed = a[scene], b[scene]
        x, y = transitions(original), transitions(changed)
        mismatch = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), None)
        if mismatch is None and len(x) != len(y):
            mismatch = min(len(x), len(y))
        results.append({
            'scene': scene, 'reference_frames': len(original), 'candidate_frames': len(changed),
            'exact_frame_sequence': original == changed,
            'image_transition_sequence': x == y,
            'reference_image_transitions': len(x), 'candidate_image_transitions': len(y),
            'first_transition_mismatch': mismatch,
            'novel_candidate_images': sorted(set(changed) - set(original)),
        })
    complete = ((reference / 'run.json').exists() and (candidate / 'run.json').exists()
                and set(a) == set(b) == set(range(15)))
    return {'complete': complete, 'all_image_sequences_match':
            complete and all(row['image_transition_sequence'] for row in results), 'scenes': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = compare(args.reference, args.candidate)
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered)
    raise SystemExit(0 if result['all_image_sequences_match'] else 1)


if __name__ == '__main__':
    main()
