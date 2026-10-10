"""Independent stdlib-only audit of captured live artifacts; no provider calls."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'acceptance' / '2026-10-10'

def audit(filename):
    view=json.loads((ROOT/filename).read_text())
    assert view['status']=='COMPLETED'
    maps={key:{o['id']:o for o in view[key]} for key in ('conditions','resources','capabilities','evidence','assessments')}
    for a in maps['assessments'].values():
        assert a['condition_id'] in maps['conditions']
        assert a['revision_evaluated']==view['revision'] and a['review_status']=='CURRENT'
        assert a['status']!='VERIFIED', 'No environment tests were run in these live cases'
        assert all(rid in maps['resources'] for rid in a['resource_ids'])
        assert all(cid in maps['capabilities'] and maps['capabilities'][cid]['resource_id'] in a['resource_ids'] for cid in a['capability_ids'])
        assert all(eid in maps['evidence'] for eid in a['evidence_ids'])
        if a['status'] in ('SUPPORTED','PARTIAL','NOT_SATISFIED','CONFLICTED'):
            claims=[maps['evidence'][eid] for eid in a['evidence_ids'] if maps['evidence'][eid]['locator'].startswith('exact source quote: ')]
            assert claims, a
            for e in claims:
                original=maps['evidence'][e['locator'].split(': ',1)[1]]
                assert e['excerpt_or_summary'] in original['excerpt_or_summary']
                assert e['source_ref']==original['source_ref']
                assert any(e['source_ref'] in maps['resources'][rid]['source_references'] for rid in a['resource_ids'])
            if a['status']=='CONFLICTED':
                assert {'SUPPORTS','REFUTES'} <= {e['stance'] for e in claims}
    p=view['proposal']
    assert p and p['validity_status']=='READY_FOR_REVIEW'
    assert p['revision_created']==view['revision']
    assert all(r in maps['resources'] for r in p['resource_ids'])
    assert all(a in maps['assessments'] for a in p['assessment_ids'])
    selected=[maps['assessments'][a] for a in p['assessment_ids']]
    covered={a['condition_id'] for a in selected if a['status'] in ('SUPPORTED','VERIFIED')}
    assert set(p['condition_coverage'])==covered
    assert set(p['uncovered_conditions'])==set(maps['conditions'])-covered
    return {'artifact':filename,'revision':view['revision'],'conditions':len(maps['conditions']),
        'resources':len(maps['resources']),'assessments':len(maps['assessments']),
        'statuses':dict(collections.Counter(a['status'] for a in maps['assessments'].values())),
        'usage':view['budget_usage'],'sha256':hashlib.sha256((ROOT/filename).read_bytes()).hexdigest(),'verdict':'PASS'}

def main():
    result=[audit(f) for f in ('web-r3.json','game-r1.json','vague-r1.json')]
    for f in ('web-r2-browser-export.json','web-r3-browser-export.json'):
        data=json.loads((ROOT/f).read_text())
        rev=2 if '-r2-' in f else 3
        assert data['revision']==rev
        original=json.loads((ROOT/f'web-r{rev}.json').read_text())
        assert data['conditions']==original['conditions'] and data['assessments']==original['assessments']
        assert data['proposal']['id']==original['proposal']['id']
    (ROOT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('PASS: 3 live artifact graphs, source quotes, current revisions, coverage and 2 browser JSON exports')

if __name__=='__main__': main()
