import xlrd
from itertools import izip

class XlsType(object):
    xls_date = 3
    xls_string = 1
    xls_float = 2
    xls_empty = 0

def cell_stream_from_sheet(sheet, end_row, end_col, start_row=0, start_col=0, 
                    row_values=lambda sheet, ndx: sheet.row_types(ndx),
                    empty_value=XlsType.xls_empty):
    """
    >>> import xlrd
    >>> wb = xlrd.open_workbook('input1.xls')
    >>> sheet = wb.sheet_by_index(0)
    >>> len([x for x in cell_stream_from_sheet(sheet, 2, 1)])
    6
    >>> len([x for x in cell_stream_from_sheet(sheet, 2, 1, start_row=1)])
    4
    >>> len([x for x in cell_stream_from_sheet(sheet, 2, 1000, start_row=1)])
    2002
    """

    for i in range(start_row, min(end_row + 1, sheet.nrows)):
        row = row_values(sheet, i)
        for j in range(start_col, min(end_col + 1, len(row))):
            yield row[j]
        for j in range(j + 1, end_col + 1):
            yield empty_value
                           
    for i_left in range(i + 1, end_row + 1):
        for j_left in range(0, end_col + 1):
            yield empty_value

if __name__ == '__main__':
    import doctest
    doctest.testmod()
