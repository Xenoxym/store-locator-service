from datetime import datetime


DAY_TO_FIELD = {
    0: "hours_mon",
    1: "hours_tue",
    2: "hours_wed",
    3: "hours_thu",
    4: "hours_fri",
    5: "hours_sat",
    6: "hours_sun",
}


def is_store_open_now(store) -> bool:
    """
    Check whether a store is currently open based on today's hours.

    Hours format:
    - "08:00-22:00"
    - "closed"
    """
    now = datetime.now()
    day_field = DAY_TO_FIELD[now.weekday()]

    hours_value = getattr(store, day_field)

    if not hours_value or hours_value == "closed":
        return False

    try:
        open_time_str, close_time_str = hours_value.split("-")

        open_time = datetime.strptime(open_time_str, "%H:%M").time()
        close_time = datetime.strptime(close_time_str, "%H:%M").time()

        current_time = now.time()

        return open_time <= current_time <= close_time

    except ValueError:
        return False