from pathlib import Path
import pytest
from shorts_factory.fact_checker import validate_topic_sources
from shorts_factory.topic_engine import load_topics, select_topic, TopicError

ROOT=Path(__file__).resolve().parents[1]

def test_topic_bank_is_curated_unique_and_sourced():
    topics=load_topics(ROOT/"config/topics.json")
    assert len(topics)>=30
    assert len({t["id"] for t in topics})==len(topics)
    for topic in topics:
        sources=validate_topic_sources(topic)
        assert sources
        assert all(b["text"].strip() and b["visual_title"].strip() for b in topic["beats"])

def test_niche_filter_and_used_topic_exclusion():
    topics=load_topics(ROOT/"config/topics.json")
    one=select_topic(topics,"science",set(),"2026-10-11")
    assert one["category"]=="science"
    remaining=select_topic(topics,"science",{one["id"]},"2026-10-11")
    assert remaining["id"]!=one["id"]

def test_topic_bank_exhaustion_fails_closed():
    topics=[{"id":"x","category":"science","title":"x","beats":[{"text":"t","visual_title":"v"}]*5,"claims":[],"source_urls":[]}]
    try:
        select_topic(topics,"science",{"x"},"2026-10-11")
    except TopicError as exc:
        assert "No unused topics remain" in str(exc)
    else:
        raise AssertionError("Exhausted topic bank should not recycle a topic")

def test_pipeline_retries_a_rejected_topic_with_a_distinct_candidate(monkeypatch):
    from shorts_factory import main as main_module
    topics=load_topics(ROOT/"config/topics.json")
    rejected, accepted=topics[0],topics[1]
    candidates=iter([rejected,accepted])
    monkeypatch.setattr(main_module,"select_topic",lambda *args,**kwargs:next(candidates))
    topic,script,sources=main_module.choose_eligible_script(topics,niche="all",used_topic_ids=set(),run_key="test-run",
        history=[{"topic_id":rejected["id"],"script_text":"previous script"}],max_attempts=2)
    assert topic["id"]==accepted["id"]
    assert script["topic_id"]==accepted["id"]
    assert sources

def test_pipeline_has_a_bounded_retry_limit(monkeypatch):
    from shorts_factory import main as main_module
    from shorts_factory.main import PipelineError
    topics=load_topics(ROOT/"config/topics.json")
    a,b=topics[0],topics[1]
    candidates=iter([a,b])
    monkeypatch.setattr(main_module,"select_topic",lambda *args,**kwargs:next(candidates))
    with pytest.raises(PipelineError,match="after at most 2 attempts"):
        main_module.choose_eligible_script(topics,niche="all",used_topic_ids=set(),run_key="test-run",
            history=[{"topic_id":a["id"]},{"topic_id":b["id"]}],max_attempts=2)
