# The game starts here.

define w = Character(_('Wille, the customer'), color="#fe9601")

init python:
    renpy.music.register_channel("original", "sfx")


label start:
    scene bg room

    stop music fadeout 2.0

    "Nothing changes from day to day."

    "The grey city outside the window, things scattered all over the apartment,
    and a pointless attempt to find something to do in the interval
    between awakening and sleep."

    play sound "audio/sfx/cell-phone-vibrate-1.mp3" loop
    "..."
    play sound "audio/sfx/cell-phone-flip-1.mp3"

    scene bg willie
    w "Hey, David, how're you? I'm glad to hear you still alive.
    Help me out, you're the only one I can turn to."

    w "The album release is in just a hour. They left yesterday to celebrate it,
    having decided they would finish the piano part in the morning, but they got
    down tonight so hard that the pianist broke his arm."

    w "We can't postpone the release in any way. Definitely can't.
    We have already agreed with all music platforms, and they want to launch
    it in Prime time."
    w "If we don't make it, I'm bankrupt!"

    w "David, finish the piano part. I do need your help. The piano part should
    be the same as on the guitar."
    w "The work is simple, but it is necessary to be in time. I pay 1000$.
    OK? Agreed."

    jump game

    return
