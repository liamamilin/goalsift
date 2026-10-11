"""Reports and JSON derive from exactly the same current or historical snapshot."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from .repository import Repository
from .security import redact_secrets

def to_json(repo: Repository, job_id: str, *, view: dict | None = None) -> dict:
    result = dict(view if view is not None else repo.current_view(job_id))
    result['exported_at'] = datetime.now(timezone.utc).isoformat()
    return json.loads(redact_secrets(json.dumps(result, ensure_ascii=False)))

def to_markdown(repo: Repository, job_id: str, *, view: dict | None = None) -> str:
    d = to_json(repo, job_id, view=view)
    goal, proposal = d['goal'], d['proposal']
    lines = ['# GoalSift 研究报告', '', f'- 任务：{job_id}', f'- 修订：{d["revision"]}',
             f'- 状态：{d["status"]}', f'- 导出时间：{d["exported_at"]}',
             '- 范围：公开来源的方案研究；方案尚未执行，来源支持不等于目标环境验收。', '', '## 目标', '']
    if goal:
        lines += [goal['statement'], '', '**用户原话：** ' + goal['original_user_text']]
        for name, label in [('constraints', '用户要求与已确认前提'), ('assumptions', '未确认假设'), ('open_questions', '待确认问题')]:
            if goal.get(name):
                lines += ['', '**' + label + '**']
                for item in goal[name]:
                    lines.append('- ' + (f"[{item.get('provenance', 'SYSTEM_ASSUMED')}] " + item.get('text', str(item)) if isinstance(item, dict) else str(item)))
        for decision in goal.get('condition_decisions', []):
            if decision['action'] == 'remove': lines.append(f"- 已移出目标（r{decision['revision']}）：{decision['original_statement']}")
    lines += ['', '## 候选路径', '']
    if proposal:
        lines += ['### ' + proposal['title'], '', proposal['summary'], '',
                  '**建议理由：** ' + proposal['recommendation_reason'], '']
        for key, label in [('integration_work', '集成工作'), ('new_work', '补充工作'), ('risks', '风险'), ('assumptions', '假设')]:
            if proposal.get(key): lines += ['**' + label + '**', *['- ' + x for x in proposal[key]], '']
        lines += ['实施费用：' + json.dumps(proposal['costs'], ensure_ascii=False), '']
    else: lines += ['当前没有有依据的候选路径。', '']
    lines += ['## 成立条件', '']
    conditions = {c['id']: c for c in d['conditions']}
    resources = {r['id']: r for r in d['resources']}
    evidence = {e['id']: e for e in d['evidence']}
    if d.get('research_scope'):
        scope = d['research_scope']
        lines += ['## 本轮定向补查', '', f"- 基于修订：{scope['base_revision']}；本轮费用上限：${scope['budget_usd']}",
                  '- 调查条件：' + '；'.join(conditions[cid]['statement'] for cid in scope['condition_ids'] if cid in conditions),
                  '- 调查问题：' + (scope['question'] or '核查所选条件的依据与缺口'),
                  f"- 沿用评价：{len(d.get('reused_assessment_ids', []))} 项；新增资料可能影响同一候选的其他条件。", '']
    for c in conditions.values():
        lines += [f'- **[{c["obligation"]} / {c["dimension"]}]** {c["statement"]} (`{c["id"]}`)',
                  '  - 确认来源：' + c.get('provenance', 'SYSTEM_ASSUMED'),
                  '  - 依据：' + c['origin'], '  - 验收方式：' + (c.get('verification_method') or '未确认')]
    lines += ['', '## 资源与许可', '']
    for r in resources.values():
        lines += [f'- **{r["name"]}** — 许可：{r.get("license_claim") or "UNKNOWN"}',
                  '  - 来源：' + r['canonical_source'], '  - ' + r['description']]
        for doc in d.get('source_reviews', {}).get(r['id'], {}).get('documents', []):
            lines.append(f"  - 补充文档（{doc['category']}）：{doc['url']}；版本 {doc.get('version') or 'UNKNOWN'}")
    lines += ['', '## 条件匹配与证据', '']
    for a in d['assessments']:
        condition = conditions.get(a['condition_id'], {}).get('statement', a['condition_id'])
        names = '、'.join(resources[r]['name'] for r in a['resource_ids'] if r in resources)
        lines += [f'### {a["status"]}：{condition}', '', f'资源：{names}', a['explanation']]
        for gap in a['gaps']: lines.append('- 缺口：' + gap)
        for eid in a['evidence_ids']:
            e = evidence.get(eid)
            if e: lines += [f'- 来源：{e["source_ref"]}（{e["locator"]}；读取于 {e["retrieved_at"]}）',
                            '  > ' + e['excerpt_or_summary'][:700].replace('\n', '\n  > ')]
        lines.append('')
    lines += ['## 研究范围与限制', '']
    for note in d.get('delivery_notes', []): lines.append('- ' + note)
    if d.get('stopped_reason'): lines.append('- 中止原因：' + d['stopped_reason'])
    lines += ['', '研究用量：' + json.dumps(d.get('budget_usage', {}), ensure_ascii=False)]
    return redact_secrets('\n'.join(lines) + '\n')
