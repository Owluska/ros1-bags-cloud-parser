import numpy as np
def filter_method(bag_object):
    ego_position = None
    ego_speed = None
    ego_direction = 0
    ego_yaw = 0
    for topic, msg, time in bag_object.read_messages(topics=['/SC/state', '/SC/close_objects']):
        if topic == '/SC/state':
            ego_position = np.array([msg.position.x, msg.position.y])
            ego_speed = msg.speed
            ego_direction = msg.direction
            ego_yaw = msg.yaw
        if topic == '/SC/close_objects':

            for obj in msg.objects:
                if not obj.info.vehid in [3016001, 1016001, 1016002, 1016003]:
                    continue
                obj_position = np.array([obj.position.x, obj.position.y])
                obj_speed = obj.speed
                
                dist = np.linalg.norm(ego_position - obj_position)
                leaving_shovel = (
                    obj.info.vehid == 3016001
                    and dist < 50.0 
                    and ego_speed > 1.0
                    and ego_direction == 1
                )

                bypassing = (
                    obj.info.vehid in [1016001, 1016002, 1016003]
                    and dist < 15.0 
                    and ego_speed > 1.0 
                    and obj_speed > 1.0
                    and ego_direction == 1
                    and abs(obj.yaw - ego_yaw) > np.pi / 2
                )
                if leaving_shovel or bypassing:
                    # print(dist, obj.info.vehid)
                    return True
    return False