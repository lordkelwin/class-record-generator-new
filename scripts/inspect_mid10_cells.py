import openpyxl

wb = openpyxl.load_workbook('samples/FM-USeP-MID-10 Course Learning Outcome Evaluation Result.xlsx', data_only=False)
ws = wb.active

print("Sheet Title:", ws.title)
for r in range(1, 42):
    line_parts = []
    for c in range(1, ws.max_column + 1):
        cell = ws.cell(r, c)
        if cell.value is not None:
            coord = cell.coordinate
            val = repr(cell.value)
            line_parts.append(f"{coord}={val}")
    if line_parts:
        print(f"Row {r:2d}: " + " | ".join(line_parts))

print("\n--- BORDERS & STYLES ---")
for r in [2, 7, 9, 10, 16, 17, 18, 24, 25, 26, 30, 31, 33, 36, 37, 39]:
    c = ws.cell(r, 1)
    top_b = c.border.top.style if c.border and c.border.top else None
    bot_b = c.border.bottom.style if c.border and c.border.bottom else None
    left_b = c.border.left.style if c.border and c.border.left else None
    right_b = c.border.right.style if c.border and c.border.right else None
    print(f"R{r}C1: border(T={top_b}, B={bot_b}, L={left_b}, R={right_b})")
