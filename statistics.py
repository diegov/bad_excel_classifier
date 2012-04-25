from collections import defaultdict
import math

def adjust_for_moderation(value, moderation):
    """moderation must be a positive exponent, values > 1 
    moderate the value, values between 0 and 1 make it more 
    radical
    >>> adjust_for_moderation(1, 2)
    1.0
    >>> adjust_for_moderation(0, 0.5)
    0.0
    >>> str(round(adjust_for_moderation(0.9, 0.5), 2))[:5]
    '0.95'
    >>> str(round(adjust_for_moderation(0.9, 20), 3))[:6]
    '0.506'
    >>> str(round(adjust_for_moderation(0.999, 20), 3))[:5]
    '0.98'
    >>> str(round(adjust_for_moderation(0.2, 20), 3))[:5]
    '0.478'
    >>> str(round(adjust_for_moderation(0.2, 10), 3))[:5]
    '0.456'
    >>> str(round(adjust_for_moderation(0.2, 3), 3))[:5]
    '0.365'
    """

    if value >= 0.5:
        expanded = (value - 0.5) * 2
        to_the_power = math.pow(expanded, moderation)
        res = to_the_power / 2.0 + 0.5
    else:
        expanded = value * 2
        to_the_power = math.pow(expanded, 1.0 / moderation)
        res = to_the_power / 2.0 

    return res

def calculate_stdev(values):
    mean = 0.0

    count = len(values)

    total = sum(values) * 1.0
    mean = total / count

    sum_of_squares = 0.0
    for val in values:
        squared_diff = math.pow(val - mean, 2)
        sum_of_squares += squared_diff

    stdev = math.sqrt(sum_of_squares / (count - 1))

    return (mean, stdev)

def bayes_combine(prob_series):
    """Calculates the bayesian combined probability based on the 
    series of probabilities

    >>> bayes_combine([0.5, 0.5])
    0.5
    >>> bayes_combine([1, 1, 1, 1])
    1.0
    >>> bayes_combine([1, 0.01, 0.02, 0.01])
    1.0
    >>> str(round(bayes_combine([0.8, 0.2, 0.5, 0.4]), 9))[:3]
    '0.4'
    >>> str(round(bayes_combine([0.8, 0.2, 0.5, 0.4, 0.5, 0.5, 0.5]), 9))[:3]
    '0.4'
    >>> str(round(bayes_combine([0.8, 0.2, 0.5, 0.4, 0.5, 0.5, 0.5, 0.5, 0.5]), 9))[:3]
    '0.4'
    """

    # To multiply biggest first
    prob_series = sorted(prob_series, reverse=True)

    numerator = reduce(lambda x, y: x * y, prob_series) * 1.0

    # Same here, trying to get biggest first when doing 1 - p
    prob_series.reverse()

    denominator = numerator + reduce(lambda x, y: x * y, [1 - p for p in prob_series])
    
    return numerator / denominator

def adjust_for_bias(prob, exponent):
    """
    >>> adjust_for_bias(0.75, 5)
    12
    >>> adjust_for_bias(0.2, 5)
    12
    >>> adjust_for_bias(0.1, 5)
    12
    >>> adjust_for_bias(0.9, 5)
    12
    >>> adjust_for_bias(0.999999, 5)
    12
    """

    if prob >= 0.5:
        operand = (prob - 0.5) * 2
        to_the_power = math.pow(operand, exponent)
        return to_the_power / 2 + 0.5
    else:
        operand = prob * 2
        return (math.pow(operand, exponent) / 2)

