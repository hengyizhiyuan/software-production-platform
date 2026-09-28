"""Authenticated preparatory journeys via the public /app Interaction API.

No tester Git, Work admission, repository repair, source write, Preview start or
remote delivery. Each immutable trial retains every public projection and receipt.
Existing production Golden journeys qualify production/governance boundaries.
"""
import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import time
if __package__:
 from .journey import ProductClient
else:
 from journey import ProductClient

PUBLIC = 'https://github.com/hengyizhiyuan/software-production-platform.git'
INTENTS = {
 'GC-LC-01': [f'我有个GitHub仓库：{PUBLIC}，把它clone下来，我要改个需求',
              '切一个 feat_test 分支', '我现在在哪个分支？'],
 'GC-LC-02': [f'把这个仓库 {PUBLIC} clone下来，然后切 feat_test。'],
 'GC-LC-03': [f'先帮我看看这个仓库 {PUBLIC} 使用什么框架，我再决定改什么。'],
 'GC-LC-04': [f'这个仓库 {PUBLIC} 以后可能会用到。'],
 'GC-LC-13': ['clone https://github.com/example/one.git https://github.com/example/two.git'],
}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--case', choices=INTENTS, required=True)
 p.add_argument('--trial', type=int, required=True)
 p.add_argument('--base', required=True)
 p.add_argument('--env-file', type=Path, required=True)
 p.add_argument('--evidence-root', type=Path, required=True)
 p.add_argument('--timeout', type=int, default=420)
 args=p.parse_args()
 directory=args.evidence_root/args.case/f'trial-{args.trial}'
 if directory.exists(): raise SystemExit('Trial identity is immutable; choose a new trial')
 directory.mkdir(parents=True)
 env=dict(line.split('=',1) for line in args.env_file.read_text().splitlines() if '=' in line)
 client=ProductClient(args.base,env['SPG_OPERATOR_TOKEN'])
 def save(name,value):
  (directory/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 save('runtime-activation.json',client.request('/api/runtime-activation'))
 creation=client.request('/api/interactions',{'human_identity':'human:lifecycle-operator'})
 save('creation.json',creation)
 identity=creation['interaction_id']
 if args.case=='GC-LC-02':
  corpus=json.loads((Path(__file__).parents[1]/'interaction-action-equivalence-v1.json').read_text(encoding='utf-8'))
  expected_operations=corpus['branch_positive_expected_operations']
  if len(expected_operations)!=len(corpus['branch_positive']):
   raise ValueError('Every positive branch variant needs a predeclared operation')
  variants=[template.format(branch=f'feat_semantic_{args.trial}_{index}')
            for index,template in enumerate(corpus['branch_positive'])]
  negatives=[template.format(branch=f'feat_absent_{args.trial}')
             for template in corpus['branch_negative']]
  INTENTS[args.case]=[f'把这个仓库 {PUBLIC} clone下来。', *variants,
    '分支创建好了吗', *negatives]
  save('semantic-equivalence-inputs.json',{'positives':variants,'expected_operations':expected_operations,'negatives':negatives})
 save('journey.json',{'case':args.case,'trial':args.trial,'interaction_id':identity,
  'human_inputs':INTENTS[args.case],'tester_git':False,'manual_rescue_actions':[],
  'source_modification':False,'human_acceptance':'PENDING'})
 states=[]
 for index,content in enumerate(INTENTS[args.case]):
  receipt=client.request(f'/api/interactions/{identity}/turns',{'content':content,
    'human_identity':'human:lifecycle-operator'})
  save(f'submission-{index+1}.json',receipt)
  deadline=time.monotonic()+args.timeout
  previous=None
  while time.monotonic()<deadline:
   state=client.request(f'/api/interactions/{identity}')
   turns=state.get('turns',[])
   if state!=previous:
    stamp=datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')
    save(f'projection-{index+1}-{stamp}.json',state)
    previous=state
   if turns and turns[-1]['status'] in {'COMPLETED','FAILED'}: break
   time.sleep(1)
  if turns:
   save(f'realization-{index+1}.json',client.request(f"/api/interactions/{identity}/turns/{turns[-1]['turn_id']}/realization"))
  states.append(state)
  if not turns or turns[-1]['status']!='COMPLETED': break
 save('latest.json',states[-1])
 no_work=all(s.get('governed_work_id') is None for s in states)
 completed=len(states)==len(INTENTS[args.case]) and all(s['turns'][-1]['status']=='COMPLETED' for s in states)
 observation=states[-1].get('repository_observation')
 checks={'no_production_work':no_work,'all_turns_completed':completed}
 if args.case in {'GC-LC-01','GC-LC-02','GC-LC-03'}:
  checks.update(repository_ready=bool(observation and observation['condition']=='READY'),
   exact_source=bool(observation and observation['source']==PUBLIC),
   exact_revision_tree=bool(observation and len(observation['revision'])==40 and len(observation['tree'])==40),
   product_continuity=bool(observation and observation.get('product_id')))
  if args.case!='GC-LC-03':
   expected_branch=f'feat_semantic_{args.trial}_7' if args.case=='GC-LC-02' else 'feat_test'
   checks['local_branch']=bool(observation and observation['repository_ref']==f'refs/heads/{expected_branch}')
  if args.case=='GC-LC-02':
   checks['positive_semantic_equivalence']=all(
    any(a['operation']==expected_operations[i] and a['speech_act']=='EXPLICIT_REQUEST'
        and a['target_branch']==f'feat_semantic_{args.trial}_{i}'
        for a in (state.get('latest_assessment') or {}).get('action_candidates', []))
    and (state.get('repository_observation') or {}).get('repository_ref')==f'refs/heads/feat_semantic_{args.trial}_{i if expected_operations[i]=="CREATE_AND_SWITCH_BRANCH" else i-1}'
    for i,state in enumerate(states[1:9])) and len(states)>=9
   last=states[8]['repository_observation'] if len(states)>=9 else {}
   checks['negative_no_git_effect']=all(
    state['repository_observation']['intake_request_id']==last.get('intake_request_id')
    and state['repository_observation']['repository_ref']==last.get('repository_ref')
    for state in states[10:]) and len(states)==len(INTENTS[args.case])
   checks['completion_query_from_reality']=len(states)>9 and expected_branch in states[9]['conversation_messages'][-1]['content']
  if args.case=='GC-LC-01':
   first=states[0].get('repository_observation') or {}
   checks['initial_main']=first.get('repository_ref')=='refs/heads/main'
   checks['unchanged_source']=bool(observation and (first.get('revision'),first.get('tree'))==(observation['revision'],observation['tree']))
   checks['observed_branch_answer']='feat_test' in states[-1]['conversation_messages'][-1]['content']
  if args.case=='GC-LC-03':
   answer=states[-1]['conversation_messages'][-1]['content']
   checks['pinned_manifest_evidence']=bool(observation and observation['revision'] in answer and 'SHA256' in answer and 'pyproject.toml' in answer)
 else:
  checks['no_repository_action']=observation is None
  if args.case=='GC-LC-13':
   semantic=(states[-1].get('latest_assessment') or {}).get('semantic_ir') or {}
   questions=semantic.get('questions') or []
   unresolved_actions=[item for item in semantic.get('items',[])
    if item.get('kind')=='OPERATIONAL_ACTION' and item.get('requires_human')
    and 'repository_source' in (item.get('action') or {}).get('unresolved_arguments',[])]
   checks['one_target_clarification']=bool(unresolved_actions
    and any(question.get('blocks_current_step') and question.get('requires_human')
      for question in questions)
    and states[-1]['conversation_messages'][-1]['content'].strip())
 result={'case':args.case,'trial':args.trial,'status':'PASS' if all(checks.values()) else 'FAIL',
   'checks':checks,'interaction_id':identity,'human_acceptance':'PENDING'}
 save('result.json',result)
 print(json.dumps(result,ensure_ascii=False),flush=True)
 if result['status']!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
