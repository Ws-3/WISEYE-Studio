"""Conservative mesh-component labels. Mixed material categories stay unknown."""
import re
import math


def validated_rules(data):
    rules=sorted(data['classes'],key=lambda rule:rule['id'])
    if [rule['id'] for rule in rules]!=list(range(1,7)):
        raise ValueError('Thermal background IDs must be exactly 1 through 6')
    for rule in rules:
        re.compile(rule['pattern'])
        for key in ('day_signal','night_signal'):
            value=rule[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1:
                raise ValueError('Thermal signals must be finite numbers within [0,1]')
    return rules


def label_name(path):
    name = str(path).rsplit('/', 1)[-1].split('.')[0]
    return re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower()


def classify(mesh, materials, rules):
    def matches(path):
        name = label_name(path)
        return {rule['id'] for rule in rules if re.search(rule['pattern'], name)}

    categories = [matches(path) for path in materials]
    found = set().union(*categories) if categories else set()
    if len(found) > 1:
        return 0, 'mixed_materials'
    if found:
        if any(len(category) != 1 for category in categories):
            return 0, 'partly_unknown_materials'
        return next(iter(found)), 'material_names'
    found = matches(mesh)
    return (next(iter(found)), 'mesh_name') if len(found) == 1 else (0, 'unknown_or_ambiguous')
