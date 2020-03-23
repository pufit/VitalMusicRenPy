init python:
    import math
    from renpy.display.layout import Container
    from renpy.display.layout import Fixed

    # Library init

    CHORDS = ["Am", "Bm", "C", "Dm", "Em", "F", "G"]

    LIBRARY_BACKGROUND_SIZE_RAW = renpy.image_size("icons/library_back.png")
    LIBRARY_BACKGROUND_SIZE = LIBRARY_BACKGROUND_SIZE_RAW[0] * config.screen_height // LIBRARY_BACKGROUND_SIZE_RAW[1], config.screen_height

    CHORD_SIZE = 120

    COLUMNS_IN_GRID = 3

    LIBRARY_TOP_OFFSET = 50
    LIBRARY_SPACING = 40

    SNAP_DISTANCE = 100

    library_grid = None


    #Play space init

    CHORD_SLOTS = 16

    PLAYSPACE_WIDTH = 5000
    PLAYSPACE_HEIGHT = 3000

    BORDER_WIDTH = 0.3
    ISLAND_WIDTH = CHORD_SLOTS * CHORD_SIZE + 200
    ISLAND_HEIGHT = 400

    INITIAL_POS = 0.5, 0.5

    class Grid(object):
        def __init__(self, cell_width, cell_height, origin_pos, spacing=0):
            self.cell_width = cell_width
            self.cell_height = cell_height
            if isinstance(spacing, int):
                spacing = (spacing, spacing, spacing, spacing) # Left, Top, Right, Bottom
            self.spacing = spacing
            self.origin_pos = origin_pos
            self.cells = {}
            self.size = 0

        def set_cell(self, cell_pos, obj):
            self.cells[cell_pos] = obj

        def get_cell(self, cell_pos):
            return self.cells[cell_pos]

        def to_global(self, pos):
            return pos[0] + self.origin_pos[0], pos[1] + self.origin_pos[1]
        
        def to_local(self, pos):
            return pos[0] - self.origin_pos[0], pos[1] - self.origin_pos[1]

        def snap_to_grid_local(self, local_pos):
            x = local_pos[0] // (self.spacing[0] + self.spacing[2] + self.cell_width)
            x = x if local_pos[0] >= 0 else x - 1
            y = local_pos[1] // (self.spacing[1] + self.spacing[3] + self.cell_height)
            y = y if local_pos[1] >= 0 else y - 1
            return x, y

        def get_cell_center_local(self, cell_pos):
            return int(cell_pos[0] * (self.spacing[0] + self.spacing[2] + self.cell_width + 0.5)), \
                   int(cell_pos[1] * (self.spacing[1] + self.spacing[3] + self.cell_height + 0.5))



    def reset_library_button(grid, island, drags, dropped):
            pos = (drags[0].x, drags[0].y)

            def get_distance(slot, pos):
                slot_screen_pos = (
                    renpy.get_adjustment(XScrollValue("play_space")).value - PLAYSPACE_WIDTH * INITIAL_POS[0] - config.screen_width / 2,
                    renpy.get_adjustment(YScrollValue("play_space")).value - PLAYSPACE_HEIGHT * INITIAL_POS[1] - config.screen_height / 2
                )
                print(slot.x, slot.y, pos[0], pos[1])
                return max(abs(slot.x - pos[0]), abs(slot.y - pos[1]))


            def find_closest():
                for slot in island.slots:
                    if get_distance(slot, pos) < SNAP_DISTANCE:
                        return slot

            print(find_closest())

            drags[0].snap(*grid.get_cell(drags[0].drag_name))

    def ChordFrame(name):
        fixed = Fixed(xysize=(CHORD_SIZE, CHORD_SIZE))
        fixed.add(im.Scale(Image("icons/chords_frame_s.png"), CHORD_SIZE, CHORD_SIZE))
        fixed.add(Text(text=str(name), align=(0.5, 0.5)))
        fixed.update()
        return fixed

    def transfer_drag(from_group, to_group, drag):
        from_group.remove(drag)
        to_group.add(drag)

    def chord_block_dragged(island, drag, drop):
        print(drag[0], drop)
        if drop:
            drag[0].slot.attached = None
            drop.attach(drag[0])
            drag[0].snap(drop.x, drop.y, delay=0.1)
        else:
            drag[0].snap(drag[0].slot.x, drag[0].slot.y)

    class SlotDrag(Drag):
        def __init__(self, image, index, pos):
            super(SlotDrag, self).__init__(
                d=image,
                pos=pos,
                drag_name="Slot" + str(index),
                draggable=False,
                droppable=True
            )
            self.index = index
            self.attached = None

        def attach(self, drag):
            if self.attached is not None:
                self.attached.remove()
            self.attached = drag
            drag.slot = self

    class ChordDrag(Drag):
        def __init__(self, name, drag_function, slot, pos):
            chord_frame = ChordFrame(name)
            super(ChordDrag, self).__init__(
                d=chord_frame,
                pos=pos,
                draggable=True,
                droppable=False,
                dragged=drag_function,
                drag_name=name,
                drag_raise=True
            )
            self.slot = slot

        def remove(self):
            self.drag_group.remove(self)

    class Island(Container):
        ALL_SLOTS = []
        def __init__(self, width, height, pos, slots, drag_function, **kwargs):
            super(Island, self).__init__(**kwargs)
            self.width = width
            self.height = height
            self.pos = pos
            self.slots = slots
            self.add(Frame(
                image=Frame(im.FactorScale("backgrounds/background_block.png", BORDER_WIDTH, BORDER_WIDTH), 200, 200),
                xysize=(width, height),
                anchor=(0.5, 0.5),
                pos=pos
            ))
            self.drag_function = renpy.curry(drag_function)(self)
            self.grid = Grid(
                cell_width=CHORD_SIZE,
                cell_height=CHORD_SIZE,
                origin_pos=(int(pos[0] * PLAYSPACE_WIDTH), int(pos[1] * PLAYSPACE_HEIGHT - 0.5 * CHORD_SIZE))
            )
            self.chord_slots = []
            self.draggroup = DragGroup()
            for i in range(-slots / 2, slots / 2):
                slot_pos = self.grid.to_global(self.grid.get_cell_center_local((i, 0)))
                slot = SlotDrag(im.Scale(Image("icons/chords_frame_s.png"), CHORD_SIZE, CHORD_SIZE), i + slots/2, pos=slot_pos)
                self.chord_slots.append(slot)
                Island.ALL_SLOTS.append((slot, self))
                self.draggroup.add(slot)
                slot.snap(*slot_pos)
            self.add(self.draggroup)
            self.update()
            self.add_chord("Am", 0)
            self.add_chord("Am", 1)

        def add_chord(self, name, slot, drag_pos=None):
            if drag_pos is None:
                drag_pos = self.grid.to_global(self.grid.get_cell_center_local((-self.slots / 2 + slot, 0)))
            chord = ChordDrag(name, self.drag_function, self.chord_slots[slot], pos=drag_pos)
            self.chord_slots[slot].attach(chord)
            self.draggroup.add(chord)
            self.update()
            return chord

        def get_drag(self, name):
            return self.draggroup.get_child_by_name(name)

        def remove_drag(self, drag):
            self.draggroup.remove(drag)

        def screen_to_local(self, pos):
            x_offset = renpy.get_adjustment(XScrollValue("play_space")).value
            y_offset = renpy.get_adjustment(YScrollValue("play_space")).value
            return (pos[0] + x_offset, pos[1] + y_offset)

    def library_button_dragged(library, drag, drop):
        def get_distance(slot):
            local_pos = slot[1].screen_to_local((drag[0].x, drag[0].y))
            local_pos = local_pos[0] + drag[0].w // 2, local_pos[1] + drag[0].h // 2
            if abs(local_pos[0] - slot[0].x) < slot[1].grid.cell_width and \
                abs(local_pos[1] - slot[0].y) < slot[1].grid.cell_height:
                return max(
                    abs(local_pos[0] - slot[0].x) < slot[1].grid.cell_width,
                    abs(local_pos[1] - slot[0].y) < slot[1].grid.cell_height
                )
            else:
                return float("inf")

        nearest = min(Island.ALL_SLOTS, key=get_distance)
        if not math.isinf(get_distance(nearest)):
            chord = nearest[1].add_chord(drag[0].drag_name, nearest[0].index) # НЕ РАБОТАЕТ >:(
        drag[0].snap(*library.drags_pos[drag[0]])

    class ChordLibrary(Container):
        def __init__(self, **kwargs):
            super(ChordLibrary, self).__init__(**kwargs)
            self.add(im.Scale(Image("icons/library_back.png"), *LIBRARY_BACKGROUND_SIZE, xalign=1.0))
            self.grid = Grid(
                cell_width=CHORD_SIZE,
                cell_height=CHORD_SIZE,
                origin_pos=(
                    config.screen_width - LIBRARY_BACKGROUND_SIZE[0] // 2 - CHORD_SIZE // 2,
                    LIBRARY_TOP_OFFSET
                ),
                spacing=LIBRARY_SPACING
            )
            self.draggroup = DragGroup()
            self.drags_pos = {}
            for i, chord in enumerate(CHORDS):
                drag_pos = self.grid.to_global(self.grid.get_cell_center_local((i % 3 - 1, i / 3)))
                chord_frame = ChordFrame(chord)
                drag = ChordDrag(
                    chord, renpy.curry(library_button_dragged)(self), None, drag_pos
                )
                self.drags_pos[drag] = drag_pos
                self.draggroup.add(drag)
            self.add(self.draggroup)
            self.update()

            
    
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
    key "game_menu" action NullAction()
    $ Island.ALL_SLOTS = []
    viewport id "play_space":
        add Frame("backgrounds/playspace.png", tile=True)
        child_size PLAYSPACE_WIDTH, PLAYSPACE_HEIGHT
        xinitial INITIAL_POS[0]
        yinitial INITIAL_POS[1]
        draggable True
        add Island(ISLAND_WIDTH, ISLAND_HEIGHT, pos=(0.5, 0.5), slots=16, drag_function=chord_block_dragged)
    add ChordLibrary()

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