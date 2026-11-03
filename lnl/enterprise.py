"""Enterprise track helpers for course 1 (00-02): object names, SQL that prints itself, the first delivery, the
pipeline, and the handover of the next deliveries to course 2.

Runs only on a Databricks workspace with Unity Catalog. Everything it creates lives in one schema you own
(lnl/config.py: ENTERPRISE_CATALOG and ENTERPRISE_SCHEMA), so you can delete it with one
DROP SCHEMA ... CASCADE, plus the pipeline, which is named after you. Course 2 (pugwala/lakehouse, enterprise/)
carries on from here with its own helpers: the next delivery, governance, the job and alerts, monitoring.
"""
import hashlib
import json
import re
import textwrap
import time
from pathlib import Path

from . import config, env

PIPELINE_FILE = "enterprise/pipeline/hero_offenders.py"
REFERENCE_TABLES = ["race_crosswalk", "religion_crosswalk", "stg_groups", "nibrs_offenses", "violence_codes",
                    "unit_crosswalk"]
LANDING_FOLDER = "hero_offenders"     # the pipeline reads every file in here
HANDOFF_FOLDER = "handoff/deliveries" # the next deliveries, staged for course 2 with a manifest
DELIVERIES = {2: 0, 3: 3}             # batch number: offender numbers a broken export cut short
TERMINAL_UPDATE_STATES = {"COMPLETED", "FAILED", "CANCELED"}


# ---- Names -----------------------------------------------------------------------------------------
def _spark():
    from .spark import get_spark
    return get_spark()


def user_email() -> str:
    return _spark().sql("SELECT current_user()").first()[0]


def user_slug() -> str:
    return re.sub(r"[^a-z0-9]+", "_", user_email().split("@")[0].lower()).strip("_")


def names() -> dict:
    """Every name the track uses, built from lnl/config.py."""
    slug = user_slug()
    catalog = config.ENTERPRISE_CATALOG
    schema = config.ENTERPRISE_SCHEMA.format(user=slug)
    fq = f"{catalog}.{schema}"
    volume = f"/Volumes/{catalog}/{schema}/{config.ENTERPRISE_VOLUME}"
    return {
        "catalog": catalog, "schema": schema, "fq": fq,
        "volume_name": f"{fq}.{config.ENTERPRISE_VOLUME}", "volume": volume,
        "landing": f"{volume}/{LANDING_FOLDER}", "handoff": f"{volume}/{HANDOFF_FOLDER}",
        "pipeline": f"lnl_hero_offenders_{slug}",
    }


def course_paths() -> dict:
    """The course's Git folder as a file path (/Workspace/...) and as a workspace object path (/Users/...)."""
    fs = str(env.REPO_ROOT)
    ws = fs[len("/Workspace"):] if fs.startswith("/Workspace/") else fs
    return {"fs": fs, "ws": ws}


def prepare(step: int, title: str) -> dict:
    """Run at the top of every enterprise notebook."""
    if not env.IS_DATABRICKS:
        raise RuntimeError("The enterprise track runs on an enterprise Databricks workspace (Unity Catalog). "
                           "Use the session notebooks for practice anywhere else.")
    env._check_core()
    if step > 0 and not config.ENTERPRISE_CATALOG:
        raise RuntimeError("Set ENTERPRISE_CATALOG in lnl/config.py first. 00_preflight shows what you can use.")
    n = names() if config.ENTERPRISE_CATALOG else {}
    print(f"Enterprise track {step}: {title}")
    print(f"  Environment : {env.environment_name()}")
    print(f"  You         : {user_email()}")
    if n:
        print(f"  Schema      : {n['fq']}")
        print(f"  Landing     : {n['landing']}")
    print("  Mock data only. Never point these notebooks at real offender data without the data owner's approval.")
    return n


def sql(statement: str, quiet: bool = False):
    """Run one SQL statement, printing it first, so every step is SQL you can read and reuse."""
    text = textwrap.dedent(statement).strip()
    if not quiet:
        print(text + ";\n")
    return _spark().sql(text)


