# System Architecture Design

The system follows a three-tier architecture that organizes components from the user interface to data management and visualization. This design ensures modularity, scalability, and efficient data flow while maintaining clear separation of responsibilities across tiers.

In **Tier 1 (Frontend)**, the web interface is built using HTML, CSS, and JavaScript to provide an intuitive and modern user experience. Users can upload compressed project archives through a clear file drop zone and adjust controls or toggles to specify search scopes and export preferences. The results dashboard displays categorized metrics, summaries, and key insights derived from project analysis. The frontend also enables users to export results into their resume or portfolio.

**Tier 2** handles the main processing and business logic. It is composed of three interconnected layers written in Rust and PyTorch. The **Backend (Rust Processing)** layer manages decompression, file filtering, and chunking of data into byte blocks, leveraging parallelization and memory-efficient techniques for performance. The **ML Processing (PyTorch)** layer employs a pretrained code classification model to analyze these byte blocks, producing skill tags, detected languages, and project categories. Finally, the **Post-Processing (Rust Business Logic)** layer performs categorization, binning, duplicate detection, and summary generation before packaging the results into a structured format to be returned to the frontend.

In **Tier 3 (Data and Display)**, the system transforms processed data into a visualization. This tier presents the categorized projects in a structured table that includes project names, dominant categories, and top tags with associated confidence levels. Users can review this information and export the results to resumes or portfolio documents, or download summarized reports for offline use.

![alt text](</docs/system architecture design/system_architecture_design.png>)
