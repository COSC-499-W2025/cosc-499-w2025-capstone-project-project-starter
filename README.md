[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20510252&assignment_repo_type=AssignmentRepo)

# Digital Artifacts & Data Mining Project 

### Team 15
- Rylan Millar - 33334400
- Alex Batke - 34354803
- Cole Powrie - 77174209
- Liam Storgaard - 64584279
- Will Tilden - 61350294
- Luis Wen Luo - 10665891

## 📖 Overview

This project focuses on analyzing digital work artifacts such as code and documents from a student or early professional’s computer. The goal is to help users understand the projects they've contributed to over the course of their degrees or professional careers, and build a resume by extracting useful insights like skills learned and contribution levels from a given directory.

For this milestone, the system can parse a zipped folder, identify project details, extract key metrics, handle permissions and privacy concerns, and output the results in simple text-based formats. This lays the groundwork for future development of an API and a visual dashboard.


## Diagrams
- [Level 1 data flow diagram](/docs/data%20flow%20diagram/explanation.md)
- [System architecture design](/docs/system%20architecture%20design/explanation.md)


## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/COSC-499-W2025/capstone-project-team-15.git
cd <repository-path>
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell)**

```powershell
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```


## Running the Application

Paste the following input into the command line or powershell and subsitute `<path to zip file>` with the local path to a zip file on your device.

```bash
python main.py <path to zip file>
```


## Troubleshooting

### Virtual Environment Script Error

If you see this error:


```
running scripts is disabled on this system
```

Run the following in the command line or powershell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
