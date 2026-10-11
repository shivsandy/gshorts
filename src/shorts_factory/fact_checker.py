from __future__ import annotations
from urllib.parse import urlparse
from typing import Any
TRUSTED_DOMAINS={"nasa.gov","usgs.gov","noaa.gov","weather.gov","nist.gov","fda.gov","energy.gov","britannica.com","ocean.si.edu","smithsonianmag.com","rmg.co.uk","apa.org","nih.gov","pubmed.ncbi.nlm.nih.gov","ncbi.nlm.nih.gov","fs.usda.gov","usda.gov","amnh.org","nationalgeographic.org"}
class FactCheckError(RuntimeError): pass

def _trusted(url: str) -> bool:
    p=urlparse(url)
    if p.scheme!="https" or not p.hostname: return False
    host=p.hostname.lower().rstrip(".")
    return any(host==d or host.endswith("."+d) for d in TRUSTED_DOMAINS)

def validate_topic_sources(topic: dict[str,Any]) -> list[str]:
    """Validate sourced claim metadata/domain allowlist; this is not automated proof of factual truth."""
    claims=topic.get("claims",[]); sources=topic.get("source_urls",[])
    if not claims or not sources: raise FactCheckError(f"Topic {topic.get('id')} has no sourced claims.")
    urls=[]
    for claim in claims:
        if len(str(claim.get("statement"," ")).strip())<20: raise FactCheckError(f"Topic {topic.get('id')} has a vague claim.")
        url=str(claim.get("source_url","")).strip()
        if not _trusted(url): raise FactCheckError(f"Topic {topic.get('id')} source is not allowlisted HTTPS: {url!r}")
        urls.append(url)
    if any(not _trusted(x) for x in sources): raise FactCheckError(f"Topic {topic.get('id')} has a non-allowlisted source URL.")
    if not set(urls).issubset(set(sources)): raise FactCheckError(f"Topic {topic.get('id')} source_urls omits a claim source.")
    return sorted(set(sources))
