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


# ---- Python mini-course, part 2: lists, dictionaries, loops, if ----------------------------------------------------
def _still_blank(func) -> bool:
    """True when a student's function still has its ___ blank in it (the name ___ is in its compiled code)."""
    return "___" in getattr(getattr(func, "__code__", None), "co_names", ())


def p2_ex1(answer):
    """How many codes mean "don't know" for escape_risk: len() of its list."""
    from .cleaning import NULL_TOKENS
    _verdict(answer, len(NULL_TOKENS["escape_risk"]), "len(codes) counts what's in the list")


def p2_ex2(answer):
    """intake_time's codes, looked up in the data dictionary."""
    from .cleaning import NULL_TOKENS
    _verdict(answer, NULL_TOKENS["intake_time"], 'look it up with square brackets: tokens["intake_time"]')


@lru_cache(maxsize=None)
def _p2_cases():
    """For each data-dictionary column: (its codes, {value: how many records}, the values apply_null_tokens empties),
    on the data after session 2's first two steps, as course 1 runs them."""
    from . import pipeline
    from .cleaning import NULL_TOKENS, apply_null_tokens, set_record_id, strip_and_null
    before = set_record_id(strip_and_null(pipeline.load_raw()))
    after = apply_null_tokens(before)
    cases = {}
    for col, codes in NULL_TOKENS.items():
        kept = before[col].notna()
        emptied = frozenset(before[col][kept & after[col].isna()])
        cases[col] = (tuple(codes), before[col][kept].value_counts().to_dict(), emptied)
    return cases


def _p2_try(func):
    """Run a student's clean_value on every different value of the four columns. Returns ('blank', None),
    ('error', message), ('wrong', message) or ('ok', {column: values it emptied})."""
    if _still_blank(func):
        return "blank", None
    found = {}
    try:
        for col, (codes, counts, emptied) in _p2_cases().items():
            found[col] = 0
            for value, n in counts.items():
                got = func(value, list(codes))
                call = f"clean_value({value!r}, {list(codes)!r}) gives {got!r}"
                if value in emptied and got is not None:
                    return "wrong", f"{call}, but {value!r} means don't know in {col}: it should give None"
                if value not in emptied and got != value:
                    return "wrong", f"{call}, but {value!r} is a real value in {col}: hand it back as it was"
                found[col] += n if got is None else 0
    except Exception as e:   # the student's code, any error: say which, don't stop the notebook
        return "error", f"{type(e).__name__}: {e}"
    return "ok", found


def p2_ex3(func):
    """clean_value gives None exactly where course 1's apply_null_tokens empties a value, and every other value
    back as it was."""
    state, detail = _p2_try(func)
    if state == "blank":
        _verdict(___, None, "")
    elif state == "error":
        print(f"❌ Your function stopped with an error: {detail}. Hint: unknown = value in codes")
    elif state == "wrong":
        print(f"❌ Not quite: {detail}. Hint: unknown = value in codes")
    else:
        n = sum(len(counts) for _, counts, _ in _p2_cases().values())
        print(f"✅ Your clean_value agrees with course 1's apply_null_tokens on all {n:,} different values in the four "
              "columns.")


def p2_payoff(func):
    """The student's clean_value over the four columns: how many don't-know codes it empties, column by column,
    against what apply_null_tokens empties (part 0's step 3)."""
    state, detail = _p2_try(func)
    if state == "blank":
        _verdict(___, None, "")
        return
    if state != "ok":
        print(f"❌ {detail}. Fix exercise 3 first.")
        return
    # "ok" means it agreed with apply_null_tokens on every value, so its counts are course 1's: say so, with them
    print(f"✅ Your clean_value finds {sum(detail.values()):,} don't-know codes, the same as course 1's "
          "apply_null_tokens (part 0, step 3). Column by column:")
    for col, n in detail.items():
        print(f"   {col:20} {n:6,}")


# ---- Python mini-course, part 3: pandas -------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _p3_raw():
    """The course file as written, every value as text (the checks' own copy)."""
    from . import pipeline
    return pipeline.load_raw()


