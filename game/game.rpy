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


    def ChordFrame(name):
        fixed = Fixed(xysize=(CHORD_SIZE, CHORD_SIZE))
        fixed.add(im.Scale(Image("icons/chords_frame_s.png"), CHORD_SIZE, CHORD_SIZE))
        fixed.add(Text(text=str(name), align=(0.5, 0.5)))
        fixed.update()
        return fixed

    def chord_block_dragged(island, drag, drop):
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
        def __init__(self, width, height, pos, slots, drag_function, global_slots_list, **kwargs):
            super(Island, self).__init__(**kwargs)
            self.width = width
            self.height = height
            self.pos = pos
            self.slots = slots
            self.global_slots_list = global_slots_list
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
                global_slots_list.append((slot, self))
                self.draggroup.add(slot)
                slot.snap(*slot_pos)
            self.add(self.draggroup)
            self.update()
            self.add_chord("Am", 0)
            self.add_chord("Am", 1)

        def add_chord(self, name, slot, drag_pos=None):
            target_pos = self.grid.to_global(self.grid.get_cell_center_local((-self.slots / 2 + slot, 0)))
            if drag_pos is None:
                drag_pos = target_pos
            chord = ChordDrag(name, self.drag_function, self.chord_slots[slot], pos=drag_pos)
            self.chord_slots[slot].attach(chord)
            self.draggroup.add(chord)
            chord.snap(*target_pos, delay=0.1)
            chord.top()
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
            if abs(local_pos[0] - slot[0].x) < slot[1].grid.cell_width and \
                abs(local_pos[1] - slot[0].y) < slot[1].grid.cell_height:
                return max(
                    abs(local_pos[0] - slot[0].x) < slot[1].grid.cell_width,
                    abs(local_pos[1] - slot[0].y) < slot[1].grid.cell_height
                )
            else:
                return float("inf")

        nearest = min(global_slots_list, key=get_distance)
        local_pos = nearest[1].screen_to_local((drag[0].x, drag[0].y))
        local_pos = int(local_pos[0]), int(local_pos[1])
        if not math.isinf(get_distance(nearest)):
            chord = nearest[1].add_chord(drag[0].drag_name, nearest[0].index)
        drag[0].snap(*library.drags_pos[drag[0]])

    class ChordLibrary(Container):
        def __init__(self, **kwargs):
            super(ChordLibrary, self).__init__(**kwargs)
            self.add(im.Scale(Image("icons/library_back.png"), *LIBRARY_BACKGROUND_SIZE, xalign=1.0))
            self.add(ImageButton(
                idle_image="icons/library_button.png",
                action=Function(self.toggle),
                xalign=1.0,
                xoffset=-LIBRARY_BACKGROUND_SIZE[0]
            ))
            self.hidden = False
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

        def toggle(self):
            global library_xpos
            if self.hidden:
                library_xpos = 0
            else:
                library_xpos = LIBRARY_BACKGROUND_SIZE[0]
            self.hidden = not self.hidden


transform library_position(x):
    subpixel True
    linear 0.5 xpos x
                

screen play_space:
    zorder 0
    key "hide_windows" action NullAction()
    viewport id "play_space":
        add Frame("backgrounds/playspace.png", tile=True)
        child_size PLAYSPACE_WIDTH, PLAYSPACE_HEIGHT
        xinitial INITIAL_POS[0]
        yinitial INITIAL_POS[1]
        draggable True
        add main_island
    hbox:
        yalign 1.0
        fixed:
            add Solid("#f0f8ff")
            xalign 0.0
            ysize 0.2
            xsize 500
            hbox:
                yalign 0.5
                imagebutton:
                    idle im.Scale("icons/play_button_idle.png", 175, 175)
                    xmargin 38
                imagebutton:
                    idle im.Scale("icons/stop_button.png", 175, 175)
                    xmargin 38
        fixed:
            add Solid("#e5e8ea")
            xalign 0.0
            ysize 0.2
            xsize 1920 - 500
    add chord_library at library_position(library_xpos)


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
    default global_slots_list = []
    default chord_library = ChordLibrary()
    default main_island = Island(
        ISLAND_WIDTH,
        ISLAND_HEIGHT,
        global_slots_list=global_slots_list,
        pos=(0.5, 0.5),
        slots=16,
        drag_function=chord_block_dragged
    )
    default library_xpos = 0
    call screen play_space