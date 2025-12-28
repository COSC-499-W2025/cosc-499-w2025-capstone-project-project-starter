# src/skills_config.py
"""
Skills configuration based on the defined skills in the ML training file
"""

SKILLS = [
    # Core engineering practices
    "Testing",
    "CI",
    "Containerization",
    "Concurrency",
    "Performance-Optimization",
    "Security-Cryptography",
    "Security-Application",
    "Security-Network",
    "Logging",
    "Metrics-Monitoring",
    "Tracing",
    "Infrastructure-as-Code",
    "Build-Systems",
    "Package-Management",
    "Scripting-Automation",
    "CLI-Tooling",

    # Web / backend / services
    "Web-Frontend",
    "Web-Backend",
    "Web-Fullstack",
    "Web-API",
    "Authentication-Authorization",
    "Microservices",
    "Messaging-Queueing",
    "Streaming-Processing",

    # Data storage / databases / caching
    "SQL-DML",
    "SQL-DDL",
    "Database-ORM",
    "Database-NoSQL",
    "Database-Graph",
    "Caching",

    # Cloud / DevOps
    "Cloud-AWS",
    "Cloud-GCP",
    "Cloud-Azure",
    "Orchestration-Kubernetes",
    "BigData",

    # Systems / low-level
    "Systems-Programming",
    "Embedded",
    "Networking-LowLevel",
    "Parallel-Computing",
    "GPU-Computing",

    # Data / ML / AI
    "Data-Wrangling",
    "Data-Engineering",
    "Data-Visualization",
    "Numerics",
    "ML-Classic",
    "ML-DeepLearning",
    "ML-NLP",
    "ML-Vision",
    "ML-Recommendation",
    "MLOps",
    "Probabilistic-Programming",

    # Other domains
    "Game-Development",
    "Functional-Programming",
    "Serialization",
]

# Skill categories for organization
SKILL_CATEGORIES = {
    "core_engineering": [
        "Testing", "CI", "Containerization", "Concurrency", "Performance-Optimization",
        "Security-Cryptography", "Security-Application", "Security-Network", "Logging",
        "Metrics-Monitoring", "Tracing", "Infrastructure-as-Code", "Build-Systems",
        "Package-Management", "Scripting-Automation", "CLI-Tooling"
    ],
    "web_backend": [
        "Web-Frontend", "Web-Backend", "Web-Fullstack", "Web-API",
        "Authentication-Authorization", "Microservices", "Messaging-Queueing",
        "Streaming-Processing"
    ],
    "data_storage": [
        "SQL-DML", "SQL-DDL", "Database-ORM", "Database-NoSQL",
        "Database-Graph", "Caching"
    ],
    "cloud_devops": [
        "Cloud-AWS", "Cloud-GCP", "Cloud-Azure", "Orchestration-Kubernetes",
        "BigData"
    ],
    "systems_lowlevel": [
        "Systems-Programming", "Embedded", "Networking-LowLevel",
        "Parallel-Computing", "GPU-Computing"
    ],
    "data_ml_ai": [
        "Data-Wrangling", "Data-Engineering", "Data-Visualization", "Numerics",
        "ML-Classic", "ML-DeepLearning", "ML-NLP", "ML-Vision",
        "ML-Recommendation", "MLOps", "Probabilistic-Programming"
    ],
    "other_domains": [
        "Game-Development", "Functional-Programming", "Serialization"
    ]
}

# Map skills to database category IDs (you'll need to update this based on your category table)
SKILL_TO_CATEGORY_MAP = {
    "Testing": 1,
    "CI": 1,
    "Containerization": 1,
    "Concurrency": 1,
    "Performance-Optimization": 1,
    "Security-Cryptography": 1,
    "Security-Application": 1,
    "Security-Network": 1,
    "Logging": 1,
    "Metrics-Monitoring": 1,
    "Tracing": 1,
    "Infrastructure-as-Code": 1,
    "Build-Systems": 1,
    "Package-Management": 1,
    "Scripting-Automation": 1,
    "CLI-Tooling": 1,
    # Add mappings for other skills based on your category table
}