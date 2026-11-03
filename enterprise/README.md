# Enterprise Track: The Course on an Enterprise Databricks Workspace

The seven sessions teach data cleansing on Databricks Free Edition, where you get a notebook, a Spark session and not much else. This track takes the same cleansing rules and runs them the way the agency workspace is built to: data in Unity Catalog, rules enforced by a Lakeflow pipeline, sensitive columns masked by the platform, a scheduled job that pages someone when the data goes bad, and monitoring that catches what nobody wrote a check for.

It's for people who finished the sessions (or at least sessions 1-5) and want to be fluent on the enterprise platform before they touch a real table.

**Mock data only.** Everything here runs on the course's fictional hero offender records. The agency workspace is approved for criminal justice information, but that doesn't make these notebooks approved for real tables. See [Before you point this at real tables](#before-you-point-this-at-real-tables).

## What you'll build

| Notebook | What you learn | What it creates | Time |
|---|---|---|---|
| `00_preflight` | What this workspace lets you do, and exactly what to ask an admin for | nothing (read-only checks) | 10 min |
| `01_unity_catalog` | Catalogs, schemas, volumes, managed tables, comments, tags, grants | your schema, a landing volume with the first delivery, the crosswalks as `ref_*` tables | 20 min |
| `02_pipeline` | Declarative pipelines, bronze/silver/gold, expectations (warn, drop, fail), schema drift, the event log, and handing the next deliveries over | the pipeline and its tables, including `silver_quarantine`, and the handoff folder | 40 min |

Run them in order. Each one takes a lunch hour or less, and each picks up what the one before it built.

Course 2, [pugwala/lakehouse](https://github.com/pugwala/lakehouse), carries on from here in its own `enterprise/` folder: the next delivery (incremental loads), governance (masks, row filters, the published view), a scheduled job that alerts, and monitoring. It starts from the pipeline you built here and the deliveries 02 hands over; it never runs this course's code.

## How it maps to the sessions

| Session | On Free Edition | On the agency workspace |
|---|---|---|
| 1 · Meet the Mess | Profile the raw file | The file lands in a volume as a delivery; Auto Loader reads it, every column as text, into `bronze_offenders` |
| 2 · Cleansing | Strip and null, valid IDs, crosswalks, checks across records | Crosswalks become governed `ref_*` tables. An invalid ID is a drop expectation, with the record kept in `silver_quarantine` for the data owner. Unmapped codes are warn expectations and `gold_domain_exceptions`. Conflicts are `gold_race_conflicts` and `gold_offense_violence_conflicts` |
| 3 · Dates | Parse dates, fix centuries | The same rules in `silver_offenders`, plus a "birth date is plausible" expectation |
| 4 · Types and the Payoff | Convert types, list what didn't convert | "converted" expectations and `gold_conversion_exceptions` |
| 5 · PySpark | The same pipeline in PySpark | That PySpark is what the pipeline runs |
| 6-7 · Text | Free text | Not in the pipeline yet; the same platform pieces apply |

The cleansing rules aren't rewritten for the pipeline. `lnl/spark_pipeline.py` holds the Spark version of sessions 2-4, tested to give the same numbers as the pandas version the sessions use, and the pipeline imports it.

## What you need before you start

`00_preflight` checks all of this and prints a list you can paste into a request. The usual asks:

| Ask | Who | Why |
|---|---|---|
| A catalog where you have `USE CATALOG` and `CREATE SCHEMA` (a sandbox catalog is ideal) | Workspace or metastore admin | Everything you build lives in one schema you own |
| Serverless compute for notebooks, jobs and pipelines | Workspace admin | Simplest setup. Without it, set `ENTERPRISE_SERVERLESS = False` and fill in the classic-compute settings |
| Notification destinations: PagerDuty (Events API v2 key) and a webhook for your ticketing system (ServiceNow, Jira, ...) | Workspace admin, plus whoever owns the receiving side | Jobs send failures to them. Your ticketing system (ServiceNow, Jira, ...) needs an inbound endpoint that turns the webhook into an incident |
| `SELECT` on `system.access`, `system.lakeflow` and `system.data_quality_monitoring` | Account or metastore admin | Lineage, run history and anomaly results in notebook 05 |
| Two account groups: one allowed to see race and religion, one for analysts | Account admin | Masks and grants decide by group. Until they exist, race and religion stay masked for everyone, which is safe |

## Setup

1. **Get the course into the workspace.** In the workspace, go to **Workspace** → your home folder → **Create** → **Git folder**, and paste the course repository's URL. The notebooks expect it at `/Workspace/Users/<you>/lunch-and-learn-data-cleansing`. Everything is done in the browser; there's nothing to install.
2. **Open `lnl/config.py`** and fill in the enterprise settings. Only `ENTERPRISE_CATALOG` is required to start:

   | Setting | What it is |
   |---|---|
   | `ENTERPRISE_CATALOG` | A catalog you can create a schema in |
   | `ENTERPRISE_SCHEMA` | Your schema; `{user}` becomes your user name, so everyone gets their own |
   | `ENTERPRISE_VOLUME` | The landing volume inside your schema |
   | `ENTERPRISE_SERVERLESS` | `True` for serverless; `False` uses the classic setting below it |
   | `ENTERPRISE_PIPELINE_POLICY_ID` | Classic compute only: a cluster policy for the pipeline |
   | `ANALYST_GROUP` | The account group 01 grants read access on the reference tables |

3. **Run `00_preflight`.** Fix anything marked ⚠️ that blocks you, then start `01_unity_catalog`.

## The bundle (`databricks.yml`)

Notebook 02 creates the pipeline with the Databricks SDK, so you can see each setting. `databricks.yml` declares the same pipeline as a **Declarative Automation Bundle** (the new name for Databricks Asset Bundles): a file you review in a pull request and deploy, which is how this should run in production.

Deploy it from the workspace: open `enterprise/databricks.yml`, click the **Deployments** icon in the left pane, choose the `dev` target, and click **Deploy**. A deployment from the workspace is source-linked: the pipeline runs the files in your Git folder rather than a copy, so a `git pull` changes what the next run uses.

Three cautions:

- **It's an untested template.** The resource definitions pass the bundle schema, but it hasn't been deployed to the agency workspace yet.
- **Use the notebooks or the bundle against a schema, not both.** Two pipelines can't publish the same tables. Delete the notebook-created pipeline first, or point the bundle at another schema.
- **Development mode renames things.** Names get a `[dev you]` prefix, so course 2, which finds the pipeline by its name, won't find a bundle-deployed one unless its own settings use the same name.

## Monitoring, alerting and cleaning up

The pipeline's expectations are this course's checks: each one is counted in the event log, and 02 shows them. The scheduled job, its alerts, the platform's own monitoring and the clean-up notebook are course 2's.

If you stop after 02, delete what you built: the pipeline (Jobs & Pipelines, then the pipeline, then Delete) and your schema (`DROP SCHEMA <catalog>.<schema> CASCADE`, which takes the tables, the volume and the handoff folder with it).

## Before you point this at real tables

The point of the track is to apply it to a few real tables. When you get there:

1. **Get the data owner's written approval** for the tables, the columns and the purpose, before you read anything.
2. **Work in the agency workspace only.** It's approved for criminal justice information. Free Edition, laptops and every other tool aren't.
3. **Use a restricted schema** that only the approved people can read, and put every output there: pipeline tables, quarantine, exception lists and profile metrics. Profile tables don't inherit masks.
4. **Read the source; never write to it.** Your pipeline reads the system of record and writes to your schema.
5. **Masks on before anyone else gets access.** Race, religion and other protected attributes are restricted, and they're never inferred to fill a gap.
6. **Nothing real goes in Git:** no extracts, no samples, no notebook output with real values. Clear outputs before you commit.
7. **AI tools follow agency AI governance.** Don't paste real records into an assistant that isn't approved for them.

## What's been tested

- The Spark cleansing rules (`lnl/spark_pipeline.py`) and the pipeline's logic were run locally on the course's 100,000 mock records and give the same numbers as the pandas sessions.
- Every Databricks SDK call, field and setting was checked against `databricks-sdk` 0.145, and the bundle's resources against the bundle schema.
- **Nothing in this track has run on a Databricks workspace yet.** Expect a few rough edges the first time through, and run it yourself before you teach it.
