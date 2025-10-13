# Level 1 DFD explanation  

- The **Level 1 DFD** represents how the **Artifact Mining System** processes user inputs into meaningful summaries and insights. It begins with the **User (a student, or recent graduate/early professional)**, who uploads a compressed project archive and sets processing options. This data enters **Process 1.0 – Capture Request**, where inputs are validated and structured before being passed to **Process 2.0 – Preprocess Data**. The preprocessing stage unpacks the archive, filters unnecessary files, and chunks data into manageable units with relevant metadata for efficient processing.

- In **Process 3.0 – Classify Content**, a machine learning model analyzes the preprocessed data to detect languages, categories, and skills represented in the files. The classified data is then passed to **Process 4.0 – Summarize Results**, which aggregates the information into key metrics summaries. Finally, **Process 5.0 – Present Output** formats these results into a user-friendly dashboard, complete with visualizations and exportable reports. Overall, the DFD captures a clear and modular pipeline from user submission to insightful, interpretable output.

![alt text](</docs/data flow diagram/level1_DFD.png>)
