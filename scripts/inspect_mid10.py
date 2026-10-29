import openpyxl

wb = openpyxl.load_workbook('samples/FM-USeP-MID-10 Course Learning Outcome Evaluation Result.xlsx', data_only=False)
ws = wb.active

print('--- MERGED RANGES ---')
for m in sorted(list(ws.merged_cells.ranges), key=lambda x: (x.min_row, x.min_col)):
    print(m)

print('\n--- COLUMN WIDTHS ---')
for col_letter, col_dim in sorted(ws.column_dimensions.items()):
    print(f'{col_letter}: {col_dim.width}')

print('\n--- ROWS WITH CONTENT & STYLES ---')
for r in range(1, 45):
    has_val = False
    for c in range(1, 15):
        cell = ws.cell(r, c)
        if cell.value is not None:
            has_val = True
            break
    if has_val:
        row_str = []
        for c in range(1, 12):
            cell = ws.cell(r, c)
            if cell.value is not None:
                val = str(cell.value).replace('\n', '\\n')
                font_name = cell.font.name if cell.font else ''
                font_size = cell.font.size if cell.font else ''
                font_bold = cell.font.bold if cell.font else False
                fill = cell.fill.start_color.rgb if (cell.fill and cell.fill.fill_type) else None
                align = cell.alignment.horizontal if cell.alignment else None
                row_str.append(f'C{c}({cell.coordinate}): "{val}" [Font: {font_name} {font_size}pt bold={font_bold}, Fill: {fill}, Align: {align}]')
        print(f'Row {r:2d} (height={ws.row_dimensions[r].height}):')
        for item in row_str:
            print('   ', item)
