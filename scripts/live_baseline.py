"""Opt-in, bounded one-shot baselines for the public acceptance fixtures.

Example: GOALSIFT_LLM_MODEL=deepseek-flash .venv/bin/python -m scripts.live_baseline --allow-paid --max-usd 0.08
No search, target project writes, or external code execution.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path
from pydantic import BaseModel
from goalsift.budget import BudgetConfig, BudgetGuard
from goalsift.llm_adapter import LLMAdapter
from goalsift.security import redact_secrets

class Answer(BaseModel):
    response: str

async def run(args):
    adapter = LLMAdapter()
    guard = BudgetGuard(BudgetConfig(budget_usd=args.max_usd, max_actions=4,
        max_runtime_seconds=180,max_model_input_tokens=20000,max_model_output_tokens=4000))
    root = Path(args.fixtures)
    cases = [('web','web-r3.json'),('game','game-r1.json'),('vague','vague-r1.json'),('vague-initial','vague-r1.json')]
    try:
        for name, filename in cases:
            dest = root / (name+'-baseline.json')
            if dest.exists():
                previous = json.loads(dest.read_text())
                guard.record(previous['usage'])
                guard.usage.actions += 1
                print(name, 'existing receipt; not repeated')
                continue
            view = json.loads((root/filename).read_text())
            text = view['original_request'] if name=='vague-initial' else view['goal']['statement']
            reserve = adapter.reservation(20000,4000)
            if reserve is None: raise RuntimeError('Unknown model price')
            guard.check(reserve_usd=reserve)
            adapter.configure_limits(20000,4000)
            start=time.monotonic()
            observed_usage = {}
            async def invoke():
                try:
                    return await adapter._run('one-shot',
                'Give ordinary one-shot advice for this goal. Prefer existing resources; explain '
                'requirements, reuse, integration, new work, risks and unknowns. Ask for a focused '
                'clarification if essential. You have no search or fetched sources, so never pretend '
                'to have checked links or run tests.',Answer,text)
                finally:
                    observed_usage.update(adapter.pop_usage())
            answer=await asyncio.wait_for(invoke(),60)
            stats=observed_usage
            guard.record(stats)
            report={'kind':'live one-shot model; no search', 'model':adapter.model_name,
                'input':text,'response':redact_secrets(answer.response),'usage':stats,
                'elapsed_seconds':round(time.monotonic()-start,2)}
            dest.write_text(json.dumps(report,ensure_ascii=False,indent=2))
            print(name,stats['model_requests'],round(stats['cost_usd'],6))
    finally:
        await adapter.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-paid',action='store_true')
    parser.add_argument('--max-usd',type=float,required=True)
    parser.add_argument('--fixtures',default='acceptance/2026-10-10')
    args=parser.parse_args()
    if not args.allow_paid: parser.error('--allow-paid is required; this calls the paid model')
    asyncio.run(run(args))
