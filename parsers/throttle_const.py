
def state_parser(msg, row, **kwargs):
    row['wheel_angle'] = msg.wheel_angle
    row['ego_speed'] = msg.speed
    row['ego_x'] = msg.position.x
    row['ego_y'] = msg.position.y
    row['ego_gear'] = msg.direction
    row['ego_status'] = msg.status
    return row


def iplace_state_parser(msg, row, **kwargs):
    row['pitch'] = msg.pitch
    return row


def pedals_parser(msg, row, **kwargs):
    min_duration = kwargs.get('min_duration', 20.0)
    min_speed = kwargs.get('speed_thresh', 0.5)
    throttle_delta_thresh = kwargs.get('throttle_delta_thresh', 1.0)
    min_throttle = kwargs.get('min_throttle', 1.0)
    wheel_angle_thresh = kwargs.get('wheel_angle_thresh', None)

    throttle = msg.throttle
    row['throttle'] = throttle

    # Additional internal fields. They do not have to be saved to CSV
    # unless you add them to columns.
    if 'throttle_ref' not in row:
        row['throttle_ref'] = None

    if 'duration' not in row:
        row['duration'] = None

    # Required state from /SC/state should already exist.
    state_is_available = (
        row.get('ego_speed') is not None and
        row.get('ego_status') is not None and
        row.get('ego_gear') is not None
    )

    if not state_is_available:
        row['t0'] = None
        row['throttle_ref'] = None
        row['duration'] = None
        return None

    valid_motion = (
        row['ego_status'] == 1 and
        row['ego_gear'] != 0 and
        row['ego_speed'] >= min_speed
    )

    if wheel_angle_thresh is not None:
        valid_motion = valid_motion and abs(row['wheel_angle']) <= wheel_angle_thresh

    valid_throttle = throttle >= min_throttle

    if not valid_motion or not valid_throttle:
        row['t0'] = None
        row['throttle_ref'] = None
        row['duration'] = None
        return None

    # Start a new candidate segment.
    if row['t0'] is None or row['throttle_ref'] is None:
        row['t0'] = row['time']
        row['throttle_ref'] = throttle
        row['duration'] = 0.0
        return None

    # Check constancy relative to the segment start,
    # not only relative to the previous throttle message.
    if abs(throttle - row['throttle_ref']) > throttle_delta_thresh:
        row['t0'] = row['time']
        row['throttle_ref'] = throttle
        row['duration'] = 0.0
        return None

    duration = row['time'] - row['t0']
    row['duration'] = duration

    if duration < min_duration:
        return None

    return row

topics = {
    '/SC/state':
        {'parser': state_parser, 'type': 'aux'},
    '/iplace/state':
        {'parser': iplace_state_parser, 'type': 'aux'},
    '/FB/pedals_gear':
        {'parser': pedals_parser, 'type': 'main'},
}

columns = [
    'ego_speed',
    'ego_x',
    'ego_y',
    'ego_gear',
    'ego_status',
    'wheel_angle',
    't0',
    'duration',
    'throttle',
    'throttle_ref',
    'pitch',
]

kwargs = {
    'speed_thresh': 0.5,
    'min_duration': 20.0,
    'throttle_delta_thresh': 1.0,
    'min_throttle': 1.0,

    # Optional. Use this if you want mostly straight movement.
    # 'wheel_angle_thresh': 0.05,
}


