"""Tests for the Python mini-course (python/), which sits between course 1 and course 2.

Run them without Databricks, in the course's Jupyter image (the data is built on first use, about 5 seconds):

    docker run --rm -u "$(id -u)" -v ~/homelake:/repo -w /repo -e PYTHONPATH=/repo -e LNL_DATA_DIR=/tmp/lnl_data \
        --entrypoint pytest lnl-jupyter:local -q -p no:cacheprovider tests/test_python_course.py

Covered here:
  - lnl/inside.py, the helpers part 0 uses to open course 1's one-line steps and show what each step changed;
  - the part 0 checks in lnl/check.py, graded against the course data, never against a stored number;
  - the part 1 checks (strings), graded against course 1's last_name_std;
  - the part 2 checks (lists, dictionaries, loops, if), graded against course 1's apply_null_tokens;
  - the part 3 checks (pandas), graded against course 1's strip_and_null;
  - the part 4 checks (patterns), graded against course 1's ID_PATTERN, profile_shapes and DATE_FORMATS;
  - the part 5 checks (your own session 2), graded against course 1's strip_and_null, apply_null_tokens and session2;
  - each part's notebook (python/0*.ipynb), run top to bottom in a real kernel twice: as delivered (every check
    asks for an answer) and with its Answers section filled in (every check passes).
"""
import contextlib
import io
import re
from pathlib import Path

import nbformat
import pandas as pd
import pytest
from nbclient import NotebookClient

from lnl import check, cleaning, env, inside, pipeline

ROOT = Path(__file__).resolve().parents[1]
PARTS = {   # notebook: (its blanks, how many checks it runs)
    ROOT / "python" / "00_open_the_box.ipynb": ({"answer_1", "answer_2", "answer_3"}, 3),
    ROOT / "python" / "01_strings.ipynb": ({"answer_1", "answer_2", "key"}, 4),
    ROOT / "python" / "02_lists_and_loops.ipynb": ({"answer_1", "answer_2", "unknown"}, 4),
    ROOT / "python" / "03_pandas.ipynb": ({"answer_1", "answer_2", "stripped"}, 4),
    ROOT / "python" / "04_patterns.ipynb": ({"answer_1", "text", "answer_3"}, 4),
    ROOT / "python" / "05_your_own_session_2.ipynb": ({"cleaned", "df", "answer_3"}, 4),
}
BLANK_LINE = re.compile(r"^(\s*)(\w+) = ___\b.*$", re.M)
ANSWER = re.compile(r"```python\n(.*?)```", re.S)


def said(fn, *args) -> str:
    """What a check printed when called with these arguments."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        fn(*args)
    return out.getvalue().strip()


@pytest.fixture(scope="module")
def raw():
    """The course file as the source system wrote it, every value as text (built on first use)."""
    env.generate()
    return pipeline.load_raw()


# ---- inside.recipe and inside.show: reading a function ----------------------------------------------------------

def _tiny(df):
    """A two-step recipe, for the tests."""
    df = cleaning.strip_and_null(df)
    from lnl.cleaning import set_record_id
    return set_record_id(df)


def test_recipe_names_each_step_in_order():
    """recipe() lists the steps a function hands its table to, in order, by name, including one on a return line."""
    assert inside.recipe(_tiny) == ["strip_and_null", "set_record_id"]


def test_recipe_of_session2_is_its_six_steps():
    """Course 1's session 2 is six named steps."""
    assert inside.recipe(cleaning.session2) == ["strip_and_null", "set_record_id", "apply_null_tokens",
                                                "repair_text_columns", "standardize_names", "standardize_domains"]


def test_show_prints_the_code_with_line_numbers():
    """show() prints a function's own code, every line numbered from 1."""
    text = said(inside.show, cleaning.strip_and_null)
    lines = text.splitlines()
    assert lines[0].split("|", 1)[0].strip() == "1" and "def strip_and_null(df" in lines[0]
    assert any("for col in text_columns(out):" in line for line in lines)
    assert [int(line.split("|", 1)[0]) for line in lines] == list(range(1, len(lines) + 1))


