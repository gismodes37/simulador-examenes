#!/usr/bin/env python
"""
PDF Parser for Chilean Radio Amateur Exam Appendices.

Standalone script (not a Django management command) that extracts questions
from SUBTEL PDF appendices and outputs JSON in the canonical format.

Usage:
    python scripts/parse_pdfs.py
    python scripts/parse_pdfs.py --input docs/ --output data/
    python scripts/parse_pdfs.py --file docs/Apendice_A_Preguntas_de_Reglamento_...pdf

Requires: PyMuPDF (pip install PyMuPDF)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install it with: pip install PyMuPDF")
    sys.exit(1)


# Appendix metadata: maps filename patterns to category/area
APPENDIX_MAP = {
    "Apendice_A": {
        "category": "all",
        "area": "Reglamento",
        "description": "Preguntas de Reglamento (todas las categorías)",
    },
    "Apendice_B": {
        "category": "all",
        "area": "Tecnica",
        "description": "Preguntas Técnicas Aspirante",
        "tema": "Aspirante",
    },
    "Apendice_C": {
        "category": "CD",
        "area": "Tecnica",
        "description": "Preguntas Técnicas Novicio",
        "tema": "Novicio",
    },
    "Apendice_D": {
        "category": "CA",
        "area": "Tecnica",
        "description": "Preguntas Técnicas General",
        "tema": "General",
    },
    "Apendice_E": {
        "category": "CE",
        "area": "Tecnica",
        "description": "Preguntas Técnicas Superior",
        "tema": "Superior",
    },
}

# Regex patterns for question parsing
# Matches: "1." or "1 )" or "1 -" at the start of a line
QUESTION_PATTERN = re.compile(
    r"^\s*(\d{1,4})\s*[\.\)\-]\s*(.+)", re.MULTILINE
)

# Matches option lines: "a)" or "a -" or "a."
OPTION_PATTERN = re.compile(
    r"^\s*([a-dA-D])\s*[\.\)\-]\s*(.+)", re.MULTILINE
)

# Matches correct answer marker
CORRECT_PATTERN = re.compile(
    r"\(?\s*(?:correcto|correcta|correct|VERDADERO)\s*\)?", re.IGNORECASE
)


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        full_text += page.get_text("text") + "\n"
    doc.close()
    return full_text


def detect_appendix_type(filename):
    """Detect the appendix type from the filename."""
    basename = Path(filename).stem
    for key, meta in APPENDIX_MAP.items():
        if key in basename:
            return meta
    return None


def parse_questions_from_text(text):
    """
    Parse questions from extracted PDF text.

    Handles the SUBTEL format:
        1. Question text here?
        a) Option A (correcto)
        b) Option B
        c) Option C
        d) Option D
    """
    questions = []

    # Normalize line endings and clean up
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split into lines
    lines = text.split("\n")

    current_question_num = None
    current_question_text = ""
    current_options = {}
    current_correct = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if this is a new question
        q_match = QUESTION_PATTERN.match(line_stripped)
        if q_match:
            # Save previous question if complete
            if (
                current_question_text
                and len(current_options) == 4
                and current_correct
            ):
                questions.append(
                    _build_question_dict(
                        current_question_text,
                        current_options,
                        current_correct,
                    )
                )

            current_question_num = int(q_match.group(1))
            current_question_text = q_match.group(2).strip()
            current_options = {}
            current_correct = None
            continue

        # Check if this is an option line
        opt_match = OPTION_PATTERN.match(line_stripped)
        if opt_match:
            letter = opt_match.group(1).upper()
            option_text = opt_match.group(2).strip()

            # Check if marked as correct
            is_correct = bool(CORRECT_PATTERN.search(option_text))
            # Clean the option text of the marker
            option_text = CORRECT_PATTERN.sub("", option_text).strip()
            # Remove trailing punctuation artifacts
            option_text = option_text.rstrip(" .,-")

            current_options[letter] = option_text
            if is_correct:
                current_correct = letter
            continue

        # If we're mid-question and this is a continuation line
        if current_question_text and not current_options:
            current_question_text += " " + line_stripped
            continue

    # Don't forget the last question
    if current_question_text and len(current_options) == 4 and current_correct:
        questions.append(
            _build_question_dict(
                current_question_text, current_options, current_correct
            )
        )

    return questions


def _build_question_dict(text, options, correct_answer):
    """Build a canonical question dictionary."""
    return {
        "text": text.strip(),
        "option_a": options.get("A", "").strip(),
        "option_b": options.get("B", "").strip(),
        "option_c": options.get("C", "").strip(),
        "option_d": options.get("D", "").strip(),
        "correct_answer": correct_answer,
        "explanation": "",
    }


def validate_question(q, index):
    """Validate a parsed question. Returns (is_valid, errors)."""
    errors = []
    if not q.get("text") or len(q["text"].strip()) < 5:
        errors.append(f"Q{index}: Question text too short or missing")

    for letter in ["A", "B", "C", "D"]:
        key = f"option_{letter.lower()}"
        if not q.get(key) or len(q[key].strip()) < 1:
            errors.append(f"Q{index}: Option {letter} is missing or empty")

    correct = q.get("correct_answer", "")
    if correct not in {"A", "B", "C", "D"}:
        errors.append(f"Q{index}: Invalid correct_answer '{correct}'")

    return len(errors) == 0, errors


def process_pdf(pdf_path, category_override=None):
    """
    Process a single PDF file and return parsed questions.

    Args:
        pdf_path: Path to the PDF file.
        category_override: Override category (useful for Appendix A).

    Returns:
        dict with 'category', 'area', 'questions' keys, or None on error.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"  Error: File not found: {pdf_path}")
        return None

    appendix_meta = detect_appendix_type(pdf_path.name)
    if appendix_meta is None:
        print(f"  Warning: Could not detect appendix type for {pdf_path.name}")
        print("  Skipping this file.")
        return None

    print(f"  Appendix: {appendix_meta['description']}")
    print(f"  Area: {appendix_meta['area']}")

    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        print(f"  Warning: No text extracted from {pdf_path.name}")
        return None

    # Parse questions
    questions = parse_questions_from_text(text)
    print(f"  Parsed {len(questions)} questions")

    # Validate
    valid_questions = []
    invalid_count = 0
    for i, q in enumerate(questions, 1):
        is_valid, errors = validate_question(q, i)
        if is_valid:
            valid_questions.append(q)
        else:
            invalid_count += 1
            for err in errors:
                print(f"    Warning: {err}")

    if invalid_count:
        print(f"  {invalid_count} questions discarded due to validation errors")

    category = category_override or appendix_meta.get("category", "all")
    if category == "all":
        # Appendix A contains Reglamento questions for all categories.
        # We'll output one file per category.
        categories = ["CD", "CA", "CE"]
        results = []
        for cat in categories:
            results.append(
                {
                    "category": cat,
                    "area": appendix_meta["area"],
                    "questions": valid_questions,
                }
            )
        return results

    return {
        "category": category,
        "area": appendix_meta["area"],
        "questions": valid_questions,
    }


