import copy
import colorsys
import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt

class SceneRenderer:
    def __init__(self, scene):
        self.vis = self.create_visualisation()
        self.scene = scene
        self.colours = self.generate_colour_map(len(scene.rooms))
        self.nav_colours = self.generate_colour_map(len(scene.navmesh_islands))

    def create_visualisation(self) -> o3d.visualization.Visualizer:
        vis = o3d.visualization.Visualizer()
        vis.create_window()
        return vis
    
    # Draws the 3D mesh of the scene
    def draw_scene_mesh(self, mesh_path):
        mesh = o3d.io.read_triangle_mesh(mesh_path, True)

        # Rotate mesh to align with Open3D coordinate system
        mesh_r = copy.deepcopy(mesh)
        R = mesh_r.get_rotation_matrix_from_xyz((-np.pi / 2, 0,0))
        mesh_r.rotate(R, center=(0,0,0))

        self.vis.add_geometry(mesh_r)
    
    # Generates a list of num_colours maximally diiferent colours
    def generate_colour_map(self, num_colours):
        HSV_tuples = [(x * 1.0 / num_colours, 1.0, 1.0) for x in range(num_colours)]
        RGB_tuples = list(map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples))
        return RGB_tuples
    
    # Plots a chart showing the index of each room and the colour assigned to it
    def plot_room_index_chart(self):
        fig, ax = plt.subplots(figsize=(10, 2))
        for i, colour in enumerate(self.colours):
            ax.add_patch(plt.Rectangle((i, 0), 1, 1, color=colour))
            ax.text(i + 0.5, 0.5, str(i+1), ha='center', va='center', color='black', fontsize=18)
        
        ax.set_xlim(0, len(self.colours))
        ax.set_ylim(0, 1)
        ax.axis('off')
        plt.show(block=False)
        plt.pause(0.1)
    
    # Draws the centroids and bounding boxes of each room in the scene
    def draw_rooms(self):
        for i, room in enumerate(self.scene.rooms):
            centroid = self.create_box_geometry(pos=room.centroid, dims=np.array([0.5, 0.5, 0.5]), colour=self.colours[i])
            self.vis.add_geometry(centroid)
            bb = self.create_bb_geometry(room.world_corners, self.colours[i])
            self.vis.add_geometry(bb)
            self.draw_bb_corners(room.world_corners, self.colours[i])

    # Draws the centroids of each object in the scene
    def draw_object_centroids(self):
        for i, room in enumerate(self.scene.rooms):
            for obj in room.objects:
                obj_geo = self.create_box_geometry(pos=obj.centroid, dims=np.array([0.15, 0.15, 0.15]), colour=self.colours[i])
                self.vis.add_geometry(obj_geo)

    # Draws lines between the centroids of each object and the room they are in
    def draw_object_room_lines(self):
        for i, room in enumerate(self.scene.rooms):
            for obj in room.objects:
                line_set = o3d.geometry.LineSet()
                line_set.points = o3d.utility.Vector3dVector(np.array([obj.centroid, room.centroid]))
                line_set.lines = o3d.utility.Vector2iVector([[0, 1]])
                line_set.paint_uniform_color(self.colours[i])
                self.vis.add_geometry(line_set)

    # Draws the bounding boxes of each object in the scene
    def draw_object_bbs(self):
        for i, room in enumerate(self.scene.rooms):
            for obj in room.objects:
                bb = self.create_bb_geometry(obj.world_corners, self.colours[i])
                self.vis.add_geometry(bb)

    # Draws the paths computed between adjacent rooms in the scene
    def draw_adjacent_paths(self):
        paths_drawn = []
        for (source_room_index, target_room_index), path in self.scene.connections.items():
            if (source_room_index, target_room_index) not in paths_drawn and (target_room_index, source_room_index) not in paths_drawn:
                paths_drawn.append((source_room_index, target_room_index))
                
                for point in path:
                    path_point_marker = self.create_sphere_geometry(pos=point, radius=0.05, colour=self.colours[source_room_index])
                    self.vis.add_geometry(path_point_marker)
    
    # Draws the start/target point used for pathfinding in each room
    def draw_room_nav_points(self):
        for (room_index, _), snapped_point in self.scene.snapped_points.items():
            point = self.create_sphere_geometry(snapped_point, radius=0.1, colour=self.colours[room_index])
            self.vis.add_geometry(point)
    
    # Draws the start/target points on both sides of each door used for pathfinding through closed doors
    # The colour of the point indicates the navmesh island that the point is snapped to
    def draw_door_nav_points(self):
        for [island_index, snapped_point] in self.scene.door_snapped_points:
            colour = self.nav_colours[island_index]
            point = self.create_sphere_geometry(snapped_point, radius=0.1, colour=colour)
            self.vis.add_geometry(point)
    
    # Draws a line between the centroids of each pair of connected rooms
    def draw_connected_rooms(self):
        for source, target in self.scene.connections:
            line_set = o3d.geometry.LineSet()
            line_set.points = o3d.utility.Vector3dVector(np.array([self.scene.rooms[source].centroid, self.scene.rooms[target].centroid]))
            line_set.lines = o3d.utility.Vector2iVector([[0, 1]])
            line_set.paint_uniform_color([0, 1, 0])
            self.vis.add_geometry(line_set)
    
    # Draws the points of each navmesh island in the scene and draws lines between successive points
    # The colour of the points indicates the navmesh island that they belong to
    def draw_navmesh(self):
        for i, island in enumerate(self.scene.navmesh_islands):
            for point in island:
                navmesh_point = self.create_sphere_geometry(pos=point, radius=0.05, colour=self.nav_colours[i])
                self.vis.add_geometry(navmesh_point)

            # Draw lines between navmesh points
            for i in range(len(island)-1):
                line_set = o3d.geometry.LineSet()
                line_set.points = o3d.utility.Vector3dVector(np.array([island[i], island[(i+1)]]))
                line_set.lines = o3d.utility.Vector2iVector([[0, 1]])
                line_set.paint_uniform_color([0.5, 0.5, 0.5])
                self.vis.add_geometry(line_set)
    
    # Draws a bounding box around all instances of the given category in the scene
    # The colour of the bounding box indicates the room that the object is in
    def draw_object_category(self, category):
        for i, room in enumerate(self.scene.rooms):
            for obj in room.objects:
                if obj.label == category:
                    bb = self.create_bb_geometry(obj.world_corners, self.colours[i])
                    self.vis.add_geometry(bb)
                    self.draw_bb_corners(obj.world_corners, self.colours[i])

    # Draws boxes at the corners of the bounding box to make them more visible
    def draw_bb_corners(self, corners, colour=[0, 0, 0]):
        for point in corners:
            box = self.create_box_geometry(pos=point, dims=np.array([0.25, 0.25, 0.25]), colour=colour)
            self.vis.add_geometry(box)

    # Creates an Open3D sphere geometry object at the given position with the given radius and colour
    def create_sphere_geometry(self, pos, radius=0.1, colour=[0, 0 ,0]) -> o3d.geometry.TriangleMesh:
        sphere = o3d.geometry.TriangleMesh.create_sphere(radius)
        sphere.paint_uniform_color(colour)
        sphere.translate(pos)
        return sphere
    
    # Creates an Open3D box geometry object at the given position with the given dimensions and colour
    def create_box_geometry(self, pos, dims=np.array([0.1, 0.1, 0.1]), colour=[0, 0, 0] ) -> o3d.geometry.TriangleMesh:
        box = o3d.geometry.TriangleMesh.create_box(dims[0], dims[1], dims[2])
        box.paint_uniform_color(colour)
        box.translate(pos - dims/2)
        return box
    
    # Creates an Open3D line set object representing the bounding box with the given corners
    def create_bb_geometry(self, corners, colour=[0, 0, 0]) -> o3d.geometry.LineSet:
        lineset = o3d.geometry.LineSet()
        vertices = np.array(corners)
        edges = np.array([
        [0, 1], [1, 2], [2, 3], [3, 0],    # Bottom face
        [4, 5], [5, 6], [6, 7], [7, 4],    # Top face
        [0, 4], [1, 5], [2, 6], [3, 7]])   # Vertical edges
        lineset.points = o3d.utility.Vector3dVector(vertices)
        lineset.lines = o3d.utility.Vector2iVector(edges)
        lineset.paint_uniform_color(colour)
        return lineset