import math
import xlrd
from itertools import izip
from collections import defaultdict
from spreadsheet import *
from statistics import *
from filter_criteria import *
import cPickle

def _open_training_set(set_name):
    with open(set_name, 'r') as f:
        return cPickle.load(f)

def _save_training_set(tset, set_name):
    with open(set_name, 'w') as f:
        cPickle.dump(tset, f, protocol=1)

def show_trainingset(*args, **kwargs):
    set_name = args[0]
    print 'Training set %s' % (set_name)
    print str(_open_training_set(set_name))
    return 0

def init_trainingset(*args, **kwargs):
    set_name = args[0]
    print 'Creating set %s' % (set_name)
    tset = TrainingSet(options.start_row, options.end_row, options.start_col, 
                       options.end_col, options.sheet)
    _save_training_set(tset, set_name)

    return 0

def train_trainingset(*args, **kwargs):
    set_name = args[0]
    files = args[1:]
    bad_set = kwargs['bad_set']
    tset = _open_training_set(set_name)
    for f in files:
        wb = xlrd.open_workbook(f)
        if bad_set:
            tset.bad(wb)
        else:
            tset.good(wb)

    _save_training_set(tset, set_name)
    return 0

def _format_cell(probs):
    from colorama import Fore, Back, Style
    total_prob = bayes_combine(probs)
    mean, stdev = calculate_stdev([x * 1.0 for x in probs])

    print_format = ''

    if total_prob < 0.3:
        print_format += Style.BRIGHT + Fore.RED
    elif total_prob > 0.7:
        print_format += Style.BRIGHT + Fore.GREEN
    else:
        print_format = Style.DIM
    
    msg = '|' + print_format + " %.02f, %.02f %s%s%s" % (round(total_prob, 2), round(stdev, 2),
                                                         Fore.RESET, Back.RESET, Style.RESET_ALL)

    return msg
    
def _show_grid(tset, cells):
    import colorama
    colorama.init()

    cols_per_row = 1 + tset.end_col - tset.start_col
    line = ''
    for ndx, cell in enumerate(cells):
        line += _format_cell(cell)
        if (ndx + 1) % cols_per_row == 0:
            print line + '|'
            line = ''

    if len(line) > 0:
        print line + '|'
        
def verify_file(*args, **kwargs):
    set_name = args[0]
    f = args[1]
    show_grid = kwargs['show_grid']
    print '\nVerifying file %s against set %s' % (f, set_name)
    
    tset = _open_training_set(set_name)
    wb = xlrd.open_workbook(f)

    prob, cells = tset.score(wb, include_cells=True)

    print '   There is a %f probability that %s is a good file\n' % (prob, f)

    if show_grid:
        _show_grid(tset, cells)

    print ''

    return 0

class TrainingCell(object):
    """Groups series for multiple criteria for a single cell"""

    def __init__(self):
        values_positive_bias = 0.835 #Good one
        #values_positive_bias = 0.35

        values_class = BiasedSeries(
            NominalSeries(ignore_blanks=True, correct_for_confidence=True, estimate_missing_probabilities=False), 
            values_positive_bias)

        #Make scores more radical
        #values_class = ModerationSeries(values_class, 0.3)

        number_range_class = ModerationSeries(NumericSeries(), 2.8)
        has_value_class = LowConfidenceSeries(BiasedSeries(HasValueSeries(correct_for_confidence=True), 1.08), 0.88)

        self.value_classes = [values_class, number_range_class, has_value_class]

        type_class = NominalSeries(ignored_values=[XlsType.xls_empty], correct_for_confidence=True, estimate_missing_probabilities=False)
        type_class = ModerationSeries(BiasedSeries(type_class, 1.9), 2)

        self.type_classes = [type_class]

    def good(self, cell_type, cell_value):
        for value_class in self.value_classes:
            value_class.good(cell_value)
        for type_class in self.type_classes:
            type_class.good(cell_type)

    def bad(self, cell_type, cell_value):
        for value_class in self.value_classes:
            value_class.bad(cell_value)
        for type_class in self.type_classes:
            type_class.bad(cell_type)

    def score(self, cell_type, cell_value):
        probs = []
        for value_class in self.value_classes:
            probs.append(value_class.score(cell_value))
        for type_class in self.type_classes:
            probs.append(type_class.score(cell_type))

        return probs

    def __repr__(self):
        return 'TCell'

