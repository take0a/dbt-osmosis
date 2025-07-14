# dbt-osmosis

<!--![GitHub Actions](https://github.com/z3z1ma/dbt-osmosis/actions/workflows/master.yml/badge.svg)-->

![PyPI](https://img.shields.io/pypi/v/dbt-osmosis)
[![Downloads](https://static.pepy.tech/badge/dbt-osmosis)](https://pepy.tech/project/dbt-osmosis)
![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)
![black](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dbt-osmosis-playground.streamlit.app/)

[![Scc Count Badge](https://sloc.xyz/github/z3z1ma/dbt-osmosis/)](https://github.com/z3z1ma/dbt-osmosis/)
[![Scc Count Badge](https://sloc.xyz/github/z3z1ma/dbt-osmosis/?category=cocomo)](https://github.com/z3z1ma/dbt-osmosis/)

## New to dbt-osmosis?

We now have a spiffy [dbt-osmosis documentation site](https://z3z1ma.github.io/dbt-osmosis/)! 🎉

Please check it out for a more in-depth introduction to dbt-osmosis. 👇

[![dbt-osmosis](/screenshots/docs_site.png)](https://z3z1ma.github.io/dbt-osmosis/)

## Migrating from 0.x.x to 1.x.x?

We have a [migration guide](https://z3z1ma.github.io/dbt-osmosis/docs/migrating) to help you out. 🚀

## What is dbt-osmosis?

Hello and welcome to the project! [dbt-osmosis](https://github.com/z3z1ma/dbt-osmosis) 🌊 serves to enhance the developer experience significantly. We do this through providing 4 core features:

1. Automated schema YAML management.

    1a. `dbt-osmosis yaml refactor --project-dir ... --profiles-dir ...`

    > Automatically generate documentation based on upstream documented columns, organize yaml files based on configurable rules defined in dbt_project.yml, scaffold new yaml files based on the same rules, inject columns from data warehouse schema if missing in yaml and remove columns no longer present in data warehouse (organize -> document)

    1b. `dbt-osmosis yaml organize --project-dir ... --profiles-dir ...`

    > Organize yaml files based on configurable rules defined in dbt_project.yml, scaffold new yaml files based on the same rules (no documentation changes)

    1c. `dbt-osmosis yaml document --project-dir ... --profiles-dir ...`

    > Automatically generate documentation based on upstream documented columns (no reorganization)

2. Workbench for dbt Jinja SQL. This workbench is powered by streamlit and the badge at the top of the readme will take you to a demo on streamlit cloud with jaffle_shop loaded (requires extra `pip install "dbt-osmosis[workbench]"`).

    2a. `dbt-osmosis workbench --project-dir ... --profiles-dir ...`

    > Spins up a streamlit app. This workbench offers similar functionality to the osmosis server + power-user combo without a reliance on VS code. Realtime compilation, query execution, pandas profiling all via copying and pasting whatever you are working on into the workbenchat your leisure. Spin it up and down as needed.

____

## Pre-commit

You can use dbt-osmosis as a pre-commit hook. This will run the `dbt-osmosis yaml refactor` command on your models directory before each commit. This is one way to ensure that your schema.yml files are always up to date. I would recommend reading the docs for more information on what this command does.

```yaml title=".pre-commit-config.yaml"
repos:
  - repo: https://github.com/z3z1ma/dbt-osmosis
    rev: v1.1.5 # verify the latest version
    hooks:
      - id: dbt-osmosis
        files: ^models/
        args: [--target=prod]
        additional_dependencies: [dbt-<adapter>]
```

___

## Workbench

The workbench is a streamlit app that allows you to work on dbt models in a side-by-side editor and query tester. I've kept this portion of the README since users can jump into the streamlit hosted workbench to play around with it via the badge below. Expect the living documentation moving forward to exist at the [dbt-osmosis documentation site](https://z3z1ma.github.io/dbt-osmosis/).

I also expect there is some untapped value in the workbench that is only pending some time from myself. I've seen a path to a truly novel development experience and look forward to exploring it.

Demo the workbench 👇

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dbt-osmosis-playground.streamlit.app/)

```sh
# NOTE this requires the workbench extra as you can see
pip install "dbt-osmosis[workbench]"

# Command to start server
dbt-osmosis workbench
```

Press "r" to reload the workbench at any time.

✔️ dbt Editor with instant dbt compilation side-by-side or pivoted

✔️ Full control over model and workbench theme, light and dark mode

✔️ Query Tester, test the model you are working on for instant feedback

✔️ Data Profiler (leverages pandas-profiling)

**Editor**

The editor is able to compile models with control+enter or dynamically as you type. Its speedy! You can choose any target defined in your profiles yml for compilation and execution.

![editor](/screenshots/osmosis_editor_main.png?raw=true "dbt-osmosis Workbench")

You can pivot the editor for a fuller view while workbenching some dbt SQL.

![pivot](/screenshots/osmosis_editor_pivot.png?raw=true "dbt-osmosis Pivot Layout")

**Test Query**

Test dbt models as you work against whatever profile you have selected and inspect the results. This allows very fast iterative feedback loops not possible with VS Code alone.

![test-model](/screenshots/osmosis_tester.png?raw=true "dbt-osmosis Test Model")

**Profile Model Results**

Profile your datasets on the fly while you develop without switching context. Allows for more refined interactive data modelling when dataset fits in memory.

![profile-data](/screenshots/osmosis_profile.png?raw=true "dbt-osmosis Profile Data")

**Useful Links and RSS Feed**

Some useful links and RSS feeds at the bottom. 🤓

![profile-data](/screenshots/osmosis_links.png?raw=true "dbt-osmosis Profile Data")

___

![graph](https://repobeats.axiom.co/api/embed/df37714aa5780fc79871c60e6fc623f8f8e45c35.svg "Repobeats analytics image")
