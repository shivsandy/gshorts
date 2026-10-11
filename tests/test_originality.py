import pytest
from shorts_factory.originality import OriginalityError, script_fingerprint, similarity, validate_originality

def test_normalized_fingerprint_is_stable():
    assert script_fingerprint("Hello,  WORLD!") == script_fingerprint("hello world")

def test_similarity_detects_near_duplicate():
    a="The Moon is moving away from Earth by a few centimeters each year because of tidal interactions."
    b="Because of tidal interactions, the Moon moves away from Earth by a few centimeters each year."
    assert similarity(a,b)>0.5

def test_duplicate_topic_rejected_even_if_copy_reworded():
    script={"topic_id":"moon","narration":"A different concise narration.","script_fingerprint":"new"}
    history=[{"topic_id":"moon","script_text":"A prior but different explanation."}]
    with pytest.raises(OriginalityError): validate_originality(script,history)

def test_exact_and_near_duplicate_scripts_rejected():
    text="The Moon is moving away from Earth by a few centimeters each year because of tidal interactions and ocean tides."
    script={"topic_id":"new","narration":text,"script_fingerprint":script_fingerprint(text)}
    with pytest.raises(OriginalityError): validate_originality(script,[{"topic_id":"old","script_text":text,"script_fingerprint":script_fingerprint(text)}])
    close={"topic_id":"other","narration":"The Moon moves away from Earth a few centimeters every year due to tidal interactions and ocean tides.","script_fingerprint":"different"}
    with pytest.raises(OriginalityError): validate_originality(close,[{"topic_id":"older","script_text":text,"script_fingerprint":"old"}],threshold=0.4)