class TrainingSet(object):
    def __init__(self, start_row, end_row, start_col, end_col, sheet):
        self.start_row = start_row
        self.end_row = end_row
        self.start_col = start_col
        self.end_col = end_col
        self.sheet = sheet
        size = (1 + self.end_row - self.start_row) * (1 + self.end_col - self.start_col)
        self.training_cells = [TrainingCell() for i in range(0, size)]
        
    def __repr__(self):
        return repr(self.__dict__)

    def good(self, xls_doc):
        action = lambda tcell, cell_type, cell_value: tcell.good(cell_type, cell_value)
        self._enumerate_against_training_cells(action, xls_doc)

    def bad(self, xls_doc):
        action = lambda tcell, cell_type, cell_value: tcell.bad(cell_type, cell_value)
        self._enumerate_against_training_cells(action, xls_doc)

    def score(self, xls_doc, include_cells=False):
        action = lambda tcell, cell_type, cell_value: tcell.score(cell_type, cell_value)
        probs = self._enumerate_against_training_cells(action, xls_doc, keep_result=True)

        flattened = reduce(lambda x, y: x + y, probs)
        if include_cells:
            return (bayes_combine(flattened), probs)
        else:
            return bayes_combine(flattened)

    def _enumerate_against_training_cells(self, action, xls_doc, keep_result=False):
        #TODO: by name or sheet
        all_results = None
        if keep_result:  
            all_results = []
        if type(self.sheet) == int:
            sheet = xls_doc.sheet_by_index(self.sheet)
        else:
            sheet = xls_doc.sheet_by_name(self.sheet)
        stream = self._stream_from_sheet(sheet)
        for tcell, (cell_type, cell_value) in zip(self.training_cells, stream):
            res = action(tcell, cell_type, cell_value)
            if keep_result:
                all_results.append(res)

        return all_results
            
    def _stream_from_sheet(self, sheet):
        return cell_stream_from_sheet(sheet, self.end_row, self.end_col, 
                                      start_col=self.start_col, start_row=self.start_row,
                                      row_values=lambda sheet, ndx: zip(sheet.row_types(ndx), sheet.row_values(ndx)),
                                      empty_value=(XlsType.xls_empty, None))

if __name__ == '__main__':

    from optparse import OptionParser, OptionGroup

    parser = OptionParser()

    parser.add_option('--init', dest='cmd', action='store_const', const=init_trainingset,
                          default=None, help='Initialises a training set')
    parser.add_option('--train', dest='cmd', action='store_const', const=train_trainingset,
                          default=None, help='Trains the training set with the files provided')
    parser.add_option('--verify', dest='cmd', action='store_const', const=verify_file,
                          default=None, help='Returns the probability that the file is good, within the specified training set')
    parser.add_option('--show', dest='cmd', action='store_const', const=show_trainingset,
                          default=None, help='Display information about the trainingset specified')

    init_opts = OptionGroup(parser, 'Init Options', 'Usage: compare.py --init [options] trainingset_name')

    init_opts.add_option('--sheet', '-s', action='store', dest='sheet', 
                         help='The sheet to process. This can be a name or an index, with base 0')

    init_opts.add_option('--row-start', '--rs', action='store', dest='start_row', 
                         help='First row to process, base 0')

    init_opts.add_option('--row-end', '--re', action='store', dest='end_row', 
                         help='Last row to process, base 0')

    init_opts.add_option('--column-start', '--cs', action='store', dest='start_col', 
                         help='First column to process, base 0')

    init_opts.add_option('--column-end', '--ce', action='store', dest='end_col', 
                         help='Last column to process, base 0')

    parser.add_option_group(init_opts)

    train_opts = OptionGroup(parser, 'Training Options', 'Usage: compare.py --train [options] trainingset_name files*')

    train_opts.add_option('--bad', dest='bad_set', action='store_const', const=True, 
                          default=False, help='Take the training files passed as part of the *bad* set\n' +
                          'By default the files passed are considered to be from the good set')
    
    parser.add_option_group(train_opts)

    verify_opts = OptionGroup(parser, 'Verification Options', 'Usage: compare.py --verify [options] trainingset_name file')
    verify_opts.add_option('--show-grid', dest='show_grid', action='store_const', const=True, 
                          default=False, help='Show the grid of probabilities per cell in addition to the overall probability.')

    parser.add_option_group(verify_opts)

    (options, args) = parser.parse_args()

    options.end_row = int(options.end_row) if options.end_row else 0
    options.end_col = int(options.end_col) if options.end_col else 0
    options.start_row = 0 if options.start_row == None else int(options.start_row)
    options.start_col = 0 if options.start_col == None else int(options.start_col)

    if options.sheet == None: options.sheet = 0
    elif options.sheet.isdigit(): options.sheet = int(options.sheet)

    if options.cmd != None:
        exit(options.cmd(*args, **options.__dict__))

    if len(args) > 0:
        if args[0] == 'test':
            import doctest
            doctest.testmod()
            exit(0)

    parser.print_help()
    exit(1)

