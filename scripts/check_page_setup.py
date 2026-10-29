import openpyxl

wb = openpyxl.load_workbook('samples/FM-USeP-MID-10 Course Learning Outcome Evaluation Result.xlsx')
ws = wb.active
print("Orientation:", ws.page_setup.orientation)
print("Paper size:", ws.page_setup.paperSize)
print("Fit to width:", ws.page_setup.fitToWidth)
print("Fit to height:", ws.page_setup.fitToHeight)
print("Fit to page:", ws.sheet_properties.pageSetUpPr.fitToPage if ws.sheet_properties.pageSetUpPr else None)
print("Margins: left=", ws.page_margins.left, "right=", ws.page_margins.right, "top=", ws.page_margins.top, "bottom=", ws.page_margins.bottom)
