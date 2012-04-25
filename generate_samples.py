#!/usr/bin/env python

import xlwt
import random

excel_date_fmt = 'YYYY/MM/DD'
date_style = xlwt.XFStyle()
date_style.num_format_str = excel_date_fmt

def identifier():
    return 'ID' + str(random.random())[-5:]

def value(start, end):
    initial = random.random()
    has_value = random.choice([True] * 9 + [False])
    
    if has_value:
        size = end - start
        return start + (initial * size)
    else:
        return ''

def write_doc(name, random_swap=False):
    wbk = xlwt.Workbook()
    sheet = wbk.add_sheet('sheet 1')

    cols = {0: ('CODE', lambda: (identifier(), None)),
            1: ('Date', lambda: (value(40500, 41000), date_style)),
            2: ('Wat', lambda: (value(1, 16), None)),
            3: ('Price', lambda: (value(10, 16), None)),
            4: ('Other', lambda: (value(20, 4000), None))}

    if random_swap:
        keys = cols.keys()
        swap1 = random.choice(keys)
        keys.remove(swap1)
        swap2 = random.choice(keys)
        cols[swap1], cols[swap2] = cols[swap2], cols[swap1]

    for k in cols:
        col_name, _ = cols[k]
        sheet.write(0, k, col_name)

    for i in range(1, 10):
        for k in cols:
            _, fun = cols[k]
            val, fmt = fun()
            if fmt:
                sheet.write(i, k, val, fmt)
            else:
                sheet.write(i, k, val)

    wbk.save(name)

if __name__ == '__main__':
    for i in range(0, 60):
        name = 'random_generated/training/training' + str(i) + '.xls'
        write_doc(name)

    for i in range(0, 8):
        name = 'random_generated/verification/verification_good' + str(i) + '.xls'
        write_doc(name)

    for i in range(0, 8):
        name = 'random_generated/verification/verification_bad_colswap' + str(i) + '.xls'
        write_doc(name, random_swap=True)
