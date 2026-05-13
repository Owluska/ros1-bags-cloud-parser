from shapely.geometry import Polygon, Point
import json
import numpy as np
from scipy.spatial.transform import Rotation

def state_parser(msg, row, **kwargs):
    row['weight'] = msg.weight
    row['speed'] = msg.speed
    row['yaw'] = msg.yaw
    row['direction'] = msg.direction
    row['x'] = msg.position.x
    row['y'] = msg.position.y
    row['status'] = msg.status
    row['at_play_field'] = None
    if row['border_polygon'] is not None:
        ego_pos = Point(row['x'], row['y'])
        row['at_play_field'] = ego_pos.covered_by(Polygon(row['border_polygon']))

    return row


# def slope_parser(msg, row, **kwargs):
#     row['slope'] = msg.slope
#     return row

def target_speed_parser(msg, row, **kwargs):
    row['target_speed_model'] = msg.data
    return row

def close_objects_parser(msg, row, **kwargs):
    # ekg_id = [3007001, 3007002, 3016001]
    ekg_id = [3007002]
    if row['x'] is None or row['y'] is None:
        return None
    
    for state in msg.objects:
        if state.info.vehid in ekg_id:
            dist = (
                (row['x'] - state.position.x) ** 2 + 
                 (row['y'] - state.position.y) ** 2) ** 0.5
            row['dist_to_ekg'] = dist
    return row

def planned_route_parser(msg, row, **kwargs):
    if row['x'] is None or row['y'] is None:
        return None
    if len(msg.points):
        row['regime'] = msg.points[0].regime
        row['target_speed_hal'] = msg.points[0].target_speed
    if len(msg.border.points):
        border_poly =[[p.x, p.y] for p in msg.border.points]
        row['border_polygon'] = border_poly
    return row


def pure_state_parser(msg, row, **kwargs):
    # print(msg)
    acc = [
        msg.linear_acceleration.x,
        msg.linear_acceleration.y,
        msg.linear_acceleration.z,
    ]
    row['acc'] = np.linalg.norm(acc)
    rot = Rotation.from_quat(
        [
            msg.pose.orientation.x,
            msg.pose.orientation.y, 
            msg.pose.orientation.z, 
            msg.pose.orientation.w 
        ]
    )
    r, p, y = rot.as_euler('xyz', degrees=False)
    row['slope'] = -p
    return row


def pedals_gear_parser(msg, row, **kwargs):
    # print(msg)
    row['brakes'] = msg.brake
    row['throttle'] = msg.throttle
    row['hydraulic'] = int(msg.hydraulic_brake != 0 or msg.loading_brake != 0)
    return row


def params_parser(msg, row, **kwargs):
    params = json.loads(msg.data)
    if 'use_estimated_roughness' in params['QarlSpeedControllerNode']:
        row['use_roughness_estimator'] = params['QarlSpeedControllerNode']['use_estimated_roughness']
    if 'speed_meatball_dist_min' in params['QarlSpeedControllerNode']:
        row['speed_meatball_dist_min'] = params['QarlSpeedControllerNode']['speed_meatball_dist_min']
    if 'speed_meatball_dist_max' in params['QarlSpeedControllerNode']:
        row['speed_meatball_dist_max'] = params['QarlSpeedControllerNode']['speed_meatball_dist_max']   
    return row

def estimated_ro_parser(msg, row, **kwargs):
    row['ro_estimated'] = msg.value
    return row

def ro_array_parser(msg, row, **kwargs):
    row['applied_ro'] = msg.data[0]
    return row

def ro_source_parser(msg, row, **kwargs):
    row['ro_source'] = msg.value
    return row

def fuel_parser(msg, row, **kwargs):
    row['fuel_level'] = msg.value
    return row

def applied_slope_parser(msg, row, **kwargs):
    row['applied_slope'] = msg.data[1]
    return row

