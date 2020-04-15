init -1000 python:

    import os

    GAME_ROOT = os.path.join(config.basedir, "game")

    config.keymap["end_level"] = []
    config.keymap["chord_placed"] = []
    config.keymap["music_stopped"] = []
    config.keymap["pointer_moved"] = []

    # Library init

    CHORDS = ["Am", "Bm", "C", "Dm", "Em", "F", "G"]

    LIBRARY_BACKGROUND_SIZE_RAW = renpy.image_size("icons/library_back.png")
    LIBRARY_BACKGROUND_SIZE = LIBRARY_BACKGROUND_SIZE_RAW[0] * config.screen_height // LIBRARY_BACKGROUND_SIZE_RAW[1], config.screen_height

    CHORD_SIZE = 120
    NOTE_SELECTOR_SIZE_RAW = renpy.image_size("icons/note_selector/inactive_block.png")
    NOTE_SELECTOR_HEIGHT = 40
    NOTE_SELECTOR_WIDTH = 60

    LIBRARY_TOP_OFFSET = 50
    LIBRARY_SPACING = 40

    # Play space init

    PLAYSPACE_WIDTH = 7000
    PLAYSPACE_HEIGHT = 3000

    BORDER_WIDTH = 0.3
    ISLAND_WIDTH = 16 * CHORD_SIZE + 200
    ISLAND_HEIGHT = 400

    INITIAL_POS = 0.5, 0.45

    # Level 1 progress grid init

    HIDDEN_CHORDS = ["Am", "F", "C", "G", "Am", "F", "Em", "G", "Am", "C", "F", "G", "Am", "F", "Em", "C"]

    # Level 2 progress grid init

    HIDDEN_NOTES = ["B", None, "A", None, "D", "E", "D", "B", None, None, "A", None, "Gb", "E", "D", "B", None, None, "A", None, "D", "E", "D", "E", None, None, "D", None, None, None, None, None,
                    "B", None, "E", None, None, None, "D", None, "B", None, "A", None, None, None, "D", None, "B", None, "E", None, None, None, "D", None, "Gb", None, "E", None, None, None, "D", None,
                    "B", None, "E", None, None, None, "D", None, "B", None, "A", None, None, None, "E", None, "B", None, "Gb", None, "E", None, "D", None, "E", None, "B", None, None, None, None, None]

    # Music init

    renpy.music.register_channel("chords", mixer="music")
    renpy.music.register_channel("backing_track", mixer="music")
    renpy.music.set_volume(0.5, channel="backing_track")
    renpy.music.register_channel("melody", mixer="music")
    renpy.music.register_channel("master", mixer="music")
    renpy.music.register_channel("melody_reference", mixer="music")
    renpy.music.set_volume(1.0, channel="melody_reference")

    TIME_SIGNATURE = 4, 4
    TEMPO = 90

    AMP_SIM_PARAMETERS = [
        "--parameter", "4,0.4", # gain
        "--parameter", "5,1.0", # bright
        "--parameter", "6,0.4", # chanel
        "--parameter", "7,0.395", # bass
        "--parameter", "8,0.55", # mid
        "--parameter", "9,0.46", # treble
        "--parameter", "10,0.395", # presence
        "--parameter", "11,0.395", # contour (?)
        "--parameter", "13,0.0", # filter
    ]