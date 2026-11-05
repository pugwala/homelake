"""Tests for the Python mini-course (python/), which sits between course 1 and course 2.

Run them without Databricks, in the course's Jupyter image (the data is built on first use, about 5 seconds):

    docker run --rm -u "$(id -u)" -v ~/homelake:/repo -w /repo -e PYTHONPATH=/repo -e LNL_DATA_DIR=/tmp/lnl_data \
        --entrypoint pytest lnl-jupyter:local -q -p no:cacheprovider tests/test_python_course.py

Covered here:
  - lnl/inside.py, the helpers part 0 uses to open course 1's one-line steps and show what each step changed;
  - the part 0 checks in lnl/check.py, graded against the course data, never against a stored number;
  - the part 1 checks (strings), graded against course 1's last_name_std;
  - the part 2 checks (lists, dictionaries, loops, if), graded against course 1's apply_null_tokens;
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
