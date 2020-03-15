init python:

    # Library init

    CHORDS = ["Am", "Bm", "C", "Dm", "Em", "F", "G"]

    LIBRARY_BACKGROUND_SIZE_RAW = renpy.image_size("icons/library_back.png")
    LIBRARY_BACKGROUND_SIZE = LIBRARY_BACKGROUND_SIZE_RAW[0] * config.screen_height // LIBRARY_BACKGROUND_SIZE_RAW[1], config.screen_height

    CHORD_SIZE = 120

    COLUMNS_IN_GRID = 3

    LIBRARY_TOP_OFFSET = 50
    LIBRARY_SPACING = 40

    LIBRARY_SIDE_OFFSET_X = (LIBRARY_BACKGROUND_SIZE[0] - COLUMNS_IN_GRID * CHORD_SIZE - (COLUMNS_IN_GRID - 1) * LIBRARY_SPACING) / 2 

    SNAP_DISTANCE = 100

    library_grid = None


    #Play space init

    CHORD_SLOTS = 16

    PLAYSPACE_WIDTH = 5000
    PLAYSPACE_HEIGHT = 3000

    BORDER_WIDTH = 0.3
    ISLAND_WIDTH = CHORD_SLOTS * CHORD_SIZE + 200
    ISLAND_HEIGHT = 400

    class CustomGrid(object):
        def __init__(self, cell_width, cell_height, spacing, cols, origin_pos):
            self.cell_width = cell_width
            self.cell_height = cell_height
            self.spacing = spacing
            self.cols = cols
            self.origin_pos = origin_pos
            self.positions_dict = {}
            self.positions_list = []
            self.size = 0

        def get_cell(self, key):
            if isinstance(key, int):
                return self.positions_list[key]
            else:
                return self.positions_dict[key]

        def add_cell(self, name=""):
            self.positions_list.append((
                self.origin_pos[0] + (self.size % self.cols) * (self.spacing + self.cell_width),
                self.origin_pos[1] + self.size / self.cols * (self.cell_height + self.spacing)
            ))
            if (name != ""):
                self.positions_dict[name] = self.positions_list[self.size]
            self.size += 1
            return self.get_cell(self.size - 1)

    def reset_library_button(grid, island, drags, dropped):
            pos = (drags[0].x, drags[0].y)

            def get_distance(cell, pos):
                x_offset = renpy.get_adjustment(XScrollValue("play_space")).value - (PLAYSPACE_WIDTH - config.screen_width) / 2 + grid.origin_pos[0]
                y_offset = renpy.get_adjustment(YScrollValue("play_space")).value - (PLAYSPACE_HEIGHT - config.screen_height) / 2 + grid.origin_pos[1]
                print(renpy.get_mouse_pos(), cell[0])
                return max(abs(cell[0] + x_offset - pos[0]), abs(cell[1] + y_offset - pos[1]))


            def find_closest():
                for cell in island.positions_list:
                    if get_distance(cell, pos) < SNAP_DISTANCE:
                        return cell

            print(find_closest())
            drags[0].snap(*grid.get_cell(drags[0].drag_name))

    def get_size(d):
        w, h = renpy.render(d, 0, 0, 0, 0).get_size()
        print(w, h)
        return w, h

    
screen chord_frame(name=''):
    frame:
        background im.Scale(Image("icons/chords_frame_s.png"), CHORD_SIZE, CHORD_SIZE)
        xsize CHORD_SIZE
        ysize CHORD_SIZE
        vbox:
            xalign 0.5
            yalign 0.5
            text "[name]"

screen chord_library(islands):
    zorder 1

    python:
        library_grid = CustomGrid(
            cell_width=CHORD_SIZE,
            cell_height=CHORD_SIZE,
            spacing=LIBRARY_SPACING,
            cols=COLUMNS_IN_GRID,
            origin_pos=(config.screen_width - LIBRARY_BACKGROUND_SIZE[0] + LIBRARY_SIDE_OFFSET_X, LIBRARY_TOP_OFFSET)
        )
        dragged_function = renpy.curry(reset_library_button)(library_grid, islands)

    fixed:
        align 0, 0
        add "icons/library_back.png" xalign 1.0 size LIBRARY_BACKGROUND_SIZE
        viewport:
            scrollbars "vertical"
            ypos LIBRARY_TOP_OFFSET
            child_size 1920, 1200
            draggroup:
                for i, name in enumerate(CHORDS):
                    drag:
                        pos library_grid.add_cell(name)
                        drag_name name
                        use chord_frame(name)
                        droppable False
                        draggable True
                        dragged dragged_function

                

screen play_space:
    zorder 0
    key "hide_windows" action NullAction()

    viewport id "play_space":
        add Frame("backgrounds/playspace.png", tile=True)
        child_size PLAYSPACE_WIDTH, PLAYSPACE_HEIGHT
        xinitial 0.5
        yinitial 0.5
        draggable True
        frame:
            background Frame(im.FactorScale("backgrounds/background_block.png", BORDER_WIDTH, BORDER_WIDTH), 200, 200)
            xysize ISLAND_WIDTH, ISLAND_HEIGHT
            anchor 0.5, 0.5
            pos 0.5, 0.5

            python:
                island = CustomGrid(
                    cell_width=CHORD_SIZE,
                    cell_height=CHORD_SIZE,
                    spacing=0,
                    cols=16,
                    origin_pos=(100, (ISLAND_HEIGHT - CHORD_SIZE) / 2)
                )

            draggroup:
                for i in range(16):
                    drag:
                        drag_name "test"
                        use chord_frame()
                        droppable True
                        draggable False
                        pos island.add_cell()

    use chord_library(island)

label disable_vn:
    $ quick_menu = False
    $ renpy.block_rollback()
    return

label enable_vn:
    $ quick_menu = True
    $ renpy.fix_rollback()
    return


label game:
    scene
    hide screen say
    call disable_vn
    call screen play_space
