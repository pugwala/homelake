"""Exercise checkers. Each prints a friendly verdict; nothing here ever stops a notebook from running."""
from datetime import date
from decimal import Decimal
from functools import lru_cache

import pandas as pd


class _Blank:
    """The ___ placeholder in exercises. Replace it with your answer."""
    def __repr__(self):
        return "___"


___ = _Blank()


def _verdict(answer, expected, hint: str, label: str = "") -> None:
    if isinstance(answer, _Blank):
        print("✏️  Replace ___ with your answer, then run the cell again.")
        return
    ok = answer == expected
    if isinstance(expected, (float, Decimal)) and not isinstance(answer, (str, bool)):
        try:
            ok = abs(float(answer) - float(expected)) < 0.01
        except (TypeError, ValueError):
            ok = False
    if ok:
        print(f"✅ Correct{': ' + label if label else ''} ({expected})")
    else:
        print(f"❌ Not quite. You have {answer!r}. Hint: {hint}")


# Cached data at each stage so checks are instant after the first call
@lru_cache(maxsize=None)
def _naive():
    from . import pipeline
    return pipeline.load_naive()


@lru_cache(maxsize=None)
def _stage(n: int):
    from . import pipeline
    return pipeline.clean_through(n)


# ---- Session 1 ------------------------------------------------------------------------------
def s1_ex1(answer):
    expected = len(_naive()["custody_level"].value_counts(dropna=False))
    _verdict(answer, expected, "count the rows in the value_counts output: len(custody_counts)")


def s1_ex2(answer):
    from .cleaning import strip_and_null
    expected = int(strip_and_null(_naive())["gender"].isna().sum())
    _verdict(answer, expected, 'use clean["gender"].isna().sum()')


def s1_ex3(answer):
    from .cleaning import strip_and_null
    expected = strip_and_null(_naive())["unit_location"].value_counts().index[0]
    _verdict(answer, expected, 'clean["unit_location"].value_counts().index[0] gives the top value')


# ---- Session 2 ------------------------------------------------------------------------------
def s2_ex1(answer):
    expected = int((_stage(2)["housing_restriction"] == "NONE").sum())
    _verdict(answer, expected, 'compare the column to the text "NONE", then .sum()')


def s2_ex2(answer):
    df = _stage(2)
    expected = int(df.loc[df["last_name_std"] == "MCDONALD", "last_name"].nunique())
    _verdict(answer, expected, 'filter last_name_std == "MCDONALD", then .nunique() on the original last_name')


def s2_ex3(answer):
    expected = int((_stage(2).groupby("sid_number").size() > 1).sum())
    _verdict(answer, expected, 'df.groupby("sid_number").size() counts records per person; how many are > 1?')


def s2_ex4(answer):
    df = _stage(2)
    expected = int((df["stg_group"].eq("HYDRA") & df["stg_status"].eq("Confirmed")).sum())
    _verdict(answer, expected, 'two conditions joined with &: df["stg_group"] == "HYDRA" and '
                               'df["stg_status"] == "Confirmed". A bare "HYDRA" is Unverified, not Confirmed.')


# ---- Session 3 ------------------------------------------------------------------------------
def s3_ex1(answer):
    from .dates import TWO_DIGIT, parse_dates
    _, labels = parse_dates(_stage(2)["sentence_date"])
    _verdict(answer, int((labels == TWO_DIGIT).sum()), 'count the format labels equal to "M/D/YY"')


def s3_ex2(answer):
    from .dates import parse_dates
    parsed, _ = parse_dates(_stage(2)["date_of_birth"])
    expected = int((parsed > date.today()).fillna(False).sum())
    _verdict(answer, expected, "compare the parsed dates to date.today() BEFORE fixing centuries")


def s3_ex3(answer):
    expected = int((_stage(3)["projected_release_date"].dt.year == 2027).sum())
    _verdict(answer, expected, 'use df3["projected_release_date"].dt.year == 2027, then .sum()')


