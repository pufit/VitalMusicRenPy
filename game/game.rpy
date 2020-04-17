init -1 python:

    import math
    import pygame_sdl2 as pygame
    import time
    
    from renpy.audio.audio import get_channel
    from renpy.display.layout import Container, Fixed, MultiBox
    from renpy.display.layout import Grid as LayoutGrid
    from renpy.display.render import render, redraw
    from threading import Thread

    class Island(Container):
        def __init__(self, width, height, pos, cell_width, cell_height, grid_origin_offset, **kwargs):
            super(Island, self).__init__(**kwargs)

            self.width = width
            self.height = height
            self.pos = pos

            self.add(Frame(
                image=Frame(im.FactorScale("backgrounds/background_block.png", BORDER_WIDTH, BORDER_WIDTH), 200, 200),
                xysize=(width, height),
                anchor=(0.5, 0.5),
                pos=pos
            ))

            self.grid = Grid(
                cell_width=cell_width,
                cell_height=cell_height,
                origin_pos=(int(pos[0] * PLAYSPACE_WIDTH + grid_origin_offset[0]), int(pos[1] * PLAYSPACE_HEIGHT + grid_origin_offset[1]))
            )

            self.update()

        def screen_to_local(self, pos):
            x_offset = renpy.get_adjustment(XScrollValue("play_space")).value
            y_offset = renpy.get_adjustment(YScrollValue("play_space")).value
            return (pos[0] + x_offset, pos[1] + y_offset)

        def local_to_screen(self, pos):
            x_offset = renpy.get_adjustment(XScrollValue("play_space")).value
            y_offset = renpy.get_adjustment(YScrollValue("play_space")).value
            return (pos[0] - x_offset, pos[1] - y_offset)


    class HiddenMarker(Container):
        def __init__(self, name, d, **kwargs):
            super(HiddenMarker, self).__init__(**kwargs)
            self.add(d)
            self.text = Text(text=str(name), align=(0.5, 0.5))
            self.add(self.text)
            self.update()

        def change_name(self, name):
            self.text.set_text(name)


    class ChordFrame(HiddenMarker):
        def __init__(self, name, size=CHORD_SIZE, **kwargs):
            super(ChordFrame, self).__init__(
                name=name,
                d=im.Scale(Image("icons/chords_frame.png"), size, size),
                xysize=(size, size),
                **kwargs
            )

    def dropped_to_slot(island, drop, drags):
        island.audio_dirty = True


    class ChordIsland(Island):
        def __init__(self, width, height, pos, slots, drag_function, global_slots_list, **kwargs):
            super(ChordIsland, self).__init__(width, height, pos, CHORD_SIZE, CHORD_SIZE, (0, - CHORD_SIZE // 2), **kwargs)

            self.slots = slots
            self.global_slots_list = global_slots_list

            self.drag_function = renpy.curry(drag_function)(self)
            self.chord_slots = []
            self.draggroup = DragGroup()
            self.start_cell_pos = -slots / 2
            for i in range(self.start_cell_pos, self.start_cell_pos + slots):
                slot_pos = self.grid.to_global(self.grid.get_cell_center_local((i, 0)))
                slot = SlotDrag(
                    d=im.Scale(Image("icons/chords_frame.png"), CHORD_SIZE, CHORD_SIZE),
                    index=i + slots/2,
                    island=self,
                    pos=slot_pos,
                    anchor=(0.5, 0.5)
                )
                self.chord_slots.append(slot)
                global_slots_list.append((slot, self))
                self.draggroup.add(slot)
                slot.snap(*slot_pos)
            self.add(self.draggroup)
            self.audio_dirty = True
            self.last_audio = None
            self.last_start = 0
            
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
            self.audio_dirty = True
            self.update()
            return chord

        def get_nodes_list(self):
            chords = []
            for slot in self.chord_slots:
                if slot.attached is not None and isinstance(slot.attached, ChordDrag):
                    chords.append(slot.attached.name)
                else:
                    chords.append("Empty")
            return chords

        @metrics.measure('chord')
        def generate_audio(self, start=0):
            if self.audio_dirty or self.last_start > start:
                self.last_start = start
                generator = Generator(TIME_SIGNATURE, TEMPO)
                for pos, chord in enumerate(self.get_nodes_list()):
                    midi_chord = Chord(*parse_chord(chord))
                    for i in range(4):
                        generator.add_chord(midi_chord, (pos + float(i) / 4) * get_quarter_notes_in_bar(), get_quarter_notes_in_bar() / 4, 80)
                generator.generate("chords_tmp")
                processed_file = process_vst("mdaPiano.dll", midi_file="chords_tmp.midi")
                self.audio_dirty = False
                self.last_audio = "audio/tmp/{0}".format(processed_file)
            return self.last_audio, "chords"
            


    class ChordLibrary(Container):
        def __init__(self, **kwargs):
            super(ChordLibrary, self).__init__(**kwargs)
            self.add(Frame(im.Scale("icons/library_back.png", *LIBRARY_BACKGROUND_SIZE), 300, 300, xsize=LIBRARY_BACKGROUND_SIZE[0], ysize=LIBRARY_BACKGROUND_SIZE[1] - 150, xalign=1.0))
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
        def __init__(self, hidden_names, marker_type, marker_size, **kwargs):
            super(ProgressGrid, self).__init__(**kwargs)
            self.hidden_names = hidden_names
            self.names_status = [False] * len(hidden_names)
            for i, chord in enumerate(hidden_names):
                if chord:
                    self.add(marker_type("?", marker_size))
                else:
                    self.names_status[i] = True
                    self.add(Null(width=marker_size, height=marker_size))

        def reveal_chord(self, index):
            self.children[index].change_name(self.hidden_names[index])
            self.names_status[index] = True
            if all(self.names_status):
                return True


    class HiddenNote(HiddenMarker):
        def __init__(self, name, size, **kwargs):
            super(HiddenNote, self).__init__(
                name=name,
                d=im.Scale("images/icons/note_marker.png", size, size),
                xysize=(size,size),
                **kwargs
            )


    class NoteSelector(renpy.Displayable):
        disabled = False

        inactive_block = im.Scale("images/icons/note_selector/inactive_block.png", NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT)
        active_block_single = im.Scale("images/icons/note_selector/active_block.png", NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT)
        active_block_left = im.Scale("images/icons/note_selector/active_block_l.png", NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT)
        active_block_right = im.Scale("images/icons/note_selector/active_block_r.png", NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT)
        active_block_middle = im.Scale("images/icons/note_selector/active_block_m.png", NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT)

        def __init__(self, notes, pos, island, left_selector=None, right_selector=None, **kwargs):
            super(NoteSelector, self).__init__(pos=pos, xysize=(NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT * len(notes)), **kwargs)
            self.notes = notes
            self.active_block_index = None
            self.active_block = None
            self.left_selector = left_selector
            self.right_selector = right_selector
            self.island = island

        def update_active_block_state(self):
            has_right_neighbor = False
            has_left_neighbor = False

            if self.right_selector and self.right_selector.active_block_index == self.active_block_index:
                has_right_neighbor = True

            if self.left_selector and self.left_selector.active_block_index == self.active_block_index:
                has_left_neighbor = True

            if has_left_neighbor and has_right_neighbor:
                self.active_block = NoteSelector.active_block_middle
            elif has_left_neighbor:
                self.active_block = NoteSelector.active_block_right
            elif has_right_neighbor:
                self.active_block = NoteSelector.active_block_left
            else:
                self.active_block = NoteSelector.active_block_single

            renpy.redraw(self, 0)

        def render(self, width, height, st, at):
            render = renpy.Render(width, height)
            inactive_render = renpy.Render(width, height / NOTE_SELECTOR_HEIGHT)
            inactive_render.place(NoteSelector.inactive_block)
            for i in range(len(self.notes)):
                if i != self.active_block_index:
                    render.blit(inactive_render, pos=(0, i * NOTE_SELECTOR_HEIGHT))
            if self.active_block_index != None:
                render.place(self.active_block, y=self.active_block_index * NOTE_SELECTOR_HEIGHT)
            return render

        def event(self, ev, x, y, st):
            if x < 0 or y < 0 or x > NOTE_SELECTOR_WIDTH or y > NOTE_SELECTOR_HEIGHT * len(self.notes):
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if NoteSelector.disabled:
                    renpy.notify("Stop music first")
                    return None
                target = int(max(0, y - 5) // NOTE_SELECTOR_HEIGHT)
                if self.active_block_index == target:
                    self.active_block_index = None
                else:
                    self.active_block_index = target
                    self.update_active_block_state()

                if self.right_selector:
                        self.right_selector.update_active_block_state()
                if self.left_selector:
                    self.left_selector.update_active_block_state()

                self.island.audio_dirty = True
                renpy.redraw(self, 0)
            return None

        def get_active_note(self):
            if self.active_block_index != None:
                return self.notes[self.active_block_index]
            else:
                return None


    class MelodyIsland(Island):
        def __init__(self, width, height, pos, minimal_note_length, available_notes, bars, **kwargs):
            super(MelodyIsland, self).__init__(
                width=width,
                height=height,
                pos=pos,
                cell_width=NOTE_SELECTOR_WIDTH,
                cell_height=NOTE_SELECTOR_HEIGHT * len(available_notes),
                grid_origin_offset=(0, -int(NOTE_SELECTOR_HEIGHT * len(available_notes) / 2)),
                **kwargs
            )
            self.minimal_note_length = minimal_note_length
            self.available_notes = available_notes
            self.selectors = []
            self.audio_dirty = True
            self.last_start = 0
            self.last_audio = None
            self.bars = bars
            note_names = VBox(anchor=(0.5, 0.5), pos=self.grid.to_global(self.grid.get_cell_center_local((-int(bars / minimal_note_length) // 2 - 1, 0))))
            for note in available_notes:
                note_name = Container(xysize=(NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT))
                note_name.add(im.Scale("images/icons/sample_block.png", NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT))
                note_name.add(Text(text=note, text_style="white_text", size=NOTE_SELECTOR_HEIGHT - 15, align=(0.5, 0.5)))
                note_names.add(note_name)
            self.add(note_names)
            for i in range(-int(bars / minimal_note_length) // 2, int(bars / minimal_note_length) // 2):
                if not self.selectors:
                    selector = NoteSelector(
                        notes=available_notes,
                        pos=self.grid.to_global(self.grid.get_cell_center_local((i, 0))),
                        anchor=(0.5, 0.5),
                        island=self
                    )
                else:
                    selector = NoteSelector(
                            notes=available_notes,
                            pos=self.grid.to_global(self.grid.get_cell_center_local((i, 0))),
                            anchor=(0.5, 0.5),
                            left_selector=self.selectors[-1],
                            island=self
                        )
                    self.selectors[-1].right_selector=selector
                self.add(selector)
                self.selectors.append(selector)

            self.draggroup = DragGroup()
            pointer_pos = self.grid.to_global(self.grid.get_cell_center_local((-int(bars / minimal_note_length) // 2, 1)))
            pointer_pos = pointer_pos[0], pointer_pos[1] - int(NOTE_SELECTOR_HEIGHT * (len(available_notes) / 2 - 0.5)) 
            self.pointer = IslandPointer(
                grid=self.grid,
                left_bound=-int(bars / minimal_note_length) // 2,
                right_bound=int(bars / minimal_note_length) // 2 - 1,
                start_cell=-int(bars / minimal_note_length) // 2,
                d=im.Scale(Image("icons/note_pointer.png"), 40, 40),
                pos=pointer_pos,
                anchor=(0.5, 0.5),
                drag_name="pointer"
            )
            self.draggroup.add(self.pointer)
            self.add(self.draggroup)
            self.update()

        def get_nodes_list(self, start=0):
            notes = []
            for selector in self.selectors:
                notes.append(selector.get_active_note())
            return notes

        @metrics.measure('melody')
        def generate_audio(self, start=0):
            if self.audio_dirty or self.last_start > start:
                self.last_start = start
                generator = Generator(TIME_SIGNATURE, TEMPO)
                notes_list = self.get_nodes_list(start=start)
                last_note = None
                last_note_duration = None
                last_note_pos = None
                for note_pos, note in list(enumerate(notes_list))[start:]:
                    if note != last_note:
                        if last_note != None:
                            generator.add_note(
                                Note(
                                    note_name=NoteName[last_note],
                                    octave=3 - (1 if last_note == "B" else 0)
                                ),
                                time=last_note_pos * get_quarter_notes_in_bar() * self.minimal_note_length,
                                duration=last_note_duration * get_quarter_notes_in_bar() * self.minimal_note_length,
                                volume=80
                            )
                        last_note = note
                        last_note_duration = 1
                        last_note_pos = note_pos
                    else:
                        if last_note != None:
                            last_note_duration += 1
                if last_note != None:
                    generator.add_note(
                            Note(
                                note_name=NoteName[last_note],
                                octave=2
                            ),
                            time=last_note_pos * get_quarter_notes_in_bar() * self.minimal_note_length,
                            duration=last_note_duration * self.minimal_note_length,
                            volume=100
                        )
                generator.generate("melody_tmp")
                processed_file = process_vst("BJAM 2.dll", midi_file="melody_tmp.midi")
                processed_file = process_vst("Sc32_JykWrakker_Mono.dll", audio_file=processed_file, parameters=AMP_SIM_PARAMETERS)
                self.last_audio = "audio/tmp/{0}".format(processed_file)
                self.audio_dirty = False
            return self.last_audio, "melody"

    def generate_and_play(generators, sources, total_duration, pointer, per_step_callback, step, play_stop_callback, mode=1):
        @metrics.measure('main')
        def run():
            def start_playback():
                renpy.queue_event("music_started")
                for i in range(1, int(total_duration // step_duration) + 1):
                    if per_step_callback and mode == 1:
                        if per_step_callback(start_cell - pointer.start_cell + i - 1):
                            renpy.queue_event("end_level")
                            return
                    while renpy.music.get_pos("master") < i * step_duration + offset:
                        if not renpy.music.is_playing("master"):
                            return
                        time.sleep(0.2)
                    pointer.move_to(start_cell + i)

            generate_and_play.is_active = True
            DisalableDrag.disabled = True
            NoteSelector.disabled = True

            start_cell = pointer.get_cell()[0]

            with metrics.context_measure('generating'):
                threads = []
                generated = []
                for generator in generators:
                    threads.append(Thread(target=lambda gen, offset : generated.append(gen(start=offset)), args=[generator, start_cell - pointer.start_cell]))
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

            step_duration = get_bar_length() * step
            offset = (start_cell - pointer.start_cell) * step_duration

            generate_and_play.play_status = mode
            if play_stop_callback:
                play_stop_callback()
            channels = []
            for source in generated:
                renpy.music.play("<from {0}>{1}".format(offset, source[0]), loop=False, synchro_start=True, channel=source[1])
                channels.append(source[1])
            for source in sources:
                renpy.music.play("<from {0}>{1}".format(offset, source[0]), loop=False, synchro_start=True, channel=source[1])
                channels.append(source[1])
            renpy.music.play("<silence {0} from {1}>".format(total_duration, offset), loop=False, synchro_start=True, channel="master")
            start_playback()

            pointer.move_to(start_cell)
            if play_stop_callback:
                play_stop_callback()
            renpy.queue_event("music_stopped")

            NoteSelector.disabled = False
            DisalableDrag.disabled = False
            generate_and_play.is_active = False
            generate_and_play.play_status = 0

            return

        if generate_and_play.is_active:
            if not generate_and_play.play_status:
                renpy.notify("Processing, please wait")
            else:
                renpy.notify("Already playing")
            return
        Thread(target=run).start()

    generate_and_play.is_active = False
    generate_and_play.play_status = 0


    def check_marker(island, progress_grid, index):
        nodes = island.get_nodes_list()
        if index >= len(nodes):
            return
        if nodes[index] and progress_grid.hidden_names[index] == nodes[index]:
            if progress_grid.reveal_chord(index):
                return True


    def stop_all_channels():
        renpy.music.stop(channel="chords")
        renpy.music.stop(channel="backing_track")
        renpy.music.stop(channel="melody")
        renpy.music.stop(channel="melody_reference")
        renpy.music.stop(channel="master")


transform library_position(x):
    subpixel True
    linear 0.5 xpos x

transform loading_rotate:
    on show:
        rotate 0
        linear 1.0 rotate 360
        repeat

screen waiting_for_end_level():
    zorder -1000
    key "end_level" action Return

screen level1():
    zorder -100
    default is_loading = False
    key "hide_windows" action NullAction()
    key "music_started" action SetScreenVariable("is_loading", False)
    viewport id "play_space":
        add Frame("backgrounds/playspace.png", tile=True)
        child_size PLAYSPACE_WIDTH, PLAYSPACE_HEIGHT
        xinitial INITIAL_POS[0]
        yinitial INITIAL_POS[1]
        draggable True
        add chord_island
    imagebutton:
        align 0.0, 0.0
        idle im.Scale("images/icons/repeat_tutorial.png", 70, 70)
        action Jump("level1_repeat_tutorial")
    showif is_loading:
        image "images/icons/loading.png" at loading_rotate:
            align 0.5, 0.5
    hbox:
        yalign 1.0
        fixed:
            add Frame("images/backgrounds/control_background.png", 50, 50)
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
                    selected generate_and_play.play_status == 1
                    action [Function(
                        generate_and_play,
                        generators=[chord_island.generate_audio],
                        sources=[("audio/guitar.mp3", "backing_track")],
                        total_duration=16 * get_bar_length(),
                        pointer=chord_island.pointer,
                        per_step_callback=renpy.curry(check_marker)(chord_island, progress_grid_level1),
                        step=1,
                        play_stop_callback=renpy.restart_interaction
                    ),
                    SetScreenVariable("is_loading", True)]
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/stop_button.png", 120, 120)
                    hover im.Scale("icons/stop_button.png", 115, 115)
                    action Function(stop_all_channels)
        fixed:
            xalign 1.0
            ysize 150
            xsize 1920 - 400
            viewport:
                yalign 0.5
                draggable True
                scrollbars "horizontal"
                add progress_grid_level1
                    
    add chord_library at library_position(library_xpos)

screen tutorial(msg, complete_event):
    key complete_event action Return
    key "hide_windows" action NullAction()
    modal is_tutorial_modal
    fixed:
        image "images/backgrounds/menu_background.png"
        align 0, 0
        xysize 0.5, 0.5
        label msg:
            background Solid("#B87A33", align=(0.5, 0.5))
            xsize 600
            align 0.6, 0.5
            padding 30, 30
            text_style "white_text"
            
    

label disable_vn:
    $ quick_menu = False
    $ config.rollback_enabled = False
    return

label enable_vn:
    $ quick_menu = True
    $ renpy.block_rollback()
    $ config.rollback_enabled = True
    return

label init_level1:
    default global_slots_list = []
    default chord_library = ChordLibrary(xoffset=LIBRARY_BACKGROUND_SIZE[0])
    default chord_island = ChordIsland(
        ISLAND_WIDTH,
        ISLAND_HEIGHT,
        global_slots_list=global_slots_list,
        pos=(0.5, 0.5),
        slots=16,
        drag_function=chord_block_dragged
    )
    default library_xpos = 0
    default progress_grid_level1 = ProgressGrid(
        rows=1,
        cols=16,
        hidden_names=HIDDEN_CHORDS,
        d=ChordFrame("?", size=130),
        marker_type=ChordFrame,
        marker_size=130,
        yspacing=10,
        xspacing=0
    )
    return

label pre_level1:
    scene
    call disable_vn
    call init_level1
    show screen level1
    jump level1

label level1:
    $ renpy.choice_for_skipping()
    define is_tutorial_modal = True
    call screen tutorial("You’ve received your first task. You have the guitar part and you should write the same piano part. Before you start the task let’s take tutorial. Click to continue!", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("The main field is a place, where the chords should be placed. Chords are stored in the {b}CHORDS{/b} tab.", "dismiss")
    $ renpy.transition(dissolve)
    $ chord_library.toggle()
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
label level1_in_process:
    call screen waiting_for_end_level
    jump post_level1

label level1_repeat_tutorial:
    define is_tutorial_modal = True
    call screen tutorial("You’ve received your first task. You have the guitar part and you should write the same piano part. Before you start the task let’s take tutorial. Click to continue!", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("The main field is a place, where the chords should be placed. Chords are stored in the {b}CHORDS{/b} tab.", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("Every slot represents one bar of the whole track. You can press press play button and you will hear the chord you placed when the track will reach this point.", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("Near Play and Stop buttons you can see blocks with question marks. At the beginning of the level all of them are closed. To open it make a right chords sequence and listen to it. Correctly chosen chords will be opened.", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("You can listen the track from any point you want by dragging the array beneath the chord blocks from left to right.", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("Now try to reveal all hidden chords. That’s the end of tutorial. Good luck!", "dismiss")
    jump level1_in_process

label post_level1:
    $ is_tutorial_modal = True
    call screen tutorial("Congratulations!\n You finished your first task!", "dismiss")
    $ stop_all_channels()
    $ metrics.increment("first_level_pass")
    pause 0.5
    call enable_vn
    hide screen level1
    $ renpy.transition(zoomout)
    scene bg willie
    w "David! You have no idea how much you helped out. And my money. These fools who work on my label couldn't have done it in 10 hours."
    w "1000$ is already on your bank account. Please start making music again, there's so much you can do."
    w "Do you remember how Rebecca always said that if even a thousandth part of the World's population had the same talent as you, art would have been the main religion of mankind since ancient times? And I completely agree with her."
    w "Please, don’t waste these money, buy equipment, find an advertiser… There’re so many options."
    w "Now I’m gonna rock out all night! The album's release exceeded all expectations. Check it out, this album will be at the top of the charts in a couple of days."
    w "Remember, I owe you one. I hope I also helped you in some way. Keep in touch, David."
    d "Willie, you’re an idiot. There’s no place for music in my life and no place for me in music."
    scene black with dissolve
    "Willie’s call aroused in David something long ago forgotten. Sometimes some absolutely new, unknown melodies began to appear in his head. And sometimes,
    but much less often, there was a smile on his face."
    "Parts of the soul, that were dead for a long time, were coming to life again.
    But he didn’t want to see it. It was not so easy to break out the state of a few last years."
    play sound "audio/sfx/cell-phone-vibrate-1.mp3" loop
    d "Not again..."
    play sound "audio/sfx/cell-phone-flip-1.mp3"
    anon "David, good evening! I have a really excellent offer for you. Listen, …"
    d "Who is it? Where did you find my phone number? Willie, if it’s your new joke, it isn’t so funny."
    anon "David, David, listen to me, please! I prefer to remain anonymous, because…"
    d "Any offer isn’t interesting for me. Goodbye."
    anon "David, I know where is Rebecca."
    d "..."
    d "Why I should trust you? It took 3 years and no one could find her. "
    anon "I got really strong contacts. A few days ago I asked to find her number and location. It wasn’t so easy, but they found her."
    anon "David, listen, I understand there’re not so reasons why you should trust me. But think about: if you’ll help me, you’ll receive her number and address."
    anon "Of course, everything can be a lie, but when you’ll receive so great opportunity next time?  Also you’ll earn some money. I think it’ll be not so bad bonus."
    d "Okay. I trust you. What do you want? "
    anon "I glad we found a compromise. So, David, there’s not so easy task for you. Recently one of my agents got an amazing demo of a local band. They plan to drop this single in a few days, and I’m absolutely sure it gonna take the top positions of all charts."
    anon "Your aim is to recover track from demo before they’ll release it. If you’ll finish at time my people will send you Rebecca’s number and address. Also you’ll receive 2000$."
    anon "If you’re worried about the legal component of my offer, I can promise – nobody’ll find you. Of course, you can think that’s a lie, but I assure you – we’ll earn so much money that it’ll cover all expenses with any vessels."
    anon "It’s in our interest to strengthen the contact with you because it’s not the last task for you probably."
    anon "Also you can call to police and tell everything about it. But I don’t advise you to do that. We have our people everywhere, and in police also. We’ll find out that you called them, and the only thing I can wish – hide so well that my guys won’t find you."
    anon "The last option just to reject my offer. Don’t worry, I’ll understand you, and nobody’ll touch you. But, David, I’ll repeat my question: when you’ll receive so great opportunity to find Rebecca next time?"
    anon "So, David, are you in?"
    d "Okay. I’m waiting for a demo."
    jump pre_level2



label init_level2:
    $ TEMPO = 90
    $ TIME_SIGNATURE = 4, 4
    default melody_island = MelodyIsland(
        6000,
        500,
        pos=(0.5, 0.5),
        minimal_note_length=0.125,
        available_notes=list(reversed(["B", "Db", "D", "E", "Gb", "G", "A"])),
        bars=12
    )
    default progress_grid_level2 = ProgressGrid(
        rows=1,
        cols=12*8,
        hidden_names=HIDDEN_NOTES,
        marker_type=HiddenNote,
        marker_size=NOTE_SELECTOR_WIDTH,
        pos=(0.5, 0.43),
        xanchor=0.5
    )
    return


screen level2():
    zorder -100
    default is_loading = False
    key "hide_windows" action NullAction()
    key "music_started" action SetScreenVariable("is_loading", False)
    viewport id "play_space":
        add Frame("backgrounds/playspace.png", tile=True)
        child_size PLAYSPACE_WIDTH, PLAYSPACE_HEIGHT
        xinitial 0.08
        yinitial INITIAL_POS[1]
        draggable True
        add melody_island
        add progress_grid_level2
    imagebutton:
        align 0.0, 0.0
        idle im.Scale("images/icons/repeat_tutorial.png", 70, 70)
        action Jump("level2")
    showif is_loading:
        image "images/icons/loading.png" at loading_rotate:
            align 0.5, 0.5
        
    hbox:
        yalign 1.0
        fixed:
            add Frame("images/backgrounds/control_background.png", 50, 50)
            xalign 0.0
            ysize 150
            xsize 600
            grid 3 1:
                align 0.5, 0.5
                xspacing 60
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/play_button_idle.png", 120, 120)
                    hover im.Scale("icons/play_button_idle.png", 115, 115)
                    selected_idle im.Scale("icons/play_button.png", 120, 120)
                    selected_hover im.Scale("icons/play_button.png", 115, 115)
                    selected generate_and_play.play_status == 1
                    action [Function(
                        generate_and_play,
                        generators=[melody_island.generate_audio],
                        sources=[["audio/level2/backing_track.mp3", "backing_track"]],
                        total_duration=12 * get_bar_length(),
                        pointer=melody_island.pointer,
                        per_step_callback=renpy.curry(check_marker)(melody_island, progress_grid_level2),
                        step=melody_island.minimal_note_length,
                        play_stop_callback=renpy.restart_interaction
                    ),
                    SetScreenVariable("is_loading", True)]
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/play_button_idle_2.png", 120, 120)
                    hover im.Scale("icons/play_button_idle_2.png", 115, 115)
                    selected_idle im.Scale("icons/play_button_2.png", 120, 120)
                    selected_hover im.Scale("icons/play_button_2.png", 115, 115)
                    selected generate_and_play.play_status == 2
                    action Function(
                        generate_and_play,
                        generators=[],
                        sources=[["audio/level2/backing_track.mp3", "backing_track"], ["audio/level2/synth.mp3", "melody_reference"]],
                        total_duration=12 * get_bar_length(),
                        pointer=melody_island.pointer,
                        per_step_callback=None,
                        step=melody_island.minimal_note_length,
                        play_stop_callback=renpy.restart_interaction,
                        mode=2
                    )
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/stop_button.png", 120, 120)
                    hover im.Scale("icons/stop_button.png", 115, 115)
                    action Function(stop_all_channels)
        add Null(width=(1920 - 600 - 600))
        fixed:
            add Frame("images/backgrounds/control_background.png", 50, 50)
            ysize 150
            xsize 600
            grid 7 1:
                align 0.5, 0.5
                for note in ["B", "Db", "D", "E", "Gb", "G", "A"]:
                    fixed:
                        xysize 70, 110
                        add Frame("images/icons/sample_block.png", 2, 2)
                        textbutton note:
                            text_align 0.5, 0.5
                            xysize 70, 110
                            text_style "white_text"
                            action Play(channel="sample_buttons_{0}".format(note), file="audio/notes/{0}.mp3".format(note), loop=False)




label pre_level2:
    scene
    call init_level2
    call disable_vn
    show screen level2
    jump level2

label level2:
    $ is_tutorial_modal = True
    $ renpy.choice_for_skipping()
    call screen tutorial("You were asked to complete your customer's track by adding guitar melody to it. Let's quickly get through the new interface", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("You can see a grid that is the main editor in this level. Each column represents one time unit (actually eighth note if you familiar with it. If not, do not worry, you don't need this knowledge for this task).", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("By pressing at any grid cell you can select which note will be played when the track will reach this column.", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("You can see hidden notes at the top of the grid. Your goal is to reveal them all. You can see new blue button in the control panel. It will play melody that you should reproduce.", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("At the bottom you can see buttons marked with note names. You can press it to check how every note sounds.", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("Tip: use blue play button and try to repeat the melody with the white buttons first. When you think that your melody is close to the original you can check it with the green play button (green play button takes some time to process your melody)", "dismiss")
    $ renpy.transition(dissolve)
    call screen tutorial("Question marks only point the start of each note in melody. You needn't to match exact same length for every note so it's completely up to you. Good luck!", "dismiss")
    call screen waiting_for_end_level
    jump post_level2

label post_level2:
    $ is_tutorial_modal = True
    call screen tutorial("Congratulations!\n Task is completed!", "dismiss")
    $ metrics.increment("second_level_pass" )
    $ stop_all_channels()
    pause 0.5
    call enable_vn
    hide screen level2
    scene bg room
    "This strange man didn’t lie. Rebecca’s address and phone number were received."
    d "It took 3 years. 3 years I tried everything to find her. I asked everyone for help. I begged everyone for help.
    And nobody could help me. Nobody. I talked with anyone who knew her and nobody had any suggestion where is she."
    d "After a year of useless searches I tried to forget her. There’s nothing left remind of her.
    But I didn’t know the main and the biggest reminder is myself. And I couldn’t do with it anything. "
    d "There’s her number. Okay, I’ll call her. It’s not so hard. "
    "..."
    d "Rebecca, hi. It’s David."


    "That is the end of this version. You are breathtaking if you have reached this point! We will continue the story with a bunch of new musical minigames to play in later updates. So stay tuned!"