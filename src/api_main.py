"""
API Client Entry Point

This script runs the Skill Scope system by making HTTP requests to the
FastAPI backend (src/api.py), rather than importing logic directly.

Usage:
    1. Start the API server: python src/api.py
    2. Run this client:      python src/api_main.py
"""

import os
import sys
import requests
import json

# Add the current directory to sys.path to allow importing local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from file_parser import compute_file_hash
from permission_manager import get_user_consent, get_analysis_mode, get_advanced_options, get_yes_no
from print_utils import (
    _center_text,
    _print_banner,
    print_project_rankings,
    print_repo_summary,
    print_chronological_projects,
    print_skills_timeline,
    print_resume_summaries,
    print_contributor_stats
)

# Configuration constants
API_URL = "http://127.0.0.1:5000"
INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "input"))


def _print_menu(title, options, prompt="Choose an option: "):
    """Helper to display a standardized menu and get user input."""
    _print_banner(title)
    for key, label in options:
        print(_center_text(f"{key}. {label}"))
    return input(_center_text(prompt)).strip()


def check_api_connection():
    """Verifies the API server is reachable by pinging the health endpoint."""
    print(_center_text(f"Connecting to API at {API_URL}..."))
    try:
        resp = requests.get(f"{API_URL}/health", timeout=2)
        if resp.status_code == 200:
            print(_center_text("API is online."))
            return True
    except requests.exceptions.RequestException:
        pass
    
    print(_center_text("Error: Could not connect to API."))
    print(_center_text("Please ensure the API server is running in a separate terminal:"))
    print(_center_text("  python src/api.py"))
    return False


def get_input_zip_file():
    """
    Lists zip files in the input directory, filters duplicates by hash,
    and prompts the user to select one for upload.
    """
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".zip")]
    if not files:
        print(_center_text(f"No .zip files found in {INPUT_DIR}"))
        return None
    
    # Deduplicate files based on content hash to avoid showing identical zips
    print(_center_text("Checking for duplicates..."))
    unique_zips = []
    seen_hashes = set()
    
    for f in files:
        full_path = os.path.join(INPUT_DIR, f)
        f_hash = compute_file_hash(full_path)
        
        if f_hash and f_hash in seen_hashes:
            continue
        if f_hash:
            seen_hashes.add(f_hash)
        unique_zips.append(f)
    files = unique_zips

    _print_banner("SELECT FILE TO UPLOAD")
    for i, f in enumerate(files, 1):
        print(_center_text(f"{i}. {f}"))
    
    choice = input(_center_text("Choose a file (0 to cancel): ")).strip()
    if not choice.isdigit():
        return None
    idx = int(choice) - 1
    if idx < 0 or idx >= len(files):
        return None
    
    return os.path.join(INPUT_DIR, files[idx])


def run_new_scan_via_api():
    """
    Orchestrates the new scan workflow:
    1. Select Analysis Mode -> 2. Select File -> 3. Consent -> 4. Upload & Scan
    """
    # 1. Analysis Mode (First)
    mode_raw = get_analysis_mode()
    if not mode_raw:
        return
    mode = mode_raw.lower()

    # 1b. Advanced Options
    advanced_options = {}
    if mode == "advanced":
        advanced_options = get_advanced_options()

    # 2. File Selection (Second)
    zip_path = get_input_zip_file()
    if not zip_path:
        return

    # 3. Consent
    # Check if consent is already granted via API (from initialization)
    consent = False
    try:
        r = requests.get(f"{API_URL}/privacy-consent")
        if r.status_code == 200:
            consent = r.json().get("privacy", {}).get("consent", False)
    except Exception:
        pass

    if not consent:
        print()
        if input(_center_text("Consent to process data? (y/n): ")).strip().lower() == 'y':
            consent = True
        else:
            print(_center_text("Consent denied. Aborting."))
            return

    # 4. Upload and Scan
    print(_center_text("Uploading and scanning via API... please wait..."))
    
    try:
        # Send file to API
        with open(zip_path, 'rb') as f:
            files = {'zip': f}
            data = {
                'analysis_mode': mode,
                'consent': str(consent).lower(),
                'persist': 'true',
                'advanced_options': json.dumps(advanced_options)
            }
            resp = requests.post(f"{API_URL}/projects/upload", files=files, data=data)
            
        if resp.status_code in (200, 201):
            result = resp.json()
            print(_center_text("Scan Complete!"))
            if result.get("duplicate"):
                print(_center_text("Note: This was a duplicate scan."))
            
            # Display summary using the returned JSON data
            scan_data = result.get("results", {})
            if scan_data:
                # 1. Print Repository Metadata for each project (if available)
                project_summaries = scan_data.get("project_summaries", [])
                for p in project_summaries:
                    if p.get("project"):
                        repo_name = p.get("repo_name") or p.get("project")
                        # Wrap strings in list because print_repo_summary expects iterables to join
                        authors_arg = [p.get("authors")] if p.get("authors") else []
                        contribs_arg = [p.get("contributors")] if p.get("contributors") else []
                        
                        print_repo_summary(
                            p.get("project"),
                            repo_name,
                            p.get("repo_root", ""),
                            authors_arg,
                            contribs_arg,
                            p.get("branch_count", 0),
                            p.get("has_merges", "Unknown"),
                            p.get("project_type", "Unknown"),
                            p.get("repo_duration_days", 0),
                            p.get("commit_frequency", "Unknown")
                        )

                # 2. Print the rest of the reports
                print_project_rankings(scan_data.get("project_summaries", []))
                print_chronological_projects(scan_data.get("projects_chronological", []))
                print_skills_timeline(scan_data.get("skills_chronological", []))
                print_resume_summaries(scan_data.get("resume_summaries", []))
                print_contributor_stats(scan_data.get("project_summaries", []))
        else:
            print(_center_text(f"API Error: {resp.status_code} - {resp.text}"))

    except Exception as e:
        print(_center_text(f"Request failed: {e}"))
    
    input(_center_text("Press Enter to continue..."))


