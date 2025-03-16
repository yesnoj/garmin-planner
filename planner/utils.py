import re

def hhmmss_to_seconds(s):
    """Converts a time string in various formats to seconds.

    Supported formats:
    - hh:mm:ss (e.g., "1:00:00", "00:00:30")
    - mm:ss (e.g., "10:00", "01:30")
    - h (e.g., "1h")
    - m (e.g., "2m")
    - s (e.g., "30s")

    Args:
        s: The time string to convert.

    Returns:
        The equivalent time in seconds as an integer.

    Raises:
        ValueError: If the input string is not in a valid format.
    """
    if not isinstance(s, str):
        raise TypeError("Input must be a string.")
    s = s.strip()
    if re.compile(r'^(\d+)\s*([hms]?)$').match(s):
        m = re.compile(r'^(\d+)\s*([hms]?)$').match(s)
        amount = int(m.group(1))
        unit = m.group(2)
        if unit == 'h':
            return 3600 * amount
        if unit == 'm':
            return 60 * amount
        if unit == 's':
            return amount
        else:
            return amount
    elif re.compile(r'^(\d+)\s*min$').match(s):
        m = re.compile(r'^(\d+)\s*min$').match(s)
        return 60 * int(m.group(1))
    else:    
        parts = s.split(":")
        if len(parts) == 2:
            try:
                return int(parts[0]) * 60 + int(parts[1])
            except ValueError:
                raise ValueError("Invalid duration provided, must use mm:ss format: " + s)
        elif len(parts) == 3:
            try:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                raise ValueError("Invalid duration provided, must use hh:mm:ss format: " + s)
        else:
            raise ValueError("Invalid duration provided, must use mm:ss or hh:mm:ss format: " + s)

def seconds_to_mmss(seconds):
    """Converts a time in seconds to a string in mm:ss format.

    Args:
        seconds: The time in seconds (int or float).

    Returns:
        A string representing the time in mm:ss format (e.g., "10:00", "01:30").

    Raises:
        TypeError: If the input is not a number (int or float).
        ValueError: If the input is negative.
    """
    if not isinstance(seconds, (int, float)):
        raise TypeError("Input must be a number.")
    if seconds < 0:
        raise ValueError("Input must be non-negative.")

    mins = int(seconds / 60)
    seconds = int(seconds - mins * 60)
    return f"{mins:02}:{seconds:02}"

def pace_to_kmph(pace):
    """Converts a pace string in mm:ss format to kilometers per hour (km/h).

    Args:
        pace: The pace string in mm:ss format (e.g., "5:00", "6:30").

    Returns:
        The equivalent speed in kilometers per hour (float).

    Raises:
        ValueError: If the pace string is not in a valid format supported by hhmmss_to_seconds.
    """
    seconds = hhmmss_to_seconds(pace)
    km_h = 60 / (seconds / 60)
    return km_h

def pace_to_ms(pace):
    """Converts a pace string in mm:ss format to meters per second (m/s).

    Args:
        pace: The pace string in mm:ss format (e.g., "5:00", "6:30").

    Returns:
        The equivalent speed in meters per second (float).

    Raises:
        ValueError: If the pace string is not in a valid format supported by hhmmss_to_seconds.
    """
    return pace_to_kmph(pace) * (1000/3600)

def ms_to_pace(ms):
    """Converts a speed in meters per second (m/s) to a pace string in mm:ss per km.

    Args:
        ms: The speed in meters per second (float).

    Returns:
        A pace string in mm:ss format (e.g., "5:00", "4:30").

    Raises:
        TypeError: If the input is not a number (int or float).
        ValueError: If the input is zero or negative.
    """
    if not isinstance(ms, (int, float)):
        raise TypeError("Input must be a number.")
    if ms <= 0:
        raise ValueError("Input must be a positive number.")
    
    seconds_per_km = round(1000 / ms)
    return seconds_to_mmss(seconds_per_km)


