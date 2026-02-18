import os
import shutil
from datetime import datetime

from db import delete_full_scan_by_id, get_full_scan_by_id, list_full_scans, update_full_scan
from file_parser import get_input_file_path
from permission_manager import get_yes_no
from resume_generator import generate_resume, generate_contributor_portfolio, edit_contributor_descriptions
from portfolio_generator import create_portfolios
from services.scan_service import analyze_scan, merge_scans

from print_utils import (
    print_repo_summary,
    print_project_rankings,
    print_chronological_projects,
    print_skills_timeline,
    print_resume_summaries,
    print_contributor_stats,
    is_noise,
)


# --------------------------------------------------------
# TIME FORMATTER
# --------------------------------------------------------

def _format_timestamp(value):
    if not value:
        return value
    try:
        ts = value.replace("Z", "+00:00")
        return datetime.fromisoformat(ts).strftime("%b %d, %Y %I:%M %p")
    except (TypeError, ValueError):
        return value


# --------------------------------------------------------
# MAIN SCAN MANAGER
# --------------------------------------------------------

def scan_manager():
    """
    Provides a loop for viewing, generating portfolios, and deleting past scans.
    Provides a loop for viewing, generating portfolios, and deleting past scans.

    """
    while True:
        choice = _print_menu(
            "SCAN MANAGER",
            [
                ("0", "Return to home screen"),
                ("1", "View stored project analyses"),
                ("2", "Generate Resume/Portfolio"),
                ("3", "Update an existing scan"),
                ("4", "Delete stored scans"),
            ],
            prompt="Choose an option (0–4): ",
        )

        if choice == "1":
            view_full_scan_details()
        elif choice == "2":
            generate_portfolio_menu()
        elif choice == "3":
            update_scan_workflow()
        elif choice == "4":
            delete_full_scan()
        elif choice == "0":
            break
        else:
            print(_center_text("Invalid input. Try again."))


# --------------------------------------------------------
# VIEW SCAN DETAILS
# --------------------------------------------------------

"""
    Lists all saved scans, allows the user to select one, and prints a detailed report.
    The report includes project rankings, timelines, skills, and contributor stats.
"""

def view_full_scan_details():
    scans = list_full_scans()
    if not scans:
        print(_center_text("No scans found."))
        return

    # 1. List available scans (lightweight metadata only)
    print()
    print(_center_text("Select a scan to view:"))
    _print_scan_list(scans)

    choice = input(_center_text("Enter number (0 to cancel): ")).strip()
    if not choice.isdigit() or int(choice) == 0:
        print(_center_text("Canceled."))
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(scans):
        print(_center_text("Invalid selection."))
        return

    # 2. Fetch the full heavy JSON data for the selected scan
    scan = get_full_scan_by_id(scans[idx]["summary_id"])
    if not scan:
        print(_center_text("Error: Could not retrieve scan data."))
        return

    data = scan["scan_data"]

        # Extract specific sections from the JSON blob

    project_summaries = data.get("project_summaries", [])
    resume_summaries = data.get("resume_summaries", [])
    skills_chronological = data.get("skills_chronological", [])
    projects_chronological = data.get("projects_chronological", [])

    # 3. Display the report sections using helper functions
    _print_header("FULL SCAN DETAILS")
    print(f"Timestamp: {_format_timestamp(scan['timestamp'])}")
    print(f"Mode: {scan['analysis_mode']}")
    print("=" * 28)

        # Print various sections of the report

    print_project_rankings(project_summaries)
    print_chronological_projects(projects_chronological)
    print_skills_timeline(skills_chronological)
    print_resume_summaries(resume_summaries)
    print_contributor_stats(project_summaries)

    print(_center_text("\nEnd of scan view.\n"))

        # Option to export the displayed report to a text file

    if get_yes_no("Export this report to a text file?"):
        from file_parser import OUTPUT_DIR
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        filename = f"scan_report_{scan['timestamp'].replace(':', '-')}.txt"
        path = os.path.join(OUTPUT_DIR, filename)

        try:
            with open(path, "w", encoding="utf-8") as f:
                print(f"Scan Report — {_format_timestamp(scan['timestamp'])}", file=f)
                print("=" * 60, file=f)
                print_project_rankings(project_summaries, file=f)
                print_chronological_projects(projects_chronological, file=f)
                print_skills_timeline(skills_chronological, file=f)
                print_resume_summaries(resume_summaries, file=f)
                print_contributor_stats(project_summaries, file=f)

            print(_center_text(f"Saved to: {path}"))
        except Exception as e:
            print(f"Error saving report: {e}")


