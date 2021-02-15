
def add(spec):
    print(spec)
    assert spec['a'] + spec['b'] == spec['res']


def add_with_params(spec):
    params = spec['params']
    assert params['a'] + params['b'] == params['res']
