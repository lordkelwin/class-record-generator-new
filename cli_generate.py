import argparse
import os
from sample_syllabus import generate_sample_syllabus_pdf
from syllabus_parser import analyze_syllabus_pdf
from excel_generator import generate_class_record_workbook


def main():
    parser = argparse.ArgumentParser(
        description="Analyze an OBE Course Syllabus PDF and translate it into a formula-driven Excel Class Record (.xlsx)."
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default="EE 211.pdf",
        help="Path to the input Syllabus PDF file (defaults to EE 211.pdf).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join("exports", "EE_211_EE_2A_OBE_Class_Record.xlsx"),
        help="Output Excel (.xlsx) class record path.",
    )
    parser.add_argument("--ai", action="store_true", help="Enable optional Gemini AI fallback parser.")
    parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY", ""), help="Gemini API Key.")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"[*] Generating sample OBE Engineering Syllabus PDF at: {args.pdf_path}")
        generate_sample_syllabus_pdf(args.pdf_path)

    print(f"[*] Analyzing Syllabus PDF: {args.pdf_path}")
    blueprint = analyze_syllabus_pdf(
        args.pdf_path,
        use_ai=args.ai,
        gemini_api_key=args.api_key,
        include_sample_students=True,
    )
    for note in blueprint.parser_notes:
        print(f"    - {note}")

    xlsx_bytes = generate_class_record_workbook(blueprint)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(xlsx_bytes)

    print(f"[+] Successfully generated OBE Class Record Workbook: {args.output} ({len(xlsx_bytes):,} bytes)")


if __name__ == "__main__":
    main()