def p3_ex1(answer):
    """How many custody_level values are written as nothing at all ("")."""
    _verdict(answer, int((_p3_raw()["custody_level"] == "").sum()), 'compare the column with "", then .sum(): (custody == "").sum()')


def p3_ex2(answer):
    """How many custody_level values course 1 makes empty: the Trust Test's Q1, cleaned."""
    from .cleaning import strip_and_null
    _verdict(answer, int(strip_and_null(_p3_raw())["custody_level"].isna().sum()),
             'strip first, then compare: (custody.str.strip() == "").sum()')


def _p3_try(func):
    """Run a student's strip_and_null on the course file. Returns ('blank', None), ('error', message),
    ('wrong', message) or ('ok', their table)."""
    if _still_blank(func):
        return "blank", None
    from .cleaning import strip_and_null
    raw = _p3_raw()
    try:
        theirs = func(raw.copy())
    except Exception as e:   # the student's code, any error: say which, don't stop the notebook
        return "error", f"{type(e).__name__}: {e}"
    ours = strip_and_null(raw)
    if not isinstance(theirs, pd.DataFrame) or list(theirs.columns) != list(ours.columns) or len(theirs) != len(ours):
        return "wrong", "your function should hand back the whole table, with every column. Did you keep `return out`?"
    for col in ours.columns:
        a, b = theirs[col].reset_index(drop=True), ours[col].reset_index(drop=True)
        differs = (a.isna() != b.isna()) | (a.notna() & b.notna() & (a.astype(object) != b.astype(object)))
        if differs.any():
            i = int(differs.to_numpy().argmax())
            show = lambda v: "empty (null)" if pd.isna(v) else repr(v)   # noqa: E731
            return "wrong", (f"in {col}, row {i:,} was written {raw[col].iloc[i]!r}: yours has {show(a.iloc[i])}, "
                             f"course 1 has {show(b.iloc[i])}")
    return "ok", theirs


def p3_ex3(func):
    """my_strip_and_null gives the same table as course 1's strip_and_null, cell for cell."""
    state, detail = _p3_try(func)
    if state == "blank":
        _verdict(___, None, "")
    elif state == "error":
        print(f"❌ Your function stopped with an error: {detail}. Hint: stripped = out[col].str.strip()")
    elif state == "wrong":
        print(f"❌ Not quite: {detail}. Hint: stripped = out[col].str.strip()")
    else:
        print(f"✅ Your function gives the same table as course 1's strip_and_null, all {detail.size:,} cells.")


def p3_payoff(func):
    """The Trust Test's Q1 from the student's own table: missing custody levels, against those that only looked empty."""
    state, detail = _p3_try(func)
    if state == "blank":
        _verdict(___, None, "")
        return
    if state != "ok":
        print(f"❌ {detail}. Fix exercise 3 first.")
        return
    looked = int((_p3_raw()["custody_level"] == "").sum())
    print(f"✅ Q1, from your own table: {int(detail['custody_level'].isna().sum()):,} records are missing a custody "
          f"level, not the {looked:,} that looked empty. Across the file your function made "
          f"{int(detail.isna().sum().sum()):,} values empty, part 0's step 1.")


# ---- Python mini-course, part 4: patterns -----------------------------------------------------------------------
P4_TRICKY = ["2381457", "023814570", "0238145O", "02381457 ", "0238-1457", ""]   # near-misses an ID check must refuse


@lru_cache(maxsize=None)
def _p4_dates() -> tuple:
    """Every different projected_release_date as written (stripped, blanks left out), in order."""
    from .cleaning import strip_and_null
    return tuple(sorted(strip_and_null(_p3_raw())["projected_release_date"].dropna().unique()))


def _p4_compare(pattern, reference, values):
    """('blank'|'error'|'wrong'|'ok', message): does the student's pattern fullmatch exactly the values the
    reference pattern does?"""
    import re
    if isinstance(pattern, _Blank):
        return "blank", ""
    if not isinstance(pattern, str):
        return "wrong", f"you have {pattern!r}; a pattern is a string, in quotes: r\"...\""
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return "error", f"Python can't read that pattern (error: {e})"
    for v in values:
        mine, theirs = bool(compiled.fullmatch(v)), bool(re.fullmatch(reference, v))
        if mine != theirs:
            return "wrong", f"{v!r} {'matches' if mine else 'does not match'} yours, but course 1's {'accepts' if theirs else 'refuses'} it"
    return "ok", len(values)


