#!/usr/bin/env python
"""
Improved PDF Parser for Chilean Radio Amateur Exam Appendices.

Extracts questions from SUBTEL PDF appendices and outputs JSON in the
canonical format. Uses answer keys from examenes.pdf.

Usage:
    python scripts/parse_pdfs_v2.py

Requires: PyMuPDF (pip install PyMuPDF)
"""

import json
import re
import sys
import io
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install it with: pip install PyMuPDF")
    sys.exit(1)

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = BASE_DIR / "data"

# PDF file paths
PDF_FILES = {
    "reglamento": DOCS_DIR / "Apendice_A_Preguntas_de_Reglamento_Aspirante_Novicio_General_Superior_20201206.pdf",
    "aspirante": DOCS_DIR / "Apendice_B_PREGUNTAS_TECNICAS_ASPIRANTE_20201206.pdf",
    "novicio": DOCS_DIR / "Apendice_C_PREGUNTAS_TECNICAS_NOVICIO_20201206.pdf",
    "general": DOCS_DIR / "Apendice_D_PREGUNTAS_TECNICAS_GENERAL_20201206.pdf",
    "superior": DOCS_DIR / "Apendice_E_PREGUNTAS_TECNICAS_SUPERIOR_20201206.pdf",
    "answer_keys": DOCS_DIR / "examenes.pdf",
}

# Output files
OUTPUT_FILES = {
    "CD_reglamento": DATA_DIR / "cd_reglamento.json",
    "CA_reglamento": DATA_DIR / "ca_reglamento.json",
    "CE_reglamento": DATA_DIR / "ce_reglamento.json",
    "XQ_reglamento": DATA_DIR / "xq_reglamento.json",
    "CD_tecnica": DATA_DIR / "cd_tecnica.json",
    "CA_tecnica": DATA_DIR / "ca_tecnica.json",
    "CE_tecnica": DATA_DIR / "ce_tecnica.json",
    "XQ_tecnica": DATA_DIR / "xq_tecnica.json",
}

# Category mapping
CATEGORY_MAP = {
    "reglamento": {"area": "Reglamento", "categories": ["CD", "CA", "CE", "XQ"]},
    "aspirante": {"area": "Tecnica", "category": "CD"},
    "novicio": {"area": "Tecnica", "category": "CA"},
    "general": {"area": "Tecnica", "category": "CE"},
    "superior": {"area": "Tecnica", "category": "XQ"},
}

# =============================================================================
# Text Extraction
# =============================================================================

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages)


def extract_text_with_formatting(pdf_path: Path) -> list:
    """Extract text with formatting info from a PDF."""
    doc = fitz.open(str(pdf_path))
    result = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = ""
                spans_info = []
                for span in line["spans"]:
                    text = span["text"]
                    flags = span["flags"]
                    bold = bool(flags & (1 << 4))
                    underline = bool(flags & (1 << 3))
                    spans_info.append({
                        "text": text,
                        "bold": bold,
                        "underline": underline,
                        "font": span["font"],
                        "size": span["size"],
                    })
                    line_text += text
                result.append({
                    "text": line_text,
                    "spans": spans_info,
                    "page": page_num + 1,
                })
    doc.close()
    return result

# =============================================================================
# Answer Key Parsing
# =============================================================================

def parse_answer_keys(examenes_pdf: Path) -> dict:
    """Parse answer keys from examenes.pdf."""
    text = extract_text_from_pdf(examenes_pdf)
    
    answer_keys = {}
    
    # Generic answer line pattern: "1 B" or "1\nB" (with optional spaces)
    answer_line_pattern = re.compile(r"(\d+)\s+([A-Da-d])")
    
    def parse_section_answers(section_text: str) -> dict:
        """Parse answers from a section text."""
        answers = {}
        for match in answer_line_pattern.finditer(section_text):
            q_num = int(match.group(1))
            answer = match.group(2).upper()
            answers[q_num] = answer
        return answers
    
    # Find all answer key sections using flexible patterns
    # Each section starts with "RESPUESTAS" and ends at the next "RESPUESTAS" or end of text
    
    # Find all positions of answer headers
    header_positions = []
    for match in re.finditer(
        r"(?:Respuestas a preguntas|RESPUESTAS A PREGUNTAS|RESPUESTAS DE PREGUNTAS)\s+Ap[ée]ndice\s+([A-E])",
        text,
        re.IGNORECASE
    ):
        letter = match.group(1).upper()
        start_pos = match.start()
        header_positions.append((letter, start_pos))
    
    # Sort by position
    header_positions.sort(key=lambda x: x[1])
    
    # Extract text for each section
    for i, (letter, start_pos) in enumerate(header_positions):
        if i + 1 < len(header_positions):
            end_pos = header_positions[i + 1][1]
        else:
            end_pos = len(text)
        
        section_text = text[start_pos:end_pos]
        answer_keys[letter] = parse_section_answers(section_text)
    
    return answer_keys

