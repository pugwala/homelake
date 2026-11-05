# Python mini-course: the Python behind course 1's cleaning

Updated 2026-11-04

A short course for between course 1 and course 2, for people who are new to Python. Course 1 showed what clean data is
worth; this shows how the code that cleaned it works. Each part starts from a result students already saw in course 1,
then teaches only the Python needed to rebuild it. Exercises are checked against course 1's own functions on the
course data, so if course 1's code changes, the checks change with it.

> ⚠️ **Mock data only.** Everything in this course is fictional.

| Part | Notebook | Starts from (the value) | Python taught (the how) |
| --- | --- | --- | --- |
| 0 | `00_open_the_box.ipynb` | `cleaning.session2(df)`, the one line from course 1 | None: a function is a named recipe; run its six steps by hand and see what each changed |
| 1 | `01_strings.ipynb` | Trust Test Q3: no KENTs as written, 3 after session 2 | Variables, strings, methods, `==`, f-strings, a first function (`match_key`), `.map` |
| 2 | *planned* | The "don't know" codes (`N/A`, `UNK`, `99:99`) | Lists, dictionaries, `for`, `if` |
| 3 | *planned* | The same count in one line | pandas: a column, `.str`, `value_counts`, filtering; write `strip_and_null` |
| 4 | *planned* | Course 1's IDs and date formats | Reading, then writing, patterns (regular expressions) |
| 5 | *planned* | "Your own session 2" | Chaining your functions; checking yours against course 1's; the same step in course 2's SQL |

Course 1's text sessions (6 and 7) aren't covered yet.

## Running it

The same as course 1: open the notebook from the course's Git folder in Databricks, attach it to the lab cluster, and
run top to bottom. The setup cell finds the course files and builds the data. Each 🧪 **Your turn** cell has a
`___` blank and a check that prints ✅ or ❌ with a hint; answers are at the bottom.

## Part 0 · Open the Box (about 30 minutes)

Students write no code. They:
1. run `cleaning.session2(raw)` again and see one record before and after (`inside.side_by_side`);
2. read the function's nine lines as a recipe (`inside.show`, `inside.recipe`);
3. run the six steps one per cell, with a plain-English report after each (`inside.report`);
4. confirm the six steps give the same table as the one line (`inside.same_table`);
5. read `strip_and_null` line by line: the four ideas parts 1 to 3 teach.

What the room should see (100,000 rows, seed 2026):

| Step | Report |
| --- | --- |
| 1 `strip_and_null` | Nulls 0 → 77,734 (**#1: 77734**) |
| 2 `set_record_id` | Rows labeled by offender_number; 97,003 SIDs rewritten as numbers |
| 3 `apply_null_tokens` | Nulls +6,122 (**#2: 6122**) |
| 4 `repair_text_columns` | 8,067 values rewritten (conduct notes 7,908, last names 159) |
| 5 `standardize_names` | 3 new `_std` columns (**#3: `"standardize_names"`**) |
| 6 `standardize_domains` | 11 new columns |

**Points worth a pause:**
- Typing `77,734` with a comma: Python reads that as two numbers. The check says so; it's a good first lesson.
- Step 3's codes come from the data dictionary (`cleaning.NULL_TOKENS`), not from guessing: `NONE` in
  `housing_restriction` is a real answer and stays.
- Running steps one at a time is also how you find a wrong number later: see which step changed it.

## Part 1 · Strings (about 45 minutes)

Students write their first function. They:
1. see Q3 asked two ways: an exact match on `KENT` finds 0 records, session 2 finds 3 (`Kent`, `kent`, `kEnT`), and
   GARCIA is typed 31 ways;
2. meet strings and variables (`name = "gArCiA"`, `len`, `+`, brackets to make spaces visible);
3. use methods (`.upper()`, `.lower()`, `.title()`, `.strip()`), which hand back a new string and never change the old one;
4. ask questions with `==` (and see why `=` isn't that);
5. build text with f-strings, and see where `.title()` goes wrong (`Mcdonald`, `Worthington Iii`) and course 1's
   `display_name` doesn't;
6. write `match_key(name)`, checked against course 1's `last_name_std` on every different last name without accents;
7. run it on all 100,000 last names with `.map`, then read `standardize_names` to see the same idea.

What the room should see:

| Exercise | Answer | The check says |
| --- | --- | --- |
| #1 | `name.upper()` | GARCIA |
| #2 | `name.upper() == "GARCIA"` | True |
| #3 | `key = name.strip().upper()` | agrees on all 9,125 different last names without accents |
| Payoff | (no blank) | 9,619 spellings become 379 names; 3 records named KENT, as session 2 found |

**Points worth a pause:**
- `=` names a value; `==` asks a question. Mixing them up is the most common first error.
- `" ".join(name.upper().split())` also passes #3: `split()` drops spaces and tabs at both ends too. Worth showing
  if someone finds it.
- The 379 names include one empty name: the last names that were only spaces and tabs. Session 2 makes those null
  instead, which part 2's "don't know" codes build on.
- Accented names were left out of the check on purpose: `fold_accents` handles them, and the notebook says so.

## Tests

`tests/test_python_course.py` covers the helpers (`lnl/inside.py`), the checks (`check.p0_*`, `check.p1_*`) and
every part's notebook, each run top to bottom twice: blanks in place (every check asks for an answer) and answers
filled in (every check passes). A notebook added to `python/` without a test fails it.
It needs no Databricks; the command is at the top of the file.
