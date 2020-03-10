init python:
    CHORDS = ["Am", "Bm", "C", "Dm", "Em", "F", "G"]

    LIBRARY_BACKGROUND_SIZE_RAW = renpy.image_size("icons/library_back.png")
    LIBRARY_BACKGROUND_SIZE = LIBRARY_BACKGROUND_SIZE_RAW[0] * 1080 // LIBRARY_BACKGROUND_SIZE_RAW[1], 1080

    def library_chord_dragged():
        print(renpy.get_widget("play_space", "ghost"))
    
    def get_size(d):
        w, h = renpy.render(d, 0, 0, 0, 0).get_size()
        print(w, h)
        return w, h
    

screen chord_frame(name='', im_tag=''):
    tag im_tag
    frame:
        background im.Scale(Image("icons/chords_frame_s.png"), 100, 100)
        xsize 100
        ysize 100
        vbox:
            xalign 0.5
            yalign 0.5
            text "[name]"

screen chord_library:
    zorder 1
    fixed:
        add "icons/library_back.png" xalign 1.0 size LIBRARY_BACKGROUND_SIZE
        vpgrid:
            xanchor 0.5
            xpos 1.0
            yalign 0.2
            spacing 70
            xoffset -LIBRARY_BACKGROUND_SIZE[0] / 2
            mousewheel True
            cols 3
            for i, name in enumerate(CHORDS):
                button:
                    use chord_frame(name)
                    action library_chord_dragged
                
        
                

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
