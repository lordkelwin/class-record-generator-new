import openpyxl

wb = openpyxl.load_workbook('samples/FM-USeP-MID-10 Course Learning Outcome Evaluation Result.xlsx')
ws = wb.active

for r in range(1, 41):
    for c in range(1, ws.max_column + 1):
        cell = ws.cell(r, c)
        if cell.value is not None or (cell.border and (cell.border.left or cell.border.top or cell.border.bottom or cell.border.right)):
            val = str(cell.value) if cell.value is not None else ""
            f_name = cell.font.name if cell.font else ""
            f_sz = cell.font.size if cell.font else ""
            f_b = cell.font.bold if cell.font else False
            h_align = cell.alignment.horizontal if cell.alignment else ""
            v_align = cell.alignment.vertical if cell.alignment else ""
            wrap = cell.alignment.wrap_text if cell.alignment else False
            fill_hex = cell.fill.start_color.rgb if (cell.fill and cell.fill.start_color) else ""
            
            b_l = cell.border.left.style if cell.border and cell.border.left else ""
            b_r = cell.border.right.style if cell.border and cell.border.right else ""
            b_t = cell.border.top.style if cell.border and cell.border.top else ""
            b_b = cell.border.bottom.style if cell.border and cell.border.bottom else ""

            if val or b_l or b_r or b_t or b_b or fill_hex:
                print(f"R{r}C{c}({cell.coordinate}): val={repr(val)[:40]} font={f_name}_{f_sz}_b{f_b} align={h_align}/{v_align}/w{wrap} fill={fill_hex} b=({b_l},{b_r},{b_t},{b_b})")
