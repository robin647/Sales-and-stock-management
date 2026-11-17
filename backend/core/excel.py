def protect_workbook(workbook):
    """Export database strings as literal text, never spreadsheet formulas.

    Assigning '=...' to an openpyxl cell marks it as a formula. Our exports
    contain computed Python totals, so no exported formula is intentional.
    """
    for sheet in workbook:
        for row in sheet:
            for cell in row:
                if cell.data_type == "f":
                    cell.data_type = "s"
