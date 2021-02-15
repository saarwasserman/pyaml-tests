

def random_params(spec):
    params = spec['params']
    assert params['a'] + params['b'] < params['res']
