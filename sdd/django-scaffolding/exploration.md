# Exploration: Django Scaffolding + Question Import System

## Current State

The project at `C:\www\simulador-examenes` is a **greenfield** — no code, no git repo, no configuration files exist. The only contents are:

```
.atl/                          # Skill registry (auto-generated)
  skill-registry.md
  .skill-registry.cache.json
docs/                          # 9 official PDFs from SUBTEL
  Apendice_A_..._20201206.pdf  # 29 pages — 108 reglamento questions (all categories)
  Apendice_B_..._20201206.pdf  # 32 pages — 62 technical questions (Aspirante)
  Apendice_C_..._20201206.pdf  # 46 pages — 95 technical questions (Novicio)
  Apendice_D_..._20201206.pdf  # 51 pages — 119 technical questions (General)
  Apendice_E_..._20201206.pdf  # 41 pages — ~103 technical questions (Superior)
  examenes.pdf                 # 209 pages — older (2017) all-in-one with answer keys
  Form_RAF_01_...pdf           # 1 page — license application form (reference only)
  instructivo_de_examenes_v2.pdf  # 1 page — exam procedure guide (reference only)
  RA.449816.2023_FD.pdf        # 1 page — sample license (reference only)
```

## Question Structure (from PDF analysis)

### Format
- Multiple-choice, 4 options (A-D), exactly one correct answer
- Numbered sequentially per section (e.g., `1.-`, `2.-`)
- Sections per appendix: Electricidad, Electrónica, Conocimiento Práctico

### Category → Exam Mapping
| Category | Appendix | Questions in Pool | Exam Size | Sections |
|----------|----------|-------------------|-----------|----------|
| Aspirante | A (reglamento) + B (tech) | 108 + 62 = 170 | 18 (from A) + 12 (from B) | B-1, B-2, B-3 |
| Novicio | A (reglamento) + C (tech) | 108 + 95 = 203 | 15 (from A) + 15 (from C) | C-1, C-2, C-3 |
| General | A (reglamento) + D (tech) | 108 + 119 = 227 | 12 (from A) + 18 (from D) | D-1, D-2, D-3 |
| Superior | A (reglamento) + E (tech) | 108 + ~103 = ~211 | 6 (from A) + 24 (from E) | E-1, E-2, E-3 |

### Answer Keys
- **examenes.pdf** (2017): Has explicit answer keys at the end in compact format (`1 B 11 D 21 A`)
- **Appendix E** (2020): Also has answer keys at the end
- **Appendices A-D** (2020): No text-extractable answer keys found — answers likely indicated via **visual formatting** (bold, underline, color) that PyPDF2 cannot detect

### Critical Finding: Answer Extraction Challenge
The 2020 appendices (A-D) do not have answer keys in extractable text. Two approaches:
1. **Use PyMuPDF (fitz)** or **pdfplumber** to detect styled text (bold = correct answer)
2. **Use examenes.pdf** (2017) as the primary source since it has explicit answer keys, then cross-reference with 2020 appendices for any new/changed questions

## Affected Areas

- `C:\www\simulador-examenes\` — project root (needs git init, Django scaffold)
- `C:\www\simulador-examenes\docs\` — PDF source files for import
- New: `manage.py`, `config/`, `apps/`, `requirements.txt`, etc. (Django structure)

## Approaches

### 1. **Django + management command for PDF import**
Create Django project with a `load_questions` management command that parses PDFs and populates the database.

- Pros: Standard Django pattern, repeatable, version-controlled data
- Cons: PDF parsing is fragile, needs careful regex + styled text detection
- Effort: Medium

### 2. **Pre-process PDFs to JSON, then import JSON**
Write a standalone Python script to extract questions from PDFs into JSON files, then use a Django management command to load the JSON.

- Pros: Separates concerns (parsing vs. loading), easier to debug/validate, JSON is human-readable
- Cons: Extra step, two scripts to maintain
- Effort: Medium (but more robust)

### 3. **Direct PDF import with pdfplumber/PyMuPDF**
Use a more capable PDF library that can detect text styling to extract both questions and correct answers in one pass.

- Pros: Single step, can detect bold/correct answers
- Cons: pdfplumber/PyMuPDF are heavier dependencies, styling detection may still be unreliable
- Effort: Medium-High

## Recommendation

**Approach 2: Pre-process to JSON, then import.**

Reasons:
1. PDF parsing is inherently fragile — separating it from Django lets you validate data independently
2. The JSON files become a **canonical source of truth** that's easy to review, diff, and version-control
3. Answer key extraction from styled text is a known hard problem — isolating it makes debugging easier
4. The import script can run standalone (no Django needed) which is useful for initial data load and future PDF updates
5. You can hand-correct any parsing errors in the JSON before importing

## Risks

- **Answer extraction from 2020 appendices (A-D)**: Visual formatting detection is unreliable. Mitigation: cross-reference with examenes.pdf answer keys, or accept manual curation for edge cases
- **PDF layout variations**: Different appendices may have slightly different formatting. Mitigation: test extraction against each appendix separately
- **Question deduplication**: examenes.pdf (2017) and appendices (2020) may overlap. Mitigation: use appendices as primary source, use examenes.pdf only for answer keys
- **Unicode/Spanish text encoding**: PDF extraction may produce garbled characters. Mitigation: UTF-8 throughout, validation step in import

## Ready for Proposal

**Yes** — the exploration is complete. The orchestrator should:
1. Present findings to the user
2. Confirm the approach (recommend Approach 2)
3. Proceed to `sdd-propose` for the "django-scaffolding" change
