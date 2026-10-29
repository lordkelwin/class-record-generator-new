import openpyxl

wb = openpyxl.load_workbook('samples/FM-USeP-MID-10 Course Learning Outcome Evaluation Result.xlsx', data_only=False)
ws = wb.active
print('Sheet name:', ws.title)

print("\n--- MERGED CELLS ---")
for m in sorted([str(m) for m in ws.merged_cells.ranges]):
    print(m)

print("\n--- ROW VALUES & FORMULAS ---")
for r in range(1, 42):
    row_vals = []
    for c in range(1, 8):
        v = ws.cell(r, c).value
        if v is not None:
            col_letter = openpyxl.utils.get_column_letter(c)
            row_vals.append(f"{col_letter}{r}: {repr(v)}")
    if row_vals:
        print(f"Row {r:2d}:", " | ".join(row_vals))

print("\n--- COLUMN WIDTHS ---")
for col_letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
    print(f"Col {col_letter}: {ws.column_dimensions[col_letter].width}")

print("\n--- ROW HEIGHTS ---")
for r in range(1, 42):
    h = ws.row_dimensions[r].height
    if h is not None:
        print(f"Row {r:2d} height: {h}")
