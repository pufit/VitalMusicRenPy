init python:
    CHORDS = ["Am", "Bm", "C", "Dm", "Em", "F", "G"]

    LIBRARY_BACKGROUND_SIZE_RAW = renpy.image_size("icons/library_back.png")
    LIBRARY_BACKGROUND_SIZE = LIBRARY_BACKGROUND_SIZE_RAW[0] * config.screen_height // LIBRARY_BACKGROUND_SIZE_RAW[1], config.screen_height

    CHORD_SIZE = 120

    COLUMNS_IN_GRID = 3

    LIBRARY_TOP_OFFSET = 50
    LIBRARY_SPACING = 40

    LIBRARY_SIDE_OFFSET_X = (LIBRARY_BACKGROUND_SIZE[0] - COLUMNS_IN_GRID * CHORD_SIZE - (COLUMNS_IN_GRID - 1) * LIBRARY_SPACING) / 2 

    GRID_POSITIONS = [
            (config.screen_width - LIBRARY_BACKGROUND_SIZE[0] + \
                + (i % COLUMNS_IN_GRID) * (LIBRARY_SPACING + CHORD_SIZE) + LIBRARY_SIDE_OFFSET_X,
            i / COLUMNS_IN_GRID * CHORD_SIZE + i / COLUMNS_IN_GRID * LIBRARY_SPACING) 
            for i in range(len(CHORDS))
        ]

    def library_chord_dragged():
        pass
    
    def get_size(d):
        w, h = renpy.render(d, 0, 0, 0, 0).get_size()
        print(w, h)
        return w, h
    

screen chord_frame(name='', im_tag=''):
    tag im_tag
    frame:
        background im.Scale(Image("icons/chords_frame_s.png"), CHORD_SIZE, CHORD_SIZE)
        xsize CHORD_SIZE
        ysize CHORD_SIZE
        vbox:
            xalign 0.5
            yalign 0.5
            text "[name]"

screen chord_library:
    zorder 1
    fixed:
        align 0, 0
        add "icons/library_back.png" xalign 1.0 size LIBRARY_BACKGROUND_SIZE
        viewport:
            ypos LIBRARY_TOP_OFFSET
            mousewheel True
            child_size 1920, 3000
            draggroup:
                for i, name in enumerate(CHORDS):
                    drag:
                        pos GRID_POSITIONS[i]
                        drag_name "test"
                        use chord_frame("test")
                        droppable False
                        draggable True

                
        
                

screen play_space:
    zorder 0
    key "hide_windows" action NullAction()

    viewport:
        add Frame("bg game.png", tile=True)
        child_size 3000, 3000
        edgescroll 100, 100
        xinitial 0.5
        yinitial 0.5
        draggable True

        draggroup:
            drag:
                drag_name "test"
                use chord_frame("test")
                droppable True
                draggable False
                xpos 0.5 ypos 0.5
            drag:
                use chord_frame("A", "ghost")
                xpos 0.5 ypos 0.5
                xoffset 100

    use chord_library

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
