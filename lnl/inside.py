"""Python mini-course, part 0: open the box. Helpers for looking inside course 1's one-line steps.

Course 1 ran each session's cleaning in one line, cleaning.session2(df). These helpers open that line up:
show() prints a function's own code, recipe() lists the steps it runs, and report() says in plain English what one
step did to the table. Nothing here changes any data.
"""
import ast
import inspect
import textwrap

import pandas as pd

SHOWN_WIDTH = 40   # side_by_side() shortens longer values to this many characters


def show(func) -> None:
    """Print a function's own code, each line numbered from 1."""
    lines = textwrap.dedent(inspect.getsource(func)).rstrip("\n").splitlines()
    width = len(str(len(lines)))
    for n, line in enumerate(lines, 1):
        print(f"{n:>{width}} | {line}")


def recipe(func) -> list:
    """The names of the steps a function runs its table through, in order: every `df = step(df)` and
    `return step(df)` line in its body."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    steps = []
    for node in tree.body[0].body:
        call = node.value if isinstance(node, (ast.Assign, ast.Return)) else None
        if isinstance(call, ast.Call):
            f = call.func
            steps.append(f.attr if isinstance(f, ast.Attribute) else f.id)
    return steps


def _differs(before: pd.Series, after: pd.Series) -> pd.Series:
    """True where a cell changed: it became or stopped being empty, or its text changed (including its type, so
    "02381457" turned into the number 2381457 counts)."""
    b, a = before.reset_index(drop=True), after.reset_index(drop=True)
    b_null, a_null = b.isna(), a.isna()
    both = ~b_null & ~a_null
    text_differs = pd.Series(False, index=b.index)
    text_differs[both] = b[both].map(repr).to_numpy() != a[both].map(repr).to_numpy()
    return (b_null != a_null) | text_differs


def _nulls(df: pd.DataFrame) -> int:
    """How many cells are empty (null)."""
    return int(df.isna().sum().sum())


def what_changed(before: pd.DataFrame, after: pd.DataFrame) -> list:
    """What one step did to a table, as plain sentences: rows, row labels, columns added and gone, empty values,
    and how many values were rewritten (compared row by row, so only when no rows came or went)."""
    lines = [f"Rows: {len(before):,} (no change)" if len(before) == len(after)
             else f"Rows: {len(before):,} → {len(after):,}"]
    label = after.index.name
    if label and label != before.index.name:
        lines.append(f"Rows are now labeled by {label} (it left the columns)")
    added = [c for c in after.columns if c not in before.columns]
    gone = [c for c in before.columns if c not in after.columns and c != label]
    if added:
        lines.append(f"New columns ({len(added)}): {', '.join(added)}")
    if gone:
        lines.append(f"Columns gone ({len(gone)}): {', '.join(gone)}")
    n0, n1 = _nulls(before), _nulls(after)
    lines.append(f"Empty values (nulls): {n0:,} (no change)" if n0 == n1
                 else f"Empty values (nulls): {n0:,} → {n1:,} ({n1 - n0:+,})")
    if len(before) == len(after):
        per_column = {c: int(_differs(before[c], after[c]).sum()) for c in before.columns if c in after.columns}
        per_column = {c: n for c, n in sorted(per_column.items(), key=lambda kv: -kv[1]) if n}
        total = sum(per_column.values())
        if not total:
            lines.append("Values rewritten: none")
        else:
            top = ", ".join(f"{c}: {n:,}" for c, n in list(per_column.items())[:3])
            more = ", ..." if len(per_column) > 3 else ""
            word = "column" if len(per_column) == 1 else "columns"
            lines.append(f"Values rewritten: {total:,}, in {len(per_column)} {word} ({top}{more})")
    return lines


def report(before: pd.DataFrame, after: pd.DataFrame) -> None:
    """Print what_changed() as a short bulleted list."""
    print("What changed:")
    for line in what_changed(before, after):
        print(f"  • {line}")


def _shown(value) -> str:
    """A value as the side-by-side shows it: text in quotes so stray spaces show, an empty value as (empty)."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return "(empty)"
    text = f'"{value}"' if isinstance(value, str) else str(value)
    return text if len(text) <= SHOWN_WIDTH else text[:SHOWN_WIDTH - 1] + "…"


def side_by_side(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """One record before and after, column by column: the record with the most values rewritten. A column that
    became the row labels is shown from the labels, and the columns the step added come last."""
    shared = [c for c in before.columns if c in after.columns]
    changed = sum(_differs(before[c], after[c]).astype(int) for c in shared)
    row = int(changed.to_numpy().argmax())
    label = after.index.name
    rows = {}
    for c in before.columns:
        if c in after.columns:
            rows[c] = (_shown(before[c].iloc[row]), _shown(after[c].iloc[row]))
        elif c == label:
            rows[c] = (_shown(before[c].iloc[row]), _shown(after.index[row]))
    for c in after.columns:
        if c not in before.columns:
            rows[c] = ("(new column)", _shown(after[c].iloc[row]))
    return pd.DataFrame.from_dict(rows, orient="index", columns=["as written", "after"])


def same_table(a: pd.DataFrame, b: pd.DataFrame) -> None:
    """Print ✅ when two tables match cell for cell, with the same columns and row labels, else ❌. It only prints, so
    the notebook shows no stray True or False under the verdict."""
    same = a.equals(b) and list(a.columns) == list(b.columns) and a.index.name == b.index.name
    print("✅ The same table, cell for cell." if same else "❌ Not the same table.")
