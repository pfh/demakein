
import re

from . import grace

def term_specification(term):
    if '=' not in term: return term
    return term.split('=',1)[0]

def term_name(term):
    if '=' not in term: return term
    return term.split('=',1)[1]


def matches(expression, tags):
    tokens = list('[]-:/^')
    
    def parse2(expression):
        assert expression, 'unexpected end of expression'
        if expression[0] == '[':
           value, expression = parse(expression[1:])
           assert expression.startswith(']'), 'expected a closing ]'
           return value, expression[1:]
        
        i = 0
        while i < len(expression) and expression[i] not in '[]:/^':
            i += 1
        assert i > 0, 'unexpected '+expression[0]
        return expression[:i] == 'all' or expression[:i] in tags, expression[i:]
    
    def parse1(expression):
        assert expression, 'unexpected end of expression'
        if expression.startswith('-'):
            value, expression = parse2(expression[1:])
            return not value, expression
        else:
            value, expression = parse2(expression)
            return value, expression
    
    def parse(expression):
        value, expression = parse1(expression)
        while expression and expression[0] in ':/^':
            operator, expression = expression[0], expression[1:]
            value2, expression = parse1(expression)
            if operator == ':':
                value = value and value2
            elif operator == '/':
                value = value or value2
            else:
                value = (not value2 and value) or (not value and value2)
        return value, expression
    
    if expression == '':
        return False        
    try:
        value, expression = parse(expression)
        assert not expression, 'don\'t know what to do with: '+expression
    except AssertionError, e:
        raise grace.Error('Could not parse: '+expression+', '+e.args[0])
    return value


def select_and_sort(select_expression, sort_expression, items, get_tags=lambda item: item.get_tags()):
    """ Select items based on select_expression then sort by sort_expression. 
        If group=True, return a list of lists being the distinct groups created by the sort expression.
        Otherwise return a list.
    """
    items = [ item for item in items
              if matches(select_expression, get_tags(item)) ]

    if not sort_expression:
        parts = []
    else:
        parts = sort_expression.split(',')
    
    def key(item):
        tags = get_tags(item)
        return [ 0 if matches(part, tags) else 1
                 for part in parts ]

    items.sort(key=key)
    
    return items


def weight(expression, tags):
    parts = expression.split(',')
    total = 0.0
    for part in parts:
        weight = 1.0
        match = re.match('^{(.*)}(.*)$',part)
        if match:
            weight = float(match.group(1))
            part = match.group(2)
        if matches(part, tags):
            total += weight
    return total


class Matchable_set(set):
    def matches(self, expression):
        return matches(expression, self)



