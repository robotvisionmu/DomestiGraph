import numpy as np
import habitat_sim as hs
from SceneRoom import SceneRoom
from SceneObject import SceneObject

class SceneGraph:

    def __init__(self):
        self.rooms = []
        self.connections = {}
        self.snapped_points = {}
        self.navmesh_islands = []
        self.door_snapped_points = []  

    def construct_graph(self, habSim:hs.Simulator):
        self.populate_rooms(habSim.semantic_scene)
        self.filter_outlier_objects()
        self.connect_rooms(habSim)
        self.connect_rooms_through_closed_doors(habSim)
        self.connections = self.make_connections_symmetric()
        self.sorted_connections = dict(sorted(self.connections.items()))
        for i in range(habSim.pathfinder.num_islands):
            self.navmesh_islands.append(habSim.pathfinder.build_navmesh_vertices(i))

    def make_connections_symmetric(self):
        symetric_connections = {}
        for (i, j) in self.connections:
            symetric_connections[(i, j)] = self.connections[(i, j)]
            if (j, i) not in self.connections:
                symetric_connections[(j, i)] = self.connections[(i, j)].reverse()
        
        return symetric_connections
    
    # Creates a SceneObject for each object in each room in habitat-sim semantic scene and creates a SceneRoom from the resulting SceneObjects
    # Ignores any objects that have a category of "Unknown" or have a zero dimensions
    # If a list of objects is empty, the SceneRoom is not created
    def populate_rooms(self, habScene:hs.scene.SemanticScene):
        for habRoom in habScene.regions:
                objects = []
                for habObject in habRoom.objects:
                    if(np.array_equal(habObject.aabb.center, np.array([0.0, 0.0, 0.0])) or np.array_equal(habObject.aabb.sizes, np.array([0.0, 0.0, 0.0])) or habObject.category.name() in ["Unknown", "unknown"]):
                        pass
                    else:
                        objects.append(SceneObject(habObject))
                        
                if(len(objects) != 0):
                    room = SceneRoom(objects)
                    if np.all(room.dims >0.1):
                        self.rooms.append(room)

    # Calculates the mean and standard deviation of the object centroids in each room and removes objects that are more than 2.5 standard deviations away from the mean
    # This is done to remove outlier objects that have been incorrectly assigned to a room that would otherwise result in invalid room bounding boxes
    def filter_outlier_objects(self):
        for room in self.rooms:
            obj_centroids = np.array([obj.centroid for obj in room.objects])
            obj_centroids = np.vstack(obj_centroids)
            mean = np.mean(obj_centroids, axis=0)
            std_dev = np.std(obj_centroids, axis=0)
            distances = abs(obj_centroids - mean)
            keep_objects = np.all(distances < 2.5*std_dev, axis=1)
            room.objects = [room.objects[i] for i in range(len(room.objects)) if keep_objects[i]]
            new_min, new_max = room.get_extents()
            room.centroid = (new_min + new_max) / 2
            room.dims = new_max - new_min
            room.world_corners = room.get_corners(new_min, new_max)
    
    # Connects rooms that are adjacent to each other
    def connect_rooms(self, habSim:hs.Simulator):
        for i, room in enumerate(self.rooms):
            for j, other_room in enumerate(self.rooms):
                if room != other_room:
                    for k in range(habSim.pathfinder.num_islands):
                        path, start_point, target_point = self.compute_path(room, other_room, k, habSim)
                        if(path):
                            if self.is_adjacent(room, other_room, path):
                                self.snapped_points[(i, k)] = start_point
                                if (i, j) not in self.connections and (j, i) not in self.connections:
                                    passes_through_adjacent_room, connection = self.passes_through_adjacent_room(i, j, path)
                                    if not passes_through_adjacent_room:
                                        self.connections[(i, j)] = path
                                    else:
                                        path_b = self.connections[connection]

                                        path_length = self.calculate_path_length(path)
                                        path_b_length = self.calculate_path_length(path_b)

                                        if path_length < path_b_length:
                                            self.connections.pop(connection)
                                            self.connections[(i, j)] = path
    
    # Connects rooms that are separated by closed doors
    def connect_rooms_through_closed_doors(self, habSim:hs.Simulator):
        for i, room in enumerate(self.rooms):
            for obj in room.objects:
                if obj.label == "door frame":
                    door_dir = np.argmin(obj.dims)
                    outside_sample_dir = (obj.centroid[door_dir] - room.centroid[door_dir])/abs(obj.centroid[door_dir] - room.centroid[door_dir])
                    inside_sample_dir = -outside_sample_dir

                    outside_offset = np.array([0, 0, 0])
                    outside_offset[door_dir] = outside_sample_dir * 0.75
                    outside_offset[1] = -obj.dims[1]/2
                    outside_sample_start = obj.centroid + outside_offset
                    outside_island_index = habSim.pathfinder.get_island(outside_sample_start)
                    outside_snapped_point = habSim.pathfinder.snap_point(outside_sample_start, outside_island_index)
                    self.door_snapped_points.append([outside_island_index, outside_snapped_point])

                    inside_offset = np.array([0, 0, 0])
                    inside_offset[door_dir] = inside_sample_dir #* 0.75
                    inside_offset[1] = -room.dims[1]/2
                    inside_sample_start = obj.centroid + inside_offset
                    inside_island_index = habSim.pathfinder.get_island(inside_sample_start)
                    inside_snapped_point = habSim.pathfinder.snap_point(inside_sample_start, inside_island_index)
                    self.door_snapped_points.append([inside_island_index, inside_snapped_point])

                    if inside_island_index != outside_island_index:
                        for j, other_room in enumerate(self.rooms):
                            if other_room != room and other_room.contains_point(outside_snapped_point):
                                room_snapped_point = habSim.pathfinder.snap_point(room.centroid - np.array([0,room.dims[1]/2,0]), inside_island_index)
                                other_room_snapped_point = habSim.pathfinder.snap_point(other_room.centroid - np.array([0,other_room.dims[1]/2,0]), outside_island_index)

                                path_a = hs.ShortestPath()
                                path_a.requested_start = room_snapped_point
                                path_a.requested_end = inside_snapped_point
                                path_a_found = habSim.pathfinder.find_path(path_a)

                                path_b = hs.ShortestPath()
                                path_b.requested_start = outside_snapped_point
                                path_b.requested_end = other_room_snapped_point
                                path_b_found = habSim.pathfinder.find_path(path_b)

                                if path_a_found and path_b_found:
                                    self.connections[(i,j)] = (self.linear_interpolation(path_a.points) + self.linear_interpolation(path_b.points))
                                    self.snapped_points[(i, inside_island_index)] = room_snapped_point
                                    self.snapped_points[(j, outside_island_index)] = other_room_snapped_point
    
    # Computes a path (if it exists) between the source and target rooms on the specified navmesh island
    def compute_path(self, sourceRoom, targetRoom, island_index, habSim:hs.Simulator):
        start_point = habSim.pathfinder.snap_point(sourceRoom.centroid - np.array([0,sourceRoom.dims[1]/2,0]), island_index)
        target_point = habSim.pathfinder.snap_point(targetRoom.centroid - np.array([0,targetRoom.dims[1]/2,0]), island_index)

        if sourceRoom.contains_point(start_point) and targetRoom.contains_point(target_point):
            path = hs.ShortestPath()
            path.requested_start = start_point
            path.requested_end = target_point
            path_found = habSim.pathfinder.find_path(path)
    
            if path_found:
                interpolated_path = self.linear_interpolation(path.points)
                interpolated_path = self.linear_interpolation(interpolated_path)
                return interpolated_path, start_point, target_point  
        
        return [], None, None  

    # Given a path between two rooms, checks if the path passes through any other room
    def is_adjacent(self, source, target, path):
        rooms_to_check = [room for room in self.rooms if room not in [source, target]]
        for point in path:
            for room in rooms_to_check:
                if (room.contains_point(point) and not(source.contains_point(point) or target.contains_point(point))):
                    return False
        return True
    
    # Given a path between two rooms, checks if the path passes through a room that is already connected to the source room
    def passes_through_adjacent_room(self, source_index, target_index, path):
        for (i, j) in self.connections:
            if i == source_index and j != target_index:
                for point in path:
                    if self.rooms[j].contains_point(point):
                        return True, (i,j)
            elif j == source_index and i != target_index:
                for point in path:
                    if self.rooms[i].contains_point(point):
                        return True, (i, j)            
        return False, None
    
    # Increases the resolution of the path by adding a point halfway between each pair of points
    def linear_interpolation(self, points):
        interpolated_points = []
        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]
            interpolated_p = (p0 + p1) / 2
            interpolated_points.append(p0)
            interpolated_points.append(interpolated_p)
        interpolated_points.append(points[-1])
        return interpolated_points  
    
    def calculate_path_length(self, path):
        length = 0
        for i in range(len(path) - 1):
            length += np.linalg.norm(path[i+1] - path[i])
        return length
    
    # Saves room data and connections to a dictionary
    def to_dict(self):
        dict = {}
        dict["rooms"] = {}
        for i, room in enumerate(self.rooms):
            key = "room_" + str(i+1)
            dict["rooms"][key] = room.to_dict()
        dict["connections"] = [list((i+1, j+1)) for (i, j) in self.sorted_connections.keys()]
        return dict
