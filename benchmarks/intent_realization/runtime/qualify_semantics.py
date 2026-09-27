"""Real compiler qualification, isolated from execution owners.

This is semantic evidence only. Owner effect qualification uses public /app
journeys and the real-database/Git ledger suite. No response is an effect oracle.
Holdout input is permitted only with a previously recorded implementation freeze.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from benchmarks.intent_realization.runtime.evidence import source_receipt, verify_freeze
from spg.application.bootstrap import bootstrap
from spg.application.intent_realization import IntentRealizationKernel, executable_semantic_actions, blocking_action_arguments
from spg.config import Settings
from spg.domain.intent_realization import ObservedEffect
from spg.domain.interaction import Interaction, InteractionRecord, InteractionInterpretationInput


class QualificationRuntime:
    """Record actual provider outputs for this synthetic qualification only.

    No prompt, environment value or authentication header is persisted. The
    declared qualification inputs contain no user secrets. Rejected outputs
    remain inspectable after the bounded repair fails.
    """
    def __init__(self, runtime, directory, identity):
        self.runtime, self.directory, self.identity = runtime, directory, identity
        self.purposes = []

    def __getattr__(self, name):
        return getattr(self.runtime, name)

    def generate(self, **options):
        purpose = str(options["purpose"])
        self.purposes.append(purpose)
        record = self.directory / f"{self.identity}-provider-{len(self.purposes)}.json"
        try:
            result = self.runtime.generate(**options)
        except Exception as error:
            record.write_text(json.dumps({"purpose":purpose,"error_type":type(error).__name__})+"\n")
            raise
        record.write_text(json.dumps({"purpose":purpose,"result":asdict(result)},default=str,indent=2)+"\n")
        return result

    def metadata(self):
        from spg.domain.model_runtime import ModelPurpose
        count = self.purposes.count(str(ModelPurpose.WIC_SEMANTIC))
        return {"qualification_semantic_compile_calls":count,
            "qualification_semantic_repair_count":max(0,count-1),
            "qualification_provider_calls":len(self.purposes)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,required=True)
    p.add_argument('--env-file',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--freeze',type=Path)
    p.add_argument('--workers',type=int,default=2)
    args=p.parse_args()
    if args.evidence.exists(): raise SystemExit('Evidence identity exists; choose a new trial')
    corpus=json.loads(args.corpus.read_text())
    root=Path(__file__).resolve().parents[3]
    identity=source_receipt(root)
    if corpus.get('holdout'):
        if not args.freeze: raise SystemExit('Holdout requires implementation freeze receipt')
        frozen=json.loads(args.freeze.read_text())
        verify_freeze(root,frozen)
        if corpus['generated_at'] <= frozen['frozen_at']: raise SystemExit('Holdout must be generated after freeze')
    args.evidence.mkdir(parents=True)
    (args.evidence/'source-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    env=dict(line.split('=',1) for line in args.env_file.read_text().splitlines() if '=' in line)
    for key,value in env.items():
        if key.startswith('SPG_'): os.environ[key]=value
    now=datetime.now(UTC)
    def evaluate(case):
        identity=uuid5(NAMESPACE_URL,'irk-qualification:'+str(args.evidence)+':'+case['id'])
        interaction=Interaction(id=identity,condition='OPEN',created_by='human:qualification',
            updated_by='human:qualification',created_at=now,updated_at=now)
        records=tuple(InteractionRecord(id=uuid5(identity,str(index)),interaction_id=identity,
            sequence=index+1,actor='HUMAN',source='human:qualification',content=text,
            content_fingerprint=sha256(text.encode()).hexdigest(),created_at=now)
            for index,text in enumerate([*case.get('context',[]),case['text']]))
        observed=ObservedEffect(owner='qualification-context',evidence_references=('repository-intake:qualification-context',),
            facts={'condition':'READY','revision':'a'*40,'tree':'b'*40,'repository_ref':'refs/heads/main',
                'branches':['main','feat_existing'],'source':'https://github.com/acme/irk-fixture.git',
                'repository_identity':'fixture:irk-semantic-context'})
        basis=InteractionInterpretationInput(interaction=interaction,records=records,
            basis_fingerprint=sha256(''.join(r.content_fingerprint for r in records).encode()).hexdigest(),
            observed_reality=(observed,))
        result={'case_id':case['id'],'group':case['group'],'effect_satisfaction':None,
            'effect_observation':'NOT_EXECUTED: compiler-only qualification',
            'input_fingerprint':records[-1].content_fingerprint}
        try:
            capability=bootstrap(Settings()).interaction_capability()
            recorder=QualificationRuntime(capability.runtime,args.evidence,case['id'])
            capability.runtime=recorder
            capability.semantic_capability.runtime=recorder
            capability.conversation_provider.runtime=recorder
            candidate=capability.interpret(basis)
            (args.evidence/(case['id']+'-candidate.json')).write_text(candidate.model_dump_json(indent=2)+'\n')
            metadata = asdict(capability.last_pipeline_evidence) if capability.last_pipeline_evidence else {}
            metadata.update(recorder.metadata())
            ir=IntentRealizationKernel().govern(candidate,basis)
            actions=executable_semantic_actions(ir)
            operations=[i.action.operation for i in actions if not i.action.conditional and not blocking_action_arguments(i.action)
                and not i.requires_human]
            target=[i.action.arguments.get('target_branch').value for i in actions
                if i.action.arguments.get('target_branch')]
            checks={'operations':sorted(operations)==sorted(case['expected_operations']),
                'branch_arguments':case.get('expected_branch') is None or target==[case['expected_branch']],
                'current_production':bool(ir.current_production)==case['current_production']}
            result.update(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
                observed_operations=operations,observed_branches=target,
                governed_ir=ir.model_dump(mode='json'),provider_metadata=metadata,
                false_execution_intent=bool(operations and not case['expected_operations']),
                missed_explicit_action=bool(case['expected_operations'] and not operations),
                inappropriate_human_intervention=bool(case['expected_operations'] and any(i.requires_human for i in ir.items)),
                self_refine_recovered=metadata['qualification_semantic_repair_count']>0)
        except Exception as error:
            evidence=getattr(locals().get('capability'),'last_pipeline_evidence',None)
            if evidence is not None:
                result['provider_metadata']=asdict(evidence)
            if 'recorder' in locals():
                result.setdefault('provider_metadata',{}).update(recorder.metadata())
            result.update(status='FAIL',error_type=type(error).__name__,error_code=str(error)[:600])
        (args.evidence/(case['id']+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ['case_id','status']},ensure_ascii=False),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results=list(executor.map(evaluate,corpus['cases']))
    if corpus.get('holdout'):
        (args.evidence/'source-identity-after.json').write_text(json.dumps(
            verify_freeze(root,frozen),indent=2)+'\n')
    n=len(results)
    report=dict(corpus_version=corpus['corpus_version'],corpus_sha256=sha256(args.corpus.read_bytes()).hexdigest(),
        completed_at=datetime.now(UTC).isoformat(),cases=n,passed=sum(r['status']=='PASS' for r in results),
        semantic_equivalence_accuracy=sum(r['status']=='PASS' for r in results)/n,
        false_execution_intents=sum(r.get('false_execution_intent',False) for r in results),
        missed_explicit_actions=sum(r.get('missed_explicit_action',False) for r in results),
        inappropriate_human_interventions=sum(r.get('inappropriate_human_intervention',False) for r in results),
        self_refine_recovered=sum(r.get('self_refine_recovered',False) for r in results),
        argument_target_cases=sum(bool(c.get('expected_branch')) for c in corpus['cases']),
        action_argument_accuracy=(sum(r.get('checks',{}).get('branch_arguments',False) for r,c in zip(results,corpus['cases']) if c.get('expected_branch')) / max(1,sum(bool(c.get('expected_branch')) for c in corpus['cases']))),
        compilation_failures=sum('error_type' in r for r in results),
        normal_compilations=sum(r.get('provider_metadata',{}).get('qualification_semantic_compile_calls')==1 for r in results),
        semantic_compile_calls=sum(r.get('provider_metadata',{}).get('qualification_semantic_compile_calls',0) for r in results),
        effect_satisfaction=None,effect_qualification='Separate live owner receipts required',
        failures=[r['case_id'] for r in results if r['status']!='PASS'])
    (args.evidence/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__': main()
