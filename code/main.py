import os
import argparse
import json
import yaml
import open3d as o3d
import numpy as np
from utils import create_habsim_instance, generate_hm3dsem_filepaths_json, save_scene_graph_to_yaml, convert_label_data_release_format
from SceneGraph import SceneGraph
from SceneRenderer import SceneRenderer

# Parse the index of the scene to be processed (index in HM3DSem_paths.json) & the dataset parent directory
parser = argparse.ArgumentParser()
parser.add_argument('--data-parent-dir', type=str, default=None, help='The absolute path to the parent directory of the scene_datasets directory')
parser.add_argument('--scene-index', type=int, default=0, help='The index of the scene to be processed in hm3d_paths.json')
args = parser.parse_args()

# Generate the scene file paths JSON file if it does not exist
if args.data_parent_dir is None:
    if not os.path.exists('../data/HM3DSem_paths.json'):
        raise ValueError("Please provide the absolute path to the parent directory of the scene_datasets directory")
    else:
        with open('../data/HM3DSem_paths.json', 'r') as f:
            scenes = json.load(f)
        data_parent_dir = os.sep.join(scenes[0].split('/')[:-5])
        print(data_parent_dir)
else:
    data_parent_dir = args.data_parent_dir
    generate_hm3dsem_filepaths_json(data_parent_dir)

# Load the scene file paths JSON file
with open('../data/HM3DSem_paths.json', 'r') as f:
    scenes = json.load(f)

# Create habitat-sim instance 
scene_config = data_parent_dir + "/scene_datasets/hm3d/hm3d_annotated_basis.scene_dataset_config.json"
scene_id = scenes[args.scene_index]
sim = create_habsim_instance(scene_config, scene_id)

# Construct the scene graph
scene_graph = SceneGraph()
scene_graph.construct_graph(sim)

# Close the habitat-sim instance, otherwise Open3D visualizer will not run
sim.close()

# Save the scene graph to a YAML file
data = scene_graph.to_dict()
save_scene_graph_to_yaml(data, scene_id)

# Create SceneRenderer instance
renderer = SceneRenderer(scene_graph)

# Draw mesh of scene
obj_filename = scene_id.split('/')[-2].split('-')[1]+'.obj'
mesh_path = os.path.join(data_parent_dir, 'scene_datasets/hm3d/obj', scene_id.split('/')[-3], scene_id.split('/')[-2], obj_filename)
renderer.draw_scene_mesh(mesh_path)

# Draw overlays
renderer.draw_rooms()
# renderer.draw_object_centroids()
# renderer.draw_object_room_lines()
# renderer.draw_object_bbs()
# renderer.draw_adjacent_paths()
# renderer.draw_room_nav_points()
# renderer.draw_door_nav_points()
# renderer.draw_connected_rooms()
# renderer.draw_navmesh()
# renderer.draw_object_category("door frame")

# Draw room index chart
renderer.plot_room_index_chart()

# Run visualizer
renderer.vis.run()

# Destroy visualizer window
renderer.vis.destroy_window()

# Convert the labelled data to release format
convert_label_data_release_format()   