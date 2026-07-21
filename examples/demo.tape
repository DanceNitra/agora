# VHS tape — render the second_brain demo to a GIF for the README.
#   1. install vhs once:  go install github.com/charmbracelet/vhs@latest   (or: brew install vhs)
#   2. from the repo root: vhs examples/demo.tape   ->   examples/demo.gif
#   3. reference it in inspeximus/README.md:  ![second_brain demo](../examples/demo.gif)

Output examples/demo.gif

Set Shell "bash"
Set FontSize 17
Set Width 1180
Set Height 820
Set Theme "Catppuccin Mocha"
Set Padding 18
Set TypingSpeed 60ms

Type "python examples/demo.py"
Sleep 600ms
Enter
Sleep 6s
