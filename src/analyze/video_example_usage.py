from src.analyze.video_analyzer import VideoAnalyzer
from pathlib import Path
from colorama import Fore, Style, init
import os
import sys

# Initialize colorama for colored terminal output
init(autoreset=True)


def analyze_single_video():
    """Analyze a single video file."""
    print(f"\n{Fore.CYAN}=== Single Video Analysis ==={Style.RESET_ALL}")

    video_path = input("Enter path to video file: ").strip().strip('"').strip("'")
    file_path = Path(video_path).expanduser().resolve()

    if not file_path.exists():
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} File not found: {file_path}")
        return

    # Ask about transcription
    transcribe = False
    print(f"\n{Fore.YELLOW}Would you like to generate a transcript? (requires audio){Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Models:{Style.RESET_ALL} tiny (fastest) | base (recommended) | small | medium | large")
    
    transcribe_choice = input("Enter model name or 'n' to skip: ").strip().lower()
    
    if transcribe_choice not in ['n', 'no', '']:
        transcribe = True
        model_name = transcribe_choice if transcribe_choice in ['tiny', 'base', 'small', 'medium', 'large'] else 'base'
        analyzer = VideoAnalyzer(whisper_model=model_name)
    else:
        analyzer = VideoAnalyzer()

    result = analyzer.analyze_file(file_path, transcribe=transcribe)

    if result:
        print(f"\n{Fore.CYAN}File:{Style.RESET_ALL} {Path(result.file_path).name}")
        print(f"Duration: {Fore.YELLOW}{result.duration_seconds:.2f}s{Style.RESET_ALL}")
        print(f"Resolution: {Fore.MAGENTA}{result.resolution}{Style.RESET_ALL}")
        print(f"FPS: {Fore.YELLOW}{result.frame_rate:.2f}{Style.RESET_ALL}")
        print(f"Frames: {Fore.YELLOW}{result.total_frames}{Style.RESET_ALL}")
        print(f"Audio: {(Fore.GREEN + 'Yes') if result.has_audio else (Fore.RED + 'No')}{Style.RESET_ALL}")
        print(f"Format: {Fore.CYAN}{result.format.upper()}{Style.RESET_ALL}")
        print(f"Type: {Fore.BLUE}{result.file_type}{Style.RESET_ALL}")
        
        if result.transcript:
            print(f"\n{Fore.CYAN}=== Transcript ==={Style.RESET_ALL}")
            print(f"Language: {Fore.YELLOW}{result.transcript_language}{Style.RESET_ALL}")
            print(f"\n{result.transcript}\n")

        # Ask to save results
        save_choice = input(f"\nSave results to JSON? (y/n): ").strip().lower()
        if save_choice == "y":
            outputs_dir = Path("outputs")
            outputs_dir.mkdir(exist_ok=True)
            
            output_path = outputs_dir / f"{file_path.stem}_analysis.json"
            
            if result.transcript:
                separate = input("Save transcript in separate file? (y/n): ").strip().lower()
                analyzer.save_to_json([result], output_path, separate_transcripts=(separate == 'y'))
            else:
                analyzer.save_to_json([result], output_path)
            
            print(f"{Fore.GREEN}[SAVED]{Style.RESET_ALL} Results exported to {output_path}")

        print(f"\n{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Video analyzed successfully!\n")
    else:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to analyze the video file.")


def analyze_video_directory():
    """Analyze all video files in a directory."""
    print(f"\n{Fore.CYAN}=== Directory Video Analysis ==={Style.RESET_ALL}")

    dir_path = input("Enter path to directory: ").strip().strip('"').strip("'")
    directory = Path(dir_path).expanduser().resolve()

    if not directory.exists() or not directory.is_dir():
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Directory not found: {directory}")
        return

    # Ask about transcription
    transcribe = False
    print(f"\n{Fore.YELLOW}Would you like to transcribe all videos with audio?{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Models:{Style.RESET_ALL} tiny (fastest) | base (recommended) | small | medium | large")
    print(f"  {Fore.YELLOW}Note:{Style.RESET_ALL} This may take time for multiple/long videos")
    
    transcribe_choice = input("Enter model name or 'n' to skip: ").strip().lower()
    
    if transcribe_choice not in ['n', 'no', '']:
        transcribe = True
        model_name = transcribe_choice if transcribe_choice in ['tiny', 'base', 'small', 'medium', 'large'] else 'base'
        analyzer = VideoAnalyzer(whisper_model=model_name)
    else:
        analyzer = VideoAnalyzer()

    results = analyzer.analyze_directory(directory, transcribe=transcribe)

    if not results:
        print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} No valid video files found in {directory}")
        return

    metrics = analyzer.calculate_collection_metrics(results)

    print(f"\n{Fore.CYAN}=== Analysis Summary ==={Style.RESET_ALL}")
    print(f"Found {Fore.YELLOW}{metrics.total_videos}{Style.RESET_ALL} video file(s)")
    print(f"Total Duration: {Fore.YELLOW}{metrics.total_duration:.2f}s{Style.RESET_ALL}")
    print(f"Average FPS: {Fore.MAGENTA}{metrics.average_fps:.2f}{Style.RESET_ALL}")
    print(f"Resolutions: {Fore.CYAN}{', '.join(metrics.resolutions) if metrics.resolutions else 'N/A'}{Style.RESET_ALL}")
    print(f"Formats: {Fore.CYAN}{', '.join(metrics.formats) if metrics.formats else 'N/A'}{Style.RESET_ALL}")
    print(f"Videos with Audio: {Fore.GREEN}{metrics.audio_videos}{Style.RESET_ALL}")
    print(f"Video-only Files: {Fore.RED}{metrics.video_only_files}{Style.RESET_ALL}")
    
    if transcribe:
        print(f"Transcribed Videos: {Fore.GREEN}{metrics.transcribed_videos}{Style.RESET_ALL}")

    # Save results to JSON
    save_choice = input(f"\nWould you like to save results to JSON? (y/n): ").strip().lower()
    if save_choice == "y":
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        
        output_path = outputs_dir / f"{directory.name}_analysis.json"
        
        if transcribe and any(r.transcript for r in results):
            separate = input("Save transcripts in separate file? (y/n): ").strip().lower()
            analyzer.save_to_json(results, output_path, separate_transcripts=(separate == 'y'))
        else:
            analyzer.save_to_json(results, output_path)
        
        print(f"{Fore.GREEN}[SAVED]{Style.RESET_ALL} Results exported to outputs/ folder")

    print(f"\n{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Directory analyzed successfully!\n")


def main():
    """Entry point for CLI-based video analyzer."""
    print(f"{Fore.CYAN}=== Video Analyzer with Transcription ==={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Analyze a single video file")
    print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Analyze all videos in a directory")

    choice = input("\nChoose an option (1 or 2): ").strip()

    if choice == "1":
        analyze_single_video()
    elif choice == "2":
        analyze_video_directory()
    else:
        print(f"{Fore.RED}Invalid choice. Please select 1 or 2.{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
        print(f"\n{Fore.GREEN}[DONE]{Style.RESET_ALL} All operations completed successfully.\n")
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[EXIT]{Style.RESET_ALL} Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}[ERROR]{Style.RESET_ALL} {str(e)}")
        sys.exit(1)