def set_tags(statement: str):
    """Run one SET TAGS statement. If the account already defines one of these keys as a governed tag, you need
    ASSIGN on it and one of its allowed values; the course carries on without the tag instead of stopping."""
    try:
        return sql(statement, quiet=True)
    except Exception as exc:
        print(f"⚠️  Tag not set ({str(exc).splitlines()[0][:140]}). If this key is a governed tag in your "
              "account, it needs ASSIGN permission and an allowed value. The rest of the notebook works without it.")


def check(label: str, ok, detail: str = "") -> bool:
    """One line of a checklist: ✅ passed, ⚠️ needs attention."""
    print(f"{'✅' if ok else '⚠️ '} {label}{': ' + detail if detail else ''}")
    return bool(ok)


# ---- Files in the landing volume -------------------------------------------------------------------
def land_full_dataset(n: dict) -> str:
    """Generate the course's 100,000 records straight into the landing folder as batch_001.csv.
    The conduct-notes answer key goes in a separate folder, so the pipeline never reads it as data."""
    import importlib
    import sys
    target = Path(n["landing"]) / "batch_001.csv"
    if target.exists():
        print(f"Already landed: {target}")
        return str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    key_dir = Path(n["volume"]) / "answer_key"
    key_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(env.REPO_ROOT / "generator"))
    gen = importlib.import_module("gen_hero_offenders")
    start = time.time()
    gen.generate(rows=config.ROWS, out=str(target), seed=config.SEED,
                 answer_key=str(key_dir / "batch_001_answer_key.csv"))
    print(f"Landed {config.ROWS:,} records in {time.time() - start:.0f}s: {target}")
    return str(target)


def _delivery(number: int, rows: int, bad_ids: int, staging: Path):
    """One later delivery from the source system as a DataFrame: new incarcerations with new offender numbers
    (03xxxxxx), the same kinds of mess as batch 1. bad_ids > 0 cuts a digit from that many offender numbers, as a
    broken export would."""
    import importlib
    import sys
    import pandas as pd
    sys.path.insert(0, str(env.REPO_ROOT / "generator"))
    gen = importlib.import_module("gen_hero_offenders")
    tmp = staging / f"batch_{number:03d}_full.csv"
    gen.generate(rows=rows + 20, out=str(tmp), seed=config.SEED + number, answer_key=str(staging / "key.csv"))
    df = pd.read_csv(tmp, dtype=str, keep_default_na=False, na_filter=False)
    famous = {r[0] for r in gen.REVIEWED}                       # fixed records that would repeat batch 1's IDs
    df = df[~df["offender_number"].isin(famous)].head(rows).reset_index(drop=True)
    base = 3_000_000 + (number - 2) * 100_000
    df["offender_number"] = [f"{base + i + 1:08d}" for i in range(len(df))]
    for i in range(min(bad_ids, len(df))):
        df.loc[i * 7, "offender_number"] = df.loc[i * 7, "offender_number"][1:]   # 7 digits: a broken export
    for leftover in (tmp, staging / "key.csv"):
        leftover.unlink(missing_ok=True)
    return df


def stage_deliveries(n: dict, rows: int = 1_000) -> dict:
    """Hand the next deliveries over to course 2: write batch_002.csv and batch_003.csv (DELIVERIES) into the
    handoff folder of your volume, with manifest.json giving each file's row count and SHA-256. Nothing lands in the
    pipeline's folder: course 2 checks each fingerprint and lands them itself. Safe to run again: the same seed
    makes the same files. Returns the manifest."""
    folder = Path(n["volume"]) / HANDOFF_FOLDER
    staging = folder / "_staging"
    staging.mkdir(parents=True, exist_ok=True)
    files = {}
    for number, bad_ids in DELIVERIES.items():
        name = f"batch_{number:03d}.csv"
        df = _delivery(number, rows, bad_ids, staging)
        df.to_csv(folder / name, index=False)
        files[name] = {"rows": len(df), "broken_offender_numbers": bad_ids,
                       "sha256": hashlib.sha256((folder / name).read_bytes()).hexdigest()}
        print(f"Staged {name}: {len(df):,} records{f' ({bad_ids} with a broken offender number)' if bad_ids else ''}")
    staging.rmdir()
    manifest = {"from": "course 1, enterprise/02_pipeline", "seed": config.SEED, "files": files}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Handed over to course 2: {folder}")
    return manifest


