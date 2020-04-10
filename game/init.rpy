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
    LIBRARY_BACKGROUND_SIZE = LIBRARY_BACKGROUND_SIZE_RAW[0] * config.screen_height // LIBRARY_BACKGROUND_SIZE_RAW[1], config.screen_height - 150

    CHORD_SIZE = 120
    NOTE_SELECTOR_SIZE_RAW = renpy.image_size("icons/note_selector/none.png")
    NOTE_SELECTOR_HEIGHT = 400
    NOTE_SELECTOR_WIDTH = int(NOTE_SELECTOR_SIZE_RAW[0] * (float(NOTE_SELECTOR_HEIGHT) / NOTE_SELECTOR_SIZE_RAW[1]))

    COLUMNS_IN_GRID = 3

    LIBRARY_TOP_OFFSET = 50
    LIBRARY_SPACING = 40

    SNAP_DISTANCE = 100

    # Play space init

    PLAYSPACE_WIDTH = 5000
    PLAYSPACE_HEIGHT = 3000

    BORDER_WIDTH = 0.3
    ISLAND_WIDTH = 16 * CHORD_SIZE + 200
    ISLAND_HEIGHT = 400

    INITIAL_POS = 0.5, 0.45

    # Progress grid init

    HIDDEN_CHORDS = ["Am", "F", "C", "G", "Am", "F", "Em", "G", "Am", "C", "F", "G", "Am", "F", "Em", "C"]

    # Music init

    renpy.music.register_channel('chords')
    renpy.music.register_channel('backing_track')
    renpy.music.register_channel('melody')
    renpy.music.register_channel('master')
    renpy.music.register_channel('util')

    TIME_SIGNATURE = 4, 4
    TEMPO = 90