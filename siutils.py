SUFFIXES=["M", "k", "", "m", "u", "n", "p"]
SUFFIX_MAX = 1e6
SUFFIX_MIN = 1e-12
UNSUFFIXED = SUFFIXES.index("")

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
def sisuffix(n, ndig=4):
    # We bias a bit in favor of unsuffixed
    if n >= 0.3 and n <= 1300.0:
        return nsigdig(n, ndig)

    wt = SUFFIX_MAX  # Weight of first suffix (M)
    for suffix in SUFFIXES:
        if n >= wt/10:
            return nsigdig(n/wt, ndig) + suffix
        wt /= 1000

    # fall back on pico for truly tiny values
    return "%s%s" % (round(n / SUFFIX_MIN, ndig-1), SUFFIXES[:-1])

# Parse an SI string with potential suffix
def si_val(s):
    if len(s) < 2:
        return float(s)

    suffix = s[-1]
    if not suffix in SUFFIXES:
        return float(s)

    pos = UNSUFFIXED - SUFFIXES.index(suffix)
    return float(s[0:-1]) * (1e3 ** pos)

# Parse an SI string or percentage of A
def si_val_or_pct(s, a):
    if s[-1] == "%":
        return si_val(s[0:-1])/100.0 * a
    return si_val(s)