# --------------------------------------------------------
# UPDATE SCAN
# --------------------------------------------------------

def update_scan_workflow():
    _print_header("UPDATE EXISTING SCAN")
    
    # 1. Select existing scan
    scans = list_full_scans()
    if not scans:
        print(_center_text("No existing scans found to update."))
        return

    print(_center_text("Select a scan to update:"))
    _print_scan_list(scans)
    
    choice = input(_center_text(f"Choose (1-{len(scans)} or 0 to cancel): ")).strip()
    if not choice.isdigit():
        return
    idx = int(choice)
    if idx == 0 or idx > len(scans):
        return
    
    target_scan_meta = scans[idx-1]
    summary_id = target_scan_meta['summary_id']
    
    # Load full data
    existing_record = get_full_scan_by_id(summary_id)
    if not existing_record:
        print(_center_text("Error loading scan data."))
        return
    
    existing_data = existing_record['scan_data']

    # 2. Select new file
    print(_center_text("Select the new ZIP file to add:"))
    result = get_input_file_path()
    if not result:
        return
    file_list, zip_hash = result
    
    # Check if this file is already in the scan
    current_hashes = set(existing_data.get("source_hashes", []))
        
    if zip_hash in current_hashes:
        print(_center_text("This file has already been added to this scan."))
        return

    # 3. Analyze
    print(_center_text("Analyzing new files..."))
    analysis_mode = existing_record['analysis_mode']
    # Use default advanced options (empty dict defaults to True in detailed_extraction)
    new_results = analyze_scan(file_list, analysis_mode, {})
    if new_results:
        new_results["source_hashes"] = [zip_hash]
    
    # 4. Merge
    merged_results = merge_scans(existing_data, new_results)
    
    # 5. Save
    try:
        update_full_scan(summary_id, merged_results)
        print(_center_text("Portfolio updated successfully."))
    except Exception as e:
        print(_center_text(f"Error updating portfolio: {e}"))

# --------------------------------------------------------
# DELETE SCAN
# --------------------------------------------------------
"""
    Lists all saved scans and allows the user to permanently delete one from the database.
"""

def delete_full_scan():
    scans = list_full_scans()
    if not scans:
        print(_center_text("No saved scans found to delete."))
        return
        
    # Display list for deletion

    print()
    print(_center_text("Select a scan to delete:"))
    _print_scan_list(scans)

    choice = input(_center_text("Enter number (0 to cancel): ")).strip()
    if not choice.isdigit() or int(choice) == 0:
        print(_center_text("Deletion canceled."))
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(scans):
        print(_center_text("Invalid selection."))
        return

    scan = scans[idx]

    # Confirm before deletion

    if get_yes_no(f"Are you sure you want to delete the scan from {scan['timestamp']}?"):
        success = delete_full_scan_by_id(scan["summary_id"])
        print(_center_text("Scan deleted.") if success else "Failed to delete scan.")
    else:
        print(_center_text("Deletion canceled."))