# =============================================================================
# Question Parsing
# =============================================================================

def parse_questions_from_text(text: str, appendix_letter: str = None) -> list:
    """
    Parse questions from extracted PDF text.
    
    Handles the SUBTEL format:
        1.- Question text here?
        A.- Option A
        B.- Option B
        C.- Option C
        D.- Option D
    """
    questions = []
    
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Split into lines
    lines = text.split("\n")
    
    current_question_num = None
    current_question_text = ""
    current_options = {}
    current_option_letter = None
    current_option_text = ""
    
    def save_current_option():
        nonlocal current_option_letter, current_option_text
        if current_option_letter and current_option_text:
            current_options[current_option_letter] = current_option_text.strip()
            current_option_letter = None
            current_option_text = ""
    
    def save_current_question():
        nonlocal current_question_num, current_question_text, current_options
        save_current_option()
        
        if current_question_text and len(current_options) == 4:
            q = {
                "text": current_question_text.strip(),
                "option_a": current_options.get("A", ""),
                "option_b": current_options.get("B", ""),
                "option_c": current_options.get("C", ""),
                "option_d": current_options.get("D", ""),
                "correct_answer": "?",
                "explanation": "",
            }
            questions.append((current_question_num, q))
        
        current_question_num = None
        current_question_text = ""
        current_options = {}
    
    # Question pattern: "1.-" or "1.- " or "1." or "1.-\n" (number only on line)
    question_pattern = re.compile(r"^\s*(\d{1,4})\s*[\.\)\-]+\s*(.*)")
    
    # Question number only pattern (for cases like "41.-\n" with text on next line)
    question_num_pattern = re.compile(r"^\s*(\d{1,4})\s*[\.\)\-]+\s*$")
    
    # Option pattern: "A.-" or "A." or "A)" or "A -" or "A.-Text" or "C:-Text" (or B, C, D)
    # Note: Some options have no space after the dot (e.g., "A.-Sólo"), some use colon
    option_pattern = re.compile(r"^\s*([A-Da-d])\s*[\.\)\-:]+\s*(.*)")
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            continue
        
        # Skip known header/footer lines (exact match or starts-with)
        skip_patterns = [
            "SUBSECRETARIA DE TELECOMUNICACIONES",
            "APENDICE A", "APENDICE B", "APENDICE C", "APENDICE D", "APENDICE E",
            "ACTUALIZADO AL", "PREGUNTAS DEL REGLAMENTO",
            "CATEGORÍA ASPIRANTE", "CATEGORÍA NOVICIO", "CATEGORÍA GENERAL", "CATEGORÍA SUPERIOR",
            "PROGRAMAS DE MATERIAS", "MATERIA PARA POSTULAR",
            "EL PRESENTE APÉNDICE", "ESTE APÉNDICE",
            "CONTIENE, ADEMÁS", "PARA OPTAR A",
            "LICENCIA CATEGORÍA", "MATERIA PARA",
            "TODAS LAS CATEGORÍAS", "LAS MATERIAS TÉCNICAS",
            "PARA LOS EFECTOS", "LAS PREGUNTAS SON",
            "PROGRAMA DE MATERIAS", "MATERIAS TECNICAS",
            "PREGUNTAS DE ELECTRICIDAD", "PREGUNTAS DE ELECTRÓNICA",
            "PREGUNTAS DE CONOCIMIENTO", "PREGUNTAS DE TRANSMISORES",
            "PREGUNTAS DE RECEPTORES", "PREGUNTAS DE PROPAGACIÓN",
            "SECCION B-1", "SECCION B-2", "SECCION B-3",
            "SECCION C-1", "SECCION C-2", "SECCION C-3",
            "SECCION D-1", "SECCION D-2", "SECCION D-3",
            "SECCION E-1", "SECCION E-2", "SECCION E-3",
            "SECCIÓN C-1", "SECCIÓN C-2", "SECCIÓN C-3",
            "SECCIÓN D-1", "SECCIÓN D-2", "SECCIÓN D-3",
            "SECCIÓN E-1", "SECCIÓN E-2", "SECCIÓN E-3",
            "RESPUESTAS A PREGUNTAS", "RESPUESTAS DE PREGUNTAS",
            "APÉNDICE", "APENDICE",
            "- Actualizado al", "Actualizado al",
        ]
        
        # Check if line matches any skip pattern
        upper_stripped = stripped.upper()
        if any(upper_stripped.startswith(p.upper()) for p in skip_patterns):
            continue
        
        # Skip lines that are just numbers with dots (section numbers like "1.1", "2.3")
        if re.match(r"^\d+\.\d+\s", stripped):
            continue
        
        # Skip lines that are just category/exam labels
        if re.match(r"^\s*(CATEGORÍA|CATEGORIA|EXAMEN|CONTIENE)\s*$", stripped, re.IGNORECASE):
            continue
        
        # Check for new question
        q_match = question_pattern.match(stripped)
        if q_match:
            q_num = int(q_match.group(1))
            q_text = q_match.group(2).strip()
            
            # Save previous question and start new one
            save_current_question()
            current_question_num = q_num
            current_question_text = q_text
            continue
        
        # Check for question number only (text on next line)
        q_num_match = question_num_pattern.match(stripped)
        if q_num_match:
            q_num = int(q_num_match.group(1))
            save_current_question()
            current_question_num = q_num
            current_question_text = ""
            continue
        
        # Check for option
        opt_match = option_pattern.match(stripped)
        if opt_match:
            save_current_option()
            current_option_letter = opt_match.group(1).upper()
            current_option_text = opt_match.group(2).strip()
            continue
        
        # If we're in an option, append text to current option
        if current_option_letter:
            current_option_text += " " + stripped
            continue
        
        # If we're in a question (no options yet), append to question text
        if current_question_num and not current_options:
            if current_question_text:
                current_question_text += " " + stripped
            else:
                current_question_text = stripped
            continue
    
    # Save the last question
    save_current_question()
    
    return questions

