# Team log (November 24 - 30, 2025)

## Github usernames

- @Canadadubstep -> Rylan Millar
- @alexbatke -> Alex Batke
- @ColePowrie -> Cole Powrie
- @liamsto -> Liam Storgaard
- @willtilden -> Will Tilden
- @LuisWenLuo -> Luis Wen

## Overview

- Updated the program so that it now stacks both the LLM and ML models when user consent is provided, and falls back to ML-only execution when consent is not given. It also fixes a bug where the unzip function returned a status message instead of a file path, which previously caused failures in the main workflow
- Integrated the exporter so it takes the predictions from the ML model, and exports to PDF
- The PDF export now supports including both ML data and LLM output, appending the LLM response neatly beneath the ML content when user consent is provided. If consent is not given, the exporter defaults to generating a PDF containing only the ML data
- Included storing users configuration for future use
- The deployment configuration was updated—including docker-compose.yml, Dockerfile, and centralized environment-based DB connection handling—to ensure reliable app–database communication and correct system dependencies. New persistence logic (llm_mapper.py) and updated permission and processing flows allow raw or structured LLM outputs to be stored alongside artifacts, with additional tooling and path fixes enabling smooth in-container testing
- Added a metadata-extraction module to store project information and enable deeper directory analysis, giving us a solid starting point to expand and capture more useful metadata. Additionally included a consent step before the LLM prompt so users can choose whether their data is analyzed, ensuring they retain full control over their privacy

## Recap of milestone goals

- Issue #128, #130, #101, #135, #138

## Burnup chart

![alt text](</logs/team/chartW13.png>)

## Table view (Completed)

![alt text](</logs/team/completedW13.png>)

## Table view (In progress)

![alt text](</logs/team/inprogressW13.png>)

## Test report

- Regression testing
![alt text](</logs/team/pipelineW13.png>)

- Tests pass in the local virtual environment
![alt text](</logs/team/virtualW13.png>)

## Additional context

- We are missing quite a bit of requirements from the milestone checklist, however I believe the heaviest requirements are done/mostly done

## Next cycle

- In the next cycle, we will integrate the ML classifier artifacts so that encoder outputs and model predictions flow directly into stored metadata, and introduce a lightweight read-only API for accessing artifacts and llm_results. We will also add CI pipelines, implement Alembic migrations with JSONB indexing, and ensure that fully tested feature branches merge cleanly into main
- Keep connecting everything else into a pipeline and get ready for the milestone presentation
- Continue improving the PDF exporter. Building on the clean, simple version we have now, by adding more customization and personalization options for users
- Refining the integration and getting assistancw with ensuring it is consistent on more powerful machines
- Addition of requirement 7, 9, and 10 into the project