# ---- Session 4 ------------------------------------------------------------------------------
def s4_ex1(answer):
    expected = round(float(_stage(4)["disciplinary_points"].mean()), 2)
    _verdict(answer, expected, "points.mean(), rounded to 2 places")


def s4_ex2(answer):
    expected = _stage(4)["restitution_owed"].sum()
    _verdict(answer, expected, "money.sum() on the converted column")


def s4_ex3(true_values, false_values):
    from .conversions import to_boolean
    if any(isinstance(v, _Blank) for v in set(true_values) | set(false_values)):
        remaining = [v for v in set(true_values) | set(false_values) if not isinstance(v, _Blank)]
        print(f"✏️  Replace the ___ entries with more spellings. So far you have {sorted(remaining)}.")
    raw = _stage(3)["escape_risk"]
    clean_true = {v for v in true_values if isinstance(v, str)}
    clean_false = {v for v in false_values if isinstance(v, str)}
    _, unmapped = to_boolean(raw, clean_true, clean_false)
    counts = unmapped.str.upper().value_counts()
    print(f"Still unmapped: {len(unmapped):,} values")
    if len(counts):
        print(counts.head(10).to_string())
    genuinely_unknown = {"MAYBE", "?", "PENDING"}
    if set(counts.index) <= genuinely_unknown:
        print("✅ Every real yes/no spelling is mapped. What's left is genuinely unknown and should stay null.")


def s4_ex4(answer):
    expected = int(_stage(4)["dampener_required"].sum())
    _verdict(answer, expected, 'flags["dampener_required"].sum() counts the True values')


# ---- Session 5 ------------------------------------------------------------------------------
def s5_ex1(answer):
    expected = int(_stage(2)["gender"].isna().sum())
    _verdict(answer, expected, 'filter F.col("gender").isNull(), then .count(). It should match pandas.')


def s5_ex2(answer):
    expected = _stage(4)["restitution_owed"].sum()
    _verdict(answer, expected, 'use s4.agg(F.sum("restitution_owed")).first()[0]. It should match pandas to the cent.')


# ---- Python mini-course, part 0: open the box -------------------------------------------------------------------
@lru_cache(maxsize=None)
def _p0_nulls_added():
    """How many nulls session 2's first and third steps each add: (strip_and_null, apply_null_tokens)."""
    from . import pipeline
    from .cleaning import apply_null_tokens, set_record_id, strip_and_null
    raw = pipeline.load_raw()
    stripped = strip_and_null(raw)
    keyed = set_record_id(stripped)
    nulls = lambda df: int(df.isna().sum().sum())   # noqa: E731
    return nulls(stripped) - nulls(raw), nulls(apply_null_tokens(keyed)) - nulls(keyed)


def _p0_number(answer, expected, hint):
    """_verdict() for a count read off a report, explaining a number typed with a comma (Python reads 77,734 as
    two numbers)."""
    if isinstance(answer, tuple):
        print(f"❌ Python reads a comma as 'two numbers', so you have {answer!r}. Type the number without the comma, "
              "like 1234.")
        return
    _verdict(answer, expected, hint)


def p0_ex1(answer):
    """How many values became empty (null) in step 1, strip_and_null?"""
    _p0_number(answer, _p0_nulls_added()[0], "read the 'Empty values (nulls)' line under step 1: the number after the + sign")


def p0_ex2(answer):
    """How many more values became empty in step 3, apply_null_tokens?"""
    _p0_number(answer, _p0_nulls_added()[1], "read the 'Empty values (nulls)' line under step 3: the number after the + sign")


def p0_ex3(answer):
    """Which step added the three name columns ending in _std? Taken by name, with or without cleaning. or ()."""
    if isinstance(answer, _Blank):
        _verdict(answer, None, "")
        return
    name = getattr(answer, "__name__", answer)
    if isinstance(name, str):
        name = name.strip().removeprefix("cleaning.").removesuffix("()").strip()
    _verdict(name, "standardize_names", "look for the step whose report says 'New columns (3)': type its name in quotes")


