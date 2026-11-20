"""Input guardrails: cheap, deterministic checks that run BEFORE retrieval or any LLM call."""
import re

REFUSAL = ("I can only answer questions about Cavli cellular IoT modules from approved public sources. "
           "I can't process code, scripts or instructions pasted into the chat. Please ask a product question, "
           "for example about a module's bands, speed, features or which module fits a requirement.")

_RULES = [
    ("code_block", re.compile(r"```|<\s*(script|iframe|img|svg|object|embed)\b|javascript\s*:|on\w+\s*=", re.I)),
    ("sql", re.compile(r"\b(select\s+.+\s+from|insert\s+into|drop\s+table|union\s+select|delete\s+from)\b", re.I)),
    ("shell", re.compile(r"(\brm\s+-rf\b|\bsudo\s|\bchmod\s|curl\s+[^|]*\|\s*(ba)?sh|\bwget\s+http|;\s*(ls|cat|rm)\b)", re.I)),
    ("code_syntax", re.compile(r"(\bdef\s+\w+\s*\(|\bimport\s+\w+\s*$|\bconsole\.log\b|\bfunction\s*\w*\s*\(|=>\s*\{|\bprint\s*\(|#include\s*<)", re.I | re.M)),
    ("prompt_injection", re.compile(
        r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+)?(previous|above|prior|earlier|your)\s+(instructions|rules|prompt)"
        r"|(reveal|show|print|repeat|leak)\s+.{0,30}(system\s+prompt|instructions|api[\s_-]?key|secret|password|credentials)"
        r"|\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be|developer\s+mode|jailbreak|DAN\b)", re.I)),
]


def check(question: str):
    """Return None if OK, else the rule name that blocked it."""
    for name, rx in _RULES:
        if rx.search(question):
            return name
    # long base64/hex-like blobs are not product questions
    if re.search(r"[A-Za-z0-9+/=]{60,}", question):
        return "encoded_blob"
    return None


_CHIT = re.compile(r"^\s*(hi|hello|hey|good\s+(morning|afternoon|evening)|thanks?( you)?|thank you( so much)?|ok(ay)?|bye|goodbye)\W*$", re.I)
GREETING = ("Hi! I can answer questions about Cavli cellular IoT modules (C16QS, CQM220, C10QM, CQS290, CQ16) using "
            "approved public sources, and help you find a module for your requirements. What would you like to know?")


def smalltalk(question: str):
    return GREETING if _CHIT.match(question) else None


_VAGUE = re.compile(r"\b(which|what)\b.{0,40}\b(product|module|one|device)s?\b.{0,25}\b(better|best|good|recommend\w*)\b"
                    r"|\b(help me (choose|pick|select)|recommend (a|me a|me the)? ?(product|module)|what do you recommend)\b", re.I)
_MODEL = re.compile(r"\b[a-z]{1,3}\d{2,3}[a-z]{0,3}\b", re.I)
CLARIFY = ("The best Cavli module depends on what you need. Tell me your key requirements, for example: network "
           "technology (LTE Cat 1, Cat 1bis, Cat 4, 5G RedCap), data speed, GNSS, eSIM, form factor, region, power "
           "consumption or application. I'll then compare the modules I have verified sources for.")


def clarify(question: str):
    """A generic 'which product is better?' with no model named and no requirement: ask, don't search or call an LLM."""
    return CLARIFY if _VAGUE.search(question) and not _MODEL.search(question) else None


_COMMERCIAL = re.compile(r"\b(price|pricing|prices|how much (does|is|do|would)|quote|quotation|in stock|stock availability|lead time|"
                         r"moq|minimum order|discount|bulk order|cost of (the|a|one) )", re.I)
NOT_VERIFIED_COMMERCIAL = ("Not verified in available sources. Pricing, stock, lead times and quotes are not published in the "
                           "approved public documents I use, so I won't guess. Please contact the Cavli sales team.")


_SPEC = re.compile(r"\b(bands?|speed|gnss|gps|esim|uart|interfaces?|temperature|dimensions?|size|os|variants?|features?|"
                   r"support\w*|memory|processor|cpu|wi-?fi|bluetooth|sleep|power|certif\w*|compare|difference)\b", re.I)


def commercial(question: str) -> bool:
    """Price/stock/lead-time questions are never answerable from the public pages: skip retrieval and the LLM.
    If the same question also asks for something answerable (bands, speed, ...), let the pipeline answer that part and
    report the price as not verified instead of refusing everything."""
    if not _COMMERCIAL.search(question):
        return False
    rest = _COMMERCIAL.sub(" ", question)
    return not _SPEC.search(rest)
