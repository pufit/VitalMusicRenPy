init python:
    from enum import IntEnum
    from midiutil import MIDIFile
    import os


    class NoteName(IntEnum):
        A = 9
        Bb = 10
        B = 11
        C = 0
        Db = 1
        D = 2
        Eb = 3
        E = 4
        F = 5
        Gb = 6
        G = 7
        Ab = 8

    class Note:
        def get_midi_num(self):
            return self.name + 12 * (self.octave + 2)

        def __init__(self, note_name, octave):
            self.name = note_name
            self.octave = octave

        def __add__(self, midi_num):
            name = NoteName((self.name + midi_num) % 12)
            octave = self.octave + (self.name + midi_num) // 12
            return Note(name, octave)

    def parse_chord(chord, octave=2):
        mode = None
        if chord == "Empty":
            return None, mode
        else:
            root = Note(NoteName[chord[0]], octave)
            if len(chord) == 1:
                mode = "major"
            elif chord[1] == "m":
                mode = "minor"
            return root, mode

    def Chord(root, mode):
        if root == None:
            return []
        notes = [root]
        if mode == "minor":         # Add third
            notes.append(root + 3)
        elif mode == "major":
            notes.append(root + 4)
        notes.append(root + 7)      # Add fifth
        return notes

    class Generator:
        def add_chord(self, notes, time, duration, volume):
            for note in notes:
                self.add_note(note, time, duration, volume)

        def add_note(self, note, time, duration, volume):
            self.file.addNote(
                track=0,
                channel=0,
                pitch=note.get_midi_num(),
                time=time,
                duration=duration,
                volume=volume
            )

        def __init__(self, time_signature, tempo):
            self.file = MIDIFile(file_format=0)
            self.file.addTempo(0, 0, tempo)
            self.file.addTimeSignature(
                track=0,
                time=0,
                numerator=time_signature[0],
                denominator=time_signature[1],
                clocks_per_tick=24,
            )

        def generate(self, file_name):
            with open("{0}/midi/{1}.midi".format(GAME_ROOT, file_name), 'wb') as output_file:
                self.file.writeFile(output_file)


    def cleanup():
        for f in os.listdir("{0}/midi".format(GAME_ROOT)):
            os.remove("{0}/midi/{1}".format(GAME_ROOT, f))