# ---- Python mini-course, part 1: strings ------------------------------------------------------------------------
P1_NAME = "gArCiA"   # how one GARCIA in the file is written


def _p1_std(text: str) -> str:
    """What course 1's standardize_names makes of one last name: its last_name_std."""
    from .cleaning import standardize_names
    return standardize_names(pd.DataFrame({"last_name": [text], "first_name": [None], "alias": [None]}))["last_name_std"].iloc[0]


def p1_ex1(answer):
    """The name in capitals, which is what course 1's last_name_std holds for it."""
    _verdict(answer, _p1_std(P1_NAME), 'put .upper() after name: name.upper()')


def p1_ex2(answer):
    """A comparison of name with "GARCIA" that ignores capitals, so it comes out True."""
    if isinstance(answer, _Blank):
        _verdict(answer, True, "")
    elif answer is True:
        print("✅ Correct: True. With both sides in capitals, the spellings match.")
    else:
        print(f"❌ Not quite. You have {answer!r}. Hint: capitals first, then compare: name.upper() == \"GARCIA\"")


@lru_cache(maxsize=None)
def _p1_names():
    """{last name: course 1's last_name_std} for every different last name without accents, after session 2."""
    df = _stage(2)
    pairs = df[["last_name", "last_name_std"]].dropna().drop_duplicates("last_name")
    pairs = pairs[pairs["last_name"].map(str.isascii)]
    return dict(zip(pairs["last_name"], pairs["last_name_std"]))


def _p1_try(func):
    """Run a student's match_key over every last name without accents. Returns (verdict, message): verdict is
    'blank', 'error' or 'ok'/'wrong' with the number that agree and the first that doesn't."""
    try:
        if isinstance(func(P1_NAME), _Blank):
            return "blank", ""
        mismatch, agree = None, 0
        for name, std in _p1_names().items():
            got = func(name)
            if got == std:
                agree += 1
            elif mismatch is None:
                mismatch = (name, got, std)
    except Exception as e:   # the student's code, any error: say which, don't stop the notebook
        return "error", f"{type(e).__name__}: {e}"
    if mismatch is None:
        return "ok", agree
    name, got, std = mismatch
    if got is None:
        return "wrong", "your function gave back nothing (None). Did you keep the line `return key`?"
    return "wrong", f"match_key({name!r}) gives {got!r}, but course 1 has {std!r}"


def p1_ex3(func):
    """match_key gives course 1's last_name_std for every last name without accents."""
    state, detail = _p1_try(func)
    if state == "blank":
        _verdict(___, None, "")
    elif state == "error":
        print(f"❌ Your function stopped with an error: {detail}. Hint: name.strip().upper()")
    elif state == "wrong":
        print(f"❌ Not quite: {detail}. Hint: name.strip().upper()")
    else:
        print(f"✅ Your match_key agrees with course 1's last_name_std on all {detail:,} different last names "
              "without accents.")


def p1_payoff(func):
    """The student's match_key over all 100,000 last names as written: how many spellings become how many names,
    and whether it finds session 2's KENTs."""
    state, detail = _p1_try(func)
    if state == "blank":
        _verdict(___, None, "")
        return
    if state == "error":
        print(f"❌ Your function stopped with an error: {detail}.")
        return
    from . import pipeline
    raw = pipeline.load_raw()["last_name"]
    keys = raw.map(func)
    kents, session2 = int((keys == "KENT").sum()), int((_stage(2)["last_name_std"] == "KENT").sum())
    line = (f"Your match_key turns {raw.nunique():,} spellings into {keys.nunique():,} names, and finds "
            f"{kents} records named KENT (session 2 found {session2}).")
    print(f"✅ {line}" if state == "ok" and kents == session2 else f"❌ {line} Fix exercise 3 first.")
