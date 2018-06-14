import mpmath as mp

def butterworth(n):
    '''Returns a list of Q values for a cascade of length N.'''

    step = mp.pi/(2.0*n)
    start = step/2.0

    q = []
    value = start
    while value < mp.pi/2:
        q.append(1./(2.0*mp.cos(value)))
        value += step

    return q
