import os
import re
import pytz
import rosbag
import tqdm
import argparse
import pandas as pd
from datetime import datetime
from multiprocessing import Pool
from parsers.diagnostics_bag_parser import *


def topic_parser(func):
    def inner(message, row, **kwargs):
        result = func(message, row, **kwargs)
        return result
    return inner

class Parser():
    tz = 'Asia/Oral'
    
    def __init__(self, root_path, topics_n_parsers, columns):
        self.df = []
        self.root_path = root_path
        self.columns = ['bag_name', 'time', 'date', 'vehid'] + columns
        
        self.topics_n_parsers = topics_n_parsers
        self.row = {col: None for col in columns}
        self.topics = list(self.topics_n_parsers.keys())
        
    def launch(self, n, **kwargs):
        bags_names = [f for f in os.listdir(root) if f.endswith('.bag')]
        pool = Pool(processes=n) 
        bags_idx = [[int((len(bags_names) / n) * i), int((len(bags_names) / n) * (i + 1))] for i in range(n)]
        bags_splited = [bags_names[i:j] for i, j in bags_idx]
        
        multiple_results = [pool.apply_async(self.work, args=(files,), kwds=kwargs) for files in bags_splited]
        
        [self.df.extend(res.get()) for res in multiple_results]
        
    def parser(self, bag_object, bag_name, **kwargs):
        self.row['bag_name'] = bag_name
        self.row['vehid'] = bag_name[:3]
        data = []
        for topic, msg, time in bag_object.read_messages(topics = self.topics):
            self.row['time'] = time.to_sec()
            self.row['date'] = datetime.fromtimestamp(time.to_sec(), tz=pytz.timezone(self.tz))
            
            result = self.topics_n_parsers[topic]['parser'](msg, self.row.copy(), **kwargs)
            if result is None:
                continue
            
            self.row = result
            
            if self.topics_n_parsers[topic]['type'] == 'main':
                data.append(self.row)
        return data
                
                
    def work(self, bags_names, **kwargs):
        pbar = tqdm.tqdm(bags_names)
        
        data = []
        for name in pbar:
            pbar.set_description(name[:-4])
            bag_path = os.path.join(self.root_path, name)
            try:
                with rosbag.Bag(bag_path, 'r') as bag:
                   data += self.parser(bag, name, **kwargs)
            except Exception as e:
                pbar.set_postfix_str(f'Error processing: {str(e)}')
                continue
        return data
        
            
    def save_dataframe(self, output_path=None):
        print(len(self.df))
        
        self.df = pd.DataFrame(self.df)
        if not output_path:
            output_path = os.path.join(os.getcwd(), 'df.csv')
        print(f'Saving to {output_path}')
        self.df.to_csv(output_path)
        
                        
    
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse ROSBags')
    parser.add_argument('--root_path', help='Root path of ROSBags', required=True)
    parser.add_argument('--output_path', help='Output path for csv file', required=False, default=None)
    parser.add_argument('--n_cpu', help='Number of processes', required=False, default=8)
    
    args  = parser.parse_args()

    root = args.root_path
    output_path = args.output_path
    n_cpu = int(args.n_cpu)
    
    
    topics = {
        '/SC/state':
            {'parser': state_parser, 'type': 'main'},
        '/SC/close_objects':
            {'parser': close_objects_parser, 'type': 'aux'},
        '/SC/planned_route':
            {'parser': planned_route_parser, 'type': 'aux'},
        '/rosout':
            {'parser': rosout_parser, 'type': 'aux'},
    }
    
    columns = [
        'status',
        'weight',
        'speed',
        'yaw',
        'direction',
        'status',
        'x',
        'y',
        'dist_to_ekg',
        'at_play_field',
        'regime',
        'areas',
        'object_type',
        'average_density',
        'average_intensity',
        'points_in_cube',
        'ransac_plane_inliers_rate',
        'farest_point_distance',
        'csp_total',
        'csp_close',
        'csp_front',
        'csp_left',
        'csp_right',
        'cycle_number',
        'lsp_total',
        'lsp_close',
        'lsp_front',
        'lsp_left',
        'lsp_right',
        'length_step'
    ]
    kwargs = {'dist_thresh' : 5}
    
    p = Parser(root_path=root, topics_n_parsers=topics, columns=columns)
    
    p.launch(n_cpu, **kwargs)
    p.save_dataframe(output_path)
    print(p.df.info())



                        

