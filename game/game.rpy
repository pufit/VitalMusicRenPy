

init python:
    class DragAndDropManager(object):

        __slots__ = (
            'started',
            'position_start',
            # ...
        )

        def __init__(self):
            pass

screen chord_frame(name=''):
    frame:
        background im.Scale("icons/chords_frame_s.png", 100, 100)
        xsize 100
        ysize 100
        vbox:
            xalign 0.5
            yalign 0.5
            text "[name]"

screen chords_library:

    frame:
        background "icons/library_back.png"
        xsize 0.1
        ysize 1
        xalign 0.9

    draggroup:

        drag:
            drag_name "A"
            use chord_frame('A')
            droppable False
            xpos 100 ypos 100

        drag:
            drag_name "Am"
            use chord_frame('Am')
            droppable False
            xpos 150 ypos 100

        drag:
            drag_name "C"
            use chord_frame('C')
            droppable False
            xpos 450 ypos 140
        drag:
            drag_name "Bm"
            use chord_frame('Bm')
            droppable False
            xpos 0.5 ypos 0.5


label game:
    scene bg game
    hide screen say
    call screen chords_library
    "..."
