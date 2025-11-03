# Team log (October 27 - November 2, 2025)

## Github usernames

- @Canadadubstep -> Rylan Millar
- @alexbatke -> Alex Batke
- @ColePowrie -> Cole Powrie
- @liamsto -> Liam Storgaard
- @willtilden -> Will Tilden
- @LuisWenLuo -> Luis Wen

## Overview

- Introduced a PyTorch-based unsupervised ML pipeline capable of classifying arbitrary code beyond Git repositories
- Finalized the database structure by adding core tables (users, artifacts, category) and removing the temporary test table
- Added a user consent system that explains privacy implications and requires approval before sending data to external LLM services
- Updated the Docker configuration to create two containers (app and database) with the correct Linux, Python, and ML setup for consistent deployment
- Implemented unzipped files being passed to the parser

## Recap of milestone goals

- #4 (Request user permission before using external services (e.g., LLM) and provide implications on data privacy about the user's data)
- #5 (Have alternative analyses in place if sending data to an external service is not permitted)
- #13 (Store project information into a database)
- Issues #66, #72, #74, and #76

## Burnup chart

![alt text](</logs/team/chartW9.png>)

## Table view (Completed)

![alt text](</logs/team/completedW9.png>)

## Table view (In progress)

![alt text](</logs/team/inprogressW9.png>)

## Test report

- Certain tests pass an others do not (using a virtual environment in VS Code on MacOS)
- All test files are in the tests folder
- No regression testing as of yet
- Tests in the testing tab in VS Code pass

## Additional context

- As we refactored our repository files, and code, some tests files need to be updated in order to pass.
