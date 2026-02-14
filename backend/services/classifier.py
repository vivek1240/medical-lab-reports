import json
import re
from typing import Iterable

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.biomarker import BiomarkerReference


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _load_aliases(raw_aliases: str | None) -> list[str]:
    if not raw_aliases:
        return []
    try:
        parsed = json.loads(raw_aliases)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        return []
    return []


def _save_alias_if_new(db: Session, biomarker: BiomarkerReference, alias: str) -> None:
    aliases = _load_aliases(biomarker.common_aliases)
    alias_norm = _normalize(alias)
    if not alias_norm:
        return
    if any(_normalize(existing) == alias_norm for existing in aliases):
        return
    aliases.append(alias)
    biomarker.common_aliases = json.dumps(aliases)
    db.add(biomarker)


def _fuzzy_match_biomarker(db: Session, test_name: str, threshold: int) -> tuple[int | None, int]:
    name_norm = _normalize(test_name)
    best_score = -1
    best_id = None

    biomarkers = db.query(BiomarkerReference).all()
    for biomarker in biomarkers:
        aliases = [biomarker.standard_name]
        aliases.extend(_load_aliases(biomarker.common_aliases))

        for alias in aliases:
            score = fuzz.ratio(name_norm, _normalize(alias))
            if score > best_score:
                best_score = score
                best_id = biomarker.id

    if best_score >= threshold:
        return best_id, best_score
    return None, best_score


def _extract_json_obj(raw_text: str) -> dict | None:
    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _llm_match_biomarker(db: Session, test_name: str) -> int | None:
    if not settings.classifier_enable_llm_fallback or not settings.openai_api_key:
        return None
    try:
        from llama_index.llms.openai import OpenAI
    except ImportError:
        return None

    biomarkers = db.query(BiomarkerReference).all()
    catalog = [{"id": b.id, "standard_name": b.standard_name, "category": b.category} for b in biomarkers]
    llm = OpenAI(model="gpt-4o-mini", api_key=settings.openai_api_key, temperature=0.0)
    prompt = f"""
You map raw lab test names to a canonical biomarker list.
Return STRICT JSON only with schema:
{{"match_id": <int|null>, "confidence": <0.0-1.0>, "reason": "<short reason>"}}

Rules:
- If uncertain, return match_id = null.
- confidence should be high only for clear synonyms.

Raw test name: {test_name}
Biomarker catalog: {json.dumps(catalog)}
"""
    response = llm.complete(prompt)
    payload = _extract_json_obj(getattr(response, "text", str(response)))
    if not payload:
        return None
    match_id = payload.get("match_id")
    confidence = payload.get("confidence")
    if not isinstance(match_id, int):
        return None
    if not isinstance(confidence, (float, int)) or float(confidence) < 0.8:
        return None

    biomarker = db.query(BiomarkerReference).filter(BiomarkerReference.id == match_id).first()
    if not biomarker:
        return None
    _save_alias_if_new(db, biomarker, test_name)
    return match_id


def classify_test_name(db: Session, test_name: str, threshold: int | None = None) -> int | None:
    score_threshold = threshold if threshold is not None else settings.classifier_fuzzy_threshold
    match_id, _ = _fuzzy_match_biomarker(db, test_name, score_threshold)
    if match_id is not None:
        return match_id

    llm_match = _llm_match_biomarker(db, test_name)
    if llm_match is not None:
        return llm_match
    return None


def classify_many(db: Session, test_names: Iterable[str]) -> dict[str, int | None]:
    return {name: classify_test_name(db, name) for name in test_names}
