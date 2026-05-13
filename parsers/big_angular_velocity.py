from shapely.geometry import Polygon, Point
import json
import re
import numpy as np
from scipy.spatial.transform import Rotation
import math


def state_parser(msg, row, **kwargs):
    row['ego_speed'] = msg.speed
    row['ego_x'] = msg.position.x
    row['ego_y'] = msg.position.y
    row['ego_gear'] = msg.direction
    row['ego_status'] = msg.status
    return row

def pure_state_parser(msg, row, **kwargs):
    if np.abs(msg.velocity.angular.x) > 0.1\
            and row['ego_gear'] != 0 and row['ego_status'] == 1:
        row['wx'] = msg.velocity.angular.x
        row['wy'] = msg.velocity.angular.y
        row['wz'] = msg.velocity.angular.z
        return row
    return None

topics = {
    '/SC/pure_state':
        {'parser': pure_state_parser, 'type': 'main'},
    '/SC/state':
        {'parser': state_parser, 'type': 'aux'}
}

columns = [
    'ego_speed',
    'ego_x',
    'ego_y',
    'ego_gear',
    'ego_status',
    'wx',
    'wy',
    'wz'
]