def dist_to_m(dist_str):
    """Converts a distance string in various formats to meters.

    Supported formats:
    - <number>km (e.g., "10km", "2.5km")
    - <number>m (e.g., "100m", "5000m")

    Args:
        dist_str: The distance string to convert.

    Returns:
        The equivalent distance in meters as an integer.

    Raises:
        TypeError: If the input is not a string.
        ValueError: If the input string is not in a valid format.
    """
    if not isinstance(dist_str, str):
        raise TypeError("Input must be a string.")
    dist_str = dist_str.strip()

    m = re.compile(r'^(\d+(?:\.\d+)?)(km|m)$').match(dist_str)
    if not m:
        raise ValueError(
            "Invalid distance provided, must use <number>km or <number>m format"
        )

    value = float(m.group(1))
    unit = m.group(2)

    if unit == 'km':
        return int(value * 1000)
    elif unit == 'm':
        return int(value)
    else:
        raise ValueError(f'unit "{unit}" not managed')


def dist_time_to_ms(dist_time):
    """Extracts the target time from a distance and time specification string.
    This function seems unused, in the provided code. I'll keep it
    for reference but I will not write tests for it.

    Args:
      dist_time: The distance and time specification, in the format "<distance> in <time>" (e.g., "3000m in 13:48")

    Returns:
      None
    """
    m = re.compile('^(.+) in (.+)$').match(dist_time)
    if m:
        ms_time = pace_to_ms(m.group(2).strip())
        m_distance = dist_to_m(m.group(1).strip())
        km_distance = m_distance / 1000
        target_pace = ms_time * km_distance
        return target_pace
    else:
        raise ValueError("Input must be in the format <distance> in <time>.")

def normalize_pace(orig_pace):
    '''
    Normalizes a pace string to the format mm:ss or hh:mm:ss with zero-padding.

    This function takes a pace string and ensures it is in a consistent format
    of mm:ss or hh:mm:ss, adding leading zeros where necessary. It also validates
    that the minutes and seconds components are below 60.

    Args:
        orig_pace: The pace string to normalize (e.g., "4:40", "04:4", "12:4:4").

    Returns:
        The normalized pace string in mm:ss or hh:mm:ss format (e.g., "04:40", "04:04", "12:04:04").

    Raises:
        ValueError: If the input string is not in a valid pace format or if minutes/seconds are >= 60.
    '''
    m = re.compile(r'^\d{1,2}:\d{1,2}:?\d{0,2}$')
    if m.match(orig_pace):
        parts = [int(part) for part in orig_pace.split(":")]
        # minutes and seconds must be belows 60
        if parts[len(parts)-1] >= 60 or parts[len(parts)-2] >= 60:
            raise ValueError('Invalid pace format: ' + orig_pace)

        # Add zero padding
        padded = [str(part).zfill(2) for part in parts]
        return ":".join(padded)
    else:
        raise ValueError('Invalid pace format: ' + orig_pace)

def get_pace_range(orig_pace, margins):
    """Calculates a pace range based on an original pace and optional margins.

    This function can handle single paces (e.g., "04:40") or pace ranges (e.g., "04:40-04:00").
    If a single pace is provided and margins are given, it calculates a range by adding/subtracting
    the margin values. If a pace range is provided, it returns the range as is.

    Args:
        orig_pace: The original pace or pace range string (e.g., "04:40", "04:40-04:00").
        margins: A dictionary containing 'faster' and 'slower' margin values in mm:ss format (e.g., {'faster': '0:03', 'slower': '0:03'}).
                 If None, no margins are applied.

    Returns:
        A tuple containing the slow and fast pace limits in seconds (slow_pace_s, fast_pace_s).

    Raises:
        ValueError: If the input pace string is not in a valid format.
    """
    # Handle case where pace provided has already been converted to tuple
    if isinstance(orig_pace, tuple):
        if isinstance (orig_pace[0], str) and (orig_pace[1], str):
            return orig_pace
        else:
            raise ValueError('Invalid pace format: ' + str(orig_pace))

    m = re.compile(r'^(\d{1,2}:\d{1,2})(?:-(\d{1,2}:\d{1,2}))?').match(orig_pace)
    if not m:
        raise ValueError('Invalid pace format: ' + orig_pace)
    
    # If only one pace was provided (e.g. 04:40)
    if not m.group(2):
        orig_pace_s = hhmmss_to_seconds(orig_pace)
        # If we have margins to add/substract
        if margins:
            fast_margin_s = hhmmss_to_seconds(margins.get('faster', '0'))
            slow_margin_s = hhmmss_to_seconds(margins.get('slower', '0'))
            fast_pace = seconds_to_mmss(orig_pace_s - fast_margin_s)
            slow_pace = seconds_to_mmss(orig_pace_s + slow_margin_s)
            return (slow_pace, fast_pace)
        # Single pace and no margins. We return the original pace for both limits.
        else:
            return (orig_pace_s, orig_pace_s)
    # If we were provided both paces, no additional margins are needed.
    else:
        pace_1 = m.group(1)
        pace_2 = m.group(2)
        return (pace_1, pace_2)