def _fetch_scans():
    """Helper to get list of scans."""
    try:
        resp = requests.get(f"{API_URL}/scans")
        if resp.status_code == 200:
            return resp.json().get("scans", [])
    except Exception:
        pass
    return []


def view_full_scan_details_via_api():
    """Lists scans and shows detailed report for selected one."""
    scans = _fetch_scans()
    if not scans:
        print(_center_text("No scans found."))
        input(_center_text("Press Enter..."))
        return

    print()
    print(_center_text("Select a scan to view:"))
    for i, s in enumerate(scans, 1):
        print(_center_text(f"{i}. Scan {s['summary_id']} - {s['timestamp']} ({s['analysis_mode']})"))

    choice = input(_center_text("Enter number (0 to cancel): ")).strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    
    idx = int(choice) - 1
    if idx < 0 or idx >= len(scans):
        print(_center_text("Invalid selection."))
        return

    summary_id = scans[idx]["summary_id"]

    # Fetch full details
    try:
        resp = requests.get(f"{API_URL}/scans/{summary_id}")
        if resp.status_code != 200:
            print(_center_text("Failed to retrieve scan details."))
            input(_center_text("Press Enter..."))
            return
        
        scan_wrapper = resp.json().get("scan", {})
        data = scan_wrapper.get("scan_data", {})

        _print_banner("FULL SCAN DETAILS")
        print(f"Timestamp: {scan_wrapper.get('timestamp')}")
        print(f"Mode: {scan_wrapper.get('analysis_mode')}")
        print("=" * 28)

        # Print Repository Metadata for each project
        project_summaries = data.get("project_summaries", [])
        for p in project_summaries:
            if p.get("project"):
                repo_name = p.get("repo_name") or p.get("project")
                authors_arg = [p.get("authors")] if p.get("authors") else []
                contribs_arg = [p.get("contributors")] if p.get("contributors") else []
                
                print_repo_summary(
                    p.get("project"),
                    repo_name,
                    p.get("repo_root", ""),
                    authors_arg,
                    contribs_arg,
                    p.get("branch_count", 0),
                    p.get("has_merges", "Unknown"),
                    p.get("project_type", "Unknown"),
                    p.get("repo_duration_days", 0),
                    p.get("commit_frequency", "Unknown")
                )

        print_project_rankings(data.get("project_summaries", []))
        print_chronological_projects(data.get("projects_chronological", []))
        print_skills_timeline(data.get("skills_chronological", []))
        print_resume_summaries(data.get("resume_summaries", []))
        print_contributor_stats(data.get("project_summaries", []))

        print(_center_text("\nEnd of scan view.\n"))
        input(_center_text("Press Enter to continue..."))
    except Exception as e:
        print(_center_text(f"Error fetching details: {e}"))
        input(_center_text("Press Enter..."))


