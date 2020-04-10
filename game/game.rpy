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

        def get_chords_list(self):
            chords = []
            for slot in self.chord_slots:
                if slot.attached is not None and isinstance(slot.attached, ChordDrag):
                    chords.append(slot.attached.name)
                else:
                    chords.append("Empty")
            return chords

        def generate_audio(self):
            generator = Generator(TIME_SIGNATURE, TEMPO)
            for pos, chord in enumerate(self.get_chords_list()):
                midi_chord = Chord(*parse_chord(chord))
                for i in range(4):
                    generator.add_chord(midi_chord, (pos + float(i) / 4) * get_quarter_notes_in_bar(), get_quarter_notes_in_bar() / 4, 80)
            generator.generate("chords_tmp")
            processed_file = process_vst("mdaPiano.dll", "chords_tmp.midi")
            return "audio/tmp/{0}".format(processed_file), "chords"


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


    def generate_and_play(generators, sources, total_duration, pointer, per_step_callback, step, play_stop_callback):
        def run():
            def start_playback():
                for i in range(1, int(total_duration // step_duration) + 1):
                    if per_step_callback:
                        if per_step_callback(start_cell - pointer.start_cell + i - 1):
                            renpy.queue_event("end_level")
                            return
                    while renpy.music.get_pos("master") < i * step_duration + offset:
                        if not renpy.music.is_playing("master"):
                            return
                        time.sleep(0.1)
                    pointer.move_to(start_cell + i)

            generate_and_play.active = True
            DisalableDrag.disabled = True

            threads = []
            generated = []
            for generator in generators:
                threads.append(Thread(target=lambda gen : generated.append(gen()), args=[generator]))
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            step_duration = get_bar_length() * step
            start_cell = pointer.get_cell()[0]
            offset = (start_cell - pointer.start_cell) * step_duration

            generate_and_play.playing = True
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


    def check_chord(island, progress_grid, index):
        chords = island.get_chords_list()
        if index >= len(chords):
            return
        if HIDDEN_CHORDS[index] == chords[index]:
            if progress_grid.reveal_chord(index):
                return True


    def stop_all_channels():
        renpy.music.stop(channel="chords")
        renpy.music.stop(channel="backing_track")
        renpy.music.stop(channel="melody")
        renpy.music.stop(channel="master")


transform library_position(x):
    subpixel True
    linear 0.5 xpos x


screen level1:
    zorder -100
    key "hide_windows" action NullAction()
    key "end_level" action Jump("after_game")
    viewport id "play_space":
        add Frame("backgrounds/playspace.png", tile=True)
        child_size PLAYSPACE_WIDTH, PLAYSPACE_HEIGHT
        xinitial INITIAL_POS[0]
        yinitial INITIAL_POS[1]
        draggable True
        add chord_island
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
                        generators=[chord_island.generate_audio],
                        sources=[("audio/guitar.mp3", "backing_track")],
                        total_duration=16 * get_bar_length(),
                        pointer=chord_island.pointer,
                        per_step_callback=renpy.curry(check_chord)(chord_island, progress_grid),
                        step=1,
                        play_stop_callback=renpy.restart_interaction
                    )
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/stop_button.png", 120, 120)
                    hover im.Scale("icons/stop_button.png", 115, 115)
                    action Function(stop_all_channels)
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
    default progress_grid = ProgressGrid(rows=1, cols=16, yspacing=10, xspacing=0)
    return

label game:
    scene
    call disable_vn
    call init_level1
    show screen level1
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
    $ renpy.pause(hard=True)

label after_game:
    $ is_tutorial_modal = True
    call screen tutorial("Congratulations!\n You finished your first task!", "dismiss")
    $ stop_all_channels()
    pause 0.5
    call enable_vn from _call_enable_vn
    hide screen level1
    $ renpy.transition(zoomout)
    scene bg willie
    w "David! You have no idea how much you helped out. And my money. These fools who work on my label couldn't have done it in 10 hours."
    w "1000$ is already on your bank account. Please start making music again, there's so much you can do."
    w "Do you remember how Rebecca always said that if even a thousandth part of the World's population had the same talent as you, art would have been the main religion of mankind since ancient times? And I completely agree with her."
    w "Please, don’t waste these money, buy equipment, find an advertiser… There’re so many options."
    w "Now I’m gonna rock out all night! The album's release exceeded all expectations. Check it out, this album will be at the top of the charts in a couple of days."
    w "Remember, I owe you one. I hope I also helped you in some way. Keep in touch, David."
    jump pre_level2


init -1 python:
        

    class NoteSelector(Window):
        def __init__(self, notes, pos, **kwargs):
            super(NoteSelector, self).__init__(style="button", pos=pos, **kwargs)
            self.focusable = True
            self.state_children = { note : im.Scale("images/icons/note_selector/{0}.png".format(i), NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT) for i, note in enumerate(notes) }
            self.state_children[None] = im.Scale("images/icons/note_selector/none.png", NOTE_SELECTOR_WIDTH, NOTE_SELECTOR_HEIGHT)
            self.selected_note = None
            self.notes = notes


        def event(self, ev, x, y, st):
            if x < 0 or y < 0 or x > NOTE_SELECTOR_WIDTH or y > NOTE_SELECTOR_HEIGHT:
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                target = int(y // NOTE_SELECTOR_WIDTH)
                if self.notes[target] == self.selected_note:
                    self.selected_note = None
                else:
                    self.selected_note = self.notes[target]
                renpy.restart_interaction()
            return None
            
        def get_child(self):
            return self.state_children[self.selected_note]

        def visit(self):
            return list(self.state_children.values())

        def get_active_note(self):
            return self.selected_note



    class MelodyIsland(Island):
        def __init__(self, width, height, pos, minimal_note_length, available_notes, bars,  **kwargs):
            super(MelodyIsland, self).__init__(
                width=width,
                height=height,
                pos=pos,
                cell_width=NOTE_SELECTOR_WIDTH,
                cell_height=NOTE_SELECTOR_HEIGHT,
                grid_origin_offset=(0, -int(NOTE_SELECTOR_HEIGHT / 2)),
                **kwargs
            )
            self.minimal_note_length = minimal_note_length
            self.available_notes = available_notes
            self.selectors = []
            for i in range(-int(bars / minimal_note_length) // 2, int(bars / minimal_note_length) // 2):
                selector = NoteSelector(
                        notes=available_notes,
                        pos=self.grid.to_global(self.grid.get_cell_center_local((i, 0))),
                        anchor=(0.5, 0.5)
                    )
                self.add(selector)
                self.selectors.append(selector)
            self.draggroup = DragGroup()
            pointer_pos = self.grid.to_global(self.grid.get_cell_center_local((-int(bars / minimal_note_length) // 2, 1)))
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

        def get_notes_list(self):
            notes = []
            for selector in self.selectors:
                notes.append(selector.get_active_note())
            return notes


        def generate_audio(self):
            generator = Generator(TIME_SIGNATURE, TEMPO)
            for pos, note in enumerate(self.get_notes_list()):
                if note:
                    generator.add_note(
                        Note(
                            note_name=NoteName[note],
                            octave=3
                        ),
                        time=pos * get_quarter_notes_in_bar() * self.minimal_note_length,
                        duration=self.minimal_note_length,
                        volume=80
                    )
            generator.generate("melody_tmp")
            processed_file = process_vst("mdaPiano.dll", "melody_tmp.midi")
            return "audio/tmp/{0}".format(processed_file), "melody"



label init_level2:
    $ melody_island = MelodyIsland(
        3000,
        1000,
        pos=(0.5, 0.5),
        minimal_note_length=0.25,
        available_notes=["A", "B", "C", "D", "E", "F", "G"],
        bars=16
    )
    return


screen level2:
    zorder -100
    key "hide_windows" action NullAction()
    key "end_level" action Jump("after_game")
    viewport id "play_space":
        add Frame("backgrounds/playspace.png", tile=True)
        child_size PLAYSPACE_WIDTH, PLAYSPACE_HEIGHT
        xinitial INITIAL_POS[0]
        yinitial INITIAL_POS[1]
        draggable True
        add melody_island
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
                        generators=[melody_island.generate_audio],
                        sources=[],
                        total_duration=16 * get_bar_length(),
                        pointer=melody_island.pointer,
                        per_step_callback=None,
                        step=melody_island.minimal_note_length,
                        play_stop_callback=renpy.restart_interaction
                    )
                imagebutton:
                    align 0.5, 0.5
                    idle im.Scale("icons/stop_button.png", 120, 120)
                    hover im.Scale("icons/stop_button.png", 115, 115)
                    action Function(stop_all_channels)


label pre_level2:
    scene
    call init_level2
    call disable_vn
    call screen level2