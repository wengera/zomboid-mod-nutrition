#!/usr/bin/env python3
"""The science register: schema constants, TSV IO and the citation grammar.

Spec: docs/superpowers/specs/2026-09-27-nutrition-mod-design.md § 0 and § 9. A row is one evidenced
value the mod may ship: `id topic parameter value range population grade citation source status
successor`. `topic` is one slug of TOPICS, so the rows a nutrient record or a system model needs are
one filter away. The grades are the research reports' — MA (meta-analysis or systematic review), RCT,
COH (cohort or observational; a case report maps here), EXP (a controlled human depletion or dosing
experiment that is not randomised), MODEL (a published mathematical model cited for its shape and
fitted constants, never for an effect size), AUTH (an authority report such as a DRI or an EFSA
opinion), TXT (a narrative review, textbook or modelling paper); a slashed pair resolves to the
left-most member of RANK. A settled, unverified or superseded row names its record: a DOI or a
PubMed id for a paper, a URL for an authority page, an ISBN for a book. An open row is a named gap
and may be empty and ungraded. The mod cites a row by its bare id and `science_check.py --scan`
resolves every such token; the illustrative id on the register's page is S0000, reserved and never
minted."""
import re

COLUMNS = ("id", "topic", "parameter", "value", "range", "population", "grade", "citation", "source", "status", "successor")
GRADES = ("MA", "RCT", "COH", "EXP", "MODEL", "AUTH", "TXT")
RANK = ("MA", "RCT", "EXP", "COH", "AUTH", "TXT")
GRADE_ALIASES = {"CASE": "COH"}
STATUSES = ("settled", "open", "superseded", "unverified")
TOPICS = ("vitamin-a", "vitamin-d", "vitamin-e", "vitamin-k", "vitamin-c", "thiamine", "riboflavin", "niacin",
          "pantothenate", "vitamin-b6", "biotin", "folate", "vitamin-b12", "choline",
          "sodium", "potassium", "chloride", "calcium", "magnesium", "phosphorus", "iron", "zinc", "copper", "iodine",
          "selenium", "manganese", "water", "fibre", "essential-fats", "carbohydrate-quality",
          "alcohol", "caffeine", "phytate", "sweat", "digestion",
          "energy", "body-composition", "lean-mass", "strength", "aerobic-capacity", "glycogen", "protein",
          "fatigue-sleep", "cognition", "mood", "perception", "healing", "immunity", "thermal", "toxicity",
          "starvation", "refeeding", "satiety", "general")
ID_RX = re.compile(r"^S\d{4}$")
PROVISIONAL_RX = re.compile(r"^S\d+\.\d+$")
TOKEN_RX = re.compile(r"\bS\d{4}\b")
CITATION_RX = re.compile(r"(?:^|[\s;,(])(?:doi:10\.\S+|pmid:\d+|url:https?://\S+|isbn:[\d-]+)", re.I)
SOURCE_RX = re.compile(r"^\S+\.md § .+$")
CITED_STATUSES = ("settled", "unverified", "superseded")
BAD_CELL_RX = re.compile(r"[\t\r\n]")
RAW_RECORD_RX = re.compile(r"\b(?:PMID|DOI|PMC)\s*\d|\b(?:PMID|DOI)\s+\S")


class RegisterError(Exception):
    def __init__(self, msg, line=1):
        super().__init__(msg)
        self.line = line


def id_int(s):
    return int(s[1:])


def id_str(n):
    return "S%04d" % n


def resolve_grade(token):
    """A report's grade token -> a GRADES member: an alias maps, a slashed pair takes the left-most member
    of RANK whichever order it is written in, MODEL never pairs, and a design label is not a grade."""
    parts = [GRADE_ALIASES.get(p.strip(), p.strip()) for p in token.split("/")]
    if any(p not in GRADES for p in parts):
        raise ValueError("%r is not a grade" % token)
    if len(parts) == 1:
        return parts[0]
    if "MODEL" in parts:
        raise ValueError("%r: MODEL never appears in a pair; a model beside a trial is two rows" % token)
    return min(parts, key=RANK.index)


def read_register(path):
    """Rows as dicts keyed by COLUMNS. Raises RegisterError on a bad header or a short row."""
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0].rstrip("\r").split("\t") != list(COLUMNS):
        raise RegisterError("%s: header must be %s" % (path, "\t".join(COLUMNS)))
    rows = []
    for n, line in enumerate(lines[1:], 2):
        cells = line.rstrip("\r").split("\t")
        if len(cells) != len(COLUMNS):
            raise RegisterError("%s:%d: %d cells, expected %d \u2014 keep the trailing empty cells" % (path, n, len(cells), len(COLUMNS)), line=n)
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def write_register(path, rows):
    for r in rows:
        for c in COLUMNS:
            if BAD_CELL_RX.search(r.get(c, "")):
                raise RegisterError("%s: cell %s holds a tab or a line break" % (r.get("id", "?"), c))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            f.write("\t".join(r.get(c, "") for c in COLUMNS) + "\n")


def validate_row(row, provisional=False):
    """Schema errors for one row (empty list = valid). Cross-row checks live in science_check."""
    errs = []
    rid = row.get("id", "")
    if not (ID_RX.match(rid) or (provisional and PROVISIONAL_RX.match(rid))):
        errs.append("id %r is not Sdddd%s" % (rid, " or S<task>.<n>" if provisional else ""))
    status = row.get("status")
    if status not in STATUSES:
        errs.append("status %r not in %s" % (status, STATUSES))
    if not row.get("parameter", "").strip():
        errs.append("parameter is empty")
    gap_closed = status == "superseded" and not any(row.get(c, "").strip() for c in ("grade", "value", "citation"))
    if status != "open" and not gap_closed:
        if row.get("topic") not in TOPICS:
            errs.append("topic %r not in TOPICS" % row.get("topic"))
        if row.get("grade") not in GRADES:
            errs.append("grade %r not in %s" % (row.get("grade"), GRADES))
    else:
        if row.get("topic") and row.get("topic") not in TOPICS:
            errs.append("topic %r not in TOPICS" % row.get("topic"))
        if row.get("grade") and row.get("grade") not in GRADES:
            errs.append("grade %r not in %s" % (row.get("grade"), GRADES))
    if RAW_RECORD_RX.search(row.get("citation", "")):
        errs.append("citation holds an unrewritten PMID/DOI/PMC record; write pmid: or doi:")
    if status in CITED_STATUSES and not gap_closed:
        if not row.get("value", "").strip():
            errs.append("value is empty on a %s row" % status)
        if not CITATION_RX.search(row.get("citation", "")):
            errs.append("citation carries no doi:, pmid:, url: or isbn: on a %s row" % status)
    if not SOURCE_RX.match(row.get("source", "")):
        errs.append("source %r is not <report>.md § <heading> (one space either side of the section sign)" % row.get("source", ""))
    succ = row.get("successor", "").strip()
    if status == "superseded" and not succ:
        errs.append("successor required when superseded")
    if status != "superseded" and succ:
        errs.append("successor set on a non-superseded row")
    if succ and not all(ID_RX.match(s.strip()) for s in succ.split(",")):
        errs.append("successor %r is not Sdddd[, Sdddd]" % succ)
    return errs
