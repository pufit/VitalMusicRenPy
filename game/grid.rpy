init -1 python:
    class Grid(object):
        def __init__(self, cell_width, cell_height, origin_pos, spacing=0):
            self.cell_width = cell_width
            self.cell_height = cell_height
            if isinstance(spacing, int):
                spacing = (spacing, spacing, spacing, spacing) # Left, Top, Right, Bottom
            self.spacing = spacing
            self.origin_pos = origin_pos
            self.size = 0

        def to_global(self, pos):
            return pos[0] + self.origin_pos[0], pos[1] + self.origin_pos[1]
        
        def to_local(self, pos):
            return pos[0] - self.origin_pos[0], pos[1] - self.origin_pos[1]

        def get_cell_by_pos_local(self, local_pos):
            x = local_pos[0] // (self.spacing[0] + self.spacing[2] + self.cell_width)
            y = local_pos[1] // (self.spacing[1] + self.spacing[3] + self.cell_height)
            return x, y

        def get_cell_center_local(self, cell_pos):
            return int(cell_pos[0] * (self.spacing[0] + self.spacing[2] + self.cell_width) + self.cell_width // 2), \
                   int(cell_pos[1] * (self.spacing[1] + self.spacing[3] + self.cell_height) + self.cell_height // 2)
