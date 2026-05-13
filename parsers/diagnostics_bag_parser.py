from shapely.geometry import Polygon, Point
import json
import re
import numpy as np
from scipy.spatial.transform import Rotation
import math

def is_object_behind(vehicle_x, vehicle_y, yaw, obj_x, obj_y):
    """
    Determine if an object is behind a vehicle based on their positions and the vehicle's heading.
    
    Args:
        vehicle_x (float): Vehicle's x-coordinate
        vehicle_y (float): Vehicle's y-coordinate
        yaw (float): Vehicle's heading angle in radians (0 is east, pi/2 is north)
        obj_x (float): Object's x-coordinate
        obj_y (float): Object's y-coordinate
        
    Returns:
        bool: True if the object is behind the vehicle, False otherwise
    """
    # Calculate the vector from vehicle to object
    dx = obj_x - vehicle_x
    dy = obj_y - vehicle_y
    
    # Calculate the angle of this vector relative to the vehicle's heading
    angle_to_object = math.atan2(dy, dx)
    relative_angle = angle_to_object - yaw
    
    # Normalize the angle to be between -pi and pi
    relative_angle = (relative_angle + math.pi) % (2 * math.pi) - math.pi
    
    # Determine if the object is behind (angle is between 90 and 270 degrees from heading)
    return abs(relative_angle) > math.pi/2

def state_parser(msg, row, **kwargs):
    row['weight'] = msg.weight
    row['speed'] = msg.speed
    row['yaw'] = msg.yaw
    row['direction'] = msg.direction
    row['x'] = msg.position.x
    row['y'] = msg.position.y
    row['z'] = msg.position.z
    row['status'] = msg.status
    if row['areas'] is not None:
        covering = [a for a in row['areas'] if Point(msg.position.x, msg.position.y).covered_by(a)]
        row['at_play_field'] = len(covering)
    return row

def close_objects_parser(msg, row, **kwargs):
    ekg_id = [3007001, 3007002, 3016001]
    # ekg_id = [3007002]
    if row['x'] is None or row['y'] is None:
        return None
    row['object_in_fov'] = 0
    for state in msg.objects:
        dist = (
            (row['x'] - state.position.x) ** 2 + 
                (row['y'] - state.position.y) ** 2) ** 0.5
        if state.info.vehid in ekg_id:
            row['dist_to_ekg'] = dist
        is_behind = is_object_behind(row['x'], row['y'], row['yaw'], state.position.x, state.position.y)
        if dist < 50 and not is_behind:
            row['object_in_fov'] = 1
            # print(dist, state.info.vehid)
    
    return row

def planned_route_parser(msg, row, **kwargs):
    if len(msg.border.points):
        border_poly = Polygon([[p.x, p.y] for p in msg.border.points])
        if row['areas'] is None:
            row['areas'] = [border_poly]
        else:
            row['areas'].append(border_poly)
    if len(msg.points):
        row['regime'] = msg.points[0].regime
        row['object_type'] = set(
            [json.loads(r)['object_type'] for r in msg.regimes if json.loads(r)['name'] == row['regime']])

    return row



def rosout_parser(msg, row, **kwargs):
    if msg.name not in ['/PointCloudDiagnosticNode', '/DetectionAnalyzer']:
        # print(msg.name)
        return None
    if  msg.msg.find('Average metrics') != -1:
        target_strs = [s.split(':') for s in  msg.msg.split('\n')]
        cur_data = {k.replace(' ', '_') : v.replace(' ', '')  for k, v in target_strs if len(v.replace(' ', ''))}
        row.update(cur_data)
        # print(row)
        return row
    if msg.msg.find('cycle specific params') != -1:
        target_strs = msg.msg.split()[1]
        keys = [
            'csp_total',
            'csp_close',
            'csp_front',
            'csp_left',
            'csp_right',
            'cycle_number'
        ]
        numbers = re.findall(r'\d+', msg.msg)  # Finds sequences of digits
        # print(numbers)  # Output: ['3', '15', '0']
        if len(numbers) != len(keys):
            return None
        cur_data = {k: v for k, v in zip(keys, numbers)}
        row.update(cur_data)
        return row
    if msg.msg.find('total detects amount') != -1:
        keys = [
            'lsp_total',
            'lsp_close',
            'lsp_front',
            'lsp_left',
            'lsp_right',
            'length_step',
            'at_area'
        ]
        numbers = re.findall(r'\d+', msg.msg)  # Finds sequences of digits
        # print(numbers)  # Output: ['3', '15', '0']
        if len(numbers) != len(keys):
            return None
        cur_data = {k: v for k, v in zip(keys, numbers)}
        row.update(cur_data)
        return row
    # print(row) 
    return None

def pure_state_parser(msg, row, **kwargs):
    row['wx'] = msg.velocity.angular.x
    row['wy'] = msg.velocity.angular.y
    row['wz'] = msg.velocity.angular.z

    row['ax'] = msg.linear_acceleration.x
    row['ay'] = msg.linear_acceleration.y
    row['az'] = msg.linear_acceleration.z
    return row