def generate_markdown_portfolio(data, user, timestamp):
    """Generates a Markdown portfolio for a specific user."""
    portfolios = create_portfolios(data)
    target_portfolio = next((p for p in portfolios if p.user_name == user), None)

    if target_portfolio:
        from file_parser import OUTPUT_DIR
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        safe_name = "".join(c for c in user if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        filename = f"Portfolio_{safe_name}.md"
        out_path = os.path.join(OUTPUT_DIR, filename)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(target_portfolio.to_markdown())
            
        print(_center_text(f"Saved portfolio to:\n{out_path}"))
    else:
        print(_center_text("Error: Could not generate portfolio for selected user."))


# --------------------------------------------------------
# PORTFOLIO GENERATION
# --------------------------------------------------------


def generate_portfolio_menu():
    """
    Menu for generating Word documents from a saved scan.
    Options:
    1) Full Project Resume (summary of all projects in the scan).
    2) Individual Contributor Resume (Word)
    3) Individual Contributor Portfolio (Markdown)specific to one person).
    """
    scans = list_full_scans()
    if not scans:
        print(_center_text("No scans found."))
        return

    # Select scan first

    print()
    print(_center_text("Select a scan to generate portfolio from:"))
    _print_scan_list(scans)

    choice = input(_center_text("Enter number (0 to cancel): ")).strip()
    if not choice.isdigit() or int(choice) == 0:
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(scans):
        print(_center_text("Invalid selection."))
        return

    # Fetch full data to access contributor profiles and project details

    scan = get_full_scan_by_id(scans[idx]["summary_id"])
    data = scan["scan_data"]

    while True:
        _print_header("GENERATION OPTIONS", width=48, sep="-")
        print(_center_text("1) Full Project Resume"))
        print(_center_text("2) Contributor Resume (Word)"))
        print(_center_text("3) Contributor Portfolio (Markdown)"))
        print(_center_text("4) Edit Resume"))
        print(_center_text("0) Back"))

        choice = input(_center_text("Enter number: ")).strip()

        if choice == "0":
            break

        if choice == "1":
            docx = generate_resume(
                data.get("project_summaries", []),
                data.get("projects_chronological", []),
                data.get("skills_chronological", []),
                scan_timestamp=scan["timestamp"],
            )
            if docx:
                print(_center_text(f"Saved:\n{docx}"))
            input(_center_text("Press Enter to continue..."))
            continue

        if choice == "4":
            edit_contributor_descriptions(target_scan=scan)
            continue

        if choice not in ("2", "3"):
            continue

        # --- Contributor Portfolio Logic ---

        contributors = [
            c for c in sorted(data.get("contributor_profiles", {}).keys())
            if not is_noise(c)
        ]

        if not contributors:
            print(_center_text("No valid contributors found."))
            continue

        print()
        print(_center_text("Select contributor:"))
        for i, c in enumerate(contributors, 1):
            print(_center_text(f"{i}. {c}"))

        sel = input(_center_text("Enter number (0 to back): ")).strip()
        if not sel.isdigit():
            continue

        idx = int(sel) - 1
        if idx < 0 or idx >= len(contributors):
            continue

        user = contributors[idx]
        profile = data["contributor_profiles"][user]
        
        if choice == "3":
            generate_markdown_portfolio(data, user, scan["timestamp"])
        elif choice == "2":
            # Default to chronological sorting
            sort_mode = "date"

            project_map = {p["project"]: p for p in data.get("project_summaries", [])}
            out = generate_contributor_portfolio(
                user,
                profile,
                project_map,
                scan_timestamp=None,
                sort_mode=sort_mode
            )

            if out:
                print(_center_text(f"Saved resume to:\n{out}"))
        
        input(_center_text("Press Enter to continue..."))


# --------------------------------------------------------
# UI HELPERS
# --------------------------------------------------------

def _center_text(text):
    width = shutil.get_terminal_size(fallback=(80, 20)).columns
    if len(text) >= width:
        return text
    padding = (width - len(text)) // 2
    return " " * padding + text


def _print_header(title, width=28, sep="="):
    print()
    print(_center_text(sep * width))
    print(_center_text(title))
    print(_center_text(sep * width))


def _print_menu(title, options, prompt="Choose an option: "):
    print()
    print(_center_text(title))
    print(_center_text("=" * len(title)))
    for key, label in options:
        print(_center_text(f"{key}) {label}"))
    return input(_center_text(prompt)).strip()


def _print_scan_list(scans):
    for i, s in enumerate(scans, start=1):
        ts = _format_timestamp(s['timestamp'])
        print(
            _center_text(
                f"{i}. Scan {s['summary_id']} - {ts} ({s['analysis_mode']})"
            )
        )