def save_questions(data, output_dir):
    """Save question data to a JSON file in the output directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(data, list):
        # Multiple files (e.g., Appendix A split by category)
        for item in data:
            filename = f"{item['category'].lower()}_{item['area'].lower()}.json"
            filepath = output_dir / filename
            _write_json(filepath, item)
    else:
        filename = f"{data['category'].lower()}_{data['area'].lower()}.json"
        filepath = output_dir / filename
        _write_json(filepath, data)


def _write_json(filepath, data):
    """Write data to a JSON file with proper formatting."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {filepath} ({len(data['questions'])} questions)")


def main():
    parser = argparse.ArgumentParser(
        description="Parse Chilean radio amateur exam PDFs into JSON format."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="docs",
        help="Input directory containing PDFs (default: docs/)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data",
        help="Output directory for JSON files (default: data/)",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Process a specific PDF file instead of the whole directory.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if args.file:
        # Process single file
        pdf_path = Path(args.file)
        print(f"Processing: {pdf_path}")
        result = process_pdf(pdf_path)
        if result:
            save_questions(result, output_dir)
    else:
        # Process all PDFs in directory
        if not input_dir.exists():
            print(f"Error: Input directory not found: {input_dir}")
            sys.exit(1)

        pdf_files = sorted(input_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {input_dir}")
            sys.exit(0)

        print(f"Found {len(pdf_files)} PDF file(s) in {input_dir}\n")
        total_questions = 0

        for pdf_path in pdf_files:
            print(f"Processing: {pdf_path.name}")
            result = process_pdf(pdf_path)
            if result:
                save_questions(result, output_dir)
                if isinstance(result, list):
                    total_questions += sum(
                        len(item["questions"]) for item in result
                    )
                else:
                    total_questions += len(result["questions"])
            print()

        print(f"Done! Total questions extracted: {total_questions}")
        print(f"JSON files saved to: {output_dir}")


if __name__ == "__main__":
    main()