# ---- The pipeline ----------------------------------------------------------------------------------
def _workspace():
    from databricks.sdk import WorkspaceClient
    return WorkspaceClient()


def _sdk_accepts(api: str, method: str, parameter: str) -> bool:
    """Whether the installed Databricks SDK has this parameter. Serverless environments ship different SDK
    versions (environment 4 has 0.49; pipeline tags arrived in 0.56)."""
    import inspect
    from databricks.sdk.service import pipelines
    cls = {"pipelines": pipelines.PipelinesAPI}[api]
    return parameter in inspect.signature(getattr(cls, method)).parameters


def pipeline_spec(n: dict) -> dict:
    from databricks.sdk.service import pipelines as P
    paths = course_paths()
    spec = {
        "name": n["pipeline"], "catalog": n["catalog"], "schema": n["schema"],
        "development": True, "continuous": False, "channel": "CURRENT",
        "libraries": [P.PipelineLibrary(file=P.FileLibrary(path=f"{paths['ws']}/{PIPELINE_FILE}"))],
        "configuration": {"lnl.course_root": paths["fs"], "lnl.landing_path": n["landing"],
                          "lnl.reference_schema": n["fq"]},
    }
    if _sdk_accepts("pipelines", "create", "tags"):        # databricks-sdk 0.56 and newer
        spec["tags"] = {"project": "homelake", "data": "mock"}
    if config.ENTERPRISE_SERVERLESS:
        spec["serverless"] = True
    else:   # classic compute: expectations need the ADVANCED edition
        spec["edition"] = "ADVANCED"
        spec["clusters"] = [P.PipelineCluster(label="default", num_workers=1,
                                              policy_id=config.ENTERPRISE_PIPELINE_POLICY_ID or None)]
    return spec


def ensure_pipeline(n: dict) -> str:
    """Create the pipeline, or update it if it already exists. Returns its ID."""
    w = _workspace()
    spec = pipeline_spec(n)
    existing = [p for p in w.pipelines.list_pipelines(filter=f"name LIKE '{n['pipeline']}'") if p.name == n["pipeline"]]
    if existing:
        pipeline_id = existing[0].pipeline_id
        w.pipelines.update(pipeline_id=pipeline_id, **spec)
        print(f"Updated pipeline {n['pipeline']} ({pipeline_id})")
    else:
        pipeline_id = w.pipelines.create(**spec).pipeline_id
        print(f"Created pipeline {n['pipeline']} ({pipeline_id})")
    return pipeline_id


def run_pipeline(pipeline_id: str, full_refresh: bool = False, timeout_minutes: int = 40) -> dict:
    """Start one update and wait for it to finish. Returns {'state', 'update_id'}."""
    w = _workspace()
    update_id = w.pipelines.start_update(pipeline_id, full_refresh=full_refresh).update_id
    print(f"Update {update_id} started{' (full refresh)' if full_refresh else ''}...", end=" ", flush=True)
    deadline = time.time() + timeout_minutes * 60
    state = None
    while time.time() < deadline:
        state = w.pipelines.get_update(pipeline_id, update_id).update.state.value
        if state in TERMINAL_UPDATE_STATES:
            break
        time.sleep(15)
    print(state)
    return {"state": state, "update_id": update_id}


def expectation_metrics(pipeline_id: str, update_id: str = None):
    """Passed and failed records per expectation, from the pipeline's event log (latest update by default)."""
    where = f"AND origin.update_id = '{update_id}'" if update_id else (
        f"AND origin.update_id = (SELECT origin.update_id FROM event_log('{pipeline_id}') "
        f"WHERE event_type = 'create_update' ORDER BY timestamp DESC LIMIT 1)")
    return sql(f"""
        SELECT e.dataset, e.name AS expectation, SUM(e.passed_records) AS passed, SUM(e.failed_records) AS failed
        FROM (
          SELECT explode(from_json(details:flow_progress:data_quality:expectations,
                 'array<struct<name: string, dataset: string, passed_records: bigint, failed_records: bigint>>')) AS e
          FROM event_log('{pipeline_id}')
          WHERE event_type = 'flow_progress' {where}
        )
        GROUP BY e.dataset, e.name
        ORDER BY failed DESC, dataset, expectation""")