# ---- inside.what_changed: what one step did to the table ---------------------------------------------------------

def test_what_changed_counts_new_nulls_and_rewritten_values():
    """Blank text turned into a null is one new null, and it counts as a rewritten value too."""
    before = pd.DataFrame({"name": [" Ann", "", "Bo"], "code": ["A", "B", "C"]})
    after = pd.DataFrame({"name": ["Ann", None, "Bo"], "code": ["A", "B", "C"]})
    lines = inside.what_changed(before, after)
    assert "Rows: 3 (no change)" in lines
    assert "Empty values (nulls): 0 → 1 (+1)" in lines
    assert "Values rewritten: 2, in 1 column (name: 2)" in lines


def test_what_changed_names_new_and_gone_columns_and_a_new_row_label():
    """A column that became the row labels is reported as that, not as gone."""
    before = pd.DataFrame({"id": ["01", "02"], "x": ["a", "b"], "old": ["p", "q"]})
    after = pd.DataFrame({"x": ["a", "b"], "x_std": ["A", "B"]}, index=pd.Index([1, 2], name="id"))
    lines = inside.what_changed(before, after)
    assert "Rows are now labeled by id (it left the columns)" in lines
    assert "New columns (1): x_std" in lines
    assert "Columns gone (1): old" in lines
    assert "Empty values (nulls): 0 (no change)" in lines
    assert "Values rewritten: none" in lines


def test_what_changed_with_a_different_row_count_says_so_and_skips_the_cell_compare():
    """Cells can only be compared row by row when no rows came or went."""
    lines = inside.what_changed(pd.DataFrame({"x": ["a", "b"]}), pd.DataFrame({"x": ["a"]}))
    assert "Rows: 2 → 1" in lines
    assert not any(line.startswith("Values rewritten") for line in lines)


def test_report_prints_every_line():
    """report() prints a heading and each what_changed() line as a bullet."""
    before, after = pd.DataFrame({"x": [""]}), pd.DataFrame({"x": [None]})
    text = said(inside.report, before, after)
    assert text.splitlines()[0] == "What changed:"
    assert all(f"  • {line}" in text for line in inside.what_changed(before, after))


# ---- inside.side_by_side and inside.same_table -------------------------------------------------------------------

def test_side_by_side_shows_the_most_changed_record_with_spaces_visible():
    """One record, before and after, column by column; text in quotes so stray spaces show, nulls as (empty); the
    step's new columns come last, marked as new."""
    before = pd.DataFrame({"id": ["01", "02"], "name": ["Ann", "  bo "], "code": ["A", "N/A"]})
    after = pd.DataFrame({"name": ["Ann", "Bo"], "code": ["A", None], "name_std": ["ANN", "BO"]},
                         index=pd.Index([1, 2], name="id"))
    table = inside.side_by_side(before, after)
    assert list(table.columns) == ["as written", "after"]
    assert table.loc["id"].tolist() == ['"02"', "2"]
    assert table.loc["name"].tolist() == ['"  bo "', '"Bo"']
    assert table.loc["code"].tolist() == ['"N/A"', "(empty)"]
    assert table.loc["name_std"].tolist() == ["(new column)", '"BO"']
    assert list(table.index) == ["id", "name", "code", "name_std"]


def test_same_table_says_yes_only_for_an_identical_table():
    """✅ when every cell, column and row label match, ❌ otherwise; it only prints, so a notebook shows no stray
    True or False under the verdict."""
    a = pd.DataFrame({"x": ["a", None]})
    assert said(inside.same_table, a, a.copy()).startswith("✅")
    assert inside.same_table(a, a.copy()) is None
    assert said(inside.same_table, a, pd.DataFrame({"x": ["a", "b"]})).startswith("❌")


def test_same_table_notices_row_labels_named_differently():
    """Same cells, but one table's rows are labeled by offender_number: not the same table (pandas' own
    DataFrame.equals ignores the label's name)."""
    a = pd.DataFrame({"x": ["a"]}, index=pd.Index([1], name="offender_number"))
    assert said(inside.same_table, a, a.rename_axis(None)).startswith("❌")