def delete_scan_via_api():
    """Lists scans and deletes selected one."""
    scans = _fetch_scans()
    if not scans:
        print(_center_text("No scans found."))
        return

    print()
    print(_center_text("Select a scan to delete:"))
    for i, s in enumerate(scans, 1):
        print(_center_text(f"{i}. Scan {s['summary_id']} - {s['timestamp']}"))

    choice = input(_center_text("Enter number (0 to cancel): ")).strip()
    if not choice.isdigit() or int(choice) == 0:
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(scans):
        return

    scan = scans[idx]
    if get_yes_no(f"Are you sure you want to delete scan {scan['summary_id']}?"):
        try:
            resp = requests.delete(f"{API_URL}/scans/{scan['summary_id']}")
            if resp.status_code == 200:
                print(_center_text("Scan deleted."))
            else:
                print(_center_text("Failed to delete scan."))
        except Exception as e:
            print(_center_text(f"Error: {e}"))
    else:
        print(_center_text("Deletion canceled."))
    
    input(_center_text("Press Enter..."))


def scan_manager_via_api():
    """Submenu for managing scans via API."""
    while True:
        sub_choice = _print_menu(
            "SCAN MANAGER (API)",
            [
                ("0", "Return to home screen"),
                ("1", "View stored project analyses"),
                ("2", "Update an existing scan"),
                ("3", "Generate Resume/Portfolio"),
                ("4", "Delete stored scans"),
            ],
            prompt="Choose an option (0-4): "
        )
        if sub_choice == "1": view_full_scan_details_via_api()
        elif sub_choice == "2": 
            print(_center_text("Update not implemented in client yet."))
            input(_center_text("Press Enter..."))
        elif sub_choice == "3": 
            print(_center_text("Generation not implemented in client yet."))
            input(_center_text("Press Enter..."))
        elif sub_choice == "4": delete_scan_via_api()
        elif sub_choice == "0": break


def initialize_app():
    """
    Application startup routine:
    - Checks API connection.
    - Displays welcome banner.
    - Checks/Sets privacy consent via API.
    - Returns the user's initial menu choice.
    """
    if not check_api_connection():
        sys.exit(1)

    print()
    print(_center_text("~~~~~~~~~~~~~~~~~~~~~~~"))
    print(_center_text("Welcome to Skill Scope!"))
    print(_center_text("~~~~~~~~~~~~~~~~~~~~~~~"))
    print()
    intro_lines = [
        "Skill Scope scans a project folder to summarize languages, frameworks,",
        "timelines, and contributions, then saves the results for later review.",
        "",
        "1) Run a new scan: choose files and an analysis mode to generate a report.",
        "2) Scan Manager: view previous scans, generate resumes/portfolios, or delete scans.",
        "3) Quit: exit the program.",
    ]
    for line in intro_lines:
        print(_center_text(line))
    print()
    initial_choice = input(_center_text("Choose an option (1-3): ")).strip()

    if initial_choice == "3":
        return initial_choice

    # Check if privacy consent is already set on the server; if not, ask locally.
    try:
        resp = requests.get(f"{API_URL}/privacy-consent")
        if resp.status_code == 200:
            settings = resp.json().get("privacy", {})
            if not settings.get("consent"):
                # Ask for consent locally if not set on server
                if not get_user_consent():
                    sys.exit(0)
                # Update API
                requests.post(f"{API_URL}/privacy-consent", json={"consent": True})
    except Exception:
        # If API check fails here, we proceed; check_api_connection already warned if down.
        pass

    return initial_choice


def home_screen(initial_choice=None):
    """Main application loop handling the top-level menu navigation."""
    pending_choice = initial_choice
    while True:
        if pending_choice is None:
            choice = _print_menu(
                "SKILL SCOPE HOME",
                [
                    ("1", "Run a new scan: choose files and an analysis mode to generate a report."),
                    ("2", "Scan Manager: view previous scans, generate resumes/portfolios, or delete scans."),
                    ("3", "Quit: exit the program."),
                ],
                prompt="Choose an option (1-3): ",
            )
        else:
            choice = pending_choice
            pending_choice = None

        if choice == "1":
            run_new_scan_via_api()
        elif choice == "2":
            scan_manager_via_api()
        elif choice == "3":
            print(_center_text("Goodbye!"))
            break
        else:
            print(_center_text("Invalid input. Try again."))


if __name__ == "__main__":
    try:
        choice = initialize_app()
        home_screen(initial_choice=choice)
    except KeyboardInterrupt:
        print()
        print(_center_text("Goodbye!"))
