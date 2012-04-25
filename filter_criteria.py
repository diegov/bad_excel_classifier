from statistics import *

class NumericRangeBase(object):
    def __add__(self, other):
        new_nums = []
        new_nums.extend(self.numbers)
        new_nums.extend(other.numbers)
        return NumericRangeCollection(new_nums)

    def _calculate(self):
        if self.count < 2:
            return (None, 0)
    
        return calculate_stdev(self.numbers)
            
    def score(self, value, unknown_samples_count=0):
        if not hasattr(self, '_result'):
            self._result = self._calculate()
            
        mean, stdev = self._result

        #with rate_divisor = 50:
        #confidence: f(self.count): f(0)=0, f(25)=0.2, f(50)=0.5 and f(100)=0.8, f(500)=0.990
        rate_divisor = 20
        confidence = 1 - (1.0 / (math.pow(self.count * 1.0 / rate_divisor, 2) + 1))

        if stdev == 0:
            if value == mean: 
                return (adjust_for_confidence(1, confidence), 1)
            else:
                return (adjust_for_confidence(0, confidence), 1)
            
        diff = abs(value - mean)

        probability = 1.0 / (math.pow(diff / stdev, 2) + 1)

        #We don't want to to be overly confident, adjust for the number of samples 
        #that we couldn't take into account because they weren't numbers
        if unknown_samples_count > 0:
            confidence *= self.count * 1.0 / (self.count + unknown_samples_count)

        return (probability, confidence)

class NumericRangeCollection(NumericRangeBase):
    def __init__(self, numbers):
        self.numbers = numbers
        self.count = len(self.numbers)

    def __add__(self, other):
        new_nums = []
        new_nums.extend(self.numbers)
        new_nums.extend(other.numbers)
        return NumericRangeCollection(new_nums)

class NumericRangeHolder(NumericRangeBase):
    def __init__(self, number):
        self.number = number
        self.count = 1 if self.number else 0

    @property
    def numbers(self):
        return [self.number] if self.number else []

class NumericSeries(object):
    """
    >>> n = NumericSeries()
    >>> n.good(0.2, 20)
    >>> n.good(0.3)
    >>> n.good(0.4, 10)
    >>> n.good(0.5, 200)
    >>> n.good(0.51, 2)
    >>> n.good(0.33, 400)
    >>> n.bad(2.33, 4)
    >>> n.bad(3.33, 34)
    >>> n.bad(0.303, 2)
    >>> n.score(0.35) > 0.8
    True
    """
    def __init__(self):
        self.good_data = NumericRangeHolder(None)
        self.bad_data = NumericRangeHolder(None)
        self.good_unknown_samples_count = 0
        self.bad_unknown_samples_count = 0

    def _as_number(self, value):
        typ = type(value)
        if typ == float or typ == int:
            return value
        else:
            try:
                return float(str(value))
            except ValueError:
                return None
        
    def good(self, value, how_much=1):
        value = self._as_number(value)
        if value == None: 
            self.good_unknown_samples_count += 1
            return

        for i in range(0, how_much):
            self.good_data += NumericRangeHolder(value)

    def bad(self, value, how_much=1):
        value = self._as_number(value)
        if value == None: 
            self.bad_unknown_samples_count += 1
            return

        for i in range(0, how_much):
            self.bad_data += NumericRangeHolder(value)

    def score(self, value):
        value = self._as_number(value)
        # We know nothing about non-numeric values...
        if value == None: return 0.5

        good_prob, good_confidence = self.good_data.score(value, unknown_samples_count=self.good_unknown_samples_count)
        bad_prob, bad_confidence = self.bad_data.score(value, unknown_samples_count=self.bad_unknown_samples_count)

        good_prob = adjust_for_confidence(good_prob, good_confidence)
        bad_prob = adjust_for_confidence(bad_prob, bad_confidence)

        return good_prob / (good_prob + bad_prob)

class BiasedSeries(object):
    """
    Exponents > 1 cause negative bias, exponents between 0 and 1
    cause positive bias
    The bias makes the prob raise slowly right above 0 and 0.5, 
    but f(0) = 0, f(0.5) = 0.5 and f(1) = 1, no matter what"""

    def __init__(self, inner_series, exponent):
        self.inner_series = inner_series
        self.exponent = exponent

    def score(self, value):
        initial = self.inner_series.score(value)
        return adjust_for_bias(initial, self.exponent)

    def good(self, value):
        self.inner_series.good(value)

    def bad(self, value):
        self.inner_series.bad(value)

