init -2 python:
    def get_audio_file_duration(file):
        renpy.music.play(file, channel="util")
        duration = renpy.music.get_duration(channel="util")
        renpy.music.stop(channel="util")
        return duration
        

    def get_quarter_notes_in_bar():
        return 4.0 / TIME_SIGNATURE[1] * TIME_SIGNATURE[0]

    def get_bar_length():
        return 60.0 * 4 * TIME_SIGNATURE[0] / (TEMPO * TIME_SIGNATURE[1])

    