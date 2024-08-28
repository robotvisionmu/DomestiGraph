import numpy as np
from SceneObject import SceneObject


class SceneRoom:
    def __init__(self, x):
        self.label = None
        self.objects = x
        min, max = self.get_extents()
        self.centroid = (min + max) / 2
        self.dims = max - min
        self.world_corners = self.get_corners(min, max)

    def get_corners(self, min, max) -> np.ndarray:
        corners = np.array([
            [min[0], min[1], min[2]],
            [max[0], min[1], min[2]],
            [max[0], min[1], max[2]],
            [min[0], min[1], max[2]],
            [min[0], max[1], min[2]],
            [max[0], max[1], min[2]],
            [max[0], max[1], max[2]],
            [min[0], max[1], max[2]]])
        return corners
    
    def get_extents(self):
        obj_centroids = np.vstack(np.array([obj.centroid for obj in self.objects]))
        min = np.min(obj_centroids, axis=0)
        max = np.max(obj_centroids, axis=0)
        return min, max
    
    def contains_point(self, point: np.ndarray) -> bool:
        x_min, z_min = self.world_corners[:, [0, 2]].min(axis=0)
        x_max, z_max = self.world_corners[:, [0, 2]].max(axis=0)
        x, y, z = point[0], point[1], point[2]
        return x_min <= x <= x_max and z_min <= z <= z_max and y <= (self.centroid[1]+1) and y >= (self.centroid[1] - self.dims[1] - 0.5)

    def to_dict(self):
        return {
            "label": self.label,
            "centroid": {"x": self.centroid.tolist()[0], "y": self.centroid.tolist()[1], "z": self.centroid.tolist()[2]},
            "dims": {"x": self.dims.tolist()[0], "y": self.dims.tolist()[1], "z": self.dims.tolist()[2]},
            "objects": [obj.label for obj in self.objects]
        }