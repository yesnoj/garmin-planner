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
    if re.compile(r'^(\d+)\s*([hms])$').match(s):
        m = re.compile(r'^(\d+)\s*([hms])$').match(s)
        amount = int(m.group(1))
        unit = m.group(2)
        if unit == 'h':
            return 3600 * amount
        if unit == 'm':
            return 60 * amount
        if unit == 's':
            return amount
    else:    
        parts = s.split(":")
        if len(parts) == 2:
            try:
                return int(parts[0]) * 60 + int(parts[1])
            except ValueError:
                raise ValueError("Invalid duration provided, must use mm:ss format")
        elif len(parts) == 3:
            try:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                raise ValueError("Invalid duration provided, must use hh:mm:ss format")
        else:
            raise ValueError("Invalid duration provided, must use mm:ss or hh:mm:ss format")

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

    print("All tests passed!")
