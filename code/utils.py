import os
import json
import yaml
import numpy as np
import habitat_sim

def create_habsim_instance(scene_config:str, scene_id:str) -> habitat_sim.Simulator:
    settings = {
        "width": 256,                               # Resolution of the observations
        "height": 256,
        "sensor_height": 0,                         # Height of sensors from agent base in meters
        "scene_dataset_config_file": scene_config,
    }

    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_dataset_config_file = settings['scene_dataset_config_file']
    sim_cfg.scene_id = scene_id

    sensor_specs = []

    color_sensor_spec = habitat_sim.CameraSensorSpec()
    color_sensor_spec.uuid = "color_sensor"
    color_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    color_sensor_spec.resolution = [settings["height"], settings["width"]]
    color_sensor_spec.position = np.array([0.0, settings["sensor_height"], 0.0], dtype=np.float32)
    color_sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_specs.append(color_sensor_spec)

    depth_sensor_spec = habitat_sim.CameraSensorSpec()
    depth_sensor_spec.uuid = "depth_sensor"
    depth_sensor_spec.sensor_type = habitat_sim.SensorType.DEPTH
    depth_sensor_spec.resolution = [settings["height"], settings["width"]]
    depth_sensor_spec.position = np.array([0.0, settings["sensor_height"], 0.0],dtype=np.float32)
    depth_sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_specs.append(depth_sensor_spec)

    semantic_sensor_spec = habitat_sim.CameraSensorSpec()
    semantic_sensor_spec.uuid = "semantic_sensor"
    semantic_sensor_spec.sensor_type = habitat_sim.SensorType.SEMANTIC
    semantic_sensor_spec.resolution = [settings["height"], settings["width"]]
    semantic_sensor_spec.position = np.array([0.0, settings["sensor_height"], 0.0], dtype=np.float32)
    semantic_sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_specs.append(semantic_sensor_spec)

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = sensor_specs

    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    sim = habitat_sim.Simulator(cfg)

    navmesh_settings = habitat_sim.NavMeshSettings()
    navmesh_settings.set_defaults()
    navmesh_settings.agent_height = 0.75
    sim.recompute_navmesh(sim.pathfinder, navmesh_settings)

    return sim

def generate_hm3dsem_filepaths_json(data_parent_dir:str):
    scene_dataset_config_path = os.path.join(data_parent_dir, "scene_datasets/hm3d/hm3d_annotated_basis.scene_dataset_config.json")
    
    with open(scene_dataset_config_path, 'r') as f:
        scene_dataset_config = json.load(f)

    paths = scene_dataset_config['stages']['paths']['.glb']
    extension = ".basis.glb"
    new_paths = []

    for path in paths:
        if path.split('/')[0] in ['train', 'val']:
            dirs = path.split('/')
            scene_name = dirs[1].split('-')[1]
            new_path = os.path.join(data_parent_dir, "scene_datasets/hm3d/", dirs[0], dirs[1], scene_name + extension)
            new_paths.append(new_path)

    with open('../data/HM3DSem_paths.json', 'w') as f:
        json.dump(new_paths, f, indent=4)

def save_scene_graph_to_yaml(data, scene_id):
    target_dir = '../data/label_data'

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    file_name = scene_id.split('/')[-2]+'.yaml'
    file_path = os.path.join(target_dir, file_name)
    print(file_path)

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            yaml.dump(data, file, sort_keys=False, default_flow_style=False)
    else:
        print("File already exists")

def convert_label_data_release_format():
    source_dir = '../data/label_data'
    target_dir = '../data/release_data'

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    scenes = sorted(os.listdir(source_dir))

    for scene in scenes:
        if not os.path.exists(os.path.join(target_dir, scene)):
            with open(os.path.join(source_dir, scene), 'r') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)

                out = {}
                out['rooms'] = {}
                
                for room_key, room in data['rooms'].items():
                    out['rooms'][room_key] = {}
                    out['rooms'][room_key]['label'] = room['label']
                    out['rooms'][room_key]['centroid'] = room['centroid']
                    out['rooms'][room_key]['dims'] = room['dims']

                out['connections'] = data['connections']

            with open(os.path.join(target_dir, scene), 'w') as f:
                yaml.dump(out, f, sort_keys=False, default_flow_style=False)
