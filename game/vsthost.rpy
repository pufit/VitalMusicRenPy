init python:
    import os
    import subprocess

    def process_vst(plugin, midi_file=None, audio_file=None, parameters=[]):
        out_file_name = "{0}_{1}.wav".format(midi_file, plugin)
        plugin_root = "{0}/vst".format(GAME_ROOT)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        if midi_file:
            input_arg = "--midi-file", os.path.join(GAME_ROOT, "midi", midi_file)
        else:
            input_arg = "--input", os.path.join(GAME_ROOT, "audio", "tmp", audio_file)
        process = subprocess.Popen(
            [os.path.join(GAME_ROOT, "utils", "mrswatson.exe"),
            input_arg[0], input_arg[1],
            '--plugin', os.path.join(GAME_ROOT, "vst", plugin),
            '--output', os.path.join(GAME_ROOT, "audio", "tmp", out_file_name),
            '--tempo', str(TEMPO),
            '--time-signature', "{0}/{1}".format(TIME_SIGNATURE[0], TIME_SIGNATURE[1]),
            '--quiet'
            ] + parameters,
            startupinfo=startupinfo
        )
        process.wait()
        return out_file_name


    def cleanup():
        for f in os.listdir("{0}/audio/tmp".format(GAME_ROOT)):
            os.remove("{0}/audio/tmp/{1}".format(GAME_ROOT, f))