def test_the_six_steps_one_at_a_time_give_session2_exactly(raw):
    """The lesson part 0 rests on: running session 2's steps by hand gives the same table as the one line."""
    from lnl import domains
    df = raw
    for step in (cleaning.strip_and_null, cleaning.set_record_id, cleaning.apply_null_tokens,
                 cleaning.repair_text_columns, cleaning.standardize_names, domains.standardize_domains):
        df = step(df)
    assert df.equals(cleaning.session2(raw))


# ---- the part 0 checks, against the course data ------------------------------------------------------------------

def test_p0_ex1_is_the_blanks_strip_and_null_empties(raw):
    """Exercise 1's answer: values that are blank once trimmed, counted straight from the raw file."""
    blanks = sum(int((raw[c].str.strip() == "").sum()) for c in raw.columns)
    assert said(check.p0_ex1, check.___).startswith("✏️")
    assert said(check.p0_ex1, blanks).startswith("✅")
    assert said(check.p0_ex1, blanks + 1).startswith("❌")


def test_p0_ex1_explains_a_number_written_with_a_comma(raw):
    """77,734 in Python is two numbers; the check says so instead of a bare ❌."""
    blanks = sum(int((raw[c].str.strip() == "").sum()) for c in raw.columns)
    text = said(check.p0_ex1, (blanks // 1000, blanks % 1000))
    assert text.startswith("❌") and "without the comma" in text


def test_p0_ex2_is_the_documented_unknown_codes(raw):
    """Exercise 2's answer: values in the data dictionary's 'unknown' list, counted from the raw file."""
    codes = sum(int(raw[c].str.strip().str.upper().isin([v.upper() for v in vals]).sum())
                for c, vals in cleaning.NULL_TOKENS.items())
    assert said(check.p0_ex2, check.___).startswith("✏️")
    assert said(check.p0_ex2, codes).startswith("✅")
    assert said(check.p0_ex2, codes - 1).startswith("❌")


@pytest.mark.parametrize("answer", ["standardize_names", " standardize_names() ", "cleaning.standardize_names",
                                    cleaning.standardize_names])
def test_p0_ex3_takes_the_step_name_however_it_is_written(answer):
    """Exercise 3's answer is the step that adds the *_std name columns: by name, with or without cleaning. or ()."""
    assert said(check.p0_ex3, answer).startswith("✅")


def test_p0_ex3_refuses_another_step():
    """A different step's name is not right."""
    assert said(check.p0_ex3, "standardize_domains").startswith("❌")


# ---- the part 1 checks (strings), against course 1's last_name_std -----------------------------------------------

def test_p1_ex1_is_the_name_in_capitals():
    """Exercise 1: "gArCiA" in capitals is what course 1's last_name_std makes of it."""
    assert said(check.p1_ex1, check.___).startswith("✏️")
    assert said(check.p1_ex1, "GARCIA").startswith("✅")
    assert said(check.p1_ex1, "Garcia").startswith("❌")


def test_p1_ex2_wants_a_comparison_that_is_true():
    """Exercise 2: a comparison that ignores capitals comes out True."""
    assert said(check.p1_ex2, check.___).startswith("✏️")
    assert said(check.p1_ex2, "gArCiA".upper() == "GARCIA").startswith("✅")
    assert said(check.p1_ex2, "gArCiA" == "GARCIA").startswith("❌")


@pytest.mark.parametrize("key", [lambda n: n.strip().upper(), lambda n: " ".join(n.upper().split())],
                         ids=["strip-upper", "split-join"])
def test_p1_ex3_passes_a_match_key_that_agrees_with_course_1(key):
    """Exercise 3: any function that gives course 1's last_name_std for every last name without accents."""
    assert said(check.p1_ex3, key).startswith("✅")


def _blank_key(name):
    """A match_key whose blank hasn't been filled in."""
    key = check.___
    return key


def _no_return(name):
    """A match_key that forgot its return line."""
    name.strip().upper()


def _boom(name):
    """A match_key that stops with an error."""
    return name.upper(1)


def test_p1_ex3_explains_what_is_wrong():
    """Blank: asks. Forgot capitals: ❌ with an example. No return: says so. An error: shows it."""
    assert said(check.p1_ex3, _blank_key).startswith("✏️")
    wrong = said(check.p1_ex3, lambda n: n.strip())
    assert wrong.startswith("❌") and "gives" in wrong
    assert "return" in said(check.p1_ex3, _no_return)
    boom = said(check.p1_ex3, _boom)
    assert boom.startswith("❌") and "TypeError" in boom


def test_p1_payoff_counts_spellings_names_and_kents(raw):
    """The payoff: the student's function over all 100,000 raw last names, and the KENTs it finds, the same 3 as
    session 2 (counted here from the raw file, not from the check's own code)."""
    spellings = raw["last_name"].nunique()
    names = raw["last_name"].str.strip().str.upper().nunique()
    kents = int((raw["last_name"].str.strip().str.upper() == "KENT").sum())
    text = said(check.p1_payoff, lambda n: n.strip().upper())
    assert text.startswith("✅")
    assert f"{spellings:,} spellings" in text and f"{names:,} names" in text and f"{kents} records named KENT" in text
    assert said(check.p1_payoff, lambda n: n).startswith("❌")
    only_kent = lambda n: "KENT" if n.strip().upper() == "KENT" else n   # noqa: E731  right KENTs, wrong elsewhere
    assert said(check.p1_payoff, only_kent).startswith("❌")
    blank = said(check.p1_payoff, _blank_key)
    assert blank.startswith("✏️") and len(blank.splitlines()) == 1, blank   # asks, and says nothing else


# ---- the part 2 checks (lists, dictionaries, loops, if), against course 1's apply_null_tokens ----------------------

def test_p2_ex1_is_how_many_codes_escape_risk_has():
    """Exercise 1: len() of escape_risk's list of don't-know codes (U and UNK)."""
    assert said(check.p2_ex1, check.___).startswith("✏️")
    assert said(check.p2_ex1, 2).startswith("✅")
    assert said(check.p2_ex1, 1).startswith("❌")


def test_p2_ex2_is_intake_times_codes_looked_up():
    """Exercise 2: the data dictionary's list for intake_time."""
    assert said(check.p2_ex2, check.___).startswith("✏️")
    assert said(check.p2_ex2, ["99:99"]).startswith("✅")
    assert said(check.p2_ex2, "99:99").startswith("❌")
    assert said(check.p2_ex2, ["U", "UNK"]).startswith("❌")


def _cv_blank(value, codes):
    """A clean_value whose blank hasn't been filled in."""
    unknown = check.___
    if unknown:
        return None
    return value


def _cv_first_code_only(value, codes):
    """Wrong: only checks the first code in the list, so UNK slips through."""
    if value == codes[0]:
        return None
    return value


def _cv_changes_values(value, codes):
    """Wrong: empties the codes, but hands every other value back in capitals."""
    if value in codes:
        return None
    return value.upper()


@pytest.mark.parametrize("func", [lambda v, c: None if v in c else v, lambda v, c: None if v.strip().upper() in c else v],
                         ids=["in", "upper-in"])
def test_p2_ex3_passes_a_clean_value_that_agrees_with_course_1(func):
    """Exercise 3: empty (None) exactly where apply_null_tokens empties a value, every other value unchanged."""
    assert said(check.p2_ex3, func).startswith("✅")


def test_p2_ex3_explains_what_is_wrong():
    """Blank: asks. A missed code or a changed value: ❌ naming the value. An error: shows it."""
    assert said(check.p2_ex3, _cv_blank).startswith("✏️")
    missed = said(check.p2_ex3, _cv_first_code_only)
    assert missed.startswith("❌") and "'UNK'" in missed
    changed = said(check.p2_ex3, _cv_changes_values)
    assert changed.startswith("❌") and "as it was" in changed
    boom = said(check.p2_ex3, lambda v, c: v.nope())
    assert boom.startswith("❌") and "AttributeError" in boom


def test_p2_ex3_checks_even_a_value_that_appears_once(raw):
    """Every different value is tried, not only common ones: a function wrong on one rare value fails."""
    counts = cleaning.strip_and_null(raw)["intake_time"].value_counts()
    rare = counts[counts == 1].index[0]
    wrong_once = lambda v, c: "WRONG" if v == rare else (None if v in c else v)   # noqa: E731
    text = said(check.p2_ex3, wrong_once)
    assert text.startswith("❌") and repr(rare) in text


def test_p2_payoff_counts_the_codes_like_part_0s_step_3(raw):
    """The payoff: the student's clean_value over the four columns finds the same don't-know codes as
    apply_null_tokens, counted here straight from the raw file."""
    total = sum(int(raw[c].str.strip().str.upper().isin(v).sum()) for c, v in cleaning.NULL_TOKENS.items())
    text = said(check.p2_payoff, lambda v, c: None if v in c else v)
    assert text.startswith("✅") and f"{total:,}" in text
    assert said(check.p2_payoff, _cv_first_code_only).startswith("❌")
    blank = said(check.p2_payoff, _cv_blank)
    assert blank.startswith("✏️") and len(blank.splitlines()) == 1, blank


# ---- the part 3 checks (pandas), against course 1's strip_and_null -------------------------------------------------

def test_p3_ex1_is_custody_levels_written_as_nothing(raw):
    """Exercise 1: custody_level values with no characters at all, counted here value by value."""
    n = int(raw["custody_level"].map(len).eq(0).sum())
    assert said(check.p3_ex1, check.___).startswith("✏️")
    assert said(check.p3_ex1, n).startswith("✅")
    assert said(check.p3_ex1, n + 1).startswith("❌")


def test_p3_ex2_is_custody_levels_empty_once_stripped(raw):
    """Exercise 2: custody_level values that are nothing but spaces and tabs, the Trust Test's Q1 once cleaned."""
    n = int(sum(1 for v in raw["custody_level"] if not v.strip()))
    assert said(check.p3_ex2, check.___).startswith("✏️")
    assert said(check.p3_ex2, n).startswith("✅")
    assert said(check.p3_ex2, int((raw["custody_level"] == "").sum())).startswith("❌")


def _sn_good(df):
    """A correct strip_and_null, written the way part 3 teaches it."""
    out = df.copy()
    for col in out.columns:
        stripped = out[col].str.strip()
        out[col] = stripped.mask(stripped == "")
    return out


def _sn_strip_only(df):
    """Wrong: trims, but leaves the empty text instead of making it null."""
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].str.strip()
    return out


def _sn_blank(df):
    """A strip_and_null whose blank hasn't been filled in."""
    out = df.copy()
    for col in out.columns:
        stripped = check.___
        out[col] = stripped.mask(stripped == "")
    return out


def test_p3_ex3_passes_a_strip_and_null_that_matches_course_1():
    """Exercise 3: the same table as cleaning.strip_and_null, cell for cell."""
    assert said(check.p3_ex3, _sn_good).startswith("✅")


def test_p3_ex3_explains_what_is_wrong():
    """Blank: asks. Trimmed but not nulled: ❌ naming a column and the value. An error: shows it."""
    assert said(check.p3_ex3, _sn_blank).startswith("✏️")
    wrong = said(check.p3_ex3, _sn_strip_only)
    assert wrong.startswith("❌") and "''" in wrong
    boom = said(check.p3_ex3, lambda df: df.nope)
    assert boom.startswith("❌") and "AttributeError" in boom


def test_p3_payoff_answers_q1_with_the_students_table(raw):
    """The payoff: Q1 from the student's own table, against what merely looked empty, counted from the raw file."""
    looked = int((raw["custody_level"] == "").sum())
    really = int(sum(1 for v in raw["custody_level"] if not v.strip()))
    text = said(check.p3_payoff, _sn_good)
    assert text.startswith("✅") and f"{really:,}" in text and f"{looked:,}" in text
    assert said(check.p3_payoff, _sn_strip_only).startswith("❌")
    blank = said(check.p3_payoff, _sn_blank)
    assert blank.startswith("✏️") and len(blank.splitlines()) == 1, blank


# ---- the part 4 checks (patterns), against course 1's ID_PATTERN, profile_shapes and DATE_FORMATS -----------------

@pytest.mark.parametrize("pattern", [r"\d{8}", r"[0-9]{8}", r"\d\d\d\d\d\d\d\d"])
def test_p4_ex1_passes_any_pattern_for_exactly_8_digits(pattern):
    """Exercise 1: a pattern that accepts every ID in the file and refuses what course 1's ID_PATTERN refuses."""
    assert said(check.p4_ex1, pattern).startswith("✅")


def test_p4_ex1_explains_what_is_wrong():
    """Blank: asks. Too loose: names a value it lets through. Not a string, or broken: says so."""
    assert said(check.p4_ex1, check.___).startswith("✏️")
    loose = said(check.p4_ex1, r"\d+")
    assert loose.startswith("❌") and "'2381457'" in loose
    strict = said(check.p4_ex1, r"[0-8]{8}")   # too strict: refuses any ID with a 9 in it
    assert strict.startswith("❌") and "does not match yours" in strict
    assert "string" in said(check.p4_ex1, 8)
    broken = said(check.p4_ex1, "(")
    assert broken.startswith("❌") and "error" in broken


def _shape_good(text):
    """A correct shape(): digits become 9, letters become A."""
    text = re.sub(r"\d", "9", text)
    return re.sub(r"[A-Za-z]", "A", text)


def _shape_capitals_only(text):
    """Wrong: only capital letters become A, so 'February' keeps its small letters."""
    text = re.sub(r"\d", "9", text)
    return re.sub(r"[A-Z]", "A", text)


def _shape_blank(text):
    """A shape() whose blank hasn't been filled in."""
    text = re.sub(r"\d", "9", text)
    text = check.___
    return text


def test_p4_ex2_passes_a_shape_function_that_matches_profile_shapes():
    """Exercise 2: the same shapes, with the same counts, as course 1's dates.profile_shapes."""
    assert said(check.p4_ex2, _shape_good).startswith("✅")


def test_p4_ex2_explains_what_is_wrong():
    """Blank: asks. Small letters left alone: ❌ naming a value. An error: shows it."""
    assert said(check.p4_ex2, _shape_blank).startswith("✏️")
    wrong = said(check.p4_ex2, _shape_capitals_only)
    assert wrong.startswith("❌") and "shape(" in wrong
    one_shape = said(check.p4_ex2, lambda t: "99/99/9999")   # always a real shape, but the wrong one
    assert one_shape.startswith("❌") and "counts" in one_shape
    boom = said(check.p4_ex2, lambda t: t.nope())
    assert boom.startswith("❌") and "AttributeError" in boom


def test_p4_ex3_is_the_pattern_for_year_month_day():
    """Exercise 3: a pattern that matches exactly the dates course 1 labels YYYY-MM-DD, not the ones with a time."""
    assert said(check.p4_ex3, check.___).startswith("✏️")
    assert said(check.p4_ex3, r"\d{4}-\d{2}-\d{2}").startswith("✅")
    with_time = said(check.p4_ex3, r"\d{4}-\d{2}-\d{2}.*")
    assert with_time.startswith("❌") and "00:00:00" in with_time


def test_p4_payoff_shows_the_shapes_of_every_date(raw):
    """The payoff: the student's shape() over the whole column, against the number of different dates in it."""
    dates_written = raw["projected_release_date"].str.strip()
    different = dates_written[dates_written != ""].nunique()
    text = said(check.p4_payoff, _shape_good)
    assert text.startswith("✅") and f"{different:,} different dates" in text
    assert said(check.p4_payoff, _shape_capitals_only).startswith("❌")
    blank = said(check.p4_payoff, _shape_blank)
    assert blank.startswith("✏️") and len(blank.splitlines()) == 1, blank


# ---- the part 5 checks (your own session 2), against course 1 -----------------------------------------------------

def _p5_clean_value(value, codes):
    """Part 2's clean_value, as a student would have it."""
    return None if value in codes else value


def _p5_null_codes(df):
    """A correct null_codes: part 2's clean_value over every column in the data dictionary."""
    out = df.copy()
    for column, codes in cleaning.NULL_TOKENS.items():
        out[column] = [_p5_clean_value(v, codes) for v in out[column]]
    return out


def _p5_first_column_only(df):
    """Wrong: stops after the dictionary's first column."""
    out = df.copy()
    for column, codes in cleaning.NULL_TOKENS.items():
        out[column] = [_p5_clean_value(v, codes) for v in out[column]]
        return out


def _p5_null_codes_blank(df):
    """A null_codes whose blank hasn't been filled in."""
    out = df.copy()
    for column, codes in cleaning.NULL_TOKENS.items():
        cleaned = check.___
        out[column] = cleaned
    return out


def _p5_session2(df):
    """A correct my_session2: parts 3, 2 and 1 in order."""
    df = _sn_good(df)
    df = _p5_null_codes(df)
    df["last_name_std"] = df["last_name"].dropna().map(lambda n: n.strip().upper())
    return df


def _p5_no_codes(df):
    """Wrong: skips step 2, so the don't-know codes stay."""
    df = _sn_good(df)
    df["last_name_std"] = df["last_name"].dropna().map(lambda n: n.strip().upper())
    return df


def _p5_no_key(df):
    """Wrong: forgets the match key."""
    return _p5_null_codes(_sn_good(df))


def _p5_session2_blank(df):
    """A my_session2 whose blank hasn't been filled in."""
    df = check.___
    df = _p5_null_codes(df)
    return df


def test_p5_ex1_passes_null_codes_that_matches_apply_null_tokens():
    """Exercise 1: after strip_and_null, the same table as course 1's apply_null_tokens."""
    assert said(check.p5_ex1, _p5_null_codes).startswith("✅")


def test_p5_ex1_explains_what_is_wrong():
    """Blank: asks. A column left out: ❌ naming it. An error: shows it."""
    assert said(check.p5_ex1, _p5_null_codes_blank).startswith("✏️")
    wrong = said(check.p5_ex1, _p5_first_column_only)
    assert wrong.startswith("❌") and "intake_time" in wrong   # the first column it left out, in table order
    boom = said(check.p5_ex1, lambda df: df.nope)
    assert boom.startswith("❌") and "AttributeError" in boom


def test_p5_ex2_passes_a_pipeline_that_matches_course_1():
    """Exercise 2: every column course 1 has after those steps, plus last_name_std on names without accents."""
    assert said(check.p5_ex2, _p5_session2).startswith("✅")


def test_p5_ex2_explains_what_is_wrong():
    """Blank: asks. A step missed: ❌ showing a code left in. The match key missing: ❌ naming it."""
    assert said(check.p5_ex2, _p5_session2_blank).startswith("✏️")
    no_codes = said(check.p5_ex2, _p5_no_codes)
    assert no_codes.startswith("❌") and "'99:99'" in no_codes   # the first code left in, in table order
    no_key = said(check.p5_ex2, _p5_no_key)
    assert no_key.startswith("❌") and "last_name_std" in no_key


def test_p5_payoff_answers_three_questions_like_course_1(raw):
    """The payoff: Q1, Q3 and missing disciplinary points from the student's own table, counted here from the raw
    file."""
    empty = lambda col: int(sum(1 for v in raw[col] if not v.strip()))   # noqa: E731
    q1 = empty("custody_level")
    points = empty("disciplinary_points") + int((raw["disciplinary_points"].str.strip() == "N/A").sum())
    kents = int((raw["last_name"].str.strip().str.upper() == "KENT").sum())
    text = said(check.p5_payoff, _p5_session2)
    assert text.startswith("✅") and f"{q1:,}" in text and f"{points:,}" in text and f"{kents} records named KENT" in text
    assert said(check.p5_payoff, _p5_no_codes).startswith("❌")
    blank = said(check.p5_payoff, _p5_session2_blank)
    assert blank.startswith("✏️") and len(blank.splitlines()) == 1, blank


@pytest.mark.parametrize("answer", [["my_strip_and_null", "clean_value"], ["clean_value", "strip_and_null"],
                                    [_sn_good, _p5_clean_value]], ids=["names", "other-order", "functions"])
def test_p5_ex3_takes_the_two_functions_however_they_are_named(answer):
    """Exercise 3: course 2's one SQL line does strip_and_null's and clean_value's jobs, in either order; a function
    is known by its name, with or without my_ (the test's own copies are named after what they stand for)."""
    if answer[0] is _sn_good:
        answer = [type("F", (), {"__name__": "my_strip_and_null"})(), type("F", (), {"__name__": "clean_value"})()]
    assert said(check.p5_ex3, answer).startswith("✅")


def test_p5_ex3_explains_what_is_wrong():
    """Blank: asks. The wrong pair: ❌. One name, not a list: says to use a list."""
    assert said(check.p5_ex3, check.___).startswith("✏️")
    assert said(check.p5_ex3, ["match_key", "clean_value"]).startswith("❌")
    assert "list" in said(check.p5_ex3, "clean_value")


# ---- the notebook ------------------------------------------------------------------------------------------------

def answers(nb) -> dict:
    """{name: code} from the notebook's Answers section: each fenced block assigns one name (its first line)."""
    start = next(i for i, c in enumerate(nb.cells) if c.cell_type == "markdown" and c.source.startswith("## Answers"))
    out = {}
    for cell in nb.cells[start:]:
        if cell.cell_type == "markdown":
            for code in ANSWER.findall(cell.source):
                out[re.match(r"\s*(\w+)\s*=", code).group(1)] = code.rstrip("\n")
    return out


def filled(nb):
    """A copy of the notebook with each `name = ___` line replaced by that name's answer."""
    nb = nbformat.reads(nbformat.writes(nb), as_version=4)
    given = answers(nb)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.source = BLANK_LINE.sub(lambda m: m.group(1) + given[m.group(2)] if m.group(2) in given
                                         else m.group(0), cell.source)
    return nb


def run(path, nb) -> list:
    """Run a notebook top to bottom in its own folder; returns every check's printed verdict, in order."""
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(path.parent)}}).execute()
    verdicts = []
    for cell in nb.cells:
        if cell.cell_type == "code" and re.search(r"check\.p\d_", cell.source):
            verdicts.append("".join(o.get("text", "") for o in cell.get("outputs", [])
                                    if o.get("output_type") == "stream").strip())
    return verdicts


