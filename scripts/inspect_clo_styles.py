import openpyxl

wb = openpyxl.load_workbook('samples/FM-USeP-MID-10 Course Learning Outcome Evaluation Result.xlsx', data_only=False)
ws = wb.active

def pcell(coord):
    c = ws[coord]
    font_str = f"font={c.font.name} {c.font.size}pt bold={c.font.bold} italic={c.font.italic} color={c.font.color.rgb if c.font.color else None}"
    fill_str = f"fill={c.fill.fill_type} {c.fill.start_color.rgb if c.fill and hasattr(c.fill, 'start_color') and c.fill.start_color else None}"
    align_str = f"align={c.alignment.horizontal}/{c.alignment.vertical} wrap={c.alignment.wrap_text}"
    border_str = f"border top={c.border.top.style if c.border and c.border.top else None} bottom={c.border.bottom.style if c.border and c.border.bottom else None} left={c.border.left.style if c.border and c.border.left else None} right={c.border.right.style if c.border and c.border.right else None}"
    num_str = f"num_format={c.number_format}"
    print(f"[{coord}] val={repr(c.value)} | {font_str} | {fill_str} | {align_str} | {border_str} | {num_str}")

print("=== DOC CONTROL BOX ===")
for coord in ['F2', 'G2', 'F3', 'G3', 'F4', 'G4', 'F5', 'G5', 'F6', 'G6']:
    pcell(coord)

print("\n=== HEADER & TITLE ===")
pcell('B2')
pcell('A7')

print("\n=== METADATA ROWS 9-13 ===")
for r in range(9, 14):
    pcell(f'A{r}')
    pcell(f'C{r}')
    pcell(f'G{r}')

print("\n=== TABLE 1 (CAP) ===")
pcell('A15')
pcell('A16')
pcell('C16')
pcell('C17')
pcell('A18')
pcell('C19')
pcell('G18')

print("\n=== TABLE 2 (CLO EVALUATION) ===")
pcell('A23')
pcell('A24')
pcell('C24')
pcell('C25')
pcell('A26')
pcell('C27')
pcell('G26')
pcell('A30')
pcell('C30')

print("\n=== NOTE & SIGNATORIES & ACTIONS ===")
pcell('A31')
pcell('A33')
pcell('D33')
pcell('A36')
pcell('D36')
pcell('A37')
pcell('D37')
pcell('A39')
pcell('D39')
