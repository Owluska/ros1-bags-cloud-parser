def km_event_parser(msg, row, **kwargs):
    if msg.code_num == 10297:
        return row
    return None