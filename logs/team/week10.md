# Team log (November 3 - 9, 2025)

## Github usernames

- @Canadadubstep -> Rylan Millar
- @alexbatke -> Alex Batke
- @ColePowrie -> Cole Powrie
- @liamsto -> Liam Storgaard
- @willtilden -> Will Tilden
- @LuisWenLuo -> Luis Wen

## Overview

- Regression testing shows in the PR into the develop branch
- Implemented more precise ON DELETE and ON UPDATE cascading behaviors across foreign key relationships, added UNIQUE constraints to prevent duplicate records, and introduced created_at and updated_at timestamp columns to key tables for better record tracking
- An update and improvement to the Docker README documentation, and the relocation of database credentials from the publicly available YAML file to a secure .env file
- PDF export functionality (sample pdf)
- The original ML categorization categories, which were only for testing, have been expanded to 54 and made more language-agnostic to better align with project requirements
- Updated the unzip_file method in the zipvalidation.py module to handle cases where the zip file name is changed after creation, which previously caused extraction errors, by creating a folder matching the zip file name before extraction

## Recap of milestone goals

- #5 (Have alternative analyses in place if sending data to an external service is not permitted)
- #13 (Store project information into a database)
- Regression testing
- PR #95, issues #86, #89, #93, #98, and #76

## Burnup chart

![alt text](</logs/team/chartW10.png>)

## Table view (Completed)

![alt text](</logs/team/completedW10.png>)

## Table view (In progress)

![alt text](</logs/team/inprogressW10.png>)

## Test report

- Some tests were refactored to include other cases
- Regression testing does not pass (error)
- Everybody's docker environment works

## Additional context

- Actions workflow does not pass (for now)
- The CI/CD pipeline shows when trying to merge code into the develop branch through a PR

## Next cycle

- Completing metadata extraction, connecting the pipeline, and performing housekeeping tasks such as adding comments
- Integrating the functional exporter implemented this week with the rest of the project through the already integrated ML model
- Making sure CI/CD pipeline works and passes
