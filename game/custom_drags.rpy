init -1 python:

    from renpy.display.layout import Container

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

    def chord_block_dragged(island, drag, drop):
        drag[0].slot.attached = None
        if drop:
            renpy.play("audio/sfx/click.mp3")
            drop.attach(drag[0])
            drag[0].snap(drop.x, drop.y)
        else:
            drag[0].remove()

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
        def __init__(self, name, size=CHORD_SIZE, **kwargs):
            super(ChordFrame, self).__init__(xysize=(size, size), **kwargs)
            self.add(im.Scale(Image("icons/chords_frame.png"), size, size))
            self.text = Text(text=str(name), align=(0.5, 0.5))
            self.add(self.text)
            self.update()

        def change_name(self, name):
            self.text.set_text(name)

    def dropped_to_slot(island, drop, drags):
        island.audio_dirty = True

    class SlotDrag(Drag):
        def __init__(self, index, island, pos, **kwargs):
            super(SlotDrag, self).__init__(
                pos=pos,
                drag_name="Slot" + str(index),
                draggable=False,
                droppable=True,
                dropped=renpy.curry(dropped_to_slot)(island),
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
            target_x = self.grid.to_global(self.grid.get_cell_center_local((cell_x, 1)))[0]
            if self.w is None:
                child = self.style.child
                if child is None:
                    child = self.child
                cr = render(child, 200, 200, 0, 0)
                self.w, self.h = cr.get_size()
            target_x -= int(self.w // 2)
            self.snap(target_x, self.y)

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