if __name__ == "__main__":
	import argparse
	from codeparser.chunking import write_chunks_json
	from codeparser.file_classification import is_binary_file
	
	parser = argparse.ArgumentParser(description="gen jsonl data for the ML model")
	parser.add_argument("root", type=str, help="Path to repo/extracted zip")
	parser.add_argument("--out", type=str, default="chunks.jsonl", help="Output file")
	parser.add_argument("--max-chars", type=int, default=2000, help="Max chars per chunk, default 2k")
	parser.add_argument("--overlap", type=int, default=200, help="Overlap chars")
	parser.add_argument("--max-file-chars", type=int, default=1_000_000, help="file char count limit")
	args = parser.parse_args()

	n = write_chunks_json(repo_root=args.root, out_json=args.out, is_binary_file=is_binary_file, max_file_chars=args.max_file_chars, max_chars=args.max_chars,overlap=args.overlap)

	print(f"Wrote {n} chunks to file {args.out}")
	