# =============================================================================
# Question Validation and Building
# =============================================================================

def build_question_dict(q_num: int, q_data: dict, answer: str = None) -> dict:
    """Build a canonical question dictionary."""
    return {
        "text": q_data["text"].strip(),
        "option_a": q_data["option_a"].strip(),
        "option_b": q_data["option_b"].strip(),
        "option_c": q_data["option_c"].strip(),
        "option_d": q_data["option_d"].strip(),
        "correct_answer": answer if answer else "?",
        "explanation": "",
    }


def validate_question(q: dict, index: int) -> tuple:
    """Validate a parsed question. Returns (is_valid, errors)."""
    errors = []
    
    if not q.get("text") or len(q["text"].strip()) < 10:
        errors.append(f"Q{index}: Question text too short or missing: '{q.get('text', '')[:50]}'")
    
    for letter in ["A", "B", "C", "D"]:
        key = f"option_{letter.lower()}"
        if not q.get(key) or len(q[key].strip()) < 1:
            errors.append(f"Q{index}: Option {letter} is missing or empty")
    
    correct = q.get("correct_answer", "")
    if correct not in {"A", "B", "C", "D"}:
        errors.append(f"Q{index}: Invalid correct_answer '{correct}'")
    
    return len(errors) == 0, errors


def clean_question_text(text: str) -> str:
    """Clean question text of artifacts."""
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove trailing punctuation artifacts
    text = re.sub(r'\s+', ' ', text)
    
    return text


def clean_option_text(text: str) -> str:
    """Clean option text of artifacts."""
    text = text.strip()
    
    # Remove "(correcto)" or similar markers
    text = re.sub(r'\s*\(?\s*(?:correcto|correcta|correct|VERDADERO)\s*\)?\s*', '', text, flags=re.IGNORECASE)
    
    # Remove trailing punctuation artifacts
    text = text.rstrip(" .,-")
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text

# =============================================================================
# Main Processing
# =============================================================================

