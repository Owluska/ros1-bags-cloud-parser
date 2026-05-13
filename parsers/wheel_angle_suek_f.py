from struct import unpack
def state_parser(msg, row, **kwargs):
    row['cur_wheel_angle'] = msg.wheel_angle
    row['weight'] = msg.weight
    row['speed'] = msg.speed
    row['yaw'] = msg.yaw
    row['direction'] = msg.direction
    row['x'] = msg.position.x
    row['y'] = msg.position.y
    row['state_time'] = msg.header.stamp.to_sec(),
    row['status'] = msg.status
    return row


def control_parser(msg, row, **kwargs):
    row['control_time'] = msg.header.stamp.to_sec()
    row['tar_wheel_angle'] = msg.steps[0].wheel_angle
    return row

def temp_pressure_parser(msg, row, **kwargs):
    f = lambda data : unpack('>H', data[2:4])[0] * 0.5
    if msg.id == 0x18FF14A0:
        row['hydraulics_pressure'] = f(msg.data)
    
    if msg.id == 419370024:   
        # print(msg.data)
        f = lambda data : data[4] - 40
        row['hydraulics_temperature'] = f(msg.data)
    return row