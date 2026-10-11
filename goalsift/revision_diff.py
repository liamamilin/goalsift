"""Read-only comparison of recorded revisions, without model inference."""
from collections import defaultdict
from .goal_review import normalized
from .source_research import source_identity


def compare_revisions(before: dict, after: dict) -> dict:
    if before['id'] != after['id']: raise ValueError('不能比较不同任务')
    old = {c['id']: c for c in before['conditions']}
    new = {c['id']: c for c in after['conditions']}
    pairs, remaining = {}, set(new)
    for cid, c in old.items():
        candidates = [nid for nid in remaining if (new[nid].get('lineage_id') or nid) == (c.get('lineage_id') or cid)]
        if not candidates:
            same_old = [item for item in old.values() if normalized(item['statement']) == normalized(c['statement'])]
            same_new = [nid for nid in remaining if normalized(new[nid]['statement']) == normalized(c['statement'])]
            if len(same_old) == len(same_new) == 1: candidates = same_new
        if len(candidates) == 1:
            pairs[cid] = candidates[0]
            remaining.remove(candidates[0])
    added = [new[nid] for nid in new if nid in remaining]
    removed = [c for cid, c in old.items() if cid not in pairs]
    fields = ('statement', 'obligation', 'dimension', 'provenance', 'verification_method')
    def semantic(c, mapping):
        return {**{k: c.get(k, 'SYSTEM_ASSUMED' if k == 'provenance' else None) for k in fields},
                'relations': sorted((rel['type'], tuple(sorted(mapping.get(t, t) for t in rel['target_ids']))) for rel in c.get('relations', []))}
    changed = [{'before': old[cid], 'after': new[nid]} for cid, nid in pairs.items()
               if semantic(old[cid], pairs) != semantic(new[nid], {})]
    resources = []
    old_res, new_res = {}, {}
    for view, index in ((before, old_res), (after, new_res)):
        for r in view['resources']: index.setdefault(source_identity(r['canonical_source']), r)
    for key in sorted(old_res.keys() | new_res.keys()):
        a, b = old_res.get(key), new_res.get(key)
        if a is None or b is None or any(a.get(k) != b.get(k) for k in ('name', 'license_claim', 'version_or_revision')):
            resources.append({'before': a, 'after': b})
    def assessments(view, condition_map):
        index, res, evidence = defaultdict(list), {r['id']: r for r in view['resources']}, {e['id']: e for e in view['evidence']}
        for a in view['assessments']:
            for rid in a['resource_ids']:
                if rid not in res: continue
                key = (condition_map.get(a['condition_id'], a['condition_id']), source_identity(res[rid]['canonical_source']))
                index[key].append({'status': a['status'], 'explanation': a['explanation'], 'gaps': a['gaps'],
                    'evidence': sorted((evidence[e]['source_ref'], evidence[e]['excerpt_or_summary']) for e in a['evidence_ids'] if e in evidence)})
        return index
    a_index, b_index = assessments(before, pairs), assessments(after, {})
    assessment_changes = []
    for key in sorted(a_index.keys() | b_index.keys(), key=str):
        a, b = a_index.get(key, []), b_index.get(key, [])
        if sorted(a, key=str) == sorted(b, key=str): continue
        cid, rkey = key
        condition = new.get(cid) or old.get(cid)
        resource = new_res.get(rkey) or old_res[rkey]
        assessment_changes.append({'condition': condition['statement'], 'condition_id': cid,
            'resource': resource['name'], 'url': resource['canonical_source'],
            'before': sorted({x['status'] for x in a}), 'after': sorted({x['status'] for x in b}),
            'before_explanations': [x['explanation'] for x in a],
            'explanations': [x['explanation'] for x in b], 'gaps': list(dict.fromkeys(g for x in b for g in x['gaps']))})
    def receipts(view):
        result = {}
        for e in sorted(view['evidence'], key=lambda e: e['retrieved_at']):
            if e.get('stance') == 'CONTEXT': result[e['source_ref']] = e
        return result
    a_docs, b_docs = receipts(before), receipts(after)
    documents = []
    for url, e in b_docs.items():
        previous = a_docs.get(url)
        if previous and previous['id'] == e['id']: continue
        kind = 'new' if not previous else ('changed' if any(previous.get(k) != e.get(k) for k in ('source_version', 'excerpt_or_summary')) else 'reread')
        documents.append({'url': url, 'kind': kind, 'category': e['locator'], 'before_version': previous.get('source_version') if previous else None,
                          'version': e.get('source_version'), 'retrieved_at': e['retrieved_at']})
    def coverage(view):
        return set((view.get('proposal') or {}).get('condition_coverage', []))
    a_coverage = {pairs.get(cid, cid) for cid in coverage(before)}
    b_coverage = coverage(after)
    newly_covered = [new[cid]['statement'] for cid in new if cid in b_coverage - a_coverage]
    newly_uncovered = [new[cid]['statement'] for cid in new if cid in a_coverage - b_coverage]
    goal_changes = [k for k in ('purpose', 'constraints', 'assumptions', 'requirements')
                    if (before.get('goal') or {}).get(k) != (after.get('goal') or {}).get(k)]
    old_evidence_ids = {e['id'] for e in before['evidence']}
    return {'base_revision': before['revision'], 'target_revision': after['revision'],
        'target_status': after['status'], 'is_partial': after['status'] != 'COMPLETED',
        'scope': after.get('research_scope'), 'goal_changes': goal_changes,
        'conditions': {'added': added, 'removed': removed, 'changed': changed, 'unchanged': len(pairs) - len(changed)},
        'resources': resources, 'documents': documents, 'assessment_changes': assessment_changes,
        'newly_covered': newly_covered, 'newly_uncovered': newly_uncovered,
        'summary': {'new_sources': sum(d['kind'] == 'new' for d in documents),
            'changed_sources': sum(d['kind'] == 'changed' for d in documents),
            'reread_sources': sum(d['kind'] == 'reread' for d in documents),
            'new_evidence': sum(e['id'] not in old_evidence_ids for e in after['evidence']),
            'reused_assessments': len(after.get('reused_assessment_ids', [])),
            'coverage_before': len(coverage(before)), 'conditions_before': len(old),
            'coverage_after': len(b_coverage), 'conditions_after': len(new)},
        'usage': {'before': before.get('budget_usage', {}), 'after': after.get('budget_usage', {})}}
