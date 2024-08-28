import numpy as np

class SceneObject:
    def __init__(self, x):
        self.label = x.category.name()
        self.centroid = x.aabb.center
        self.dims = x.aabb.sizes
        self.world_corners = self.get_corners(self.centroid - self.dims/2, self.centroid + self.dims/2)
 
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
    
    def to_dict(self):
        return {
            "label": self.label,
            "centroid": {"x": self.centroid.tolist()[0], "y": self.centroid.tolist()[1], "z": self.centroid.tolist()[2]},
            "dims": {"x": self.dims.tolist()[0], "y": self.dims.tolist()[1], "z": self.dims.tolist()[2]},
        }