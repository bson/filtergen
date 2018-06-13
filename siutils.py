SUFFIXES=["M", "k", "", "m", "u", "n", "p"]

# Reduce number n to a given number of significant digits m and return as string
def nsigdig(n, m):
    s = "%s" % n
    if len(s) > m:
        s = s[0:m]
    # drop any trailing period
    if s[-1] == '.':
        return s[0:-1]
    return s

# Give a number an SI suffix and return as string
def sisuffix(n):
    # We bias a bit in favor of unsuffixed
    if n >= 0.3 and n <= 1300.0:
        return nsigdig(n, 4)

    wt = 1e6  # Weight of first suffix (M)
    for suffix in SUFFIXES:
        if n >= wt/10:
            return nsigdig(n/wt, 4) + suffix
        wt /= 1000

    # fall back on pico for truly tiny values
    return "%sp" % round(n * 1e12, 3)

# Parse an SI string with potential suffix
def si_val(s):
    if len(s) < 2:
        return float(s)
    suffix = s[-1]
    if not suffix in SUFFIXES: return float(s)
    pos   = 2 - SUFFIXES.index(suffix)
    return float(s[0:-1]) * (1e3 ** pos)

# Parse an SI string or percentage of A
def si_val_or_pct(s, a):
    if s[-1] == "%":
        return si_val(s[0:-1])/100.0 * a
    return si_val(s)
