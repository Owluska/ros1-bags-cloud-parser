from shapely.geometry import Polygon, Point
import json
import re
import numpy as np
from scipy.spatial.transform import Rotation
import math


def state_parser(msg, row, **kwargs):
    if msg.status != 1 or msg.direction == 0 or msg.speed > 2:
        row['t0'] = None
        return None
    if msg.speed <= 2:
        if row['t0'] is None:
            row['t0'] = row['time']
            return None
        if row['time'] - row['t0'] < 20:
            return None
    row['ego_speed'] = msg.speed
    row['ego_x'] = msg.position.x
    row['ego_y'] = msg.position.y
    row['ego_gear'] = msg.direction
    row['ego_status'] = msg.status
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
    't0',
]