# --- Main block for testing ---
if __name__ == "__main__":
    print("Testing hhmmss_to_seconds...")
    assert hhmmss_to_seconds("10:00") == 600
    assert hhmmss_to_seconds("01:30") == 90
    assert hhmmss_to_seconds("1:00:00") == 3600
    assert hhmmss_to_seconds("00:00:30") == 30
    assert hhmmss_to_seconds("1h") == 3600
    assert hhmmss_to_seconds("2m") == 120
    assert hhmmss_to_seconds("30s") == 30
    assert hhmmss_to_seconds("30") == 30
    try:
        hhmmss_to_seconds("invalid")
        assert False
    except ValueError:
        assert True

    print("Testing seconds_to_mmss...")
    assert seconds_to_mmss(600) == "10:00"
    assert seconds_to_mmss(90) == "01:30"
    assert seconds_to_mmss(3600) == "60:00"
    assert seconds_to_mmss(30) == "00:30"

    print("Testing pace_to_kmph...")
    assert pace_to_kmph("5:00") == 12.0
    assert pace_to_kmph("6:00") == 10.0
    assert pace_to_kmph("3:00") == 20.0

    print("Testing pace_to_ms...")
    assert pace_to_ms("5:00") == 12.0 * (1000/3600)
    assert pace_to_ms("6:00") == 10.0 * (1000/3600)
    assert pace_to_ms("3:00") == 20.0 * (1000/3600)

    print("Testing dist_to_m...")
    assert dist_to_m("10km") == 10000
    assert dist_to_m("2.5km") == 2500
    assert dist_to_m("100m") == 100
    assert dist_to_m("5000m") == 5000
    assert dist_to_m(" 10km ") == 10000
    assert dist_to_m(" 2.5km") == 2500
    assert dist_to_m("100m ") == 100
    assert dist_to_m(" 5000m ") == 5000
    assert dist_to_m("1km") == 1000
    assert dist_to_m("1.5m") == 1

    try:
        dist_to_m("invalid")
        assert False
    except ValueError:
        assert True
    
    try:
        dist_to_m("10l")
        assert False
    except ValueError:
        assert True
    try:
        dist_to_m(10)
        assert False
    except TypeError:
        assert True

    print("Testing dist_time_to_ms...")
    assert dist_time_to_ms("3000m in 13:48") == pace_to_ms("13:48")*3
    assert dist_time_to_ms("100m in 00:30") == pace_to_ms("00:30")*0.1
    assert dist_time_to_ms("3km in 10:00") == pace_to_ms("10:00")*3
    assert dist_time_to_ms("1km in 04:30") == pace_to_ms("04:30")

    try:
        dist_time_to_ms("invalid")
        assert False
    except ValueError:
        assert True
    try:
        dist_time_to_ms(10)
        assert False
    except TypeError:
        assert True

    print("Testing time/distance to pace.")
    assert ms_to_pace(dist_time_to_ms("10000m in 40:00")) == '04:00'
    assert ms_to_pace(dist_time_to_ms("42.2km in 03:00:00")) == '04:16'

    print("Testing normalize_pace...")
    assert normalize_pace('04:40') == '04:40'
    assert normalize_pace('4:40') == '04:40'
    assert normalize_pace('04:4') == '04:04'
    assert normalize_pace('4:4') == '04:04'
    assert normalize_pace('12:4:4') == '12:04:04'
    assert normalize_pace('2:4:4') == '02:04:04'

    print("Testing get_pace_range...")
    assert get_pace_range('04:40', None) == (280, 280)
    assert get_pace_range('04:40', {'faster': '0:10', 'slower': '0:10'}) == (290, 270)
    assert get_pace_range('04:40-04:20', None) == (280, 260)

    print("All tests passed!")