def process_appendix(appendix_key: str, answer_keys: dict) -> list:
    """
    Process a single appendix and return parsed questions.
    
    Returns list of (category, area, questions) tuples.
    """
    pdf_path = PDF_FILES[appendix_key]
    meta = CATEGORY_MAP[appendix_key]
    
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_path.name}")
    print(f"Area: {meta['area']}")
    print(f"{'='*60}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        print(f"  ERROR: No text extracted from {pdf_path.name}")
        return []
    
    # Parse questions
    raw_questions = parse_questions_from_text(text)
    print(f"  Raw questions parsed: {len(raw_questions)}")
    
    # Get answer key
    letter_map = {
        "reglamento": "A",
        "aspirante": "B",
        "novicio": "C",
        "general": "D",
        "superior": "E",
    }
    appendix_letter = letter_map.get(appendix_key, "A")
    answers = answer_keys.get(appendix_letter, {})
    print(f"  Answer keys found: {len(answers)}")
    
    # Build questions with answers
    results = []
    questions_with_answers = 0
    questions_without_answers = 0
    validation_errors = 0
    
    for q_num, q_data in raw_questions:
        answer = answers.get(q_num, None)
        
        # Clean texts
        q_data["text"] = clean_question_text(q_data["text"])
        for letter in ["A", "B", "C", "D"]:
            key = f"option_{letter.lower()}"
            q_data[key] = clean_option_text(q_data[key])
        
        # Build question
        q = build_question_dict(q_num, q_data, answer)
        
        # Validate
        is_valid, errors = validate_question(q, q_num)
        
        if is_valid:
            results.append(q)
            if answer:
                questions_with_answers += 1
            else:
                questions_without_answers += 1
        else:
            validation_errors += 1
            for err in errors:
                print(f"    WARNING: {err}")
    
    print(f"  Valid questions: {len(results)}")
    print(f"  With answers: {questions_with_answers}")
    print(f"  Without answers: {questions_without_answers}")
    print(f"  Validation errors: {validation_errors}")
    
    # Determine output categories
    if appendix_key == "reglamento":
        # Appendix A is shared across all categories
        return [
            (cat, meta["area"], results)
            for cat in meta["categories"]
        ]
    else:
        return [(meta["category"], meta["area"], results)]


def save_results(results: list, output_path: Path):
    """Save results to a JSON file."""
    category, area, questions = results
    
    data = {
        "category": category,
        "area": area,
        "questions": questions,
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  Saved: {output_path.name} ({len(questions)} questions)")


def main():
    """Main entry point."""
    print("="*60)
    print("Chilean Radio Amateur Exam PDF Parser v2")
    print("="*60)
    
    # Check if files exist
    for key, path in PDF_FILES.items():
        if not path.exists():
            print(f"ERROR: File not found: {path}")
            sys.exit(1)
    
    # Parse answer keys first
    print("\nParsing answer keys from examenes.pdf...")
    answer_keys = parse_answer_keys(PDF_FILES["answer_keys"])
    
    for key, answers in answer_keys.items():
        print(f"  Appendix {key}: {len(answers)} answers")
    
    # Process each appendix
    all_results = {}
    total_questions = 0
    
    for appendix_key in ["reglamento", "aspirante", "novicio", "general", "superior"]:
        results = process_appendix(appendix_key, answer_keys)
        
        for category, area, questions in results:
            key = f"{category}_{area}"
            all_results[key] = (category, area, questions)
            total_questions += len(questions)
    
    # Save results
    print("\n" + "="*60)
    print("Saving results...")
    print("="*60)
    
    for key, (category, area, questions) in all_results.items():
        output_path = DATA_DIR / f"{category.lower()}_{area.lower()}.json"
        save_results((category, area, questions), output_path)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_with_answers = 0
    total_without_answers = 0
    
    for key, (category, area, questions) in all_results.items():
        with_answers = sum(1 for q in questions if q["correct_answer"] != "?")
        without_answers = len(questions) - with_answers
        total_with_answers += with_answers
        total_without_answers += without_answers
        
        print(f"\n{category} - {area}:")
        print(f"  Total questions: {len(questions)}")
        print(f"  With answers: {with_answers}")
        print(f"  Without answers: {without_answers}")
    
    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {total_questions} questions")
    print(f"  With answers: {total_with_answers}")
    print(f"  Without answers: {total_without_answers}")
    print(f"{'='*60}")
    
    # List output files
    print("\nOutput files:")
    for key in sorted(all_results.keys()):
        category, area, questions = all_results[key]
        output_path = DATA_DIR / f"{category.lower()}_{area.lower()}.json"
        if output_path.exists():
            print(f"  {output_path}")


if __name__ == "__main__":
    main()
