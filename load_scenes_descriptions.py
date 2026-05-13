import subprocess
import os

if __name__ == "__main__":
    output_path = "/home/vist/from_cloud/detector_3d/scenes_descs/"
    remote_path = "/robotics-ml/testing_datasets/map-detector-big-dataset/"
    remote_name = "S3"

    files_lst_str = subprocess.check_output(['rclone', 'ls',  f'{remote_name}:{remote_path}'], text=True)
    for size_name in files_lst_str.split("\n"):
        if not size_name: continue
        size, name = size_name.split()
        if name.endswith('bag'): continue
        cmd = f'rclone copy {remote_name}:{remote_path}{name} {output_path}'
        subprocess.call(cmd.split())
        scene, file = name.split("/")
        os.rename(f'{output_path}/{file}', f'{output_path}/{scene}.{file}')
        # break