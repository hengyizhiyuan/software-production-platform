from types import SimpleNamespace
from uuid import uuid4
import pytest
from spg.application.intent_realization import IntentRealizationKernel,IntentRealizationViolation
from spg.domain.intent_realization import ObservedEffect,SemanticArgument,SemanticClause,SemanticItem,SemanticKind as K,SemanticOrigin as Origin,SemanticProvenance,TurnSemanticCandidate


def basis_and_items():
 record=SimpleNamespace(id=uuid4(),actor='HUMAN',content='Explain the current version.')
 human=SemanticProvenance(origin=Origin.HUMAN_EXPLICIT,source_record_id=record.id,source_text=record.content)
 witness=SemanticProvenance(origin=Origin.REPOSITORY_OBSERVED,evidence_reference='owner:repository')
 question=SemanticItem(item_id='question',kind=K.QUESTION,statement='Explain the actual version',provenance=(human,),confidence=1)
 fact=SemanticItem(item_id='observed',kind=K.FACT,statement='Supplemental current repository fact',provenance=(witness,),confidence=1,observed_facts={'revision':SemanticArgument(value='a'*40,provenance=witness)})
 basis=SimpleNamespace(records=(record,),interaction=SimpleNamespace(id=uuid4()),basis_fingerprint='a'*64,observed_reality=(ObservedEffect(owner='repository',evidence_references=('owner:repository',),facts={'revision':'a'*40}),))
 return basis,record,question,fact,human,witness


def govern(basis,record,items,*,text=None):
 candidate=TurnSemanticCandidate(items=items,clauses=(SemanticClause(clause_id='human',source_record_id=record.id,source_text=text or record.content,semantic_item_ids=('question',)),))
 return IntentRealizationKernel().govern(SimpleNamespace(semantic_intent=candidate,provider_identity='declared:semantic-compiler'),basis)


def test_actual_owner_fact_does_not_need_fabricated_human_clause():
 basis,record,question,fact,_,_=basis_and_items()
 ir=govern(basis,record,(question,fact))
 assert len(ir.items)==2 and ir.items[1].observed_facts['revision'].value=='a'*40
 obligations=IntentRealizationKernel().obligations(ir,uuid4())
 assert len(obligations)==1 and obligations[0].plane.value=='INTERACTION'
 assert obligations[0].semantic_item_id=='question'


@pytest.mark.parametrize('invalid', ['human_fact','owner_question','no_exact_claim'])
def test_supplemental_exception_cannot_hide_unmapped_human_meaning_or_non_fact(invalid):
 basis,record,question,fact,human,_=basis_and_items()
 changes={'human_fact':{'provenance':(human,)},'owner_question':{'kind':K.QUESTION},'no_exact_claim':{'observed_facts':{}}}[invalid]
 with pytest.raises(IntentRealizationViolation,match='PRIMARY_INTENT_CLAUSE_LOST'):
  govern(basis,record,(question,fact.model_copy(update=changes)))


def test_supplemental_fact_still_rejects_fabricated_owner_value():
 basis,record,question,fact,_,witness=basis_and_items()
 fact=fact.model_copy(update={'observed_facts':{'revision':SemanticArgument(value='invented',provenance=witness)}})
 with pytest.raises(IntentRealizationViolation,match='fact claim differs'):
  govern(basis,record,(question,fact))


def test_supplemental_fact_does_not_cover_missing_human_punctuation():
 basis,record,question,fact,_,_=basis_and_items()
 with pytest.raises(IntentRealizationViolation,match='PRIMARY_INTENT_CLAUSE_LOST'):
  govern(basis,record,(question,fact),text=record.content[:-1])
