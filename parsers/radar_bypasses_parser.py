from shapely.geometry import Polygon, Point
import json
import re
import numpy as np
from scipy.spatial.transform import Rotation
import math


def state_parser(msg, row, **kwargs):
    if msg.direction == 0 or msg.status != 1:
        return None
    row['ego_speed'] = msg.speed
    row['ego_x'] = msg.position.x
    row['ego_y'] = msg.position.y
    row['ego_gear'] = msg.direction
    row['ego_status'] = msg.status
    return row

def close_objects_parser(msg, row, **kwargs):
    if row['has_left_umrr'] is None\
        or row['has_right_umrr'] is None \
        or row['has_front_umrr'] is None \
        or row['has_rear_umrr'] is None:
        # print(row)
        # has_left_umrr
        # has_rear_umrr
        # has_front_umrr
        # has_right_umrr

        return None
    if row['ego_x'] is None or row['ego_y'] is None:

        return None
    if not 'dist_thresh' in kwargs or not 'speed_thresh' in kwargs:
        return None
    
    if row['ego_gear'] == 0 or row['ego_status'] != 1:
        return None
    
    dist_thresh = kwargs['dist_thresh']
    speed_thresh = kwargs['speed_thresh']
    for state in msg.objects:
        dist = (
            (row['ego_x'] - state.position.x) ** 2 + 
                (row['ego_y'] - state.position.y) ** 2) ** 0.5
        if dist < dist_thresh and state.speed >= speed_thresh:
            row['object_id'] = state.info.vehid
            row['object_speed'] = state.speed
            row['object_x'] = state.position.x
            row['object_y'] = state.position.y
            return row
    
    return None

def umrr_parser(msg, row, **kwargs):
    # print(f'has_{msg.header.frame_id}')
    row[f'has_{msg.header.frame_id}'] = msg.header.frame_id
    return row

topics = {
    '/SC/close_objects':
        {'parser': close_objects_parser, 'type': 'main'},
    '/SC/state':
        {'parser': state_parser, 'type': 'aux'},
    '/left_umrr/radar_data':
        {'parser': umrr_parser, 'type': 'aux'},
    '/right_umrr/radar_data':
        {'parser': umrr_parser, 'type': 'aux'},
    '/rear_umrr/radar_data':
        {'parser': umrr_parser, 'type': 'aux'},
    '/front_umrr/radar_data':
        {'parser': umrr_parser, 'type': 'aux'}
}

columns = [
    'ego_speed',
    'ego_x',
    'ego_y',
    'ego_gear',
    'object_id',
    'object_speed',
    'object_x',
    'object_y',
    'has_left_umrr',
    'has_right_umrr',
    'has_front_umrr',
    'has_rear_umrr'
]



