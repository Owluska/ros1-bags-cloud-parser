import json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import sys
import os
import re
from pprint import pprint
import subprocess
from subprocess import Popen, PIPE
import random
# import rosbag
import subprocess
from tqdm import tqdm
import multiprocessing 
from parsers.diagnostics_bag_parser import *
from collections import Counter



def bag_name_to_date(bag_name):
    # pref = 'XXX_'
    # date_template = 'YYYY-MM-DD-HH-MM-SS'
    # date_str = bag_name[len(pref) : len(pref) + len(date_template)]
    bag_name = bag_name.replace("/", "")
    pattern = r'\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}'
    matches = re.findall(pattern, bag_name)

    if matches is None or len(matches) != 1:
        return None
    return datetime.strptime(matches[0], '%Y-%m-%d-%H-%M-%S')

def is_less(bag_name, dates_range):
    bag_date = bag_name_to_date(bag_name)
    if not bag_date:
        return False
    dates = [datetime.strptime(s, '%Y-%m-%d-%H-%M-%S') for s in dates_range]
    return dates[0] <= bag_date

def is_more(bag_name, dates_range):
    bag_date = bag_name_to_date(bag_name)
    if not bag_date:
        return False
    dates = [datetime.strptime(s, '%Y-%m-%d-%H-%M-%S') for s in dates_range]
    return dates[1] >= bag_date

def search_fst_appropriate_bag(bag_names, conditions, checker):
    l, r = 0, len(bag_names) - 1
    
    while l < r:
        mid = l + (r - l) // 2
        
        if not checker(bag_names[mid], conditions):
            l = mid + 1
        else:
            r = mid
            
    if checker(bag_names[l], conditions):
        return l
    return -1

def search_fst_not_appropriate_bag(bag_names, conditions, checker):
    l, r = 0, len(bag_names) - 1
    
    while l < r:
        mid = l + (r - l) // 2
        
        if checker(bag_names[mid], conditions):
            l = mid + 1
        else:
            r = mid
            
    if not checker(bag_names[l], conditions):
        return l
    return -1

def get_appropriate_bags(bag_names, conditions):
    bag_names = [(f, bag_name_to_date(f)) for f in bag_names 
                 if f[-4:] == '.bag' and  f[:3].isdigit() and bag_name_to_date(f)]
    bag_names = sorted(bag_names, key=lambda item: item[1])
    bag_names = [f for f, date in bag_names]
    frst_idx = search_fst_appropriate_bag(bag_names, conditions, is_less)
    if frst_idx == -1:
        return []
    scnd_idx = search_fst_not_appropriate_bag(bag_names[frst_idx:], conditions, is_more)
    if scnd_idx == -1:
        return bag_names[frst_idx:]
    scnd_idx += frst_idx
    return bag_names[frst_idx:scnd_idx]

# def filter_method(bag_object):
#     return True
    

def load_data(target_path, out_folder, target_topics=None, dates_range=None, split=1, filter_method=None, target_bags_list=None):
    def default_method(bag_object, **kwargs):
        return True
    
    def load_bags(file_names, target_path, out_folder, target_topics, filter_method):
        pbar = tqdm(file_names)
        target_topics = set(target_topics)
        for name in pbar:
            rclone_path = os.path.join(target_path, name)

            pbar.set_description(name)
            if name.find('.bag') == -1:
                pbar.set_postfix_str('skiping')
            cmd = ["rclone", "copy", rclone_path, out_folder]
            subprocess.Popen(cmd).wait()

            if name.find('/') != -1:
                path, name = os.path.split(name)
            file_path = os.path.join(out_folder, name)
            if not os.path.exists(file_path):
                print(rclone_path, out_folder)
            # topics = []
            # try:
            #     bag = rosbag.Bag(file_path, "r")
            #     topics = bag.get_type_and_topic_info()[1].keys()
            #     passed_filter = filter_method(bag)
            #     bag.close()
            # except KeyboardInterrupt:
            #     cmd = ["rm", file_path]
            #     pbar.set_postfix_str('removing')
            #     subprocess.Popen(cmd).wait()
            #     break
            # except Exception:
            #     pbar.set_postfix_str('exception')
            #     pass
            # target_bag = True
            # if len(target_topics):
            #     target_bag |= len(list((set(topics) & target_topics)))
            # if not target_bag:
            #     cmd = ["rm", file_path]
            #     pbar.set_postfix_str('removing')
            #     subprocess.Popen(cmd).wait()
            # else:
            #     pbar.set_postfix_str('saving')
                # return
                
        return

    cmd = ["rclone", "ls", target_path]
    out, err = subprocess.Popen(
        cmd ,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE).communicate()
    file_names = [item.split(' ')[1] for item in str(out).split('\\n') if len(item.split(' ')) > 1]
    if target_bags_list is not None:
        file_names = [name for name in file_names for pattern in target_bags_list if name.find(pattern) != -1]
    if target_bags_list is None and dates_range is not None:
        file_names =  get_appropriate_bags(file_names, dates_range)
    # print(file_names)
    print(f'Found {len(file_names)}')
    n = split
    # print(file_names)
    files_idx = [[int((len(file_names) / n) * i), int((len(file_names) / n) * (i + 1))] for i in range(n)]
    files_splited = [file_names[i:j] for i, j in files_idx]
    if target_topics is None:
        target_topics = []
    
    filter_method = default_method if filter_method is None else filter_method
    bags = []
    processes = []
    for files in files_splited:
        p = multiprocessing.Process(target=load_bags, args=(files, target_path, out_folder, target_topics, filter_method))
        p.start()
        processes.append(p)
        

        
    for p in processes:
        p.join()
        
    return bags




out_folder = '/home/vist/from_cloud/108_detector_threhs_search/bags/'
target_path = 'S3:/levy-storage/queue/erg/'
time_range = ['2024-12-25-00-00-00', '2025-12-25-00-00-00']
from_file = True
file_path = '/home/vist/scripts/erg_lidar_stops_10-04-2026_108'

ncpus = 1
# filter_method_ = filter_method
target_topics = []
save_result = False
file_bags_list = []

if from_file:
    if not file_path:
        raise ValueError("<from_file> var is True but path is not provided!")
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise ValueError("<from_file> var is True but provided path is wrong!")
    
    with open(file_path, 'r') as f:
        file_bags_list = [l.replace('\n', '') for l in f.readlines()]



bags = load_data(target_path, out_folder, target_topics, dates_range=time_range, split=ncpus, target_bags_list=file_bags_list)

if save_result:
    existing_bags = [{"Path": os.path.join(target_path, f), "Name":f} for f in os.listdir(out_folder) if f[-4:] == '.bag']
    # print(existing_bags)

    with open(out_folder + 'bags_list.json', 'w') as f:
        json.dump(bags, f, indent=2)
