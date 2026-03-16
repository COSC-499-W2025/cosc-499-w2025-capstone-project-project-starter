"""LaTeX template for resume export (team-3 style)."""


class ResumeTemplate:
    LATEX_TEMPLATE = r"""
    \documentclass[a4paper]{article}
    \usepackage{fullpage}
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{textcomp}
    \usepackage[utf8]{inputenc}
    \usepackage[T1]{fontenc}
    \usepackage[hidelinks]{hyperref}
    \usepackage[left=2cm, right=2cm, top=2cm]{geometry}
    \usepackage{longtable}
    \usepackage{enumitem}
    \setlist[itemize]{leftmargin=0pt, itemsep= -3pt, topsep=0pt, label=\textbullet, labelsep=0.5em}
    \textheight=10in
    \pagestyle{empty}
    \raggedright

    \newcommand{\lineunder}{\vspace*{-8pt} \\ \hspace*{-18pt} \hrulefill \\}
    \newcommand{\header}[1]{{\hspace*{-18pt}\vspace*{6pt} \textsc{#1}} \vspace*{-6pt} \lineunder}

    \begin{document}
    \vspace*{-40pt}
    \vspace*{-2pt}
    \begin{center}
    {\Huge \scshape {{name}}}\\
    \vspace{2pt}
    \vspace*{2pt}
    \href{mailto:{email}}{{{email}}}\\
    {links_block}
    \end{center}

    \header{Education}
    \vspace{2mm}
    {education_section}
    \vspace{2mm}

    \header{Skills}
    \vspace{2mm}
    \begin{longtable}{p{4cm}p{12cm}}
    {skills_table}
    \end{longtable}
    \vspace{1mm}

    \header{Projects / Experience}
    \vspace{2mm}
    {projects}

    \end{document}
    """