def _p4_say(state, detail, hint, ok_line):
    """Print the verdict for a pattern exercise."""
    if state == "blank":
        _verdict(___, None, "")
    elif state == "ok":
        print(f"✅ {ok_line.format(n=detail)}")
    else:
        print(f"❌ Not quite: {detail}. Hint: {hint}")


def p4_ex1(pattern):
    """A pattern for an ID: exactly 8 digits, like course 1's ID_PATTERN, tried on every ID in the file and on some
    near-misses."""
    from .cleaning import ID_PATTERN
    raw = _p3_raw()
    sids = raw["sid_number"].str.strip()
    values = P4_TRICKY + sorted(set(raw["offender_number"]) | set(sids[sids != ""]))
    state, detail = _p4_compare(pattern, ID_PATTERN, values)
    _p4_say(state, detail, r'a digit is \d, and {8} means exactly 8 of them: r"\d{8}"',
            "Your pattern agrees with course 1's ID_PATTERN on all {n:,} IDs and near-misses.")


def _p4_shapes_try(func):
    """Run a student's shape() on every projected_release_date as written and compare its counts with course 1's
    dates.profile_shapes. Returns (state, detail), detail being their counts when 'ok'."""
    if _still_blank(func):
        return "blank", None
    from .cleaning import strip_and_null
    from .dates import profile_shapes
    column = strip_and_null(_p3_raw())["projected_release_date"]
    course1 = profile_shapes(column, top=1_000_000)["count"].to_dict()
    try:
        theirs = column.dropna().map(func)
    except Exception as e:   # the student's code, any error: say which, don't stop the notebook
        return "error", f"Your function stopped with an error: {type(e).__name__}: {e}"
    for value, got in zip(column.dropna(), theirs):
        if got not in course1:
            return "wrong", f"shape({value!r}) gives {got!r}, which isn't one of course 1's shapes"
    counts = theirs.value_counts().to_dict()
    if counts != course1:
        return "wrong", "your shapes are right but their counts differ from course 1's"
    return "ok", counts


def p4_ex2(func):
    """shape(): every digit becomes 9 and every letter becomes A, giving course 1's profile_shapes table."""
    state, detail = _p4_shapes_try(func)
    if state == "blank":
        _verdict(___, None, "")
    elif state == "ok":
        print(f"✅ Your shape function gives course 1's profile_shapes table exactly: {len(detail)} shapes.")
    else:
        print(f"❌ {detail}. Hint: text = re.sub(r\"[A-Za-z]\", \"A\", text)")


def p4_ex3(pattern):
    """The pattern for a date written like 2029-11-03, tried on every projected_release_date against course 1's
    YYYY-MM-DD pattern."""
    from .dates import DATE_FORMATS
    reference = next(regex for label, regex, _ in DATE_FORMATS if label == "YYYY-MM-DD")
    state, detail = _p4_compare(pattern, reference, list(_p4_dates()))
    _p4_say(state, detail, r'four digits, a dash, two digits, a dash, two digits: \d{4}-...',
            "Your pattern picks out exactly the dates course 1 reads as YYYY-MM-DD, among all {n:,} different dates.")


def p4_payoff(func):
    """The student's shape() over the whole column: how many different dates become how many shapes, top five."""
    state, detail = _p4_shapes_try(func)
    if state == "blank":
        _verdict(___, None, "")
        return
    if state != "ok":
        print(f"❌ {detail}. Fix exercise 2 first.")
        return
    from .dates import DATE_FORMATS
    print(f"✅ Your shape function turns {len(_p4_dates()):,} different dates into {len(detail)} shapes. "
          f"Course 1 recognizes every one of them with {len(DATE_FORMATS)} patterns. The five most common:")
    for shape, n in sorted(detail.items(), key=lambda kv: -kv[1])[:5]:
        print(f"   {shape:22} {n:7,}")
