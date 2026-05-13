from shapely.geometry import Polygon, Point
import numpy as np
from scipy.spatial.transform import Rotation


def state_parser(msg, row, **kwargs):
    speed_thresh = kwargs.get('speed_thresh', 2.0)
    wheel_angle_thresh = kwargs.get('wheel_angle_thresh', 0.05)
    min_duration = kwargs.get('min_duration', 30.0)

    if 'straight_segment_saved' not in row:
        row['straight_segment_saved'] = False

    is_valid_straight_motion = (
        msg.status == 1 and
        msg.direction != 0 and
        msg.speed > speed_thresh and
        abs(msg.wheel_angle) <= wheel_angle_thresh
    )

    if not is_valid_straight_motion:
        row['t0'] = None
        row['straight_segment_saved'] = False
        return None

    if row['t0'] is None:
        row['t0'] = row['time']
        row['straight_segment_saved'] = False
        return None

    duration = row['time'] - row['t0']

    if duration < min_duration:
        return None

    if row['straight_segment_saved']:
        return None

    row['wheel_angle'] = msg.wheel_angle
    row['ego_speed'] = msg.speed
    row['ego_x'] = msg.position.x
    row['ego_y'] = msg.position.y
    row['ego_gear'] = msg.direction
    row['ego_status'] = msg.status
    row['duration'] = duration

    row['straight_segment_saved'] = True

    return row

topics = {
    '/SC/state':
        {'parser': state_parser, 'type': 'main'}
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
    'straight_segment_saved',
]



kwargs = {
    'speed_thresh': 2.0,
    'wheel_angle_thresh': 0.05,
    'min_duration': 30.0,
}