def adjust_for_confidence(prob, confidence):
    """A confidence of 1 will return prob unmodified. 
    The result will approach 0.5 as confidence gets closer to 0.
    A confidence of 0 will always return a probability of 0.5, 
    regardless of prob.

    >>> adjust_for_confidence(1, 1)
    1.0
    >>> adjust_for_confidence(0.25, 1)
    0.25
    >>> adjust_for_confidence(0.25, 0)
    0.5
    >>> adjust_for_confidence(0, 0)
    0.5
    >>> adjust_for_confidence(0, 0.5)
    0.25
    >>> adjust_for_confidence(0.25, 0.5)
    0.375
    >>> str(adjust_for_confidence(0.9, 0.1))[:4]
    '0.54'
    >>> str(adjust_for_confidence(0.1, 0.1))[:4]
    '0.46'
    >>> adjust_for_confidence(0.3, 0.01)
    0.498
    """
    
    return prob * confidence + (0.5 * (1 - confidence))

class Histogram(defaultdict):
    """Caching histogram

    >>> obj = Histogram({'test': 20, 'other': 20})
    >>> obj.value_total
    40
    >>> obj.value_total
    40
    >>> obj['test'] = 60
    >>> obj.value_total
    80
    >>> obj.value_total
    80
    >>> obj['test'] += 5
    >>> obj.value_total
    85
    >>> Histogram().value_total
    0
    """
    
    def __init__(self, default_type=int, *args, **kwargs):
        #Hack, pickle workaround
        if default_type != int:
            new_args = [default_type]
            new_args.extend(args)
            args = new_args
            default_type = int
            
        super(Histogram, self).__init__(default_type, *args, **kwargs)
        self._total = sum([self[k] for k in self])

    def __setitem__(self, key, value):
        # Careful, defaultdict calls __setitem__ when the key isn't found, 
        # causing a stack overflow here if we don't check
        prev = super(Histogram, self).__getitem__(key) if key in self else 0
        super(Histogram, self).__setitem__(key, value)
        self._total += (value - prev)

    @property
    def value_total(self):
        return self._total
        
def calculate_bayes_probability(value, good_values, bad_values, correct_for_confidence=False,
                        estimate_missing_probabilities=True):
    """
    >>> calculate_bayes_probability('hey', Histogram({'hey': 40, 'no': 20}), \
                           Histogram({'hey': 2, 'feck': 1}))
    0.5
    >>> res = calculate_bayes_probability('hey', Histogram({'hey': 40, 'no': 20}), \
                           Histogram({'hey': 2, 'feck': 1}), \
                           correct_for_confidence=True); str(round(res, 3))[:5]
    '0.564'
    >>> res = calculate_bayes_probability('hey', Histogram({'hey': 40, 'no': 20}), \
                           Histogram({'hey': 20, 'feck': 40}), \
                           correct_for_confidence=True); str(round(res, 3))[:5]
    '0.667'
    >>> res = calculate_bayes_probability('hey', Histogram({'hey': 40, 'no': 20}), \
                           Histogram({'hey': 20, 'feck': 40})); str(round(res, 3))[:5]
    '0.667'
    """
    def prob_and_total(value, data):
        count = data.get(value)
        total = data.value_total
        return (count, total)

    good_count, good_total = prob_and_total(value, good_values)
    bad_count, bad_total = prob_and_total(value, bad_values)

    all_total = good_total + bad_total

    simple_prob = False

    if (not good_count) and (not bad_count):
        if not estimate_missing_probabilities:
            simple_prob = True

    good_prob = good_count * 1.0 / good_total if good_count else 1.0 / (all_total * 2)
    bad_prob = bad_count * 1.0 / bad_total if bad_count else 1.0 / (all_total * 2)

    if correct_for_confidence:
        good_conf = min(1.0, good_total * 2.0 / all_total)
        bad_conf = min(1.0, bad_total * 2.0 / all_total)
        good_prob = adjust_for_confidence(good_prob, good_conf)
        bad_prob = adjust_for_confidence(bad_prob, bad_conf)

    if simple_prob:
        #TODO: Review this vs. the "/ all_total" calcs above
        #using the average probability per value here, it they're 
        #too scattered we don't want to punish the isolated 
        #value too much
        distinct_count = len(good_values.keys()) + len(bad_values.keys())
        avg_per_value = all_total * 1.0 / distinct_count
        return (good_prob + (0.5 / avg_per_value)) / 2

    return good_prob / (good_prob + bad_prob)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
