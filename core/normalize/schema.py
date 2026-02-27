from dataclasses import dataclass
from typing import List, Optional

try:
    from pydantic import BaseModel, ValidationError
    try:
        from pydantic import ConfigDict
        _HAS_PYDANTIC_V2 = True
    except ImportError:
        ConfigDict = None
        _HAS_PYDANTIC_V2 = False
except ImportError as exc:
    raise ImportError("pydantic is required. Install with: pip install pydantic") from exc


class _ExtraBase(BaseModel):
    if _HAS_PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:
        class Config:
            extra = "allow"


class _Center(_ExtraBase):
    x: Optional[float] = None
    y: Optional[float] = None


class _CharCaption(_ExtraBase):
    char_caption: Optional[str] = None
    caption: Optional[str] = None
    idx: Optional[int] = None
    centers: Optional[List[_Center]] = None


class _Caption(_ExtraBase):
    base_caption: Optional[str] = None
    char_captions: Optional[List[_CharCaption]] = None


class _V4Prompt(_ExtraBase):
    caption: Optional[_Caption] = None


class _NovelAIRaw(_ExtraBase):
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    uc: Optional[str] = None
    v4_prompt: Optional[_V4Prompt] = None
    v4_negative_prompt: Optional[_V4Prompt] = None
    char_prompts: Optional[List[_CharCaption]] = None
    char_negative_prompts: Optional[List[_CharCaption]] = None
    version: Optional[int] = None


class _NovelAIMeta(_ExtraBase):
    vendor: Optional[str] = None
    normalized: Optional[_NovelAIRaw] = None
    raw: Optional[_NovelAIRaw] = None


@dataclass
class ParsedCharPrompt:
    idx: int
    caption: str


@dataclass
class ParsedNovelAI:
    vendor: str
    source: str
    prompt: str
    negative_prompt: str
    char_prompts: List[ParsedCharPrompt]
    char_negative_prompts: List[ParsedCharPrompt]


def _parse_model(model, data):
    try:
        if hasattr(model, "model_validate"):
            return model.model_validate(data)
        return model.parse_obj(data)
    except ValidationError:
        return None


def _get_base_caption(v4_prompt):
    if not v4_prompt or not v4_prompt.caption:
        return ""
    return v4_prompt.caption.base_caption or ""


def _collect_char_prompts(items):
    results = []
    if not items:
        return results
    for idx, item in enumerate(items):
        if not item:
            continue
        caption = item.char_caption or item.caption or ""
        if not caption:
            continue
        item_idx = item.idx if item.idx is not None else idx
        results.append(ParsedCharPrompt(idx=item_idx, caption=caption))
    return results


def _get_v4_char_captions(v4_prompt):
    if not v4_prompt or not v4_prompt.caption:
        return None
    return v4_prompt.caption.char_captions


def parse_novelai_payload(data):
    source = "input"
    vendor = None
    src = data

    if isinstance(data, dict):
        vendor = data.get("vendor")
        if isinstance(data.get("normalized"), dict):
            src = data.get("normalized")
            source = "normalized"
        elif isinstance(data.get("raw"), dict):
            src = data.get("raw")
            source = "raw"

    raw_model = _parse_model(_NovelAIRaw, src)
    if raw_model is None:
        raw_model = _NovelAIRaw()

    prompt = raw_model.prompt or _get_base_caption(raw_model.v4_prompt)
    negative = raw_model.negative_prompt or raw_model.uc or _get_base_caption(
        raw_model.v4_negative_prompt
    )

    char_prompts = _collect_char_prompts(raw_model.char_prompts)
    if not char_prompts:
        char_prompts = _collect_char_prompts(_get_v4_char_captions(raw_model.v4_prompt))

    char_negative_prompts = _collect_char_prompts(raw_model.char_negative_prompts)
    if not char_negative_prompts:
        char_negative_prompts = _collect_char_prompts(
            _get_v4_char_captions(raw_model.v4_negative_prompt)
        )

    return ParsedNovelAI(
        vendor=vendor or "novelai",
        source=source,
        prompt=prompt or "",
        negative_prompt=negative or "",
        char_prompts=char_prompts,
        char_negative_prompts=char_negative_prompts,
    )
