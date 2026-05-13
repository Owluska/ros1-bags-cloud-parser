

def events_parser(msg, row, **kwargs):
    if msg.code_num in [10400, 10401, 10402] and int(msg.add_info.split('|')[5]) == 1:
        row['code_num'] = msg.code_num
        row['add_info'] = msg.add_info
        row['event_stamp'] = msg.header.stamp.to_sec()
        return row
    return None


def state_parser(msg, row, **kwargs):
    row['state_stamp'] = msg.header.stamp.to_sec()
    row['state_x'] = msg.position.x
    row['state_y'] = msg.position.y
    row['state_speed'] = msg.speed
    row['state_gear'] = msg.direction
    return row


topics = {
    '/GS/event':
        {'parser': events_parser, 'type': 'main'},
    '/SC/state':
        {'parser': state_parser, 'type': 'aux'}
}

columns = [
    'code_num',
    'add_info',
    'event_stamp',
    'state_stamp',
    'state_x',
    'state_y',
    'state_speed',
    'state_gear'
]