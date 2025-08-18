def find_first_negative(data_list):
    for idx, item in enumerate(data_list[2:], start=2):
        if item < 0:
            return item, idx
    return None, None
