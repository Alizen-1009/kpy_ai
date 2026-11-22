"""Explicit manual scorer smoke probe; never contacts a model."""
import json
from pathlib import Path
import code128_client as c

IMAGE = 'sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef'


def main():
    evidence = Path('sandbox-evidence/controls')
    evidence.mkdir(exist_ok=False)
    original = c.bounded
    events = []

    def traced(argv, *args, **kwargs):
        event = {'argv': argv}
        events.append(event)
        try:
            result = original(argv, *args, **kwargs)
            event.update(status='ok', raw=result.decode(errors='replace'))
            if argv[1] == 'rm':
                try:
                    original(['docker', 'inspect', '--type', 'container', argv[-1]])
                    event['absence_verified'] = False
                except RuntimeError as exc:
                    event['absence_verified'] = 'No such' in str(exc)
                    event['absence_raw'] = str(exc)
            return result
        except Exception as exc:
            event.update(status=type(exc).__name__, error=str(exc))
            raise
        finally:
            (evidence/'docker-events.json').write_text(json.dumps(events, indent=2))

    c.bounded = traced
    result = {'purpose': 'scorer validation only; not model Code128 score', 'image': IMAGE}
    try:
        w = c.workloads()
        answers = {
            'lru_cache': '''def lru_cache(operations, capacity):
    from collections import OrderedDict
    d, out = OrderedDict(), []
    for op in operations:
        key = op[1]
        if op[0] == 'get':
            out.append(d.get(key))
            if key in d: d.move_to_end(key)
        else:
            d[key] = op[2]
            d.move_to_end(key)
            if len(d) > capacity: d.popitem(last=False)
    return out
''',
            'merge_intervals': '''def merge_intervals(intervals):
    out = []
    for a,b in sorted(intervals):
        if out and a <= out[-1][1]: out[-1][1] = max(b,out[-1][1])
        else: out.append([a,b])
    return out
''',
            'topological_order': '''def topological_order(nodes, edges):
    remaining, out = set(nodes), []
    while remaining:
        ready = sorted(n for n in remaining if not any(v == n and u in remaining for u,v in edges))
        if not ready: return []
        out.append(ready[0]); remaining.remove(ready[0])
    return out
''',
            'longest_unique_substring': '''def longest_unique_substring(text):
    seen, left, best = {}, 0, 0
    for i,ch in enumerate(text):
        left = max(left,seen.get(ch,-1)+1)
        best = max(best,i-left+1); seen[ch] = i
    return best
''',
            'kth_largest': 'def kth_largest(numbers, k):\n    return sorted(numbers, reverse=True)[k-1]\n',
            'min_window': '''def min_window(text, pattern):
    from collections import Counter
    if not pattern: return ''
    need, best = Counter(pattern), None
    for i in range(len(text)):
        have = Counter()
        for j in range(i,len(text)):
            have[text[j]] += 1
            if all(have[k] >= v for k,v in need.items()):
                candidate = text[i:j+1]
                if best is None or len(candidate) < len(best): best = candidate
                break
    return best or ''
''',
            'group_anagrams': '''def group_anagrams(words):
    groups = {}
    for word in words: groups.setdefault(''.join(sorted(word)),[]).append(word)
    return list(groups.values())
''',
            'flatten_dict': '''def flatten_dict(data, sep='.'):
    out = {}
    def visit(d,path):
        for k,v in d.items():
            p = path+[k]
            if isinstance(v,dict) and v: visit(v,p)
            else: out[sep.join(p)] = v
    visit(data,[])
    return out
'''}
        rows = []
        for task, answer in answers.items():
            score = c.sandbox(IMAGE, task, answer, w.fixed_unit_cases(task))
            rows.append({'task': task, 'score': score})
            (evidence/(task+'.json')).write_text(json.dumps(rows[-1], indent=2))
        result['positive'] = c.summary(rows)
        assert result['positive']['passed'] == 128
        for name, body in [('wrong', 'return -1'), ('loop', 'while True: pass'),
                           ('flood', "print('x'*2000000); return 0")]:
            answer = 'def longest_unique_substring(text):\n    '+body+'\n'
            try:
                score = c.sandbox(IMAGE, 'longest_unique_substring', answer,
                                  w.fixed_unit_cases('longest_unique_substring'))
                result[name] = score
            except Exception as exc:
                result[name] = {'error_type': type(exc).__name__, 'error': str(exc)}
            (evidence/(name+'.json')).write_text(json.dumps(result[name], indent=2))
    except Exception as exc:
        result.update(error_type=type(exc).__name__, error=str(exc))
    (evidence/'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
