init -1 python:

    import math
    import os
    import pygame_sdl2 as pygame
    import time
    
    from Queue import Queue
    from renpy.audio.audio import get_channel
    from renpy.display.layout import Container
    from renpy.display.layout import Fixed
    from renpy.display.layout import Grid as LayoutGrid
    from renpy.display.render import render, redraw
    from threading import Thread

    renpy.music.register_channel('chords')
    renpy.music.register_channel('backing_track')


    GAME_ROOT = os.path.join(config.basedir, "game")

    # Library init

    CHORDS = ["Am", "Bm", "C", "Dm", "Em", "F", "G"]

    LIBRARY_BACKGROUND_SIZE_RAW = renpy.image_size("icons/library_back.png")
    LIBRARY_BACKGROUND_SIZE = LIBRARY_BACKGROUND_SIZE_RAW[0] * config.screen_height // LIBRARY_BACKGROUND_SIZE_RAW[1], config.screen_height - 150

    CHORD_SIZE = 120

    COLUMNS_IN_GRID = 3

    LIBRARY_TOP_OFFSET = 50
    LIBRARY_SPACING = 40

    SNAP_DISTANCE = 100

    library_grid = None

    # Play space init

    CHORD_SLOTS = 16

    PLAYSPACE_WIDTH = 5000
    PLAYSPACE_HEIGHT = 3000

    BORDER_WIDTH = 0.3
    ISLAND_WIDTH = CHORD_SLOTS * CHORD_SIZE + 200
    ISLAND_HEIGHT = 400

    INITIAL_POS = 0.5, 0.5

    # Progress grid init

    HIDDEN_CHORDS = ["Am", "F", "C", "G", "Am", "F", "Em", "G", "Am", "C", "F", "G", "Am", "F", "Em", "C"]

    # Music init

    TIME_SIGNATURE = 4, 4
    TEMPO = 90


    DRAG_BLOCKED = False
        

    config.keymap["end_level"] = []
    config.keymap["chord_placed"] = []
    config.keymap["music_stopped"] = []
    config.keymap["pointer_moved"] = []


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

        def get_cell_by_pos_local(self, local_pos):
            x = local_pos[0] // (self.spacing[0] + self.spacing[2] + self.cell_width)
            y = local_pos[1] // (self.spacing[1] + self.spacing[3] + self.cell_height)
            return x, y

        def get_cell_center_local(self, cell_pos):
            return int(cell_pos[0] * (self.spacing[0] + self.spacing[2] + self.cell_width) + self.cell_width // 2), \
                   int(cell_pos[1] * (self.spacing[1] + self.spacing[3] + self.cell_height) + self.cell_height // 2)


    class DisalableDrag(Drag):
        disabled = False

        def __init__(self, **kwargs):
            super(DisalableDrag, self).__init__(**kwargs)
            self.disabled = False

        def event(self, ev, x, y, st):
            if not DisalableDrag.disabled:
                self.disabled = False
                super(DisalableDrag, self).event(ev, x, y, st)
            else:
                if self.is_focused() and ev.type == pygame.MOUSEBUTTONDOWN:
                    renpy.notify("Stop music first")
                if not self.disabled:
                    self.disabled = True
                    super(DisalableDrag, self).event(pygame.MOUSEBUTTONUP, x, y, st)


    class ChordFrame(Container):
        def __init__(self, name, size=CHORD_SIZE):
            super(ChordFrame, self).__init__(xysize=(size, size))
            self.add(im.Scale(Image("icons/chords_frame.png"), size, size))
            self.text = Text(text=str(name), align=(0.5, 0.5))
            self.add(self.text)
            self.update()

        def change_name(self, name):
            self.text.set_text(name)


    def chord_block_dragged(island, drag, drop):
        drag[0].slot.attached = None
        if drop:
            renpy.play("audio/sfx/click.mp3")
            drop.attach(drag[0])
            drag[0].snap(drop.x, drop.y)
        else:
            drag[0].remove()


    class SlotDrag(Drag):
        def __init__(self, index, pos, **kwargs):
            super(SlotDrag, self).__init__(
                pos=pos,
                drag_name="Slot" + str(index),
                draggable=False,
                droppable=True,
                **kwargs
            )
            self.index = index
            self.attached = None

        def attach(self, drag):
            if self.attached is not None:
                self.attached.remove()
            self.attached = drag
            drag.slot = self


    class ChordDrag(DisalableDrag):
        def __init__(self, name, drag_function, slot, pos, **kwargs):
            chord_frame = ChordFrame(name)
            super(ChordDrag, self).__init__(
                d=chord_frame,
                pos=pos,
                draggable=True,
                droppable=False,
                dragged=drag_function,
                drag_name=name,
                drag_raise=True,
                **kwargs
            )
            self.slot = slot
            self.name = name

        def remove(self):
            self.drag_group.remove(self)


    class IslandPointer(Drag):
        def __init__(self, grid, left_bound, right_bound, start_cell, **kwargs):
            super(IslandPointer, self).__init__(droppable=False, **kwargs)
            self.grid = grid
            self.left_bound = left_bound
            self.right_bound = right_bound
            self.start_cell = start_cell
            self.last_cell_x = None

        def move_to(self, cell_x):
            if cell_x > self.right_bound:
                return
            target_x, target_y = self.grid.to_global(self.grid.get_cell_center_local((cell_x, 1)))
            if self.w is None:
                child = self.style.child
                if child is None:
                    child = self.child
                cr = render(child, 200, 200, 0, 0)
                self.w, self.h = cr.get_size()
            target_x -= int(self.w // 2)
            target_y -= int(self.h // 2)
            self.snap(target_x, target_y)

        def event(self, ev, x, y, st):
            cell_x, cell_y = self.get_cell(self.x + x, self.y + y)
            if cell_x >= self.left_bound and cell_x <= self.right_bound and not DisalableDrag.disabled:
                x = self.grid.to_global(self.grid.get_cell_center_local((cell_x, cell_y)))[0] - self.x - self.w // 2
                super(IslandPointer, self).event(ev, x, 0, st)
                if self.drag_moved:
                    if self.last_cell_x is not None and cell_x != self.last_cell_x:
                        renpy.queue_event("pointer_moved")
                    self.last_cell_x = cell_x
                    
            else:
                super(IslandPointer, self).event(ev, 0, 0, st)

        def get_cell(self, x=None, y=None):
            if x is None:
                x = self.x
            if y is None:
                y = self.y
            return self.grid.get_cell_by_pos_local(self.grid.to_local((x, y)))


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
                origin_pos=(int(pos[0] * PLAYSPACE_WIDTH), int(pos[1] * PLAYSPACE_HEIGHT - CHORD_SIZE // 2))
            )
            self.chord_slots = []
            self.draggroup = DragGroup()
            self.start_cell_pos = -slots / 2
            for i in range(self.start_cell_pos, self.start_cell_pos + slots):
                slot_pos = self.grid.to_global(self.grid.get_cell_center_local((i, 0)))
                slot = SlotDrag(
                    d=im.Scale(Image("icons/chords_frame.png"), CHORD_SIZE, CHORD_SIZE),
                    index=i + slots/2,
                    pos=slot_pos,
                    anchor=(0.5, 0.5)
                )
                self.chord_slots.append(slot)
                global_slots_list.append((slot, self))
                self.draggroup.add(slot)
                slot.snap(*slot_pos)
            self.add(self.draggroup)
            
            pointer_pos = self.grid.to_global(self.grid.get_cell_center_local((-slots / 2, 1)))
            self.pointer = IslandPointer(
                grid=self.grid,
                left_bound=-slots / 2,
                right_bound=slots / 2 - 1,
                start_cell=self.start_cell_pos,
                d=im.Scale(Image("icons/pointer_orange.png"), CHORD_SIZE*0.8, CHORD_SIZE*0.8),
                pos=pointer_pos,
                anchor=(0.5, 0.5),
                drag_name="pointer"
            )
            self.draggroup.add(self.pointer)

            self.update()

        def add_chord(self, name, slot, drag_pos=None):
            target_pos = self.grid.to_global(self.grid.get_cell_center_local((-self.slots / 2 + slot, 0)))
            if drag_pos is None:
                drag_pos = target_pos
            chord = ChordDrag(name, self.drag_function, self.chord_slots[slot], pos=drag_pos, align=(0.5, 0.5))
            self.chord_slots[slot].attach(chord)
            self.draggroup.add(chord)
            chord.snap(*target_pos, delay=0.1)
            chord.top()
            self.update()
            return chord

        def screen_to_local(self, pos):
            x_offset = renpy.get_adjustment(XScrollValue("play_space")).value
            y_offset = renpy.get_adjustment(YScrollValue("play_space")).value
            return (pos[0] + x_offset, pos[1] + y_offset)

        def get_chords_list(self):
            chords = []
            for slot in self.chord_slots:
                if slot.attached is not None and isinstance(slot.attached, ChordDrag):
                    chords.append(slot.attached.name)
                else:
                    chords.append("Empty")
            return chords


    def library_button_dragged(library, drag, drop):
        def get_distance(slot):
            local_pos = slot[1].screen_to_local((drag[0].x, drag[0].y))
            if abs(local_pos[0] - slot[0].x) < slot[1].grid.cell_width // 2 and \
                abs(local_pos[1] - slot[0].y) < slot[1].grid.cell_height // 2:
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
            renpy.play("audio/sfx/click.mp3")
            chord = nearest[1].add_chord(drag[0].drag_name, nearest[0].index)
            renpy.queue_event("chord_placed")
        drag[0].snap(*library.drags_pos[drag[0]])


    class ChordLibrary(Container):
        def __init__(self, **kwargs):
            super(ChordLibrary, self).__init__(**kwargs)
            self.add(im.Scale(Image("icons/library_back.png"), *LIBRARY_BACKGROUND_SIZE, xalign=1.0))
            button = Fixed(
                xalign=1.0, 
                xoffset=-LIBRARY_BACKGROUND_SIZE[0],
                yoffset=LIBRARY_TOP_OFFSET,
                xysize=renpy.image_size("icons/library_button.png")
            )
            button.add(ImageButton(
                idle_image="icons/library_button.png",
                action=Function(self.toggle)
            ))
            button.add(
                Transform(
                    child=Text(
                        "CHORDS",
                        align=(0, 0.5)
                    ),
                    rotate=-90
                )
            )
            self.add(button)
            self.hidden = True
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
                    chord, renpy.curry(library_button_dragged)(self), None, drag_pos, align=(0.5, 0.5)
                )
                self.drags_pos[drag] = int(drag_pos[0] - 0.5 * CHORD_SIZE), int(drag_pos[1] - 0.5 * CHORD_SIZE)
                self.draggroup.add(drag)
            self.add(self.draggroup)
            self.update()

        def toggle(self):
            global library_xpos
            if self.hidden:
                library_xpos = -LIBRARY_BACKGROUND_SIZE[0]
            else:
                library_xpos = 0
            self.hidden = not self.hidden


    class ProgressGrid(LayoutGrid):
        def __init__(self, **kwargs):
            super(ProgressGrid, self).__init__(**kwargs)
            for chord in HIDDEN_CHORDS:
                self.add(ChordFrame("?", size=130))
            self.chords_status = [False] * len(HIDDEN_CHORDS)

        def reveal_chord(self, index):
            self.children[index].change_name(HIDDEN_CHORDS[index])
            self.chords_status[index] = True
            if all(self.chords_status):
                return True



    def get_quarter_notes_in_bar():
        return 4.0 / TIME_SIGNATURE[1] * TIME_SIGNATURE[0]

    def get_bar_length():
        return 60.0 * 4 * TIME_SIGNATURE[0] / (TEMPO * TIME_SIGNATURE[1])


    def generate_and_play(generators, args, sources, pointer, per_bar_callback, play_stop_callback):
        def run():
            generate_and_play.active = True
            DisalableDrag.disabled = True

            start_cell = pointer.get_cell()[0]
            offset = (start_cell - pointer.start_cell) * get_bar_length()

            def move_pointer():
                for i in range(1, 17 - start_cell):
                    if per_bar_callback(start_cell - pointer.start_cell + i - 1):
                        renpy.queue_event("end_level")
                        return
                    while renpy.music.get_pos(sources[0][1]) < i * get_bar_length() + offset:
                        if not renpy.music.is_playing(sources[0][1]):
                            return
                        time.sleep(0.1)
                    pointer.move_to(start_cell + i)

            threads = []
            q = Queue()
            for generator, arg in zip(generators, args):
                threads.append(Thread(target=lambda gen, arg : q.put(gen(arg)), args=(generator, arg)))
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            generate_and_play.playing = True
            play_stop_callback()
            channels = []
            while not q.empty():
                source = q.get()
                renpy.music.play("<from {0}>{1}".format(offset, source[0]), loop=False, synchro_start=True, channel=source[1])
            for source in sources:
                renpy.music.play("<from {0}>{1}".format(offset, source[0]), loop=False, synchro_start=True, channel=source[1])

            move_pointer()

            pointer.move_to(start_cell)
            play_stop_callback()
            renpy.queue_event("music_stopped")
            DisalableDrag.disabled = False
            generate_and_play.active = False
            generate_and_play.playing = False

            return

        if generate_and_play.active:
            if not generate_and_play.playing:
                renpy.notify("Processing, please wait")
            else:
                renpy.notify("Already playing")
            return
        Thread(target=run).start()

    generate_and_play.active = False
    generate_and_play.playing = False

    def generate_chords(island):
        generator = Generator(TIME_SIGNATURE, TEMPO)
        for pos, chord in enumerate(island.get_chords_list()):
            midi_chord = Chord(*parse_chord(chord))
            for i in range(4):
                generator.add_chord(midi_chord, (pos + float(i) / 4) * get_quarter_notes_in_bar(), get_quarter_notes_in_bar() / 4, 80)
        generator.generate("chords_tmp")
        processed_file = process_vst("mdaPiano.dll", "chords_tmp.midi")
        return "audio/tmp/{0}".format(processed_file), "chords"


    def check_chord(island, progress_grid, index):
        chords = island.get_chords_list()
        if HIDDEN_CHORDS[index] == chords[index]:
            if progress_grid.reveal_chord(index):
                return True


transform library_position(x):
    subpixel True
    linear 0.5 xpos x


screen play_space:
    zorder -100
    key "hide_windows" action NullAction()
    key "end_level" action Jump("after_game")
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
            add Solid("#AAAAAA")
            xalign 0.0
            ysize 150
            xsize 400
            grid 2 1:
                align 0.5, 0.5
                xspacing 60
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/play_button_idle.png", 120, 120)
                    hover im.Scale("icons/play_button_idle.png", 115, 115)
                    selected_idle im.Scale("icons/play_button.png", 120, 120)
                    selected_hover im.Scale("icons/play_button.png", 115, 115)
                    selected generate_and_play.playing
                    action Function(
                        generate_and_play,
                        [generate_chords],
                        [main_island],
                        [("audio/guitar.mp3", "backing_track")],
                        main_island.pointer,
                        renpy.curry(check_chord)(main_island, progress_grid),
                        renpy.restart_interaction
                    )
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/stop_button.png", 120, 120)
                    hover im.Scale("icons/stop_button.png", 115, 115)
                    action [Stop('chords'), Stop('backing_track')]
        fixed:
            add Solid("#AAAAAA")
            xalign 0.0
            ysize 150
            xsize 1920 - 400
            viewport:
                yalign 0.5
                draggable True
                scrollbars "horizontal"
                add progress_grid
    add chord_library at library_position(library_xpos)

screen tutorial(msg, complete_event):
    key complete_event action Return
    key "hide_windows" action NullAction()
    modal is_tutorial_modal
    fixed:
        image "images/backgrounds/menu_background.png"
        align 0, 0
        xysize 0.5, 0.5
        # add Solid("#B87A33", area=(220, 112, 600, 330))
        label msg:
            background Solid("#B87A33", align=(0.5, 0.5))
            xsize 600
            align 0.6, 0.5
            padding 30, 30
            text_style "white_text"
            
    

label disable_vn:
    $ quick_menu = False
    $ renpy.block_rollback()
    return

label enable_vn:
    $ quick_menu = True
    $ renpy.fix_rollback()
    return

label init_ui:
    default global_slots_list = []
    default chord_library = ChordLibrary(xoffset=LIBRARY_BACKGROUND_SIZE[0])
    default main_island = Island(
        ISLAND_WIDTH,
        ISLAND_HEIGHT,
        global_slots_list=global_slots_list,
        pos=(0.5, 0.5),
        slots=16,
        drag_function=chord_block_dragged
    )
    default library_xpos = 0
    default progress_grid = ProgressGrid(rows=1, cols=16, yspacing=10, xspacing=0)
    return

label game:
    scene
    call disable_vn from _call_disable_vn
    call init_ui from _call_init_ui
    show screen play_space
    $ renpy.choice_for_skipping()
    define is_tutorial_modal = True
    call screen tutorial("You’ve received your first task. You have the guitar part and you should write the same piano part. Before you start the task let’s take tutorial. Click to continue!", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("The main field is a place, where the chords should be placed. Chords are stored in the {b}CHORDS{/b} tab.", "dismiss")
    $ chord_library.toggle()
    $ renpy.transition(dissolve)
    $ is_tutorial_modal = False
    call screen tutorial("Try to put any chord on the main field. Drag the chord from library to any free slot.", "chord_placed")
    $ renpy.transition(dissolve)
    $ is_tutorial_modal = False
    call screen tutorial("Every slot represents one bar of the whole track. Now you can try to press play button and you will hear the chord you placed when the track will reach this point.", "music_stopped")
    $ renpy.transition(dissolve)
    $ is_tutorial_modal = True
    call screen tutorial("Near Play and Stop buttons you can see blocks with question marks. At the beginning of the level all of them are closed. To open it make a right chords sequence and listen to it. Correctly chosen chords will be opened.", "dismiss")
    $ renpy.transition(dissolve)
    $ is_tutorial_modal = False
    call screen tutorial("You can listen the track from any point you want by dragging the array beneath the chord blocks from left to right. Try it!", "pointer_moved")
    $ renpy.transition(dissolve)
    $ is_tutorial_modal = True
    call screen tutorial("Now try to reveal all hidden chords. That’s the end of tutorial. Good luck!", "dismiss")
    $ renpy.transition(dissolve)
    $ is_tutorial_modal = False
    $ renpy.pause(hard=True)

label after_game:
    "You finished your task!"
    pause get_bar_length()
    $ renpy.transition(zoomout)
