# Python mini-course: the Python behind course 1's cleaning

Updated 2026-11-05

A short course for between course 1 and course 2, for people who are new to Python. Course 1 showed what clean data is
worth; this shows how the code that cleaned it works. Each part starts from a result students already saw in course 1,
then teaches only the Python needed to rebuild it. Exercises are checked against course 1's own functions on the
course data, so if course 1's code changes, the checks change with it.

> ⚠️ **Mock data only.** Everything in this course is fictional.

| Part | Notebook | Starts from (the value) | Python taught (the how) |
| --- | --- | --- | --- |
| 0 | `00_open_the_box.ipynb` | `cleaning.session2(df)`, the one line from course 1 | None: a function is a named recipe; run its six steps by hand and see what each changed |
| 1 | `01_strings.ipynb` | Trust Test Q3: no KENTs as written, 3 after session 2 | Variables, strings, methods, `==`, f-strings, a first function (`match_key`), `.map` |
| 2 | `02_lists_and_loops.ipynb` | No disciplinary points recorded: 3,005 empty, but 5,851 really | Lists, dictionaries, `for`, `if`, `None`, a counter; write `clean_value`; read `apply_null_tokens` and `display_name` |
| 3 | `03_pandas.ipynb` | Trust Test Q1: 1,536 custody levels look empty, 2,991 are | DataFrame and Series, a question of every value, `.sum()`, `.str`, `.loc` filtering, `.mask`, `.isna()`; write `strip_and_null` |
| 4 | `04_patterns.ipynb` | Trust Test Q4: `01-01-2018` as text, `1999-11-02` really | Reading and writing patterns (`\d`, `{8}`, `[A-Za-z]`, `+`), `re.fullmatch`, `re.sub`; prove the IDs; write `shape` |
| 5 | `05_your_own_session_2.ipynb` | Q1, Q3 and missing disciplinary points, all wrong as written | A list made by a loop on one line; chaining functions into a pipeline; checking it against course 1; reading course 2's SQL |

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

## Part 2 · Lists, Dictionaries and Loops (about 45 minutes)

Students write the job of course 1's `apply_null_tokens`. They:
1. count the records with no disciplinary points recorded: 3,005 are empty, but another 2,846 say `N/A`, so the real
   answer is 5,851;
2. meet the data dictionary (`cleaning.NULL_TOKENS`) as a dictionary of lists;
3. use lists (`codes[0]`, `in`, `len`, `.append`, `" ".join`), then dictionaries (`tokens["intake_time"]`), and see
   that `housing_restriction` isn't in it because `NONE` there is a real answer;
4. loop with `for`, including over `.items()`, and decide with `if` / `else`; meet `None`;
5. write `clean_value(value, codes)`, checked against `apply_null_tokens` on every different value in the four
   columns;
6. run it with a loop inside a loop and a counter over the whole file: 6,122 codes, part 0's step 3;
7. read `apply_null_tokens` and `display_name` line by line (`elif`, `enumerate`, `isinstance`, `not`).

What the room should see:

| Exercise | Answer | The check says |
| --- | --- | --- |
| #1 | `len(codes)` | 2 |
| #2 | `tokens["intake_time"]` | `['99:99']` |
| #3 | `unknown = value in codes` | agrees on all 9,906 different values in the four columns |
| Payoff | (no blank) | 6,122 codes: disciplinary_points 2,846, escape_risk 923, intake_time 1,976, protective_custody 377 |

**Points worth a pause:**
- Python counts from 0: `codes[0]` is the first code. Expect someone to try `codes[2]` and get an error; let them.
- `value.upper() in codes` also passes #3. The file has no lowercase codes today, but course 1 capitalizes first in
  case a future file does: a good habit, not a need.
- The loop over the whole file takes a second or two for about 388,000 checks. Part 3's one-line pandas version does
  the same faster, which is why course 1 uses it.

## Part 3 · pandas (about 45 minutes)

Students write course 1's `strip_and_null`, as part 0 promised. They:
1. look at Q1's column as a list: `'G2'` to `'G5'`, then `''`, `'  '`, `'       '`...;
2. meet the DataFrame and the Series (`raw.shape`, `raw["custody_level"]`);
3. ask a question of every value (`custody == "G2"`) and count with `.sum()`: part 2's loop and counter, in one line;
4. use `.str.strip()` on a whole column, filter rows with `.loc`, and empty values with `.mask`;
5. finish `my_strip_and_null`, checked against course 1's on all 2,700,000 cells;
6. answer Q1 from their own table, then read course 1's version: theirs, line for line, apart from `text_columns`.

What the room should see:

| Exercise | Answer | The check says |
| --- | --- | --- |
| #1 | `(custody == "").sum()` | 1536 |
| #2 | `(custody.str.strip() == "").sum()` | 2991 |
| #3 | `stripped = out[col].str.strip()` | the same table as course 1, all 2,700,000 cells |
| Payoff | (no blank) | Q1: 2,991 missing, not the 1,536 that looked empty; 77,734 values made empty (part 0, step 1) |

**Points worth a pause:**
- `True` counts as 1. That one fact turns "how many?" into `.sum()`.
- pandas is about twice as fast as part 2's loop on one column, which isn't the point. The point is one line instead of
  a loop and a counter, with fewer places to go wrong.
- Course 1 loops over `text_columns(out)`, not `out.columns`, so it still works once later sessions add numbers and
  dates.

## Part 4 · Patterns (about 45 minutes)

Students read and write the patterns behind course 1's ID proof and date formats. They:
1. see Q4 asked of the dates as written (`01-01-2018`, text sorted by its first character) and after session 3
   (`1999-11-02`), then a sample of the 45,025 different dates;
2. learn the pattern pieces course 1 uses (`\d`, `{8}`, `{1,2}`, `[A-Za-z]`, `+`) and `re.fullmatch`;
3. see the naive load turn `02381457` into `2381457` (Q5), then write the ID pattern and read `set_record_id`'s proof;
4. write `shape()` with `re.sub` (digits to 9, letters to A), checked against `dates.profile_shapes`;
5. watch 45,025 dates collapse into 26 shapes, read `DATE_FORMATS`' nine patterns, write the `YYYY-MM-DD` one and
   read `classify_formats`.

What the room should see:

| Exercise | Answer | The check says |
| --- | --- | --- |
| #1 | `r"\d{8}"` | agrees with `ID_PATTERN` on all 186,885 IDs and near-misses |
| #2 | `text = re.sub(r"[A-Za-z]", "A", text)` | course 1's `profile_shapes` table exactly: 26 shapes |
| Payoff | (no blank) | 45,025 different dates, 26 shapes, 9 patterns recognize every one |
| #3 | `r"\d{4}-\d{2}-\d{2}"` | exactly the dates course 1 reads as YYYY-MM-DD |

**Points worth a pause:**
- Every ID in the file passes. The pattern isn't there to find bad IDs today; it's the proof course 1 demands before
  converting any, and `raise` stops the pipeline the day one fails.
- `fullmatch` matters: `r"\d{4}-\d{2}-\d{2}"` must not match `2027-01-17 00:00:00`. With `re.search` it would.
- Recognizing a format isn't reading a date: `02/30/2020` has the right shape but no such day. Session 3 flags those.

## Part 5 · Your Own Session 2 (about 45 minutes)

Students chain their own functions into a pipeline and prove it against course 1. They:
1. ask three questions of the raw file and get three wrong answers (1,536 missing custody levels, 1,457 with no
   disciplinary points, 0 KENTs);
2. start from their own `match_key`, `clean_value` and `my_strip_and_null`, given filled in so everyone starts equal;
3. write `null_codes` with a list made by a loop on one line, checked against `apply_null_tokens` on 2,700,000 cells;
4. chain `my_session2` (strip and null, the codes, the match key), checked against course 1 on every cell;
5. get all three answers right from their own table: 2,991, 5,851 and 3, the same as course 1;
6. read course 2's `w_text` SQL macro (quoted as text, dated) and say which two of their functions it does.

What the room should see:

| Exercise | Answer | The check says |
| --- | --- | --- |
| #1 | `cleaned = [clean_value(v, codes) for v in out[column]]` | course 1's apply_null_tokens table, all 2,700,000 cells |
| #2 | `df = my_strip_and_null(df)` | matches course 1 on all 2,700,000 cells and last_name_std without accents |
| Payoff | (no blank) | 2,991 missing custody levels, 5,851 with no disciplinary points, 3 KENTs, as course 1 |
| #3 | `["my_strip_and_null", "clean_value"]` | trim and nullif are strip_and_null; CASE WHEN ... IN is clean_value |

**Points worth a pause:**
- `.dropna().map(match_key)` then assigned back: pandas puts each result on its own row, so the left-out rows stay
  empty. It's the first time students see rows lined up by label rather than position.
- Course 2's list of codes includes `NONE`, which course 1's file treats as a real answer. Lists of codes belong to a
  source and its data owner, not to the language.
- The SQL is quoted, not run: course 1 doesn't depend on course 2. If course 2's macro changes, update the quote and
  its date.
- The closing lesson is the one every part used: check your code against something you trust, cell by cell.

## Tests

`tests/test_python_course.py` covers the helpers (`lnl/inside.py`), the checks (`check.p0_*` to `check.p5_*`) and
every part's notebook, each run top to bottom twice: blanks in place (every check asks for an answer) and answers
filled in (every check passes). A notebook added to `python/` without a test fails it.
It needs no Databricks; the command is at the top of the file.
