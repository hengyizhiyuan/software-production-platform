"""Generate unseen wording only after implementation freeze; oracles precede wording.

The generator sees an ontology and declared intentions, never the developer
corpus, implementation, prompts or failed examples. Its output cannot change an
oracle. Preserve the original provider response and identity beside the corpus.
"""
import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from benchmarks.intent_realization.runtime.evidence import verify_freeze
from spg.application.bootstrap import bootstrap
from spg.config import Settings
from spg.domain.model_runtime import ModelPurpose


class Wording(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str


class WordingBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cases: list[Wording]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze",type=Path,required=True)
    parser.add_argument("--env-file",type=Path,required=True)
    parser.add_argument("--directory",type=Path,required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    frozen = json.loads(args.freeze.read_text())
    verify_freeze(root,frozen)
    if args.directory.exists():
        raise SystemExit("Holdout identity already exists; never overwrite unseen generation")
    args.directory.mkdir(parents=True)
    for line in args.env_file.read_text().splitlines():
        if "=" in line:
            key,value = line.split("=",1)
            if key.startswith("SPG_"):
                os.environ[key] = value
    specifications = []
    def declare(group,meaning,operations=(),*,branch=None,repository_source=None,production=False,context=(),
            required_kinds=(), action_intents=()):
        identity = "HO-%03d" % (len(specifications)+1)
        specifications.append(dict(id=identity,group=group,meaning=meaning,
            expected_operations=list(operations),expected_branch=branch,
            expected_repository_source=repository_source,
            current_production=production,context=list(context),
            required_kinds=list(required_kinds),action_intents=list(action_intents)))
    source = "http://qualified-git-fault:8080/trials/holdout-" + uuid4().hex[:10] + "/business-app.git"
    # Each target is fixed before generation. No generated prose is used as code.
    for index in range(4):
        branch = "feat_holdout_"+uuid4().hex[:10]
        declare("branch_both","Explicitly create AND switch to literal branch "+branch,
            ["CREATE_AND_SWITCH_BRANCH"],branch=branch)
        declare("branch_create_only","Explicitly create literal branch "+branch+"; stay on current branch, no switch",
            ["CREATE_BRANCH"],branch=branch)
        declare("branch_switch_only","Switch to already existing feat_existing; do not create any branch",
            ["SWITCH_BRANCH"],branch="feat_existing")
        declare("hard_negative","Discuss whether a future branch "+branch+" might be useful; explicitly do not execute now")
        declare("search_negation","Withdraw previous GitHub search and forbid external retrieval now; ask only for a conceptual explanation",
            context=("We might search GitHub for validation libraries later.",))
        declare("acquisition_future_goal","Acquire literal repository "+source+" now; a future unspecified change remains unadmitted",
            ["ACQUIRE_REPOSITORY"],repository_source=source)
        declare("production","Request a small reviewable customer data collection form now in the current repository; no delivery permission",
            production=True)
        declare("contextual_branch","Current explicit consent to create and switch to the branch named in the previous Human record; retain that literal argument",
            ["CREATE_AND_SWITCH_BRANCH"],branch=branch,context=("The branch name I intend to use is "+branch+".",))
        declare("conditional_negative","Branch "+branch+" may be created only after future review approval which has not happened; no current action")
        declare("delivery_negative","Keep current Candidate for review; explicitly forbid pushing or publishing now")
    declare("search_positive", "Search GitHub now for public Python input validation libraries and return source-backed findings",
        ["SEARCH_GITHUB"], action_intents=("SEARCH_GITHUB",))
    declare("acceptance_without_delivery", "Accept the already reviewed exact Candidate, while forbidding delivery or push",
        action_intents=("ACCEPT_CANDIDATE",),
        context=("The exact Candidate has been independently reviewed and is ready for my decision.",))
    declare("explicit_delivery_authorization", "Explicitly authorize delivery of the already accepted exact Candidate now",
        action_intents=("AUTHORIZE_DELIVERY",),
        context=("The exact Candidate was accepted; delivery still awaits my separate authorization.",))
    declare("production_correction", "Correct the current production goal: keep only a customer entry form and remove the earlier dashboard request",
        production=True, required_kinds=("CORRECTION",),
        context=("Build a reviewable dashboard with customer entry in this current repository.",))
    declare("work_scope_answer", "Answer the pending current Work scope question: search only users by name and email, excluding customers and orders",
        required_kinds=("CONSTRAINT",),
        context=("The current Work needs search, and its owner asks which business domain and fields it must cover.",))
    declare("mixed_action_constraint", "Create a literal local branch feat_holdout_mixed, stay on the current branch, and constrain the current Work to user-facing UI only",
        ["CREATE_BRANCH"], branch="feat_holdout_mixed", required_kinds=("CONSTRAINT",),
        action_intents=("CREATE_BRANCH",))
    declare("colloquial_punctuation", "In colloquial mixed Chinese and English with unusual punctuation, ask to switch to existing feat_existing only",
        ["SWITCH_BRANCH"], branch="feat_existing", action_intents=("SWITCH_BRANCH",))
    (args.directory/"declared-oracles.json").write_text(json.dumps(specifications,ensure_ascii=False,indent=2)+"\n")
    runtime = bootstrap(Settings()).interaction_capability().runtime
    result = runtime.generate(purpose=ModelPurpose.WIC_SEMANTIC,
        instructions=("Generate unseen natural Human developer messages for the declared intentions. "
            "Return each id exactly once. Change wording, never meaning or literal targets. "
            "Use diverse colloquial Chinese, mixed Chinese/English, punctuation variation and contextual follow-ups. "
            "Do not write implementation hints, source filenames, command syntax, or additional operations. "
            "For cases with context generate only the latest message; prior context is fixed. "
            "Preserve separate acceptance and delivery authority, typed Work constraints and every mixed clause. "
            "For hard negatives make the absence of current execution clear. "
            "Return exactly one data object with only cases: [{id, text}, ...]. "
            "Do not include JSON Schema definitions, $defs, properties or any schema metadata."),
        input_text=json.dumps(specifications,ensure_ascii=False),
        output_schema=WordingBatch.model_json_schema())
    (args.directory/"original-provider-output.json").write_text(result.output_text)
    metadata = asdict(result)
    metadata.pop("output_text")
    (args.directory/"provider-receipt.json").write_text(json.dumps(metadata,default=str,indent=2)+"\n")
    wording = WordingBatch.model_validate_json(result.output_text)
    by_id = {case.id:case.text for case in wording.cases}
    if len(by_id) != len(wording.cases) or set(by_id) != {case["id"] for case in specifications}:
        raise SystemExit("Holdout generation failed identity validation; preserve failed response and generate a new batch")
    verify_freeze(root,frozen)
    corpus = dict(corpus_version="irk-unseen-holdout-v1",holdout=True,
        generated_at=datetime.now(UTC).isoformat(),freeze_source_fingerprint=frozen["source_fingerprint"],
        generation_method="Fixed independent intentions; generated wording only; no implementation/developer corpus supplied",
        cases=[{**{key:value for key,value in case.items() if key != "meaning"},"text":by_id[case["id"]]}
            for case in specifications])
    (args.directory/"corpus.json").write_text(json.dumps(corpus,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"cases":len(specifications),"generated_after_freeze":True,"directory":str(args.directory)}))


if __name__ == "__main__":
    main()