def test_every_part_is_tested():
    """Each notebook in python/ is listed in PARTS, so none ships untested."""
    assert sorted(ROOT.glob("python/*.ipynb")) == sorted(PARTS)


@pytest.mark.parametrize("path", PARTS, ids=lambda p: p.stem)
def test_part_ships_clean_with_an_answer_for_every_blank(path):
    """Stored without outputs, like course 1's notebooks; its blanks are the expected ones, each answered at the
    bottom."""
    nb = nbformat.read(path, as_version=4)
    code = [c for c in nb.cells if c.cell_type == "code"]
    assert code and not any(c.outputs or c.execution_count for c in code)
    blanks = {m.group(2) for c in code for m in BLANK_LINE.finditer(c.source)}
    assert blanks == PARTS[path][0] and blanks <= set(answers(nb))


@pytest.mark.parametrize("path", PARTS, ids=lambda p: p.stem)
def test_part_as_delivered_runs_and_every_check_asks_for_an_answer(path):
    """Blanks in place: no error anywhere, and every check prints its 'Replace ___' prompt."""
    verdicts = run(path, nbformat.read(path, as_version=4))
    assert len(verdicts) == PARTS[path][1] and all("Replace ___" in v for v in verdicts), verdicts


@pytest.mark.parametrize("path", PARTS, ids=lambda p: p.stem)
def test_part_with_the_answers_filled_in_every_check_passes(path):
    """The Answers section's code in place of each blank: every check says ✅."""
    verdicts = run(path, filled(nbformat.read(path, as_version=4)))
    assert len(verdicts) == PARTS[path][1] and all(v.startswith("✅") for v in verdicts), verdicts
