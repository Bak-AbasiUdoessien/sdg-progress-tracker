"""
trend.py  -  The maths behind "is this country on track for 2030?"
Written by hand (no numpy) so you can see and explain every step in an interview.
"""


def linear_fit(years, values):
    """
    Fit a straight line  value = slope * year + intercept  using least squares.
    Returns (slope, intercept). slope = average change per year.
    """
    n = len(years)                                    # number of data points
    if n < 2:                                         # a line needs at least two points
        raise ValueError("need at least 2 data points to fit a trend")
    mean_x = sum(years) / n                           # average year
    mean_y = sum(values) / n                          # average value
    # Covariance-style numerator: how x and y move together around their averages.
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(years, values))
    # Variance of x: how spread out the years are.
    den = sum((x - mean_x) ** 2 for x in years)
    if den == 0:                                      # every year identical -> slope undefined
        raise ValueError("years must not all be the same")
    slope = num / den                                 # least-squares slope formula
    intercept = mean_y - slope * mean_x               # the line always passes through (mean_x, mean_y)
    return slope, intercept


def project(slope, intercept, year):
    """Value the trend line predicts for a given year."""
    return slope * year + intercept                   # plug the year into y = m*x + c


def clamp(value, low=0.0, high=100.0):
    """Keep percentages inside a sensible range (a trend can't go above 100% or below 0%)."""
    return max(low, min(high, value))                 # min() caps the top, max() caps the bottom


def assess(years, values, target, higher_is_better, target_year=2030, is_percent=True):
    """
    Decide whether the indicator will hit its target by target_year.
    Returns a dict with the numbers a report needs.
    """
    slope, intercept = linear_fit(years, values)              # fit the trend line
    projected = project(slope, intercept, target_year)        # where the line lands in 2030
    if is_percent:                                            # percentages are bounded 0-100
        projected = clamp(projected)
    else:                                                     # rates (e.g. deaths per 1,000) can't go negative
        projected = max(0.0, projected)

    if higher_is_better:                                      # e.g. % with electricity: want it to go UP
        on_track = projected >= target
        moving_right_way = slope > 0
    else:                                                     # e.g. % in poverty: want it to go DOWN
        on_track = projected <= target
        moving_right_way = slope < 0

    latest_year, latest_value = years[-1], values[-1]         # last item in each list = most recent
    years_needed = None                                       # stays None if the target is never reached
    if slope != 0 and moving_right_way:                       # only meaningful if we're heading toward the target
        # Solve target = slope * year + intercept for year.
        years_needed = (target - intercept) / slope - latest_year
        years_needed = max(0.0, years_needed)                 # already past the target -> 0 years

    return {
        "latest_year": latest_year,
        "latest_value": round(latest_value, 2),
        "change_per_year": round(slope, 3),
        "projected_2030": round(projected, 2),
        "target": target,
        "on_track": on_track,
        "years_to_target": None if years_needed is None else round(years_needed, 1),
    }
