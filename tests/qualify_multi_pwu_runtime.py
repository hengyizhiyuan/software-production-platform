"""Drive bounded dogfood through the normal Product intent/API surface.

No Candidate acceptance, database reset or synthetic execution completion.
State is saved before/after each submission so interrupted runs remain auditable.
"""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

PRODUCT = '5bf5e153-0367-43a4-98ef-91b69a188ef3'
REQUESTS = {
    'A': '针对已有的「恒溢启源官网 Dogfood」产品，新开一个独立的软件改动事项：分别新增 faq.html 常见问题页面和 contact.html 联系我们页面，这是两个独立页面，均沿用现有官网风格；每页包含中文标题、简短说明与返回首页的链接。只新增这两个文件，不修改首页或其他文件；验证两页存在、内容完整、链接目标和精确改动范围。完成后形成候选成果，等待我验收。',
    'B': '针对已有的「恒溢启源官网 Dogfood」产品，新开一个独立的软件改动事项：新增共享的 team.html 团队介绍页面，再新增 team-directory.html 团队目录页面；团队目录依赖前一步已验证的团队页，必须链接到 team.html 和 index.html。只新增这两个文件，保持已有官网结构；验证精确范围、页面内容与依赖链接，不修改其他文件。完成后形成候选成果，等待我验收。',
    'C': '针对已有的「恒溢启源官网 Dogfood」产品，新开一个独立的软件改动事项：独立新增 services.html 服务介绍页和 news.html 公司新闻页，两页分别包含中文标题、说明和返回 index.html 的链接；两份成果完成各自验证后，整合并再次验证两页作为同一事项的最终成果。只新增 services.html 和 news.html，不修改其他文件。完成后形成候选成果，等待我验收。',
    'D': '针对已有的「恒溢启源官网 Dogfood」产品，新开一个独立的软件改动事项：在 index.html 中补充一个标题为「关于恒溢启源」且链接到已有 about.html 的导航入口，并新增 tests/navigation.test.js，以 Node 内置 test/assert 和文件读取验证该入口标题及链接。只修改 index.html 和新增 tests/navigation.test.js，不修改其他文件；两个目标都必须有明确改动和独立验证，不能产生空的生产单元。完成后形成候选成果，等待我验收。',
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['submit', 'inspect'])
    parser.add_argument('scenario', choices=list(REQUESTS))
    parser.add_argument('--url', default='http://8.130.172.58:8080')
    parser.add_argument('--token-file', required=True)
    parser.add_argument('--state', required=True)
    args = parser.parse_args()
    path = Path(args.state)
    state = json.loads(path.read_text()) if path.exists() else {}
    token = Path(args.token_file).read_text().strip()
    def call(route, body=None):
        request = Request(args.url+route, data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    if args.mode == 'submit':
        assert args.scenario not in state, 'Existing submission must be reconciled, not repeated'
        state[args.scenario] = {'request': REQUESTS[args.scenario], 'submission':'STARTED'}
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        receipt = call('/api/experience/intent', {'text':REQUESTS[args.scenario], 'selected_product_id':PRODUCT})
        state[args.scenario].update(receipt=receipt, submission='RECEIVED')
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print(json.dumps({key:receipt.get(key) for key in ('kind','interaction_id','turn_id')}, ensure_ascii=False))
    else:
        receipt = state[args.scenario]['receipt']
        iid, tid = receipt['interaction_id'], receipt['turn_id']
        realization = call(f'/api/interactions/{iid}/turns/{tid}/realization')
        state[args.scenario]['realization'] = realization
        interaction = call('/api/interactions/'+iid)
        state[args.scenario]['interaction'] = interaction
        print('interaction',json.dumps({key:interaction.get(key) for key in ('governed_work_id','response_text','current_turn_id','assessment_id','response_contract')},ensure_ascii=False))
        print('obligations', json.dumps(realization.get('obligations'), ensure_ascii=False))
        work = interaction.get('governed_work_id')
        if work:
            projection = call('/api/works/'+work)
            state[args.scenario]['work'] = projection
            print('work',json.dumps({key:projection.get(key) for key in ('work_id','status','current_production_step','what_happens_next','production_plan_runtime')}, ensure_ascii=False))
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