class LowConfidenceSeries(object):
    def __init__(self, inner_series, confidence):
        self.inner_series = inner_series
        self.confidence = confidence

    def score(self, value):
        initial = self.inner_series.score(value)
        return adjust_for_confidence(initial, self.confidence)

    #Pickle doesn't like getattr tricks so we do this instead
    def good(self, value):
        self.inner_series.good(value)

    def bad(self, value):
        self.inner_series.bad(value)

class ModerationSeries(object):
    """Exponents > 1 result in a radical bias, exponents between 0-1 
    produce a moderation bias.
    A moderation bias results is an s-curve with a plateau around 
    the 0.5 value.
    """
    def __init__(self, inner_series, exponent):
        self.inner_series = inner_series
        self.exponent = exponent

    def score(self, value):
        initial = self.inner_series.score(value)
        return adjust_for_moderation(initial, self.exponent)

    #Pickle doesn't like getattr tricks so we do this instead
    def good(self, value):
        self.inner_series.good(value)

    def bad(self, value):
        self.inner_series.bad(value)


class NominalSeries(object):
    """
    >>> n = NominalSeries()
    >>> n.good('test')
    >>> n.bad('gold', 20)
    >>> n.good('diego', 300)
    >>> n.bad('patata', 500)
    >>> n.score('test') > 0.4
    True
    >>> n.score('diego') > 0.5
    True
    >>> n.score('patata') < 0.5
    True
    >>> bayes_combine([n.score('test'), n.score('diego'), n.score('patata')]) > 0.5
    True
    """
    def __init__(self, ignore_blanks=False, ignored_values=[], correct_for_confidence=True,
                 estimate_missing_probabilities=True):
        self.good_data = Histogram()
        self.bad_data = Histogram()

        self.good_unknown_samples_count = 0
        self.bad_unknown_samples_count = 0

        self.ignore_blanks = ignore_blanks
        self.ignored_values = ignored_values

        self.correct_for_confidence = correct_for_confidence

        self.estimate_missing_probabilities=estimate_missing_probabilities

    def _has_value(self, value):
        if value:
            if value == '' or repr(value).strip() == '':
                return False
            else: 
                return True
        else: 
            return False

    def _should_ignore(self, value):
        if value in self.ignored_values:
            return True
        if self.ignore_blanks:
            if not self._has_value(value):
                return True
        return False

    def good(self, value, how_much=1):
        if self._should_ignore(value):
            self.good_unknown_samples_count += how_much
            return
            
        self.good_data[value] += how_much

    def bad(self, value, how_much=1):
        if self._should_ignore(value):
            self.bad_unknown_samples_count += how_much
            return

        self.bad_data[value] += how_much

    def score(self, value):
        if len(self.good_data) == 0:
            return 0.5
        if self._should_ignore(value):
            return 0.5

        res = calculate_bayes_probability(value, self.good_data, self.bad_data, correct_for_confidence=self.correct_for_confidence,
                                  estimate_missing_probabilities=self.estimate_missing_probabilities)
        #print '   Nominal series score for \'%s\': %f' % (str(value), res)
        return res

class HasValueSeries(NominalSeries):
    """
    >>> n = HasValueSeries()
    >>> n.good('', 100)
    >>> n.good(None, 50)
    >>> n.bad('patata', 500)
    >>> n.bad(1.2, 5)
    >>> n.bad('', 1)
    >>> n.score('test') < 0.4
    True
    >>> n.score('') > 0.8
    True
    """
    def __init__(self, *args, **kwargs):
        super(HasValueSeries, self).__init__(*args, **kwargs)

    def good(self, value, how_much=1):
        value = self._has_value(value)
        super(HasValueSeries, self).good(value, how_much)

    def bad(self, value, how_much=1):
        value = self._has_value(value)
        super(HasValueSeries, self).bad(value, how_much)

    def score(self, value):
        value = self._has_value(value)
        return super(HasValueSeries, self).score(value)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
