[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20510252&assignment_repo_type=AssignmentRepo)

# Digital Artifacts & Data Mining Project 
### Team 15
- Rylan Millar - 33334400
- Alex Batke - 34354803
- Cole Powrie - 77174209
- Liam Storgaard - 64584279
- Will Tilden - 61350294
- Luis Wen Luo - 10665891

## 📖 About




# Project-Starter
Please use the provided folder structure for your project. You are free to organize any additional internal folder structure as required by the project. 


```
.
├── docs                    # Documentation files
│   ├── contract            # Team contract
│   ├── proposal            # Project proposal 
│   ├── design              # UI mocks
│   ├── minutes             # Minutes from team meetings
│   ├── logs                # Team and individual Logs
│   └── ...          
├── src                     # Source files (alternatively `app`)
├── tests                   # Automated tests 
├── utils                   # Utility files
└── README.md
```

Please use a branching workflow, and once an item is ready, do remember to issue a PR, review, and merge it into the master branch.
Be sure to keep your docs and README.md up-to-date.

# System Architecture Diagram
-Frontend: Our frontend will be built using React and Typescript to handle our drag-and-drop interface, visualize updates, and assist in export functionality.
-Backend: Our backend is a combination of Rust and Python. We are using Rust as our preprocessing engine in order to scan directories and chunk files, cache results, and extra data. We are using Python(PyTorch+FastAPI) for our ML service and using pretrained PyTorch models to classify skills, languages, and contributions to return labelled classifications.

![alt text](<docs/design/SYS_DIA.png>)

# DFD Level 1
-This DFD illustrates how data moves throughout the system from the user's input to the final output. Our system first captures the user input, then pre-processes and unpacks the data into pre-chunked streams, classifies the content using our pre-trained ML model, and finally summarizes and presents the final report.

![alt text](<docs/design/DFD1.png>)
