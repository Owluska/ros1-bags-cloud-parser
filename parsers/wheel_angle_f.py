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

def pressure_parser(msg, row, **kwargs):
    f = lambda data : (data[0] + data[1] * 256) * 0.02
    if msg.id == 0x18f0080b:
        row['hydraulics_pressure'] = f(msg.data)
    return row

def temperature_parser(msg, row, **kwargs):
    # print([(i, l.label) for i, l in enumerate(msg.layout.dim) if l.label == "hydraulic_temperature_raw"])
    ti = [i for i, l in enumerate(msg.layout.dim) if l.label == "hydraulic_temperature_raw"]
    print([l for i, l in enumerate(msg.layout.dim)])
    if len(ti):
        ti = ti[0]
        row['hydraulics_temperature'] = msg.data[ti]
    return row